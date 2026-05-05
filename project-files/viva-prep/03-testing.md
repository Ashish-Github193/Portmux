# PortMUX — How to Run the Tests

**364 tests total** = 332 unit (mocked) + 32 E2E (Docker, real tmux + sshd).

---

## Prerequisites

| Tool | Why |
|---|---|
| `uv` | Python project + dependency runner |
| `tmux` | Required at runtime (not for unit tests, since they mock it) |
| `docker` | Required only for E2E tests |

Install project + dev deps:

```bash
uv install .
```

---

## 1. Unit Tests (fast, mocked, no tmux/SSH needed)

Run **only** unit tests — these mock tmux, SSH, and the filesystem:

```bash
uv run pytest tests/unit/
```

Equivalent using the marker (excludes anything tagged `e2e`):

```bash
uv run pytest tests/ -m "not e2e"
```

Run a single test file:

```bash
uv run pytest tests/unit/commands/test_add.py
```

Run a single test by name:

```bash
uv run pytest tests/unit/commands/test_add.py::test_add_local_forward
```

Verbose output (shows each test name as it runs):

```bash
uv run pytest tests/unit/ -v
```

Stop at first failure (useful while debugging):

```bash
uv run pytest tests/unit/ -x
```

### With coverage report

```bash
uv run pytest --cov=portmux                       # terminal summary
uv run pytest --cov=portmux --cov-report=html     # HTML report → htmlcov/index.html
```

### What the unit tests cover

```
tests/unit/
├── backend/      # TmuxBackend adapter
├── cli/          # Main CLI group, utility functions
├── commands/     # Click command wrappers (add, init, list, remove, …)
├── core/         # Config, profiles, startup
├── health/       # Checker, monitor, logger, state machine
├── ssh/          # Forward spec parsing, SSH command building
└── tmux/         # Session, windows, diagnostics
```

---

## 2. E2E Tests (real tmux + sshd inside Docker)

E2E tests run inside a Docker container that has tmux + an SSH server installed,
so they exercise the **real** stack — no mocks anywhere.

### Run all E2E tests

```bash
./tests/e2e/scripts/run.sh
```

That script builds the Docker image (first run takes a minute) and runs the
full E2E suite inside it.

### Interactive debugging shell

```bash
./tests/e2e/scripts/run.sh bash
```

Drops you into a `bash` shell **inside** the container with tmux + sshd
already configured. Useful when an E2E test fails and you want to poke
around — run `portmux init`, attach to the session, etc.

### What the E2E tests cover

```
tests/e2e/
├── scripts/        # Dockerfile, entrypoint.sh, run.sh
├── conftest.py     # fixtures: session_name, free_port, tcp_server, polling helpers
├── session/        # init, destroy, force flags, isolation between sessions
├── forward/        # add/remove/refresh, real traffic flow through the tunnel
├── health/         # healthy / dead / unhealthy detection, diagnostics
└── monitor/        # auto-restart on tunnel death, max retries, log output
```

### Key E2E fixtures (from `tests/e2e/conftest.py`)

| Fixture | What it gives you |
|---|---|
| `session_name` | A unique tmux session name per test, with auto-teardown |
| `portmux_service` / `monitored_service` | Real `TmuxBackend` + temp log path |
| `tcp_server` | A threaded echo server on a dynamic port (target for tunnels) |
| `free_port` | Factory returning unused ephemeral ports |
| `wait_for_port()` / `wait_for_condition()` | Polling helpers (avoids fixed `sleep`) |

---

## 3. Combined Runs

Run **everything** (unit + e2e — needs Docker):

```bash
uv run pytest tests/unit/ && ./tests/e2e/scripts/run.sh
```

Run unit tests with coverage in CI:

```bash
uv run pytest tests/ -m "not e2e" --cov=portmux --cov-report=term-missing
```

---

## 4. Quick Reference Cheat-Sheet

| Goal | Command |
|---|---|
| All unit tests | `uv run pytest tests/unit/` |
| Unit tests via marker | `uv run pytest tests/ -m "not e2e"` |
| One file | `uv run pytest tests/unit/commands/test_add.py` |
| One test by name | `uv run pytest path::test_name` |
| Verbose | `uv run pytest tests/unit/ -v` |
| Stop on first fail | `uv run pytest tests/unit/ -x` |
| Coverage (terminal) | `uv run pytest --cov=portmux` |
| Coverage (HTML) | `uv run pytest --cov=portmux --cov-report=html` |
| All E2E tests | `./tests/e2e/scripts/run.sh` |
| E2E debug shell | `./tests/e2e/scripts/run.sh bash` |

---

## 5. Talking Point for the Viva

> "We have two test layers because they answer different questions.
> The 332 **unit tests** ask *'is each component logically correct?'* — they
> mock tmux and SSH so they run in milliseconds and can verify edge cases
> like malformed forward specs or backend errors.
> The 32 **E2E tests** ask *'does the whole system actually move bytes?'* —
> they spin up a real tmux + sshd in Docker, open a real tunnel, push real
> traffic through it, and even kill the SSH process to verify auto-reconnect.
> Unit tests catch logic bugs; E2E tests catch integration bugs that mocks
> can hide."

This framing — *unit = logic, E2E = integration* — is the answer examiners
look for when they ask "why two test suites?".
