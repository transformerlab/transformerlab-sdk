from __future__ import annotations

from http.cookiejar import Cookie, CookieJar
from typing import Any, Dict, List, Optional

_cookie_jar: Optional[CookieJar] = None
_sealed_session: Optional[str] = None


def _make_cookie(name: str, value: str, domain: str = "localhost", path: str = "/", secure: bool = False) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path=path,
        path_specified=True,
        secure=secure,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def set_cookies(cookies: List[Dict[str, Any]]) -> None:
    """
    Set cookies for SDK HTTP calls. Intended to be called by the host app
    after login, passing browser cookies needed by the API (e.g., session/refresh/org).

    cookies: list of dicts like {"name": str, "value": str, "domain": str, "path": "/", "secure": bool}
    """
    global _cookie_jar
    jar = CookieJar()
    for c in cookies or []:
        name = c.get("name")
        value = c.get("value")
        if not name or value is None:
            continue
        domain = c.get("domain", "localhost")
        path = c.get("path", "/")
        secure = bool(c.get("secure", False))
        jar.set_cookie(_make_cookie(name=name, value=value, domain=domain, path=path, secure=secure))
    _cookie_jar = jar


def get_cookie_jar() -> Optional[CookieJar]:
    return _cookie_jar


def set_sealed_session(token: str | None) -> None:
    global _sealed_session
    _sealed_session = token


def get_sealed_session() -> Optional[str]:
    return _sealed_session


