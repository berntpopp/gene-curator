"""SSRF guard for admin-configured provider base URLs."""

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    """The base URL is not allowed as an outbound LLM endpoint."""


_EMBEDDED_V4 = (
    ipaddress.IPv6Network("64:ff9b::/96"),  # NAT64
    ipaddress.IPv6Network("::/96"),  # IPv4-compatible
)


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        elif any(ip in net for net in _EMBEDDED_V4):
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    # is_global excludes loopback, private, link-local (169.254.169.254 metadata),
    # CGNAT (100.100.100.200 metadata), ULA (fd00:ec2::254 metadata) and reserved.
    return ip.is_global and not ip.is_multicast


def validate_base_url(url: str, *, kind: str) -> str:
    """Return url if every resolved address is public; raise UnsafeURLError otherwise.

    ponytail: checked at save and client construction; httpx resolves again per
    request, so a DNS-rebinding window remains. Pin the resolved IP if that matters.
    """
    if kind == "mock":
        return url  # MockProvider never opens a connection
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise UnsafeURLError("Provider base URL must be an https URL with a host")
    if parts.username or parts.password:
        raise UnsafeURLError("Provider base URL must not embed credentials")
    try:
        infos = socket.getaddrinfo(
            parts.hostname, parts.port or 443, type=socket.SOCK_STREAM
        )
    except (OSError, UnicodeError, ValueError):
        raise UnsafeURLError("Provider host does not resolve") from None
    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise UnsafeURLError("Provider host does not resolve")
    for address in addresses:
        if not _is_public(ipaddress.ip_address(str(address).split("%")[0])):
            raise UnsafeURLError("Provider host resolves to a non-public address")
    return url
