"""Client utilities for interacting with the Infosweb Banesco user management API.

The helper functions contained in this module wrap the REST endpoints that were
provided in the Postman collection for obtaining an OAuth token and
activating/deactivating users. The module also exposes a small CLI that can be
used locally or from automation (for example, in Okta Workflows via the Invoke
API) to trigger these operations.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "http://129.80.151.82:8081"
TOKEN_PATH = "/Banesco/integracion/oauth/token"
ACTIVATE_PATH = "/Banesco/integracion/api/v1/usuarios/activar"
DEACTIVATE_PATH = "/Banesco/integracion/api/v1/usuarios/desactivar"

ENV_BASE_URL = "INFOSWEB_BASE_URL"
ENV_CLIENT_ID = "INFOSWEB_CLIENT_ID"
ENV_CLIENT_SECRET = "INFOSWEB_CLIENT_SECRET"


class InfoswebError(RuntimeError):
    """Exception raised when the Infosweb API returns an unexpected response."""

    def __init__(self, status_code: int, payload: Any) -> None:
        message = f"Infosweb API returned status {status_code}: {payload}"
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass
class TokenResponse:
    """Payload returned by the OAuth token endpoint."""

    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    scope: Optional[str] = None

    @staticmethod
    def from_response(data: Dict[str, Any]) -> "TokenResponse":
        try:
            access_token = data["access_token"]
            token_type = data.get("token_type", "Bearer")
        except KeyError as exc:  # defensive: malformed payload
            raise InfoswebError(status_code=200, payload=data) from exc
        return TokenResponse(
            access_token=access_token,
            token_type=token_type,
            expires_in=data.get("expires_in"),
            scope=data.get("scope"),
        )


def _get_base_url(override: Optional[str] = None) -> str:
    return override or os.getenv(ENV_BASE_URL, DEFAULT_BASE_URL)


def request_token(
    *,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 10.0,
) -> TokenResponse:
    """Request a bearer token using the client credentials flow."""

    cid = client_id or os.getenv(ENV_CLIENT_ID)
    csecret = client_secret or os.getenv(ENV_CLIENT_SECRET)
    if not cid or not csecret:
        raise ValueError(
            "Client ID/secret must be provided either via parameters or the "
            f"{ENV_CLIENT_ID}/{ENV_CLIENT_SECRET} environment variables."
        )

    url = f"{_get_base_url(base_url).rstrip('/')}{TOKEN_PATH}"
    response = requests.post(
        url,
        data={"grant_type": "client_credentials"},
        auth=(cid, csecret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )

    if response.status_code != 200:
        raise InfoswebError(response.status_code, _safe_json(response))
    return TokenResponse.from_response(response.json())


def activate_user(
    username: str,
    *,
    access_token: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Activate an Infosweb user by `nombre_usuario`."""

    token = access_token or request_token(
        client_id=client_id, client_secret=client_secret, base_url=base_url, timeout=timeout
    ).access_token
    url = f"{_get_base_url(base_url).rstrip('/')}{ACTIVATE_PATH}"
    payload = {"nombre_usuario": username}
    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if response.status_code != 200:
        raise InfoswebError(response.status_code, _safe_json(response))
    return _safe_json(response)


def deactivate_user(
    username: str,
    *,
    access_token: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Deactivate an Infosweb user by `nombre_usuario`."""

    token = access_token or request_token(
        client_id=client_id, client_secret=client_secret, base_url=base_url, timeout=timeout
    ).access_token
    url = f"{_get_base_url(base_url).rstrip('/')}{DEACTIVATE_PATH}"
    payload = {"nombre_usuario": username}
    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if response.status_code != 200:
        raise InfoswebError(response.status_code, _safe_json(response))
    return _safe_json(response)


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Infosweb API helper CLI")
    parser.add_argument(
        "--base-url",
        default=os.getenv(ENV_BASE_URL, DEFAULT_BASE_URL),
        help="Base URL for the Infosweb API (default from ENV or Postman collection)",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv(ENV_CLIENT_ID),
        help="Client ID for the OAuth token endpoint (overrides environment variable)",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv(ENV_CLIENT_SECRET),
        help="Client secret for the OAuth token endpoint (overrides environment variable)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: 10)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    token_parser = subparsers.add_parser("token", help="Retrieve an access token")
    token_parser.add_argument(
        "--raw",
        action="store_true",
        help="Only print the access token value instead of the full JSON response",
    )

    for action in ("activate", "deactivate"):
        action_parser = subparsers.add_parser(action, help=f"{action.capitalize()} a user")
        action_parser.add_argument("username", help="`nombre_usuario` to process")
        action_parser.add_argument(
            "--access-token",
            help="Existing bearer token to reuse (skips requesting a fresh one)",
        )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "token":
            token_resp = request_token(
                client_id=args.client_id,
                client_secret=args.client_secret,
                base_url=args.base_url,
                timeout=args.timeout,
            )
            if args.raw:
                print(token_resp.access_token)
            else:
                _print_json(token_resp.__dict__)
            return 0

        if args.command == "activate":
            result = activate_user(
                args.username,
                access_token=args.access_token,
                client_id=args.client_id,
                client_secret=args.client_secret,
                base_url=args.base_url,
                timeout=args.timeout,
            )
            _print_json(result)
            return 0

        if args.command == "deactivate":
            result = deactivate_user(
                args.username,
                access_token=args.access_token,
                client_id=args.client_id,
                client_secret=args.client_secret,
                base_url=args.base_url,
                timeout=args.timeout,
            )
            _print_json(result)
            return 0

        parser.error(f"Unhandled command {args.command}")
    except InfoswebError as err:
        sys.stderr.write(str(err) + "\n")
        return 1
    except requests.RequestException as err:
        sys.stderr.write(f"HTTP request failed: {err}\n")
        return 2
    except ValueError as err:
        sys.stderr.write(f"Configuration error: {err}\n")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
