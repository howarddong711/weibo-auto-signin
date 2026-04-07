# Weibo Auto Signin Notification Module Design

## Summary

This design adds a lightweight notification module to `weibo-auto-signin`.
The module sends one plain-text summary after each full check-in run, regardless
of whether the run contains successes, failures, or cookie-invalid accounts.

The first notification release supports exactly two channels:

- PushPlus
- SMTP email

The notification layer must stay downstream from the check-in flow. It consumes
final run results and sends summaries, but it does not control or alter the
check-in process itself.

## Goals

- Send one summary notification after each run.
- Use the same summary content for all enabled channels.
- Support PushPlus and generic SMTP email.
- Keep notification configuration separate from cookie input.
- Ensure notification failures never break the check-in run itself.

## Non-Goals

- Per-topic instant notifications
- Success-only or failure-only notification modes
- Rich HTML emails
- Markdown or rich-text PushPlus formatting
- Additional channels such as Telegram, ServerChan, Feishu, or enterprise chat
- Retry queues, job persistence, or database-backed delivery state

## Product Behavior

After the check-in run completes and all account results are collected:

1. The app computes a plain-text summary from the final result objects.
2. The app loads notification configuration from environment variables.
3. The app determines which channels are fully configured.
4. The app sends the same summary through each enabled channel.
5. The app logs delivery success or failure per channel.

If no notification channel is configured, the app logs that notification is
disabled and exits normally.

If one channel fails, the other channels should still be attempted.

## Architecture

The notification module should be structured as a small adapter layer:

- `notify.py`
  - notification entrypoint
  - summary title/body generation
  - channel selection logic
  - sequential dispatch to enabled notifiers

- `notifiers/pushplus.py`
  - PushPlus-specific HTTP request logic

- `notifiers/email.py`
  - generic SMTP email sending logic

The notification module depends only on the existing result models and logger.
It must not depend on the Weibo HTTP client or cookie parsing logic.

## File Structure

The design adds the following files:

```text
src/weibo_auto_signin/
├── notify.py
└── notifiers/
    ├── __init__.py
    ├── email.py
    └── pushplus.py

tests/
├── test_notify.py
├── test_notifier_email.py
└── test_notifier_pushplus.py
```

## Notification Trigger Point

The existing CLI flow should remain:

1. load config
2. run check-in
3. log summary
4. send notifications
5. exit with appropriate code

Notification dispatch should happen after result generation and logging, not
inside the per-account or per-topic execution path.

## Summary Format

All channels share the same summary content.

Title example:

```text
微博超话签到汇总 2026-04-07
```

Body example:

```text
成功账号: 2
失败账号: 1
Cookie 失效: 0

[account-1]
SSR集换社: +4 exp rank 12
微博观影团: 已签到

[account-2]
失败: Failed to bootstrap session: HTTP request failed

[account-3]
Cookie 无效: Missing required cookie keys: SUBP
```

Required summary sections:

- overall counts
  - successful accounts
  - failed accounts
  - cookie-invalid accounts
- per-account block
- per-topic lines when available
- account-level error line when the account failed before topic retrieval

Formatting should stay pure plain text and easy to read in both PushPlus and
email clients.

## Channel Configuration

Configuration is environment-variable based only.

### PushPlus

Required:

- `PUSHPLUS_TOKEN`

Optional:

- `NOTIFY_TITLE_PREFIX`

If `PUSHPLUS_TOKEN` is set, PushPlus is enabled.

### SMTP Email

Required:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO`

Optional:

- `SMTP_USE_TLS`
- `NOTIFY_TITLE_PREFIX`

If any required SMTP field is missing, email delivery is skipped and a warning
is logged.

`SMTP_TO` should support one or more recipients, comma-separated.

## Channel Selection Rules

- If PushPlus config is complete, enable PushPlus.
- If SMTP config is complete, enable SMTP email.
- If neither is complete, log `notification disabled` and return.
- Channel initialization errors should be logged and should not crash the run.

## PushPlus Delivery Design

PushPlus should send one HTTP request per run.

Expected behavior:

- HTTP `POST`
- endpoint: `https://www.pushplus.plus/send`
- plain-text title/body payload
- short timeout
- non-2xx response is logged as a delivery failure

The notifier should return a simple success/failure result to the caller rather
than exiting or raising uncaught exceptions.

## SMTP Delivery Design

Email delivery should use generic SMTP so it works with common providers such as
QQ Mail, 163 Mail, and Gmail-compatible SMTP setups.

Expected behavior:

- construct a plain-text message
- use standard SMTP authentication
- support optional TLS flag
- support one or more recipients
- log delivery success or failure

The implementation should stay generic and should not special-case any one
provider.

## Error Handling

Notification failures must never alter check-in result computation.

Rules:

- check-in run completes first
- notification exceptions are caught and logged
- one failed notifier does not block the others
- CLI exit code remains based on check-in outcome, not notifier outcome

This ensures the notification module is an add-on capability, not a new failure
source.

## Logging

The notification layer should log:

- whether notifications are enabled
- which channels are active
- per-channel send success
- per-channel send failure with concise reason

Sensitive data must never be logged:

- PushPlus token
- SMTP password
- raw cookie strings

## Testing Strategy

The first test suite should include:

- summary text generation
- PushPlus request payload construction
- SMTP message construction
- channel enable/disable logic based on environment variables
- notification dispatch behavior when one channel fails and another succeeds

Avoid live-network tests in the repository test suite.
Use fakes/mocks for HTTP and SMTP interactions.

## Integration Notes

This design intentionally does not change the cookie input path or workflow
logic beyond adding optional environment variables for notifications.

GitHub Actions users can later add:

- `PUSHPLUS_TOKEN`
- SMTP environment variables

without changing the existing cookie secret format.

## Resolved Decisions

- notification timing: always once per run
- content format: plain text only
- supported channels: PushPlus and generic SMTP email
- configuration source: environment variables only
- delivery behavior: best-effort, never blocks main run

## Implementation Readiness

This scope is intentionally small and isolated.
The next step should be a focused implementation plan that:

- adds summary formatting
- adds PushPlus notifier
- adds SMTP notifier
- integrates notify dispatch into the CLI flow
- adds tests for formatting and delivery behavior
