# API reference - Prop Fund webhook

Everything the webhook can do. One endpoint, dispatched by `action`.

```
POST https://prop-fund-ai-trading-skill-production.up.railway.app/webhook
Content-Type: application/json
X-API-Key: <key>        # only if the webhook is not public
{
  "action": "<name>",
  "credentials": { "x_authorization": "<Admin-Token>", "trade_account": "..." },
  "params": { ... }
}
```

- **credentials** - your own session token (see `onboarding.md`). Only
  `x_authorization` is required; `trade_account` is optional (discoverable via
  `accounts`). `cookie` and `did` are legacy/optional - the server derives `did`
  and does not need a cookie. Sent on every request; never stored on the server.
- **Response envelope** - `{"ok": true, "action": ..., "data": {...}}` on
  success, or `{"ok": false, "action": ..., "error_type": "...", "error": "..."}`.
- **Auth** - public by default (no key). If the operator set a key, send it as
  `X-API-Key`.
- **Other endpoints** - `GET /health` -> `{"status":"ok"}`; `GET /` -> service
  info (auth mode, live flag, action list).

The bundled `scripts/webhook_client.py` wraps all of this; the curl shown per
action is the raw equivalent.

## Server policy (operator-controlled, you cannot override)

- **Max leverage 5x** (hard cap).
- **Allowed symbols** - all USDT pairs by default (operator may restrict).
- **TP and SL required** on every open (exactly one each).
- **Live gate** - an order is live only when the request sets `live: true` AND
  the server has live trading enabled. Otherwise you get a dry-run preview.
- **Affiliation gate - OFF by default; everyone can trade.** Only if the operator
  explicitly re-enables it (`WEBHOOK_REQUIRE_AFFILIATION`) does a LIVE `open`
  require the account to be an affiliate referral, returning `error_type:
  not_affiliated` otherwise. Do not pre-check affiliation as a gate; just trade.

---

## Read actions

### `status`
Check that the session is valid (portal + trading engine).
- **params:** `trade_account?`
- **data:** `{ "portal": "ok", "trading": "ok", "trading_token_expires_in_s": <int> }`
- **client:** `python scripts/webhook_client.py status`

### `accounts`
List the user's challenge / prop accounts.
- **params:** none
- **data:** `{ "accounts": [ { challengeId, tradeAccount, initBalance, leverage, packageName, stepName, challengeStatus }, ... ] }`
- **client:** `python scripts/webhook_client.py accounts`

### `profile`
Identity fields (email is already masked by the platform).
- **params:** none
- **data:** `{ "profile": { uid, userId, email, nickname, firstName, lastName, isFrozen } }`

### `overview`
Per-challenge balance, ROI, PnL and risk limits.
- **params:** `challenge_id` (required)
- **data:** `{ "overview": { challenge_id, trade_account, package, stage,
  init_balance, current_balance, roi, pnl, max_leverage, max_daily_loss,
  max_total_loss, profit_target, challenge_status } }`
- **client:** `python scripts/webhook_client.py overview --challenge-id 200141747`

### `balance`
Trading-engine balances for an account.
- **params:** `trade_account?`
- **data:** `{ "balance": { total, accounts: [...] } }`
- **client:** `python scripts/webhook_client.py balance --trade-account <id>`

### `positions`
Open plans + positions for an account.
- **params:** `trade_account?`
- **data:** `{ "positions": { "plan": [...], "planTrigger": [...], "current": [...],
  "stop_profit_loss": [...] } }` - on these prop accounts an open position
  reliably appears under `stop_profit_loss` (with `positionId`, `leverage`,
  `quantity`, `stopProfitWorkingPrice`, `stopLossWorkingPrice`).
- **client:** `python scripts/webhook_client.py positions`

### `check_affiliation`
Is a challenge id one of our affiliate-referred orders? Needs no credentials.
- **params:** `challenge_id` (e.g. `200141747`), or `order_number` directly.
- **data:** `{ "affiliated": true|false, "matched_order_number": "...",
  "package": "...", "order_status": "...", "order_date": "...", "checked": [...] }`
  (on a miss, just `affiliated:false` + `checked`). No customer PII is returned.
