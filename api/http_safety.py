"""
Outbound URL safety (SSRF mitigation) for scrapers and integrations.
"""

import ipaddress
import os
from urllib.parse import urlparse

_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

ALLOWED_EGRESS_HOSTS = {
    h.strip().lower()
    for h in os.environ.get("ALLOWED_EGRESS_HOSTS", "").split(",")
    if h.strip()
}


def is_safe_egress_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_HOSTS:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass
    if ALLOWED_EGRESS_HOSTS and host not in ALLOWED_EGRESS_HOSTS:
        return False
    return True
