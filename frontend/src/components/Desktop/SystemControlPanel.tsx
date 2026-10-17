import { useEffect, useState } from 'react';
import './desktopPhase6.css';
import {
  executeSystemControl,
  fetchDesktopActions,
  fetchDesktopSettings,
  saveDesktopSettings,
  type DesktopAction,
  type DesktopSettings,
} from './systemControlApi';
import { useAppStore } from '../../lib/store';
import { Monitor, AppWindow, Palette, ShieldCheck } from 'lucide-react';

const ACCENT_HEX: Record<DesktopSettings['accent'], string> = {
  violet: '#8b5cf6',
  cyan: '#0891b2',
  amber: '#f59e0b',
  emerald: '#10b981',
  rose: '#f43f5e',
};

const APP_CHOICES = ['calculator', 'text_editor', 'browser', 'file_manager', 'terminal'];

/**
 * Phase 6 desktop system-control surface.
 *
 * Attractive by requirement (owner, 2026-10-16): gradient hero, glass
 * cards, deliberate spacing — not a default unstyled panel. Every
 * consequential action shows an explicit approval step naming the
 * EXACT action + params before anything is sent; the server grant is
 * single-use and bound to those exact params.
 */
export function SystemControlPanel() {
  const apiUrl = useAppStore((s) => s.settings.apiUrl) || '';
  const apiKey = useAppStore((s) => s.settings.apiKey) || undefined;

  const [actions, setActions] = useState<DesktopAction[]>([]);
  const [settings, setSettings] = useState<DesktopSettings | null>(null);
  const [windowId, setWindowId] = useState('');
  const [appId, setAppId] = useState('calculator');
  const [path, setPath] = useState('');
  const [pending, setPending] = useState<{ action: string; params: Record<string, unknown> } | null>(null);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);

  useEffect(() => {
    fetchDesktopActions(apiUrl, apiKey).then(setActions).catch(() => setActions([]));
    fetchDesktopSettings(apiUrl, apiKey).then(setSettings).catch(() => setSettings(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl]);

  const isConsequential = (action: string) =>
    actions.find((a) => a.action === action)?.consequential ?? false;

  async function run(action: string, params: Record<string, unknown>) {
    setError('');
    setResult('');
    if (isConsequential(action)) {
      // Step 1: show the exact action + params and wait for the user.
      setPending({ action, params });
      return;
    }
    await doExecute(action, params);
  }

  async function doExecute(action: string, params: Record<string, unknown>) {
    setBusy(true);
    setPending(null);
    try {
      const out = await executeSystemControl(apiUrl, action, params, apiKey);
      setResult(JSON.stringify(out.result, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function updateSettings(patch: Partial<DesktopSettings>) {
    if (!settings) return;
    const next = { ...settings, ...patch };
    setSettings(next);
    setSettingsSaved(false);
    try {
      await saveDesktopSettings(apiUrl, next, apiKey);
      setSettingsSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="pj6-page">
      <header className="pj6-hero">
        <span className="pj6-badge">Desktop · Phase 6</span>
        <h1>System Control</h1>
        <p>
          Manage windows, launch allowlisted apps, and open files — from the desktop GUI.
          Consequential actions always ask first and need a fresh, single-use approval for
          the exact action shown. Nothing here runs a shell command.
        </p>
        <div className="pj6-status-strip">
          <div className="pj6-stat">
            <span className="pj6-stat-value">{actions.length}</span>
            <span className="pj6-stat-label">Actions available</span>
          </div>
          <div className="pj6-stat">
            <span className="pj6-stat-value">{settings ? 'Connected' : 'Unreachable'}</span>
            <span className="pj6-stat-label">Backend</span>
          </div>
          <div className="pj6-stat">
            <span className="pj6-stat-value">Always on</span>
            <span className="pj6-stat-label">Confirmation</span>
          </div>
        </div>
      </header>

      <div className="pj6-grid">
        <section className="pj6-card">
          <div className="pj6-card-head">
            <span className="pj6-card-icon" aria-hidden="true"><Monitor size={18} /></span>
            <h2>Windows</h2>
          </div>
          <p className="pj6-sub">List windows, then focus, minimise, maximise, or close one. Closing needs approval.</p>
          <div className="pj6-row">
            <button className="pj6-btn pj6-btn-ghost" disabled={busy} onClick={() => run('list_windows', {})}>
              List windows
            </button>
          </div>
          <div className="pj6-row" style={{ marginTop: 12 }}>
            <input
              className="pj6-input"
              placeholder="Window ID (e.g. w1)"
              value={windowId}
              onChange={(e) => setWindowId(e.target.value)}
            />
          </div>
          <div className="pj6-row" style={{ marginTop: 10 }}>
            <button className="pj6-btn" disabled={busy || !windowId} onClick={() => run('focus_window', { window_id: windowId })}>Focus</button>
            <button className="pj6-btn pj6-btn-ghost" disabled={busy || !windowId} onClick={() => run('minimize_window', { window_id: windowId })}>Minimise</button>
            <button className="pj6-btn pj6-btn-ghost" disabled={busy || !windowId} onClick={() => run('maximize_window', { window_id: windowId })}>Maximise</button>
            <button className="pj6-btn pj6-btn-danger" disabled={busy || !windowId} onClick={() => run('close_window', { window_id: windowId })}>Close</button>
          </div>
        </section>

        <section className="pj6-card">
          <div className="pj6-card-head">
            <span className="pj6-card-icon" aria-hidden="true"><AppWindow size={18} /></span>
            <h2>Apps &amp; Files</h2>
          </div>
          <p className="pj6-sub">Launch an allowlisted app, list a folder, or open a file inside your allowed roots. Sensitive files are blocked.</p>
          <div className="pj6-row">
            <select className="pj6-select" value={appId} onChange={(e) => setAppId(e.target.value)}>
              {APP_CHOICES.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
            <button className="pj6-btn" disabled={busy} onClick={() => run('launch_app', { app_id: appId })}>Launch app</button>
          </div>
          <div className="pj6-row" style={{ marginTop: 12 }}>
            <input
              className="pj6-input"
              placeholder="Folder or file path"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            />
          </div>
          <div className="pj6-row" style={{ marginTop: 10 }}>
            <button className="pj6-btn pj6-btn-ghost" disabled={busy || !path} onClick={() => run('list_directory', { path })}>List folder</button>
            <button className="pj6-btn" disabled={busy || !path} onClick={() => run('open_path', { path })}>Open</button>
          </div>
        </section>

        <section className="pj6-card">
          <div className="pj6-card-head">
            <span className="pj6-card-icon" aria-hidden="true"><Palette size={18} /></span>
            <h2>Appearance</h2>
          </div>
          <p className="pj6-sub">Desktop theme, accent, and density. Saved to the server as soon as you pick one.</p>
          {settings ? (
            <>
              <div className="pj6-chip-row">
                {(['dark', 'light', 'system'] as const).map((t) => (
                  <button
                    key={t}
                    className={`pj6-chip ${settings.theme === t ? 'pj6-chip-selected' : ''}`}
                    onClick={() => updateSettings({ theme: t })}
                  >
                    {t[0].toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
              <div className="pj6-row" style={{ marginTop: 14 }}>
                {(Object.keys(ACCENT_HEX) as DesktopSettings['accent'][]).map((a) => (
                  <button
                    key={a}
                    title={a}
                    aria-label={`Accent ${a}`}
                    className={`pj6-swatch ${settings.accent === a ? 'pj6-swatch-selected' : ''}`}
                    style={{ background: ACCENT_HEX[a] }}
                    onClick={() => updateSettings({ accent: a })}
                  />
                ))}
              </div>
              <div className="pj6-chip-row" style={{ marginTop: 14 }}>
                {(['comfortable', 'compact'] as const).map((d) => (
                  <button
                    key={d}
                    className={`pj6-chip ${settings.density === d ? 'pj6-chip-selected' : ''}`}
                    onClick={() => updateSettings({ density: d })}
                  >
                    {d[0].toUpperCase() + d.slice(1)}
                  </button>
                ))}
              </div>
              {settingsSaved && <p className="pj6-note">Saved.</p>}
              <p className="pj6-note">
                Confirmation is always on: consequential actions need a fresh approval every
                time. No setting can turn the gate off.
              </p>
            </>
          ) : (
            <p className="pj6-note">Appearance settings are unavailable (server unreachable).</p>
          )}
        </section>
      </div>

      {pending && (
        <div className="pj6-grid" style={{ marginTop: 18 }}>
          <div className="pj6-approval" style={{ gridColumn: '1 / -1' }}>
            <div className="pj6-card-head">
              <span className="pj6-card-icon" aria-hidden="true"><ShieldCheck size={18} /></span>
              <strong>Approve this exact action?</strong>
            </div>
            <p>
              This grants ONE single-use approval for exactly what is shown below. Changing
              any value needs a new approval.
            </p>
            <code>{JSON.stringify({ action: pending.action, params: pending.params })}</code>
            <div className="pj6-row" style={{ marginTop: 12 }}>
              <button className="pj6-btn" disabled={busy} onClick={() => doExecute(pending.action, pending.params)}>
                Approve &amp; run
              </button>
              <button className="pj6-btn pj6-btn-ghost" disabled={busy} onClick={() => setPending(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="pj6-grid" style={{ marginTop: 18 }}>
          <pre className="pj6-result" style={{ gridColumn: '1 / -1' }}>{result}</pre>
        </div>
      )}
      {error && (
        <div className="pj6-grid" style={{ marginTop: 18 }}>
          <pre className="pj6-result pj6-result-error" style={{ gridColumn: '1 / -1' }}>{error}</pre>
        </div>
      )}
    </div>
  );
}