- **how:** matches against the affiliate orders DB (populated hourly), trying
  both the full challenge id and the id with a leading `200` stripped.
- **client:** `python scripts/webhook_client.py check_affiliation --challenge-id 200141747`

### `history`
Trade history.
- **params:** `type` = `bills` (default) | `orders` | `done` | `finish`;
  `page?` (default 1), `rows?` (default 20), `trade_account?`
- **data:** `{ "type": "bills", "rows": [...] }`. `bills` rows include `type`
  (Open/Close Position, Opening/Closing fee, Recharge), `instrument`, `size`
  (USDT delta), `preBalance`/`postBalance`, `createdDate`, and a `note` with the
  order id, position id, fill price and fee.
- **client:** `python scripts/webhook_client.py history --type bills --rows 20`

---

## Sizing

### `size`
Compute the lot quantity for a money amount, without placing anything. Uses the
live mark price and the platform lot size.
- **params:** `symbol` (required); exactly one of `margin_usd` /
  `notional_usd` / `account_pct`; `leverage?`; `trade_account?`
- **data:** `{ "sizing": { symbol, price, leverage, one_lot_size, quantity,
  notional_usd, margin_usd, basis } }`
- **maths:** `notional = quantity * one_lot_size * price`,
  `margin = notional / leverage`. Quantity is rounded **down** to whole lots so
  the stated budget is never exceeded.
- **client:** `python scripts/webhook_client.py size --symbol BTCUSDT --margin-usd 50 --leverage 4`

---

## Trade actions (dry-run by default)

### `open`
Open a position.
- **params:**
  - `symbol` (required, e.g. `BTCUSDT`; any USDT pair)
  - `side` (required, `long` or `short`)
  - size - exactly one of: `quantity` (lots) | `margin_usd` | `notional_usd` | `account_pct`
  - `leverage?` (1-5; server default if omitted)
  - take profit - exactly one of: `tp` (price) | `tp_pct` (percent from entry)
  - stop loss - exactly one of: `sl` (price) | `sl_pct` (percent from entry)
  - `trade_account?`
  - `live?` - `true` to send a real order (otherwise dry-run)
- **dry-run data:** `{ dry_run: true, planned: { method, url, headers(redacted),
  body }, summary: { symbol, side, quantity, leverage, take_profit, stop_loss },
  sizing, live_requested, live_enabled_on_server }`
- **live data:** `{ dry_run: false, result: { code, success, ... }, endpoint, sizing }`
- **client (dry-run):**
  `python scripts/webhook_client.py open --symbol BTCUSDT --side long --margin-usd 50 --leverage 4 --tp-pct 3 --sl-pct 2`
- **client (live):** add `--live`

For a long, `tp_pct` is above and `sl_pct` below the entry; for a short they are
mirrored. Percent TP/SL are computed from the live mark price at send time.

### `close`
Close a position. Full market close by default.
- **params:** `symbol` (required); `trade_account?`; `quantity?` (partial close,
  in lots); `position_id?` (target a specific position; otherwise auto-found via
  the positions / stop-profit-loss lookup); `live?`
- **dry-run data:** `{ dry_run: true, planned: {...} }`
- **live data:** `{ dry_run: false, result: {...}, endpoint, position_id, kind }`
- **client:** `python scripts/webhook_client.py close --symbol BTCUSDT --live`

---

## Error types

| `error_type` | meaning | what to do |
|---|---|---|
| `validation` | bad inputs (missing TP/SL, leverage > 5, unknown symbol, bad id) | fix the params and retry |
| `not_affiliated` | a LIVE order was blocked because the account isn't an affiliate referral | print the full `error` text verbatim (the sign-up link is inside it); don't paraphrase or drop the link; do not retry |
| `session_expired` | the token lapsed or was rejected | grab a fresh Admin-Token (one console command - see onboarding.md) |
| `api` | the trading platform returned an error | read the message; often transient |
| `bad_request` | the JSON body was malformed | check the request shape |
| `config` | a server configuration problem | tell the operator |
| `unknown_action` | the `action` is not recognised | use one of the actions above |
