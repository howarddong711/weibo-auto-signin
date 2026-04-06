# Weibo Auto Signin MVP Design

## Summary

`weibo-auto-signin` is a lightweight open source Python CLI tool for Weibo super-topic check-in.
The first release focuses on simplicity: users provide one or more full cookie strings, the tool parses the required cookie fields, fetches the followed super-topic list for each account, and performs check-in for each topic.

This MVP supports:

- local CLI execution
- multi-account configuration
- JSON-based configuration
- GitHub Actions scheduled execution
- console and file logging

This MVP does not support:

- QR-code login or browser-assisted cookie capture
- web frontend or backend services
- notifications through third-party channels
- non-check-in fan interaction features

## Goals

- Provide a simple open source repository that users can run locally with minimal setup.
- Support multiple Weibo accounts in a single run.
- Accept full cookie strings instead of requiring manual extraction of specific fields.
- Make the same core CLI usable both locally and in GitHub Actions.
- Keep the implementation intentionally small, readable, and original rather than cloning an existing project structure.

## Non-Goals

- Building a long-running platform or hosted SaaS
- Storing user accounts in a database
- Implementing QR login or automated browser login
- Implementing likes, reposts, comments, private messages, or fan-group automation
- Implementing rich dashboards, historical analytics, or notification integrations

## Product Scope

The first version is a command-line tool repository, not a service.
Users run it in one of two ways:

1. locally, by creating a JSON config file and executing the CLI
2. on GitHub Actions, by storing the same JSON payload in repository secrets and using the bundled workflow

The output is intentionally simple:

- per-account progress in stdout
- a final per-run summary
- rotating local log files for local execution
- GitHub Actions logs for remote execution

## User Experience

### Local Run

The user clones the repository, installs dependencies, creates an `accounts.json` file, and runs the CLI.
The CLI validates the config, parses cookie strings, performs check-in, and prints a structured summary.

### GitHub Actions Run

The user forks the repository, stores account JSON in a repository secret, enables the bundled workflow, and optionally configures a schedule.
The workflow writes the JSON secret to a runtime config file and invokes the same CLI entrypoint used locally.

## Architecture

The repository should use a lightweight modular CLI structure with clear responsibilities:

- `cli`: command-line entrypoint and top-level orchestration
- `config`: loading and validating JSON configuration
- `cookie`: parsing full cookie strings into key-value pairs
- `client`: low-level Weibo HTTP session management and API requests
- `checkin`: high-level multi-account check-in orchestration
- `models`: typed result models for account and topic results
- `logging`: logger setup for console and file output

This keeps the code easy to understand while avoiding the fragility of a single-file script.
It also keeps future expansion possible without prematurely introducing service-layer or web-app complexity.

## Proposed Repository Layout

```text
weibo-auto-signin/
├── .github/
│   └── workflows/
│       └── checkin.yml
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-07-weibo-auto-signin-mvp-design.md
├── src/
│   └── weibo_auto_signin/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── cookie.py
│       ├── client.py
│       ├── checkin.py
│       ├── logging.py
│       └── models.py
├── tests/
│   ├── test_config.py
│   ├── test_cookie.py
│   └── test_results.py
├── accounts.example.json
├── pyproject.toml
└── README.md
```

## Configuration Design

The MVP uses JSON for both local and GitHub Actions execution.

Example `accounts.example.json`:

```json
{
  "accounts": [
    {
      "name": "main-account",
      "cookie": "SUB=...; SUBP=...; SCF=...; ALF=...",
      "enabled": true
    }
  ]
}
```

Rules:

- `accounts` is required and must be a non-empty array
- `name` is optional but recommended
- `cookie` is required and must be a non-empty string
- `enabled` defaults to `true` if omitted

The tool parses the full cookie string and extracts required fields internally.
For the MVP, the parser should at minimum support extracting `SUB` and `SUBP`.
Other keys may be preserved in the parsed cookie map and passed through to the HTTP session when present.

## Cookie Handling

The cookie parser should:

- split the raw cookie string on `;`
- trim whitespace
- split each item on the first `=`
- ignore malformed empty segments
- preserve all valid cookie key-value pairs in a dictionary

The parser should also expose validation helpers so the CLI can fail fast when required keys are missing.

Validation behavior:

- if `SUB` is missing, the account is invalid
- if `SUBP` is missing, the account is invalid
- invalid accounts should be reported clearly before any network requests are made

This keeps the UX simple while still allowing future compatibility if Weibo starts relying on more cookie keys.

## Weibo Client Design

The client is responsible for HTTP behavior only.
It should encapsulate:

- a persistent `requests.Session`
- base headers such as user-agent and language
- cookie injection from parsed cookie fields
- initial session bootstrap
- super-topic list fetching
- per-topic check-in requests

