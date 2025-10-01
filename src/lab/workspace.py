import os
import json
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor
from urllib.error import URLError, HTTPError

from .auth import get_cookie_jar

try:
	import browser_cookie  # type: ignore
except Exception:  # pragma: no cover - optional dependency may be unavailable at import time
	browser_cookie = None  # type: ignore


def _home_dir() -> str:
	home_dir = os.getenv("TFL_HOME_DIR", os.path.join(os.path.expanduser("~"), ".transformerlab"))
	os.makedirs(home_dir, exist_ok=True)
	return home_dir


def _default_workspace_dir() -> str:
	# Backward-compatible env override for tests/deployments
	if "TFL_WORKSPACE_DIR" in os.environ:
		return os.environ["TFL_WORKSPACE_DIR"]
	return os.path.join(_home_dir(), "workspace")


def _api_base_url() -> str:
	# Try to detect Electron app default port; allow override if provided
	return os.getenv("TFL_API_BASE_URL", "http://localhost:8338")


def _load_browser_cookies_for_api() -> object | None:
	"""Attempt to load browser cookies for the API host using browser_cookie.

	Returns a cookie jar suitable for HTTPCookieProcessor, or None if not available.
	"""
	if browser_cookie is None:
		return None
	try:
		# Extract domain from API base URL to filter cookies
		from urllib.parse import urlparse

		parsed = urlparse(_api_base_url())
		domain = parsed.hostname or "localhost"
		# Try Chrome/Chromium family first, then Firefox, then load-all fallback
		for loader in (
			lambda: browser_cookie.chrome(domain_name=domain),
			lambda: browser_cookie.brave(domain_name=domain),
			lambda: browser_cookie.edge(domain_name=domain),
			lambda: browser_cookie.vivaldi(domain_name=domain),
			lambda: browser_cookie.firefox(domain_name=domain),
			lambda: browser_cookie.load(),
		):
			try:
				jar = loader()
				if jar:
					return jar
			except Exception:
				continue
		return None
	except Exception:
		return None


def _current_org_id(timeout_seconds: float = 2.0) -> str | None:
	try:
		api_url = f"{_api_base_url().rstrip('/')}/auth/me"
		req = Request(api_url, headers={"Accept": "application/json"})
		# Prefer in-memory cookies set via lab.set_cookies
		jar = get_cookie_jar()
		if jar is None:
			# Fallback: try loading cookies from the user's browser
			jar = _load_browser_cookies_for_api()  # type: ignore
		if jar is not None:
			opener = build_opener(HTTPCookieProcessor(jar))
			with opener.open(req, timeout=timeout_seconds) as resp:
				data = json.loads(resp.read().decode("utf-8"))
				return data.get("organization_id")
		# No cookies available; best-effort unauthenticated call
		with urlopen(req, timeout=timeout_seconds) as resp:
			data = json.loads(resp.read().decode("utf-8"))
			return data.get("organization_id")
	except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
		return None
	except Exception:
		return None


def get_workspace_dir() -> str:
	"""
	Return the current workspace directory for the logged-in app user.

	Resolves to ~/.transformerlab/orgs/<org_id>/workspace when an org id is present
	in the current session (queried via /auth/me). Falls back to legacy
	~/.transformerlab/workspace or TFL_WORKSPACE_DIR when not authenticated.
	"""
	# Preserve explicit override
	if "TFL_WORKSPACE_DIR" in os.environ:
		return os.environ["TFL_WORKSPACE_DIR"]

	org_id = _current_org_id()
	if org_id:
		return os.path.join(_home_dir(), "orgs", org_id, "workspace")

	# Fallback: pre-login or offline
	return _default_workspace_dir()


