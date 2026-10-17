# Platform Compatibility (Windows / WSL2 / macOS / Linux)

How Paradox Jarvis Ultra behaves on each host OS, what Phase 5 fixed,
and what is still limited. Install entry points live in
[Installation](install.md); this page is the compatibility matrix, not a
second installer.

## Status matrix

| Area | Linux | WSL2 | macOS | Native Windows |
|---|---|---|---|---|
| Install | `install.sh` ([Linux](linux.md)) | `install.sh` inside WSL ([WSL2](wsl2.md)) | `install.sh` ([macOS](macos.md)) | `install.ps1` ([native Windows](windows-native.md), advanced) |
| CLI, config, memory, scheduler | Yes | Yes | Yes | Yes |
| `jarvis start/stop/status` daemon | Yes | Yes (nohup, no systemd) | Yes (launchd path via gateway) | Yes (hidden console, `CREATE_NO_WINDOW`) |
| Sandboxed subprocess (`run_sandboxed`) | Yes | Yes | Yes | Yes (own process group; `SYSTEMROOT`/`TEMP` passed through) |
| File tools with an allowed-dirs boundary | Yes | Yes | Yes | **Refused** — see below |
| File tools with no boundary | Yes (legacy open, no containment claimed) | Yes | Yes | Yes (legacy open, no containment claimed) |
| Mini-SWE agent / SWE-bench harness timeout kill | Yes | Yes | Yes | Only with Git Bash (`bash` on PATH); else a clear error |
| Hybrid runner cell lock | Yes (`flock`) | Yes (`flock`) | Yes (`flock`) | Yes (`msvcrt` byte-range lock) |
| Slack daemon spawn / stop | Yes | Yes | Yes | Yes (no more `os.kill(pid, 0)` probe) |
| iMessage | No (macOS-only by design) | No | Yes | No |
| Pearl mining (CPU / RAPL / Docker) | Yes | Docker-dependent | Apple Silicon path only | Not supported / untested |
| Screen capture | `mss` / Pillow | `mss` / Pillow | `mss` / Pillow | Built-in PowerShell / .NET |

## What Phase 5 changed

One shared module — `src/openjarvis/core/platform.py` — now owns the
platform branches that used to be scattered and inconsistent:

- `platform_id()` / `is_windows()` / `is_macos()` / `is_linux()` /
  `is_wsl()` — WSL detection via `WSL_DISTRO_NAME` / `WSL_INTEROP` or the
  `/proc/version` kernel string. `platform_id()` returns `"darwin"` for
  macOS to match the analytics event vocabulary.
- `detached_spawn_kwargs()` — `start_new_session=True` on POSIX,
  `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` on Windows (CPython's
  Windows `_execute_child` silently ignores `start_new_session`).
- `bash_argv(command)` — `bash -lc` when bash exists, `sh -c` as the
  POSIX fallback, and a loud `RuntimeError` on Windows without bash
  instead of running bash commands under the wrong shell.
- `kill_process_tree(pid)` — `killpg` SIGTERM → SIGKILL on POSIX,
  `taskkill /T` → `taskkill /F /T` on Windows (Windows has no SIGKILL).

Call sites fixed to use it: the subprocess sandbox (its
`preexec_fn=os.setsid` raised on Windows), the mini-SWE bash runner, the
SWE-bench harness hard-timeout helper, the hybrid runner cell lock (its
unconditional `import fcntl` made the whole module unimportable on
Windows), the Minions default log dir (was hardcoded `/tmp`), and the
Slack / iMessage daemons (their `os.kill(pid, 0)` liveness probe
**killed the process it was probing** on Windows, because there
`os.kill` maps any signal to `TerminateProcess`).

Already portable before Phase 5 and left alone: the daemon state lock,
the GUI lifecycle helpers, the memory fact-store lock, the code
interpreter (`preexec_fn` already POSIX-gated), Pearl subprocess
teardown (`Popen.terminate()` / `kill()`), and the `/dev/null` sentinel
in `apply_patch` (a git patch-format token, not a filesystem path).

## Known limitations (not fixed, by design or by scope)

- **File tools refuse on native Windows when a boundary is configured.**
  The descriptor-based TOCTOU open (`open_within` /
  `open_for_write_within`) needs `O_NOFOLLOW` + `dir_fd`, which Windows
  does not provide. Refusing is the fail-closed choice: a
  `resolve-then-open` fallback would re-introduce the symlink-swap race
  the TOCTOU helpers exist to close. Without a configured boundary the
  legacy string open is used and no containment is claimed.
- **POSIX permission bits are best-effort on Windows.** Vault /
  credential files are written with `0o600` / `0o700`, but Windows
  `os.chmod` only honours the read-only bit — there are no POSIX ACLs.
  The Windows keychain backend is additionally untested.
- **Real Windows / macOS testing has not happened.** Phase 5 was
  implemented and tested on Linux with mocked platform differences
  (`sys.platform`, `os.name`, fake `msvcrt`). No real Windows or macOS
  machine, no real keychain daemon, and no live desktop run were
  involved. Treat native-Windows behaviour as implemented-but-unverified
  until it is exercised on a real machine with the owner's go-ahead.
- **Mining is Linux-oriented.** RAPL energy sampling reads
  `/sys/class/powercap` (Linux-only, guarded by `exists()`); Pearl
  mining on Windows is unsupported; macOS mining uses the separate
  Apple Silicon path.
- **WSL2 notes.** Run inside the WSL2 shell, not from PowerShell, and
  keep `OPENJARVIS_HOME` on the Linux filesystem rather than under
  `/mnt/<drive>`: Windows drives mounted into WSL2 differ in line
  endings, permissions, and file-locking behaviour.

## Line endings

The repo is LF-only (no CRLF files). Git on Windows should preserve
that (`core.autocrlf=input` or `false`); the patch tool tolerates CRLF
inside patch text.
