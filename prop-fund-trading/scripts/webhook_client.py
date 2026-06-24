#!/usr/bin/env python3
"""Zero-dependency client for the Prop Fund public webhook.

Stdlib only (no pip install needed). It reads your own platform session from a
local ``creds.json`` (or PROP_FUND_* env vars) and calls the hosted webhook.

Safety: open/close are DRY-RUN by default; add --live to actually trade.

Examples:
  python webhook_client.py status
  python webhook_client.py accounts
  python webhook_client.py balance --trade-account 1000000000000000001
  python webhook_client.py size --symbol BTCUSDT --margin-usd 50 --leverage 4
  python webhook_client.py open --symbol BTCUSDT --side long --margin-usd 50 \
      --leverage 4 --tp-pct 3 --sl-pct 2            # dry-run preview
  python webhook_client.py open --symbol BTCUSDT --side long --margin-usd 50 \
      --leverage 4 --tp-pct 3 --sl-pct 2 --live     # real order
  python webhook_client.py close --symbol BTCUSDT --live
  python webhook_client.py history --type bills
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

# The shared, hosted webhook (public). Override with --url or PROP_FUND_WEBHOOK_URL.
DEFAULT_URL = "https://prop-fund-ai-trading-skill-production.up.railway.app/webhook"

# Param fields each action accepts (CLI dashes -> argparse underscores).
ACTION_PARAMS = {
    "status": ["trade_account"],
    "accounts": [],
    "profile": [],
    "overview": ["challenge_id"],
    "balance": ["trade_account"],
    "positions": ["trade_account"],
    "size": ["symbol", "margin_usd", "notional_usd", "account_pct", "leverage", "trade_account"],
    "open": ["symbol", "side", "quantity", "margin_usd", "notional_usd", "account_pct",
             "leverage", "tp", "sl", "tp_pct", "sl_pct", "trade_account"],
    "close": ["symbol", "trade_account", "quantity", "position_id"],
    "history": ["type", "page", "rows", "trade_account"],
    "check_affiliation": ["challenge_id", "order_number"],
}


def load_creds() -> dict:
    """Load the caller's session from creds.json or PROP_FUND_* env vars."""

    # Only x_authorization (the Admin-Token) is required. cookie/did are legacy
    # and optional - the server derives `did` and doesn't need the cookie.
    keys = ("x_authorization", "trade_account", "cookie", "did")
    candidates = []
    if os.environ.get("PROP_FUND_CREDS"):
        candidates.append(Path(os.environ["PROP_FUND_CREDS"]))
    skill_dir = Path(__file__).resolve().parent.parent
    candidates += [skill_dir / "creds.json", Path.cwd() / "creds.json"]
    data = None
    for p in candidates:
        if p and p.is_file():
            data = json.loads(p.read_text())
            break
    if data is None and os.environ.get("PROP_FUND_X_AUTHORIZATION"):
        data = {k: os.environ.get("PROP_FUND_" + k.upper(), "") for k in keys}
    if data is None or not data.get("x_authorization"):
        raise SystemExit(
            "No token found.\n"
            "Put your Admin-Token in creds.json as x_authorization (copy "
            "creds.example.json), or set PROP_FUND_X_AUTHORIZATION.\n"
            "See onboarding.md: log in, open the browser console, run "
            'copy(localStorage.getItem("Admin-Token")).'
        )
    return {k: data.get(k, "") for k in keys}


def post(action: str, params: dict, creds: dict, url: str, api_key: str | None) -> dict:
    body = json.dumps({"action": action, "credentials": creds, "params": params}).encode()
    headers = {"content-type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:300]
        return {"ok": False, "error_type": "http", "error": f"HTTP {exc.code}", "detail": detail}
    except Exception as exc:  # network / timeout
        return {"ok": False, "error_type": "network", "error": str(exc)}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="webhook_client.py", description="Prop Fund webhook client.")
    p.add_argument("--url", default=os.environ.get("PROP_FUND_WEBHOOK_URL", DEFAULT_URL))
    p.add_argument("--api-key", default=os.environ.get("PROP_FUND_WEBHOOK_API_KEY"),
                   help="Only needed if the webhook is not public.")
    sub = p.add_subparsers(dest="action", required=True)

    for name in ("status", "accounts", "profile", "balance", "positions"):
        sp = sub.add_parser(name)
        if name != "accounts" and name != "profile":
            sp.add_argument("--trade-account", dest="trade_account", default=None)

    ov = sub.add_parser("overview"); ov.add_argument("--challenge-id", dest="challenge_id", required=True)

    sz = sub.add_parser("size")
    sz.add_argument("--symbol", required=True)
    sz.add_argument("--margin-usd", dest="margin_usd", type=float)
    sz.add_argument("--notional-usd", dest="notional_usd", type=float)
    sz.add_argument("--account-pct", dest="account_pct", type=float)
    sz.add_argument("--leverage", type=float)
    sz.add_argument("--trade-account", dest="trade_account", default=None)

    op = sub.add_parser("open")
    op.add_argument("--symbol", required=True)
    op.add_argument("--side", required=True, choices=["long", "short"])
    op.add_argument("--quantity", type=float)
    op.add_argument("--margin-usd", dest="margin_usd", type=float)
    op.add_argument("--notional-usd", dest="notional_usd", type=float)
    op.add_argument("--account-pct", dest="account_pct", type=float)
    op.add_argument("--leverage", type=float)
    op.add_argument("--tp", type=float)
    op.add_argument("--sl", type=float)
    op.add_argument("--tp-pct", dest="tp_pct", type=float)
    op.add_argument("--sl-pct", dest="sl_pct", type=float)
    op.add_argument("--trade-account", dest="trade_account", default=None)
    op.add_argument("--live", action="store_true")

    cl = sub.add_parser("close")
    cl.add_argument("--symbol", required=True)
    cl.add_argument("--trade-account", dest="trade_account", default=None)
    cl.add_argument("--quantity", type=float)
    cl.add_argument("--position-id", dest="position_id", default=None)
    cl.add_argument("--live", action="store_true")

    hi = sub.add_parser("history")
    hi.add_argument("--type", default="bills", choices=["bills", "orders", "done", "finish"])
    hi.add_argument("--page", type=int, default=1)
    hi.add_argument("--rows", type=int, default=20)
    hi.add_argument("--trade-account", dest="trade_account", default=None)

    ca = sub.add_parser("check_affiliation", help="Is a challenge id one of our affiliate orders?")
    ca.add_argument("--challenge-id", dest="challenge_id")
    ca.add_argument("--order-number", dest="order_number")

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    # check_affiliation queries our own DB; it needs no per-user token.
    creds = {} if args.action == "check_affiliation" else load_creds()

    params = {}
    for field in ACTION_PARAMS.get(args.action, []):
        val = getattr(args, field, None)
        if val is not None:
            params[field] = val
    if getattr(args, "live", False):
        params["live"] = True

    resp = post(args.action, params, creds, args.url, args.api_key)
    print(json.dumps(resp, indent=2))
    return 0 if resp.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