The client should not know about JSON files, CLI flags, or workflow setup.
It should only expose methods like:

- `bootstrap_session()`
- `fetch_user_info()`
- `fetch_followed_topics()`
- `checkin_topic(topic)`

## Check-In Flow

For each enabled account:

1. Parse and validate the raw cookie string.
2. Create a Weibo client session.
3. Bootstrap the session and confirm the account is still valid.
4. Fetch the account identity needed for downstream requests.
5. Fetch all followed super-topics.
6. Check in each topic in sequence.
7. Accumulate per-topic results and account-level summary data.

The process should continue even if one account fails.
Within an account, the process should continue even if one topic check-in fails.

## Result Model

The CLI should work with explicit result models instead of ad hoc dictionaries.
At minimum the MVP should represent:

- topic title
- topic check-in status
- message returned by Weibo
- optional experience increment
- optional rank information
- account display name
- resolved uid when available
- account-level success or failure status
- cookie-invalid status
- accumulated per-topic results

This makes terminal output, log output, and future notification integrations easier to extend.

## CLI Design

The CLI should stay intentionally small.
Recommended commands and flags:

- default execution: run all enabled accounts from a config file
- `--config <path>`: override config path
- `--account <name>`: run only one named account

The default local config path should be a simple repository-root file such as `accounts.json`.

The CLI should:

- validate the config before execution
- print progress per account
- print progress per topic
- print a final summary with counts
- exit non-zero when all accounts fail before completing useful work

## Logging Design

Local runs should log to:

- console
- a local `logs/` directory with rotating files

GitHub Actions runs should rely primarily on stdout, but file logging can still happen within the workspace during the run.

Logging should include:

- run start
- account start
- topic check-in progress
- cookie validation failures
- request-level recoverable failures
- final summary

Sensitive values such as full cookie strings must never be logged.

## Error Handling

The MVP should prefer predictable continuation over aggressive failure.

Rules:

- one account failing must not stop other accounts
- one topic failure must not stop the remaining topics
- config validation errors should be explicit and easy to understand
- cookie-invalid accounts should be marked distinctly from transient request failures
- unexpected HTTP or JSON parsing issues should be captured as readable error messages

The user should always get a final run summary, even when some work fails.

## Rate Limiting and Request Behavior

The MVP should include small randomized delays between topic check-ins to reduce the chance of obvious burst behavior.
The delays do not aim to eliminate detection risk; they only make the request pattern less abrupt.

Retry behavior should stay minimal:

- allow a small retry count for transient failures
- do not retry obvious cookie-invalid states

## GitHub Actions Design

The repository should include a ready-to-use workflow at `.github/workflows/checkin.yml`.

The workflow should:

- support `workflow_dispatch`
- support a simple scheduled trigger
- install Python
- install project dependencies
- create `accounts.json` from a repository secret such as `WEIBO_ACCOUNTS_JSON`
- invoke the CLI

The workflow should not require users to edit code just to provide credentials.
The README should explain how to fork the repo, add the secret, and enable the schedule.

## Testing Strategy

The MVP should include lightweight automated tests for stable logic only.

Required test areas:

- cookie parsing
- cookie validation
- config loading and invalid config handling
- result formatting and summary aggregation

The MVP should avoid brittle live-network tests against Weibo.
Runtime verification of the live behavior should come from manual local runs and GitHub Actions runs.

## Security and Privacy

The repository should treat cookies as secrets.

Requirements:

- never print raw cookies to logs
- never commit real cookies
- provide an example config file only
- document secret storage for GitHub Actions
- document cookie expiration and rotation expectations

## Documentation Requirements

The README should explain:

- what the tool does
- what it does not do
- local setup
- JSON config format
- GitHub Actions setup
- common failures such as expired cookies
- a short warning about account risk and platform changes

## Future Expansion Path

Later phases may add:

- browser-assisted QR login for cookie acquisition
- web frontend and backend account management
- additional Weibo interaction tasks
- notification providers

These features are intentionally excluded from the MVP and must not shape the initial code into a service-oriented architecture yet.

## Open Decisions Resolved

The following design decisions are fixed for phase one:

- project type: open source Python CLI tool
- account input: full raw cookie string
- account scope: multi-account
- config format: JSON
- default output: console and log files only
- GitHub Actions support: bundled workflow in the repository
- originality constraint: use the reference repository for behavior understanding only, not as a code template

## Implementation Readiness

This scope is intentionally narrow enough for a clean first implementation.
The next step after spec approval is to write an implementation plan for:

- repository scaffolding
- config and cookie parsing
- Weibo client implementation
- check-in orchestration
- CLI and logging
- GitHub Actions workflow
- tests and documentation
