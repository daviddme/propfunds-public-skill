# Onboarding - one value, about a minute

This skill needs **one** value: your session **token** (`x_authorization`).
No cookie, no browser extension, no header hunting. We verified that the token
is the only thing the API actually checks - the cookie isn't needed at all, and
the device id is generated for you.

## Step 1 - copy your token (one console command)

1. Log in to the Bitfunded trader portal: `https://trader.bitfunded.com`
2. Open the browser console: **F12** (or `Cmd+Option+I`) -> **Console** tab.
3. Paste this and press Enter:

   ```js
   copy(localStorage.getItem("Admin-Token"))
   ```

   That copies your token to the clipboard. (To see it instead of copying, run
   `localStorage.getItem("Admin-Token")` and copy the printed string.)

## Step 2 - save it

Copy the template and paste your token in:

```bash
cp creds.example.json creds.json
```

```json
{
  "x_authorization": "<paste your token here>",
  "trade_account": ""
}
```

**Never commit `creds.json`** - it is gitignored. Treat the token like a
password.

## Step 3 - pick your account and verify

```bash
python scripts/webhook_client.py accounts   # lists your challenges + tradeAccount ids
python scripts/webhook_client.py status      # want portal: ok, trading: ok
```

Put the `tradeAccount` id you want to trade into `creds.json` as
`trade_account` (or pass `--trade-account <id>` per command). Done.

## If it stops working

The token is tied to your browser login and will eventually expire. If `status`
returns `session_expired`, just repeat Step 1 (one console command) to grab a
fresh token and save it again.

## Why this changed (you may have seen the old way)

Earlier docs asked for a cookie (via Cookie-Editor) plus two request headers
(`x-authorization`, `did`). It turned out:

- the **cookie is not needed** at all,
- **`did`** is a device id the platform accepts as any value, so it is generated
  for you,
- the portal **`x-authorization` token** (which lives in your browser at
  `localStorage["Admin-Token"]`) is the only thing that authenticates.

So you only need that one token now. Ignore any older cookie instructions.
