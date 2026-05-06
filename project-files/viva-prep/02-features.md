# PortMUX — Features & How to Run Them

Every command runs from the project root after install:

```bash
uv install .
```

Global flags (must come **before** the subcommand):
`--session/-s NAME`, `--config/-c PATH`, `--verbose/-v`, `--version`

---

## 1. Session Lifecycle

| Action | Command |
|---|---|
| Create the portmux tmux session + run startup commands + start monitor | `portmux init` |
| Initialize with a named profile | `portmux init -p dev` |
| Use a custom session name | `portmux --session mysession init` |
| Use a custom config file | `portmux --config ./my-config.toml init` |
| Destroy the entire session | `portmux remove --destroy-session -f` |

**What happens on `init`:**
1. Creates a tmux session (default name: `portmux`).
2. Runs `[startup]` commands from `~/.portmux/config.toml`.
3. Auto-starts the background monitor in a `_monitor` window.

---

## 2. Port Forwards

### Local forward (`L`) — make a remote service reachable locally

```bash
portmux add L 8080:localhost:80 user@server.com
# → access remote port 80 at localhost:8080
```

### Remote forward (`R`) — expose a local service to the remote

```bash
portmux add R 9000:localhost:3000 user@server.com
# → remote can reach your local 3000 at its 9000
```

### With a specific identity key

```bash
portmux add L 5432:db.internal:5432 user@bastion -i ~/.ssh/prod_key
```

### Listing forwards

```bash
portmux list                # human-readable table (fast, no health check)
portmux list --json         # machine-readable JSON output
```

### Removing forwards

```bash
portmux remove L:8080:localhost:80          # remove specific forward (with confirm)
portmux remove --all -f                     # remove all forwards, no confirm
portmux remove --destroy-session -f         # kill the entire tmux session
```

### Refreshing (reconnecting) forwards

```bash
portmux refresh L:8080:localhost:80         # reconnect one tunnel
portmux refresh --all                       # reconnect every tunnel
portmux refresh --all --delay 2             # 2s gap between reconnects
```

**Window naming convention:** `{Direction}:{Spec}` →
`L:8080:localhost:80`, `R:9000:localhost:9000`. The `_monitor` window is
excluded from forward listings.

---

## 3. Health Monitoring

PortMUX runs three independent checks per tunnel:

- **Process alive** — is the SSH PID still running?
- **Pane scan** — detects stuck passphrase prompts, DNS errors, connection refused.
- **TCP port probe** — verifies the local port accepts connections.

### Status (one-shot health check)

```bash
portmux status              # health table + monitor status + recent errors
```

### Foreground watch (live, terminal-only — no file logging)

```bash
portmux watch                  # default 30s interval
portmux watch --interval 5     # custom interval in seconds
```

### Background monitor daemon (file-logged, auto-reconnect)

```bash
portmux monitor start       # start the daemon manually
portmux monitor stop        # stop it
portmux monitor status      # is it running?
tail -f ~/.portmux/health.log   # watch the log live
```

> Auto-started by `portmux init` when `[monitor].enabled = true` (default).
> Foreground `watch` and the background daemon do **not** duplicate logs —
> only the daemon writes to disk.

---

## 4. Profiles

Profiles let you run multiple environments (dev, prod, staging) with
different sessions, identities, and startup commands.

```bash
portmux init --profile development     # init with dev profile
portmux init --profile production      # init with prod profile
portmux profile list                   # list all configured profiles
portmux profile show dev               # show one profile's resolved config
portmux profile active                 # show the currently active profile
```

Profile values **override** base config; unset values **inherit** from `[general]`.

---

## 5. Configuration

Location: `~/.portmux/config.toml` (override with `--config PATH`).

```toml
[general]
session_name = "portmux"
default_identity = "~/.ssh/id_rsa"      # optional, auto-detected if absent
reconnect_delay = 1
max_retries = 3

[startup]
auto_execute = true
commands = [
    "portmux add L 8080:localhost:80 user@prod",
    "portmux add L 5432:db.internal:5432 user@prod",
]

[monitor]
enabled = true              # auto-start daemon on portmux init
check_interval = 30.0       # seconds between health checks
tcp_timeout = 2.0           # TCP probe timeout
auto_reconnect = true       # auto-restart dead tunnels

[profiles.development]
session_name = "portmux-dev"
default_identity = "~/.ssh/dev_key"
commands = ["portmux add L 3000:localhost:3000 user@dev"]

[profiles.production]
session_name = "portmux-prod"
commands = ["portmux add L 5432:prod-db:5432 user@bastion"]
```

**Identity resolution order:** explicit `-i` flag → `config.default_identity` → auto-detected key in `~/.ssh/`.

---

## 6. Quick Demo Script (for the viva)

```bash
# 1. Spin up
portmux init

# 2. Add a tunnel
portmux add L 8080:localhost:80 user@your-server

# 3. Show the health table
portmux status

# 4. Show the live monitor in another terminal
portmux watch

# 5. Show profiles
portmux profile list

# 6. Tear everything down
portmux remove --destroy-session -f
```

---

## 7. Command Reference (one-liner cheat-sheet)

| Command | What it does |
|---|---|
| `portmux init` | Create session, run startup, start monitor |
| `portmux init -p NAME` | Init with a profile |
| `portmux add L|R SPEC user@host [-i KEY]` | Add a forward |
| `portmux list [--json]` | List forwards (no health check) |
| `portmux remove NAME` | Remove one forward |
| `portmux remove --all -f` | Remove all forwards |
| `portmux remove --destroy-session -f` | Kill the session |
| `portmux refresh NAME` / `--all` | Reconnect a tunnel / all |
| `portmux status` | Health table + monitor status + errors |
| `portmux watch [--interval N]` | Live foreground monitor |
| `portmux monitor start|stop|status` | Background daemon control |
| `portmux profile list|show|active` | Profile inspection |
