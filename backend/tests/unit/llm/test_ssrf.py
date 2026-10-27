"""SSRF validator for provider base URLs. DNS is faked; no network."""

import socket
from typing import Any

import pytest

from app.llm.ssrf import UnsafeURLError, validate_base_url


def fake_dns(monkeypatch: pytest.MonkeyPatch, *ips: str) -> None:
    def resolve(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        if not ips:
            raise socket.gaierror("no such host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)


def test_public_https_url_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dns(monkeypatch, "160.79.104.10")
    url = "https://api.anthropic.com"
    assert validate_base_url(url, kind="anthropic") == url


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.3.4",
        "192.168.1.1",
        "169.254.169.254",  # AWS/GCP/Azure metadata
        "100.100.100.200",  # Alibaba metadata (CGNAT)
        "0.0.0.0",
        "::1",
        "fd00:ec2::254",  # AWS IPv6 metadata
        "fe80::1",
        "::ffff:127.0.0.1",
        "64:ff9b::7f00:1",  # NAT64 loopback
        "64:ff9b::a9fe:a9fe",  # NAT64 metadata
        "::7f00:1",  # IPv4-compatible loopback
        "224.0.0.1",
    ],
)
def test_private_loopback_and_metadata_rejected(
    monkeypatch: pytest.MonkeyPatch, ip: str
) -> None:
    fake_dns(monkeypatch, ip)
    with pytest.raises(UnsafeURLError):
        validate_base_url("https://llm.example.org", kind="openai_compatible")


def test_nat64_of_public_ipv4_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dns(monkeypatch, "64:ff9b::808:808")
    assert validate_base_url("https://llm.example.org", kind="anthropic")


def test_any_private_answer_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dns(monkeypatch, "8.8.8.8", "10.0.0.1")
    with pytest.raises(UnsafeURLError):
        validate_base_url("https://llm.example.org", kind="anthropic")


def test_unresolvable_host_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dns(monkeypatch)
    with pytest.raises(UnsafeURLError):
        validate_base_url("https://nope.invalid", kind="anthropic")


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.org",
        "ftp://api.example.org",
        "https://",
        "https://user:pw@api.example.org",
    ],
)
def test_non_https_or_credentialed_url_rejected(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    fake_dns(monkeypatch, "8.8.8.8")
    with pytest.raises(UnsafeURLError):
        validate_base_url(url, kind="openai_compatible")


def test_mock_kind_skips_network_checks() -> None:
    assert validate_base_url("mock://local", kind="mock") == "mock://local"


def test_empty_dns_answer_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [])
    with pytest.raises(UnsafeURLError):
        validate_base_url("https://llm.example.org", kind="anthropic")
