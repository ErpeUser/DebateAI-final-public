from app.services.request_guard import (
    host_header_allowed,
    hostname_allowed,
    origin_allowed,
)


def test_localhost_subdomains_are_not_trusted():
    assert hostname_allowed("localhost")
    assert hostname_allowed("127.0.0.1")
    assert not hostname_allowed("evil.localhost")
    assert not origin_allowed("http://evil.localhost")


def test_private_hosts_require_explicit_policy_at_the_origin_boundary():
    assert host_header_allowed("192.168.1.10")
    assert not origin_allowed("http://evil.example")
    assert origin_allowed("http://127.0.0.1:3000")
