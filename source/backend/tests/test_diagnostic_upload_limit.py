import asyncio
import pathlib
import sys
import unittest
from app.services.diagnostic_upload_limit import DiagnosticUploadLimitMiddleware


class UploadLimitTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, chunks, headers=(), path='/api/calibration/asr'):
        messages = []
        reached = []
        async def app(scope, receive, send):
            while True:
                message = await receive()
                reached.append(message.get('body', b''))
                if not message.get('more_body'):
                    break
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})
        queue = list(chunks)
        async def receive():
            body = queue.pop(0)
            return {'type': 'http.request', 'body': body, 'more_body': bool(queue)}
        async def send(message):
            messages.append(message)
        middleware = DiagnosticUploadLimitMiddleware(app, max_bytes=8)
        await middleware({'type': 'http', 'path': path, 'headers': list(headers)}, receive, send)
        return messages[0]['status'], reached

    async def test_chunked_body_is_limited_before_parser(self):
        status, reached = await self.request([b'1234', b'56789'])
        self.assertEqual(status, 413)
        self.assertEqual(reached, [])

    async def test_content_length_oversize_no_parser(self):
        self.assertEqual((await self.request([b''], [(b'content-length', b'9')]))[0], 413)

    async def test_false_content_length_does_not_bypass_count(self):
        self.assertEqual((await self.request([b'123456789'], [(b'content-length', b'1')]))[0], 413)

    async def test_limit_boundary(self):
        self.assertEqual(await self.request([b'1234', b'5678']), (200, [b'12345678']))

    async def test_unrelated_uploads_are_not_changed(self):
        self.assertEqual((await self.request([b'123456789'], path='/api/documents'))[0], 200)

    async def test_legacy_asr_also_protected(self):
        self.assertEqual((await self.request([b'123456789'], path='/api/diagnostics/local-fit/asr'))[0], 413)

    async def test_invalid_length(self):
        self.assertEqual((await self.request([b''], [(b'content-length', b'-1')]))[0], 400)

if __name__ == '__main__':
    unittest.main()
