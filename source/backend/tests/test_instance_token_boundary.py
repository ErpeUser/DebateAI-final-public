"""Malformed instance credentials must reject, never crash or use first/last wins."""
import asyncio
import os
import unittest
from unittest.mock import patch
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.services.request_guard import RequestGuardMiddleware

TOKEN = 'test-instance-token'
HEADER = b'x-debateai-instance'


def make_app(guard=True, dependency=False):
    app = FastAPI()
    dependencies = []
    if dependency:
        from app.routers.updates import require_instance_token
        dependencies = [Depends(require_instance_token)]

    @app.api_route('/protected', methods=['GET', 'POST'], dependencies=dependencies)
    def protected():
        return {'protected': True}

    @app.get('/')
    def bootstrap():
        return {'frontend': True}

    if guard:
        app.add_middleware(RequestGuardMiddleware)
    return app


class InstanceTokenBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'DEBATEAI_INSTANCE_TOKEN': TOKEN, 'DEBATEAI_ALLOWED_HOSTS': '', 'DEBATEAI_ALLOWED_ORIGINS': ''})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def request(self, headers, *, method='GET', dependency=False, guard=True):
        with TestClient(make_app(guard, dependency), base_url='http://localhost', raise_server_exceptions=False) as client:
            return client.request(method, '/protected', headers=headers)

    def test_non_ascii_header_rejects_without_server_error(self):
        for method in ('GET', 'POST'):
            with self.subTest(method=method):
                response = self.request([(HEADER, b'\xff')], method=method)
                self.assertEqual(403, response.status_code)
                self.assertNotIn(TOKEN, response.text)

    def test_non_ascii_cookie_rejects_without_server_error(self):
        response = self.request([(b'cookie', b'debateai_instance="\377"')])
        self.assertEqual(403, response.status_code)

    def test_duplicate_instance_headers_never_use_first_value(self):
        for first, second in ((TOKEN, 'wrong'), ('wrong', TOKEN), (TOKEN, TOKEN)):
            with self.subTest(order=(first, second)):
                response = self.request([(HEADER, first.encode()), (HEADER, second.encode())])
                self.assertEqual(403, response.status_code)

    def test_empty_explicit_header_does_not_fall_back_to_valid_cookie(self):
        response = self.request([(HEADER, b''), (b'cookie', ('debateai_instance='+TOKEN).encode())])
        self.assertEqual(403, response.status_code)

    def test_ambiguous_cookie_is_refused(self):
        for cookie in ('debateai_instance=wrong; debateai_instance='+TOKEN, 'debateai_instance='+TOKEN+'; debateai_instance=wrong'):
            with self.subTest(cookie=cookie):
                self.assertEqual(403, self.request([(b'cookie', cookie.encode())]).status_code)

    def test_whitespace_separated_duplicate_cookies_are_refused(self):
        for separator in (" ", "\t", "\r\n"):
            raw = ("debateai_instance=wrong" + separator + "debateai_instance=" + TOKEN).encode()
            with self.subTest(separator=repr(separator)):
                self.assertEqual(403, self.request([(b"cookie", raw)]).status_code)

    def test_split_cookie_headers_cannot_hide_duplicates(self):
        response = self.request([(b'cookie', ('debateai_instance='+TOKEN).encode()), (b'cookie', b'debateai_instance=wrong')])
        self.assertEqual(403, response.status_code)

    def test_valid_single_header_and_cookie_still_authorize(self):
        for headers in ([(HEADER, TOKEN.encode())], [(b'cookie', ('theme=dark; debateai_instance='+TOKEN).encode())]):
            with self.subTest(headers=headers):
                self.assertEqual(200, self.request(headers).status_code)

    def test_valid_header_does_not_bypass_foreign_origin(self):
        response = self.request([(HEADER, TOKEN.encode()), (b'origin', b'https://attacker.example')], method='POST')
        self.assertEqual(403, response.status_code)

    def test_bootstrap_cookie_still_allows_protected_read(self):
        with TestClient(make_app(), base_url='http://localhost') as client:
            response = client.get('/')
            self.assertEqual(200, response.status_code)
            self.assertEqual(TOKEN, response.cookies.get('debateai_instance'))
            self.assertEqual(200, client.get('/protected').status_code)

    def test_update_dependency_non_ascii_rejects_without_guard(self):
        self.assertEqual(403, self.request([(HEADER, b'\xff')], method='POST', dependency=True, guard=False).status_code)

    def test_update_dependency_rejects_duplicate_headers_without_guard(self):
        self.assertEqual(403, self.request([(HEADER, TOKEN.encode()), (HEADER, b'wrong')], method='POST', dependency=True, guard=False).status_code)

    def test_update_dependency_still_requires_header_not_cookie(self):
        self.assertEqual(403, self.request([(b'cookie', ('debateai_instance='+TOKEN).encode())], method='POST', dependency=True, guard=False).status_code)
        self.assertEqual(200, self.request([(HEADER, TOKEN.encode())], method='POST', dependency=True, guard=False).status_code)

    def test_malformed_configured_token_fails_closed(self):
        with patch.dict(os.environ, {'DEBATEAI_INSTANCE_TOKEN': '\u00ff'}):
            self.assertEqual(403, self.request([(HEADER, TOKEN.encode())]).status_code)

    def websocket(self, protocols):
        messages = []
        called = []
        async def downstream(scope, receive, send):
            called.append(True)
            await send({'type': 'websocket.accept'})
        async def receive():
            return {'type': 'websocket.connect'}
        async def send(message):
            messages.append(message)
        scope = {'type': 'websocket', 'path': '/ws/test', 'headers': [(b'host', b'localhost'), *protocols]}
        asyncio.run(RequestGuardMiddleware(downstream)(scope, receive, send))
        return called, messages

    def test_websocket_non_ascii_protocol_closes_without_exception(self):
        called, messages = self.websocket([(b'sec-websocket-protocol', b'debateai.instance.\xff')])
        self.assertFalse(called)
        self.assertEqual('websocket.close', messages[0]['type'])
        self.assertEqual(1008, messages[0]['code'])

    def test_websocket_ambiguous_instance_protocols_are_refused(self):
        for protocols in (
            [(b'sec-websocket-protocol', ('debateai.instance.'+TOKEN+', debateai.instance.wrong').encode())],
            [(b'sec-websocket-protocol', ('debateai.instance.'+TOKEN).encode()), (b'sec-websocket-protocol', b'debateai.instance.wrong')],
        ):
            with self.subTest(protocols=protocols):
                called, messages = self.websocket(protocols)
                self.assertFalse(called)
                self.assertEqual('websocket.close', messages[0]['type'])

    def test_websocket_one_instance_plus_unrelated_protocol_still_works(self):
        called, messages = self.websocket([(b'sec-websocket-protocol', ('chat, debateai.instance.'+TOKEN).encode())])
        self.assertTrue(called)
        self.assertEqual('debateai.instance.'+TOKEN, messages[0]['subprotocol'])


if __name__ == '__main__':
    unittest.main()