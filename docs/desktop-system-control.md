# Desktop GUI / System Control — Phase 6

Desktop only. No Android / emulator work.

## What exists

- **Frontend surface:** `/system-control` route (sidebar → System Control)
  — `frontend/src/components/Desktop/SystemControlPanel.tsx` (gradient
  hero, glass cards, approval step, appearance card),
  `frontend/src/components/Desktop/systemControlApi.ts`,
  `frontend/src/components/Desktop/desktopPhase6.css`.
  Attractive by owner requirement (2026-10-16): clean modern visual
  design, not default-looking.
- **Backend:** `src/openjarvis/desktop/system_control.py` (action
  catalogue, validation, approval-gated dispatch, redacted results),
  `src/openjarvis/desktop/settings.py` (appearance-only settings,
  owner-only persistence).
- **REST:** `src/openjarvis/server/desktop_routes.py` — registered in
  `create_app`:
  - `GET /v1/desktop/system-control/actions`
  - `POST /v1/desktop/system-control/execute`
  - `GET / PUT /v1/desktop/settings`

## Security (unchanged posture)

- Consequential actions (focus/minimise/maximise/close window,
  launch app, open path) require a **single-use approval** for the
  exact `(action, params)` pair, granted via
  `POST /v1/approvals/tool` with tool `desktop.system_control` and
  consumed by `ConfirmationGate.consume_matching`. No blanket approval.
  Read-only actions (list windows/apps/directory) need no approval.
- **No shell / arbitrary-command action exists.** App launching is
  allowlist-only (`calculator`, `text_editor`, `browser`,
  `file_manager`, `terminal` — labels only, no executable paths).
- File paths must resolve inside allowed roots (default: home dir);
  sensitive files (`.env`, keys, credentials, …) are blocked and
  filtered from listings. Backend output is redacted before it leaves
  the service. Settings cannot disable the confirmation gate.
- Default backend is `NoOpDesktopBackend`: desktop control reports
  unavailable until a platform backend (Tauri commands / OS automation)
  is wired in via `app.state.desktop_backend`. No real desktop
  interaction happens in this phase.

## Not done / not verified

- No live desktop run: no real window/app/file action has executed
  against a real desktop. The platform backend is not implemented.
- Frontend vitest suite not run here (`node_modules` not installed in
  this worktree); backend pytest suites pass (see phase report).
- `list_directory` uses the string-level containment pre-check, not the
  descriptor-based `open_within` open — acceptable because it never
  opens a file, only lists names.
