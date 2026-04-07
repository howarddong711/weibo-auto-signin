# weibo-auto-signin

Minimal Weibo super-topic auto check-in CLI.

The tool reads one or more full Weibo cookie strings from a plain-text file,
checks each account's followed super-topics, and attempts daily check-in for
those topics.
It is intended for local runs and GitHub Actions scheduled runs.

## What This Does Not Do

- It does not acquire Weibo cookies for you.
- It does not bypass cookie expiration, account risk controls, or platform changes.
- It does not run live-network tests in the repository test suite.

## Development

This project targets Python 3.13 and is intended to be managed with `uv`.

```bash
uv run pytest tests/test_smoke.py
```

## Local Setup

1. Install Python 3.13 and `uv`.
2. Clone or fork the repository.
3. Create a local config file from the example:

```bash
cp cookies.example.txt cookies.txt
```

4. Replace the placeholder cookie values with your own Weibo cookie values.
5. Run the CLI:

```bash
uv run python -m weibo_auto_signin.cli --config cookies.txt
```

Optional notification environment variables:

- `PUSHPLUS_TOKEN` enables PushPlus delivery.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and
  `SMTP_TO` enable SMTP email delivery.
- `SMTP_USE_TLS=false` disables STARTTLS if your SMTP server does not use it.
- `NOTIFY_TITLE_PREFIX` overrides the default notification title prefix.

## Config Format

`cookies.txt` is a plain-text file with one full cookie string per line:

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

Blank lines are ignored. Do not commit real cookies. Keep real values in
`cookies.txt` locally or in a GitHub Actions repository secret.

## GitHub Actions Setup

The repository includes `.github/workflows/checkin.yml` for manual and scheduled
runs.

1. Fork the repository.
2. Open the fork's `Settings` > `Secrets and variables` > `Actions`.
3. Add a repository secret named `WEIBO_COOKIES`.
4. Optional: add `PUSHPLUS_TOKEN` and/or SMTP-related repository secrets if you
   want run summaries delivered outside the Actions log.
5. For SMTP, add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
   `SMTP_FROM`, and `SMTP_TO`. Add `SMTP_USE_TLS` only if you need to disable
   STARTTLS.
6. Paste one or more full cookie strings as the secret value, one per line.
7. Enable GitHub Actions on the fork if GitHub prompts you to do so.
8. Run the `Weibo Check-in` workflow manually from the `Actions` tab, or rely on
   the schedule.

Example secret value:

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

The bundled schedule runs at `22:30` UTC, which is `06:30` in China Standard
Time. Edit the cron expression in `.github/workflows/checkin.yml` if another
time is more appropriate.

## Notes

- Expired or incomplete cookies are reported as cookie-invalid account failures.
- GitHub Actions logs include check-in summaries, but raw cookie values should
  not be printed.
- Weibo may change endpoints or anti-abuse behavior. If requests start failing,
  rotate cookies first, then review recent platform changes.
- Automated sign-in can carry account risk. Use a schedule and account setup you
  are comfortable with.
