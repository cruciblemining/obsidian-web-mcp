"""Tests for the OAuth client-authentication hardening.

Exercises the /authorize and /oauth/token endpoints via a minimal
Starlette app so we cover the HTTP-visible behavior (status codes,
error bodies) rather than poking private helpers only.
"""

import base64
import hashlib
import secrets

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient


ENV_CLIENT_ID = "test-env-client"
ENV_CLIENT_SECRET = "env-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
REGISTERED_CLIENT_ID = "vault-mcp-registered-fixture"
REGISTERED_CLIENT_SECRET = "registered-secret-yyyyyyyyyyyyyyyyyyyyyyyyyyy"


@pytest.fixture
def oauth_client(monkeypatch, tmp_path):
    """Mount oauth_routes on a bare Starlette app and hand back a TestClient.

    Swaps in a temp path for the persisted-clients file and seeds the
    in-memory registry with a known registered client. Env-configured
    client is pre-seeded via monkeypatched config attributes.
    """
    monkeypatch.setenv("VAULT_MCP_TOKEN", "test-token")
    monkeypatch.setenv("VAULT_OAUTH_CLIENT_ID", ENV_CLIENT_ID)
    monkeypatch.setenv("VAULT_OAUTH_CLIENT_SECRET", ENV_CLIENT_SECRET)

    from obsidian_vault_mcp import config, oauth

    monkeypatch.setattr(config, "VAULT_MCP_TOKEN", "test-token")
    monkeypatch.setattr(config, "VAULT_OAUTH_CLIENT_ID", ENV_CLIENT_ID)
    monkeypatch.setattr(config, "VAULT_OAUTH_CLIENT_SECRET", ENV_CLIENT_SECRET)

    clients_file = tmp_path / ".oauth_clients.json"
    monkeypatch.setattr(oauth, "_CLIENTS_FILE", clients_file)
    monkeypatch.setattr(
        oauth,
        "_registered_clients",
        {
            REGISTERED_CLIENT_ID: {
                "client_secret": REGISTERED_CLIENT_SECRET,
                "client_name": "fixture",
                "redirect_uris": [],
                "created_at": 0,
            }
        },
    )
    monkeypatch.setattr(oauth, "_auth_codes", {})

    app = Starlette(routes=oauth.oauth_routes)
    return TestClient(app)


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _authorize(client, client_id, *, code_challenge=None, code_challenge_method="S256"):
    verifier, challenge = _pkce_pair()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": "https://example.test/cb",
    }
    if code_challenge is None:
        params["code_challenge"] = challenge
    elif code_challenge != "":
        params["code_challenge"] = code_challenge
    params["code_challenge_method"] = code_challenge_method
    return client.get("/oauth/authorize", params=params, follow_redirects=False), verifier


# --- /authorize client-id validation --------------------------------------

def test_authorize_rejects_unknown_client_id(oauth_client):
    resp, _ = _authorize(oauth_client, "totally-made-up-client")
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_client"


def test_authorize_accepts_env_configured_client(oauth_client):
    resp, _ = _authorize(oauth_client, ENV_CLIENT_ID)
    assert resp.status_code == 302
    assert "code=" in resp.headers["location"]


def test_authorize_accepts_registered_client(oauth_client):
    resp, _ = _authorize(oauth_client, REGISTERED_CLIENT_ID)
    assert resp.status_code == 302
    assert "code=" in resp.headers["location"]


# --- /authorize PKCE enforcement ------------------------------------------

def test_authorize_requires_pkce_challenge(oauth_client):
    resp, _ = _authorize(oauth_client, ENV_CLIENT_ID, code_challenge="")
    assert resp.status_code == 400
    assert resp.json()["error_description"] == "code_challenge required"


def test_authorize_rejects_non_s256_challenge_method(oauth_client):
    resp, _ = _authorize(
        oauth_client,
        ENV_CLIENT_ID,
        code_challenge_method="plain",
    )
    assert resp.status_code == 400
    assert "S256" in resp.json()["error_description"]


# --- /token authorization_code client auth ---------------------------------

def _complete_authorize(client, client_id):
    resp, verifier = _authorize(client, client_id)
    assert resp.status_code == 302, resp.text
    # Extract code from Location: https://example.test/cb?code=...
    from urllib.parse import urlparse, parse_qs
    code = parse_qs(urlparse(resp.headers["location"]).query)["code"][0]
    return code, verifier


def test_token_rejects_missing_client_credentials(oauth_client):
    code, verifier = _complete_authorize(oauth_client, ENV_CLIENT_ID)
    resp = oauth_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://example.test/cb",
            "code_verifier": verifier,
            # client_id / client_secret missing
        },
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_client"


def test_token_rejects_wrong_client_secret(oauth_client):
    code, verifier = _complete_authorize(oauth_client, ENV_CLIENT_ID)
    resp = oauth_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://example.test/cb",
            "code_verifier": verifier,
            "client_id": ENV_CLIENT_ID,
            "client_secret": "wrong-secret",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_client"


def test_token_accepts_env_client_credentials(oauth_client):
    code, verifier = _complete_authorize(oauth_client, ENV_CLIENT_ID)
    resp = oauth_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://example.test/cb",
            "code_verifier": verifier,
            "client_id": ENV_CLIENT_ID,
            "client_secret": ENV_CLIENT_SECRET,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "test-token"
    assert body["token_type"] == "bearer"


def test_token_accepts_registered_client_credentials(oauth_client):
    code, verifier = _complete_authorize(oauth_client, REGISTERED_CLIENT_ID)
    resp = oauth_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://example.test/cb",
            "code_verifier": verifier,
            "client_id": REGISTERED_CLIENT_ID,
            "client_secret": REGISTERED_CLIENT_SECRET,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "test-token"


def test_token_client_credentials_grant_rejects_unknown(oauth_client):
    resp = oauth_client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "nope",
            "client_secret": "nope",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_client"


def test_token_client_credentials_grant_accepts_registered(oauth_client):
    resp = oauth_client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": REGISTERED_CLIENT_ID,
            "client_secret": REGISTERED_CLIENT_SECRET,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "test-token"
