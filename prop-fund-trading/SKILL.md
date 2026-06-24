---
name: Prop Fund Trading
description: >-
  Trade an authorised Bitfunded-style prop-firm account through a hosted webhook.
  Use when the user wants to check their prop account (status, accounts,
  balance, positions, overview, history), size a position, or open/close a BTC
  (or other USDT-pair) trade. The user supplies one value - their session token
  (x_authorization), copied from the browser console. Dry-run is always the
  default; a live order needs an explicit confirmation and the --live flag.
---

# Prop Fund Trading

This skill lets you operate a user's **own authorised** prop-firm trading
account through a shared, hosted webhook on Railway. Each user supplies their
own browser session credentials; nothing is stored on the server. It is for
personal trading automation of an account the user is authorised to trade. Do
not use it to trade accounts the user does not own.

The webhook lives at:
`https://prop-fund-ai-trading-skill-production.up.railway.app/webhook`

You talk to it with the bundled client:
`python scripts/webhook_client.py <action> [flags]`

## First run: onboarding

Setup needs exactly **one value**: the user's session token. If a command
returns `error_type: "session_expired"` or the client says "No token found",
walk them through `onboarding.md`. In short:

1. Log in to `https://trader.bitfunded.com`, open the browser console (F12 ->
   Console), and run: `copy(localStorage.getItem("Admin-Token"))`.
2. Paste that token into `creds.json` (copy `creds.example.json`) as
   `x_authorization`.
3. Run `accounts` to list their challenges, and put the chosen `tradeAccount`
   id into `creds.json` as `trade_account` (or pass `--trade-account`).

Then `python scripts/webhook_client.py status` should show `portal: ok` /
`trading: ok`. No cookie, no browser extension, no header hunting - the token is
the only thing the API checks, and `did` is generated server-side.

Never ask the user to paste their token into the chat. They put it into
`creds.json` themselves. `creds.json` is gitignored - never commit it.

## Golden rules (never break these)

1. **Default to dry-run first.** Always show / run the order without `--live`
   first; it returns a preview and sends nothing.
2. **Never trade without a stop loss AND a take profit.** Both are mandatory.
3. **Exactly one TP and one SL** per order.
4. **Maximum leverage is 5x** (hard cap on the server). Never request more.
5. **Never expose secrets.** Never print the user's cookie, `x-authorization`,
   `did`, or any token. The webhook redacts responses; do not undo that.
6. **Live needs an explicit `--live` and user confirmation.** Show the exact
   command, get a clear yes, then run it - unless the user has explicitly told
   you to auto-execute in this session.

## What you can do (every API action)

See `api-reference.md` for full parameters and response shapes. Quick map:

| The user asks... | Run |
|---|---|
| "is my account connected / session valid?" | `status` |
| "list my accounts / challenges" | `accounts` |
| "show my profile" | `profile` |
| "challenge overview / how am I doing" | `overview --challenge-id <id>` |
| "what's my balance" | `balance` |
| "show my positions" | `positions` |
| "how many lots is $50 / 2% of my account" | `size --symbol BTCUSDT --margin-usd 50` |
| "open a trade" | `open ...` (dry-run, then `--live`) |
| "close my BTC position" | `close --symbol BTCUSDT --live` |
| "show my trade history / bills" | `history --type bills` |
| "is this account/challenge affiliated to us?" | `check_affiliation --challenge-id <id>` |

## Checking affiliation when a user adds an account

When a user first connects a new prop account/challenge, check whether it came
through our affiliate link before doing anything else:

```bash
python scripts/webhook_client.py check_affiliation --challenge-id 200141747
```

`{"affiliated": true, ...}` means it's one of our referred orders; `false` means
it isn't (or our affiliate data hasn't synced yet). It needs no token. The check
tries both the full challenge id and the id with a leading `200` stripped, since
the challenge id looks like `200<orderNumber>`.

Add `--trade-account <id>` to target a specific subaccount (omit to use the
default in `creds.json`).

### Live trading requires affiliation

Live `open` orders are gated server-side. If the account isn't one of our
affiliate referrals, the webhook blocks the live order (it never reaches the
broker) and returns:

```json
{"ok": false, "error_type": "not_affiliated",
 "error": "This account is not affiliated, and if you recently signed up, it may take one hour for our system to catch up. If you didn't use our link, we only accept affiliated accounts. Please register using our affiliate link to get access: https://www.bitfunded.com/client/register?regid=8824327733",
 "affiliate_link": "https://www.bitfunded.com/client/register?regid=8824327733"}
```

When you get `error_type: not_affiliated`, **print the full `error` text to the
user verbatim, including the affiliate link inside it.** Do not paraphrase it to
something like "affiliation is required" and do not drop the link. Then stop; do
not retry the live order. Dry-run previews are never gated, so you can still show
what the trade would do.

## Taking a trade

When the user says "take a trade", collect or infer all of:

- **symbol** (e.g. BTCUSDT - any USDT pair is supported)
- **side** (long or short)
- **size**: either `--quantity <lots>` OR a money amount:
  `--margin-usd <X>` (commit ~$X margin), `--account-pct <P>` (P% of balance),
  or `--notional-usd <X>`
- **leverage** (1-5; defaults to the server default if omitted)
- **take profit**: `--tp <price>` OR `--tp-pct <percent from entry>`
- **stop loss**: `--sl <price>` OR `--sl-pct <percent from entry>`

If any are missing, ask, unless the user gave a strategy/risk model you can
derive them from. Then:

1. Show and run the **dry-run** (no `--live`) and relay the preview.
2. If the user confirms, show the `--live` command and run it.
3. After a live order, run `positions` to confirm it opened.

### Example

**User:** "Take a BTC long, ~$50, 4x, TP 3%, SL 2%."

**You:** "Here's the dry-run first:"

```bash
python scripts/webhook_client.py open --symbol BTCUSDT --side long \
    --margin-usd 50 --leverage 4 --tp-pct 3 --sl-pct 2
```

After they confirm:

```bash
python scripts/webhook_client.py open --symbol BTCUSDT --side long \
    --margin-usd 50 --leverage 4 --tp-pct 3 --sl-pct 2 --live
```

Then `python scripts/webhook_client.py positions` to confirm it's open.

## Closing

```bash
python scripts/webhook_client.py close --symbol BTCUSDT            # dry-run preview
python scripts/webhook_client.py close --symbol BTCUSDT --live     # full market close
```

Close auto-finds the open position. For a partial close add `--quantity <lots>`;
to target a specific position add `--position-id <id>`. After a live close,
confirm with `positions`.

## Reading the response

The client prints JSON: `{"ok": true, "action": ..., "data": {...}}` on success,
or `{"ok": false, "error_type": "...", "error": "..."}` on failure. Common
`error_type`s: `validation` (bad inputs - fix and retry), `not_affiliated` (live
order blocked - show the `error` message + `affiliate_link`, don't retry),
`session_expired` (creds lapsed - re-do onboarding), `api` (platform error),
`bad_request` (malformed call).

## Safety reminders

- A live order is real money. Keep test sizes small.
- Always confirm a live position opened (and, if you opened a test, that it
  closed) with `positions`.
- If a close fails, stop and tell the user; never leave a live position you
  meant to close.
