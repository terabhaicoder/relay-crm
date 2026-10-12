#!/usr/bin/env python3
"""Exercise the real HTTP API through the deployed frontend on disposable staging."""

from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener
from uuid import uuid4


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3007")
    parser.add_argument(
        "--allow-create-workspace",
        action="store_true",
        required=True,
        help="Use an isolated staging instance; this creates persisted test records.",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.path
    ):
        parser.error("Use an HTTP(S) origin without credentials or a path.")
    client = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(method: str, path: str, payload=None, raw: bytes | None = None):
        headers = {"Origin": base, "Idempotency-Key": str(uuid4())}
        body = raw
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if raw is not None:
            headers["Content-Type"] = "text/plain"
        request = Request(
            base + "/api/v1" + path, data=body, method=method, headers=headers
        )
        with client.open(request, timeout=30) as response:
            data = response.read()
            if data and "application/json" in response.headers.get("Content-Type", ""):
                return json.loads(data)
            return data

    exercise(call)
    print("HTTP transport through the staging frontend passed.")


def exercise(call) -> None:
    call("GET", "/health/ready")
    suffix = uuid4().hex[:12]
    call(
        "POST",
        "/auth/signup",
        {
            "name": "Staging Verification",
            "company_name": "Explicit QA Workspace " + suffix,
            "email": f"qa-{suffix}@example.test",
            "password": secrets.token_urlsafe(24),
        },
    )
    lead = call(
        "POST",
        "/leads",
        {
            "name": "QA Buyer",
            "company": "QA Company",
            "email": f"buyer-{suffix}@example.test",
            "value": "12345.67",
        },
    )
    conversion = call("POST", f"/leads/{lead['id']}/convert", {"create_deal": True})
    replay = call("POST", f"/leads/{lead['id']}/convert", {"create_deal": True})
    if any(
        conversion[key]["id"] != replay[key]["id"]
        for key in ("contact", "party", "deal")
    ):
        raise ValueError("Repeated conversion returned different record links.")
    deal_id = conversion["deal"]["id"]
    won = call("POST", f"/deals/{deal_id}/won")
    if won["status"] != "won":
        raise ValueError("Deal did not close successfully.")
    task = call("POST", "/activities", {"name": "QA onboarding", "type": "task"})
    if call("POST", f"/activities/{task['id']}/complete")["status"] != "completed":
        raise ValueError("Task did not complete.")
    ticket = call(
        "POST",
        "/tickets",
        {"name": "QA handoff", "description": "Staging acceptance test"},
    )
    call(
        "POST",
        f"/tickets/{ticket['id']}/messages",
        {"body": "QA internal handoff", "internal": True},
    )
    call("PATCH", f"/tickets/{ticket['id']}", {"status": "Resolved"})
    contents = b"Verified staging file\n"
    query = urlencode(
        {"entity_type": "tickets", "entity_id": ticket["id"], "filename": "qa.txt"}
    )
    file = call("POST", "/attachments?" + query, raw=contents)
    if call("GET", f"/attachments/{file['id']}/download") != contents:
        raise ValueError("Downloaded attachment differs from uploaded bytes.")
    call("POST", "/auth/logout")
    try:
        call("GET", "/auth/me")
    except HTTPError as error:
        if error.code != 401:
            raise
    else:
        raise ValueError("Signed-out session still has access.")
    print(
        "CRM journey assertions passed: signup, conversion/replay, deal win, task, support, attachment, logout."
    )
    print(
        "An explicitly named QA workspace was retained in this disposable staging database."
    )


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        raise SystemExit(
            f"HTTP staging journey failed with status {error.code}; inspect server logs without exposing credentials."
        ) from None
    except (URLError, ValueError, KeyError) as error:
        raise SystemExit(f"HTTP staging journey failed: {error}") from None
