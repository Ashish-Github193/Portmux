# PortMUX

_(Port Multiplexer and Manager)_

## Why?

- **Port** → The domain is SSH port forwarding (local & remote).
- **MUX** → Reference to tmux (your orchestration backend) and the concept of multiplexing many connections into one controlled interface.

---

## Vision

PortMUX will be a command-line **TUI tool** for orchestrating, monitoring, and dynamically managing multiple SSH port-forwarding sessions using **tmux** as the execution layer.
It abstracts tmux complexity and focuses on **port-based workflows**, letting users create, refresh, remove, and inspect forwards without manual command composition.

---

## Primary Goals

1. **Persistent Session Management**
   - A single, persistent tmux session dedicated to SSH port forwards.
   - Survives shell exits, network drops, or terminal crashes.
2. **Dynamic Control (without attaching)**
   - Add new forwards in real-time.
   - Remove forwards without touching others.
   - Refresh forwards by killing and recreating them with updated parameters.
3. **Unified Interface**
   - A TUI providing a real-time overview of active forwards, their direction (L/R), source/destination, and status.
   - Minimal manual tmux commands — everything accessible via menu or hotkeys.
4. **Scriptability**
   - CLI commands available for automation outside the TUI  
     _(e.g., `portmux add L 8080:host:80 user@host`)_.
   - Integrates into shell scripts, deployment tools, or cron jobs.

---

## System Overview

### Layers

1. **Execution Layer** → `tmux` session (`pfmgr` or `portmux`) holds SSH processes.
2. **Control Layer** → Python functions interacting with tmux non-interactively:
   - `ForwardNewPort`
   - `RemoveForwardedPort`
   - `RefreshForwardedPort`
   - `ListForwardedPorts`
3. **Presentation Layer** → TUI for human interaction:
   - Uses Python `Rich` library for creating rich TUI.
   - Load the TUI based on the running tmux session.
   - List view of all active forwards.
   - Actions bound to keys (Add, Remove, Refresh, Attach).
   - Optional log view of a selected forward.

---

## Core Features

### 1. Add Forward

- **User specifies:**
  - **Direction**: `L` (Local) / `R` (Remote)
  - **Port spec**:
    - `<local>:<remote_host>:<remote_port>`
    - `<remote>:<local_host>:<local_port>`
  - **Target SSH host**: `user@hostname`
  - **Identity file paths**: `~/home/x/<some-xyz-path>/id_rsa`
- Creates a new tmux window named `L:spec` or `R:spec`.
- Runs:
  ````bash
  ssh -N -L ...```
    or
  ```bash
  ssh -N -R ...```
  ````

## 2. Remove Forward
- Select by name or from TUI list.
- Kills the tmux window associated with that forward.

## 3. Refresh Forward
- Removes the existing forward and immediately recreates it.
- Optional reconnection delay to avoid stale TCP locks.

## 4. Inspect Forward
- Option to attach directly to the tmux window for live SSH output.

## 5. List Active Forwards
**Displays:**

- Window name
- Direction
- Spec
- Uptime

---

### Actions
- **a** → Add Forward
- **r** → Remove Forward
- **f** → Refresh Forward
- **i** → Inspect Forward
- **q** → Quit

