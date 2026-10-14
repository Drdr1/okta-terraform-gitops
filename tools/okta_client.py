"""Small read-only Okta Management API client.

Auth, in order of preference:
  1. OAuth 2.0 client credentials with private_key_jwt (OKTA_API_CLIENT_ID,
     OKTA_API_PRIVATE_KEY, OKTA_API_PRIVATE_KEY_ID, OKTA_API_SCOPES) - the
     same service app and env vars the Terraform provider uses.
  2. OKTA_API_TOKEN (SSWS) - only for a quick local look at a sandbox.

Only GET is implemented on purpose: discovery must never change the org.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Iterator
from urllib.parse import urlparse

import jwt  # PyJWT
import requests

DEFAULT_READ_SCOPES = (
    "okta.groups.read okta.apps.read okta.policies.read "
    "okta.networkZones.read okta.authorizationServers.read okta.idps.read"
)


def org_url() -> str:
    name = os.environ["OKTA_ORG_NAME"]
    base = os.environ.get("OKTA_BASE_URL", "okta.com")
    return f"https://{name}.{base}"


def next_link(link_header: str | None) -> str | None:
    """Return the rel="next" URL from an Okta Link header, if any."""
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.split(";")
        if len(section) < 2:
            continue
        url = section[0].strip().strip("<>")
        if any(s.strip() == 'rel="next"' for s in section[1:]):
            return url
    return None


class OktaClient:
    def __init__(self, base_url: str | None = None, session: requests.Session | None = None):
        self.base_url = (base_url or org_url()).rstrip("/")
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expiry = 0.0

    # --- auth -----------------------------------------------------------
    def _auth_header(self) -> dict[str, str]:
        if os.environ.get("OKTA_API_CLIENT_ID"):
            if not self._token or time.time() > self._token_expiry - 60:
                self._fetch_oauth_token()
            return {"Authorization": f"Bearer {self._token}"}
        token = os.environ.get("OKTA_API_TOKEN")
        if token:
            return {"Authorization": f"SSWS {token}"}
        raise SystemExit("Set OKTA_API_CLIENT_ID + private key, or OKTA_API_TOKEN.")

    def _fetch_oauth_token(self) -> None:
        client_id = os.environ["OKTA_API_CLIENT_ID"]
        key = os.environ["OKTA_API_PRIVATE_KEY"]
        if os.path.isfile(key):
            with open(key, encoding="utf-8") as fh:
                key = fh.read()
        scopes = os.environ.get("OKTA_API_SCOPES", DEFAULT_READ_SCOPES).replace(",", " ")
        token_url = f"{self.base_url}/oauth2/v1/token"
        now = int(time.time())
        kid = os.environ.get("OKTA_API_PRIVATE_KEY_ID")
        assertion = jwt.encode(
            {"iss": client_id, "sub": client_id, "aud": token_url,
             "iat": now, "exp": now + 300, "jti": str(uuid.uuid4())},
            key,
            algorithm="RS256",
            headers={"kid": kid} if kid else None,
        )
        resp = self.session.post(token_url, data={
            "grant_type": "client_credentials",
            "scope": scopes,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        }, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + int(body.get("expires_in", 3600))

    # --- reads ----------------------------------------------------------
    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        for _ in range(5):
            resp = self.session.get(url, params=params, headers=self._auth_header(), timeout=60)
            if resp.status_code == 429:
                reset = int(resp.headers.get("X-Rate-Limit-Reset", time.time() + 5))
                time.sleep(max(1, reset - int(time.time()) + 1))
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError(f"Rate limited too many times on {url}")

    def list(self, path: str, params: dict | None = None) -> Iterator[dict]:
        """Yield every item of a paginated collection."""
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        self._check_same_origin(url)
        while url:
            resp = self._get(url, params)
            yield from resp.json()
            url = next_link(resp.headers.get("Link"))
            params = None  # the next link already carries the cursor
            if url:
                self._check_same_origin(url)

    def _check_same_origin(self, url: str) -> None:
        """The bearer token must only ever go to the org, over https."""
        u, base = urlparse(url), urlparse(self.base_url)
        if u.scheme != "https" or u.netloc != base.netloc:
            raise ValueError(f"Refusing to send credentials to {url}")
