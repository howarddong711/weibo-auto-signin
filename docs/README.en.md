# weibo-auto-signin

A minimal CLI for Weibo super-topic daily check-in.

The project is designed to stay simple:

- provide one or more full Weibo cookie strings
- run locally or through GitHub Actions
- optionally receive a plain-text summary by PushPlus or SMTP email

## Quick Start

Requirements:

- Python `3.13`
- `uv`

Install dependencies:

```bash
uv sync
```

Create a local cookie file:

```bash
cp cookies.example.txt cookies.txt
```

Each line is one full cookie string:

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

Run locally:

```bash
uv run python -m weibo_auto_signin.cli --config cookies.txt
```

## GitHub Actions

The repository includes a workflow at [checkin.yml](../.github/workflows/checkin.yml).

Add this repository secret:

- `WEIBO_COOKIES`

Value format:

```text
SUB=...; SUBP=...; SCF=...; ALF=...
SUB=...; SUBP=...; SCF=...; ALF=...
```

Optional notification secrets:

- `PUSHPLUS_TOKEN`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO`
- `SMTP_USE_TLS`
- `NOTIFY_TITLE_PREFIX`

Then open the `Actions` tab and run `Weibo Check-in`, or wait for the scheduled run.

## Notes

- This project does not fetch cookies for you.
- Expired cookies and platform changes can break check-ins.
- Do not commit real cookie values into the repository.
- The main documentation is written in Chinese in [README.md](../README.md).
