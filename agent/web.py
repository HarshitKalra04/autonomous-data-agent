"""Safe HTTP fetching for the fetch_url tool (standard library only)."""
import ipaddress
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

MAX_BYTES = 2_000_000


class FetchError(Exception):
    """A fetch problem that should be reported back to the LLM as text."""


def _check_url(url: str) -> None:
    """Allow only http(s) URLs that point to the public internet."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("only http and https URLs are allowed")
    if not parsed.hostname:
        raise FetchError("URL has no host name")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port)
    except socket.gaierror:
        raise FetchError(f"could not resolve host '{parsed.hostname}'")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise FetchError("blocked: the address is not on the public internet")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow redirects automatically (each target would need re-checking)."""

    def redirect_request(self, *args, **kwargs):
        return None


def safe_fetch(url: str, timeout: int = 15):
    """Return (status, content_type, body_bytes) or raise FetchError."""
    _check_url(url)
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "autonomous-data-agent/2.0",
            "Accept": "application/json, text/csv, text/plain, */*",
        },
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise FetchError("response is larger than the 2 MB limit; request less data")
            return resp.status, resp.headers.get("Content-Type", "unknown"), body
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            raise FetchError(f"redirected (HTTP {e.code}) to {e.headers.get('Location')}; fetch that URL directly if you trust it")
        raise FetchError(f"HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            raise FetchError(f"request timed out after {timeout}s")
        raise FetchError(f"network error: {e.reason}")
    except TimeoutError:
        raise FetchError(f"request timed out after {timeout}s")
