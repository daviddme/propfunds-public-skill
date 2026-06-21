# public_skills

Installable Claude Skill(s) for trading an authorised Bitfunded-style prop-firm
account through the hosted webhook. Copy a skill folder into your own skills
repo (or your Claude skills directory) and go.

## What's here

```
public_skills/
└── prop-fund-trading/          <- the skill (copy this whole folder)
    ├── SKILL.md                <- skill instructions (Claude loads this)
    ├── onboarding.md           <- how a user gets their session (Cookie-Editor)
    ├── api-reference.md        <- every webhook action documented
    ├── creds.example.json      <- credential template (copy to creds.json)
    ├── .gitignore              <- keeps creds.json out of git
    └── scripts/
        └── webhook_client.py   <- zero-dependency client (Python stdlib only)
```

It talks to the shared, hosted webhook:
`https://prop-fund-ai-trading-skill-production.up.railway.app/webhook`

No server to run. The user only needs their own browser session (a cookie plus
two headers). Everything is multi-user and stateless - the server stores no
credentials.

## Install

### Into a GitHub skills repo (to share)

Copy the `prop-fund-trading/` folder into your skills repository and commit it
(it has its own `.gitignore` so a user's `creds.json` never gets committed):

```bash
cp -r prop-fund-trading /path/to/your-skills-repo/skills/
```

Anyone who clones that repo gets the skill.

### Into Claude Code

Drop `prop-fund-trading/` into your Claude Code skills directory (e.g.
`~/.claude/skills/prop-fund-trading/`). Claude discovers it via `SKILL.md`.

### Into the cloud (claude.ai)

Add the skill to your project / skills there. The user supplies their session in
`creds.json` (or as `PROP_FUND_*` environment values); the bundled client runs
in the code-execution sandbox, which has the network access it needs.

## First run

1. Follow `prop-fund-trading/onboarding.md` to get the cookie (Cookie-Editor)
   and the two headers, and save them in `creds.json`.
2. Verify:
   ```bash
   cd prop-fund-trading
   python scripts/webhook_client.py status
   python scripts/webhook_client.py accounts
   ```
3. Ask Claude things like "show my balance", "what's 2% of my account on BTC",
   or "open a BTC long, $50, 4x, TP 3%, SL 2%" - it drives the client for you,
   dry-run first.

## Requirements

- Python 3.8+ (the client uses only the standard library - no `pip install`).
- A funded/authorised Bitfunded account you own.

## Safety

Dry-run is the default. A live order needs the explicit `--live` flag. Max
leverage is capped at 5x server-side, and every order must carry a take profit
and a stop loss. Your `creds.json` holds your session - keep it private and
never commit it. See `prop-fund-trading/SKILL.md` and `api-reference.md` for the
full rules.

## Updating

The skill calls the hosted webhook, so new server-side features appear
automatically with no change on the user's side. If the webhook URL ever
changes, update the `DEFAULT_URL` in `scripts/webhook_client.py` (or set
`PROP_FUND_WEBHOOK_URL`).
