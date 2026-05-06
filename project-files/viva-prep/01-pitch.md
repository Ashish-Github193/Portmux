# PortMUX — Viva Pitch Notes

## The Hook (one-line thesis)

> "PortMUX turns SSH port forwards from ephemeral terminal commands into
> **observable, supervised, declarative infrastructure** — by treating each
> tunnel as a tmux window."

Lead with this. Examiners stop probing once they understand the *thesis*; if
you only describe features, they keep digging for one.

---

## Strongest Pitch Angles

### 1. The clever reuse — "tmux as a process supervisor"

Instead of writing a new daemon, we composed boring tech: tmux already gives
you persistence (survives terminal close), isolation (one window per process),
and observability (`capture-pane` = free log scraping). One window = one
tunnel = one observable, killable unit.

This is the kind of insight examiners reward — *"I didn't reinvent supervisord;
I noticed tmux already was one for shells, and made it work for tunnels."*

### 2. The problem is real and unsolved

- `ssh -L` dies with the terminal, no health check, no inventory.
- `autossh` resurrects *one* tunnel — no fleet management, no profiles, no observability.
- `sshuttle` is VPN-style routing — different problem.
- Nobody treated *"managing N tunnels as supervised processes with health checks"* as the unit of work.

### 3. Layered architecture you can defend

Walk the examiner through `CLI → Service → Backend Protocol → tmux`.
The `TunnelBackend` Protocol is the strongest design point — it means the tool
isn't married to tmux; you could swap in systemd or a custom supervisor.
That's textbook dependency inversion.

### 4. Health checks as a real subsystem, not a flag

Three *independent* signals fused into a state machine:
- **Process alive** — is the SSH PID still running?
- **Pane scan** — detects stuck passphrase prompts, DNS errors, "Connection refused".
- **TCP port probe** — verifies the local port actually accepts connections.

Async, with auto-reconnect and a buffered file logger. This is the part that
elevates the project above "CLI wrapper around ssh".

### 5. Testing discipline

**364 tests** — 332 unit (mocked) + 32 E2E (Docker, real tmux + sshd).
B.Tech projects rarely have E2E infrastructure. Mention it.

### 6. Honest limitations slide

Show the "Known Issues" — health detail dropped before display, no SSH agent
awareness, no cross-session port conflict detection. *Examiners trust honesty
more than polish.* It also gives you a clean answer to "what would you do
next?" → Phase 7 (TUI mode + agent awareness).

---

## Demo Flow (90 seconds — lands every time)

1. `portmux init` — session up, monitor starts.
2. `portmux add L 8080:localhost:80 user@server` — show the new tmux window appearing.
3. `portmux status` — show the health table.
4. `tmux send-keys` Ctrl-C inside the tunnel window to kill SSH.
5. `tail -f ~/.portmux/health.log` — watch auto-restart fire.

The visual *"I broke it, it healed itself"* beat does more work than any slide.

---

## Questions to Pre-Bake

| Question | One-liner answer |
|---|---|
| Why not `autossh`? | Single-tunnel resilience only — no fleet inventory, no profiles, no observability. |
| Why not `systemd` units? | Non-portable, requires root, no `tmux attach` to inspect a stuck tunnel. |
| Why not `screen`? | `libtmux` gives structured queries via `-F` format strings — `screen` doesn't. |
| Why Python over Go? | Click + Rich + libtmux ecosystem; readability for a 4-person team. |
| How does it scale? | Bound by tmux's window limit (thousands), not by our tool. |
| Security model? | Delegates entirely to SSH. Stores no credentials. Doesn't manage keys. *(This is a strength, not a gap.)* |
| What's "novel" here? | The *composition* — tmux-as-supervisor + pluggable backend + multi-signal health checks as one coherent tool. |
| What did you learn? | Pluggable architecture (Protocol-based DI), async health checks, Docker-based E2E testing, buffered logging discipline. |

---

## Narrative Arc (use this if asked to "walk us through the project")

1. **Pain** — Setting up dev access to a remote stack means juggling 6+ SSH tunnels; they die, you don't notice, work breaks.
2. **Existing tools** — Fragile, single-tunnel, no observability.
3. **Insight** — tmux already solves persistence + observability for shells. Reuse it for tunnels.
4. **Result** — One CLI, declarative TOML config, health checks, auto-restart, profiles, 364 tests.
5. **Honesty** — Here's what's still missing, and here's what Phase 7 fixes.
