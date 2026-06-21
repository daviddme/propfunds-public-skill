# Onboarding - get your Bitfunded session

This skill trades **your own** account through a hosted webhook. To do that it
needs your browser's logged-in session: one cookie and two request headers.
You get them once, save them in `creds.json`, and you're set.

Nothing here bypasses any security. You are copying a session your own browser
already has, from your own logged-in account.

You need four values:

| field | where it comes from |
|---|---|
| `cookie` | the **Cookie-Editor** extension (Export -> Header String) |
| `x_authorization` | DevTools -> a `trader.bitfunded.com` request header |
| `did` | DevTools -> a `cb.bitfunded.com` request header |
| `trade_account` | the `accounts` command lists yours (you don't hunt for it) |

## Part 1 - the cookie (Cookie-Editor)

1. Install **Cookie-Editor** from the Chrome Web Store
   (https://chromewebstore.google.com/ - search "Cookie-Editor").
2. Log in to the Bitfunded trader portal in Chrome
   (`https://trader.bitfunded.com`). Make sure you can see your dashboard.
3. Click the **Cookie-Editor** icon in the toolbar **while you are on the
   bitfunded.com tab**.
4. At the bottom of Cookie-Editor click **Export** (the export icon), then
   choose **Export as Header String**.
   - This copies a single line like `name1=value1; name2=value2; ...` to your
     clipboard. That is exactly the `cookie` value you need.
5. Paste it as the `cookie` field in `creds.json`.

> Tip: if you only see "Export as JSON / Netscape", pick **Header String** if
> available. If your version lacks it, use DevTools instead (Part 2 also shows
> the cookie as the `-b '...'` value in a copied cURL).

## Part 2 - the two headers (DevTools)

Cookie-Editor only exports cookies, so grab these two headers from DevTools:

1. Still logged in, press `F12` (or `Cmd+Option+I`) to open DevTools, go to the
   **Network** tab, and tick **Preserve log**.
2. Click around your dashboard so requests appear.
3. Find a request to **`trader.bitfunded.com`** (e.g. one ending in
   `/analyzer/accounts` or `/users/profile`). Click it, open the
   **Headers** section (or right-click -> **Copy -> Copy as cURL**), and read
   off:
   - `x-authorization: <long value>`  -> this is `x_authorization`.
4. Now click any chart or the trade panel so a request to
   **`cb.bitfunded.com`** fires. Open that request's headers and read off:
   - `did: <uuid value>`  -> this is `did`.

## Part 3 - save creds.json

Copy the template and fill it in:

```bash
cp creds.example.json creds.json
```

```json
{
  "cookie": "<the Header String from Cookie-Editor>",
  "x_authorization": "<the x-authorization header>",
  "did": "<the did header>",
  "trade_account": ""
}
```

Leave `trade_account` blank for now. **Never commit `creds.json`** - it is
gitignored. Treat these values like a password.

## Part 4 - verify and find your trade account

```bash
python scripts/webhook_client.py status
```

You want `"portal": "ok"` and `"trading": "ok"`. Then list your accounts:

```bash
python scripts/webhook_client.py accounts
```

Pick the `tradeAccount` id of the challenge you want to trade and put it in the
`trade_account` field of `creds.json` (or pass `--trade-account <id>` per
command).

## When it stops working

These values are tied to your browser login and **expire**. If `status` says
`session_expired` (or a `403`), just redo Part 1 and Part 2 to refresh the
cookie and headers, and save them again. Logging out of Bitfunded invalidates
them, which is how you "rotate" if a value ever leaks.
