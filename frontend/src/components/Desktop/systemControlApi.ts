// Phase 6 desktop system-control + desktop-settings API client.
// Consequential actions are two-step by design: grant a single-use
// approval for the EXACT (action, params) pair, then execute. The server
// consumes the grant on first use; a replay is refused (403).

export interface DesktopAction {
  action: string;
  consequential: boolean;
  params: Record<string, string>;
}

export interface DesktopSettings {
  theme: 'dark' | 'light' | 'system';
  accent: 'violet' | 'cyan' | 'amber' | 'emerald' | 'rose';
  density: 'comfortable' | 'compact';
  start_view: 'chat' | 'system-control' | 'settings';
  reduced_motion: boolean;
  confirm_before_consequential: boolean;
}

export interface SystemControlResult {
  action: string;
  result: Record<string, unknown>;
}

function authHeaders(apiKey?: string): Record<string, string> {
  return apiKey ? { Authorization: `Bearer ${apiKey}` } : {};
}

async function request<T>(
  apiUrl: string,
  path: string,
  init: RequestInit | undefined,
  apiKey?: string,
): Promise<T> {
  const res = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { ...authHeaders(apiKey), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // keep status text
    }
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchDesktopActions(
  apiUrl: string,
  apiKey?: string,
): Promise<DesktopAction[]> {
  const data = await request<{ actions: DesktopAction[] }>(
    apiUrl,
    '/v1/desktop/system-control/actions',
    undefined,
    apiKey,
  );
  return data.actions ?? [];
}

/** Grant a single-use approval, then execute. Never skips the grant. */
export async function executeSystemControl(
  apiUrl: string,
  action: string,
  params: Record<string, unknown>,
  apiKey?: string,
): Promise<SystemControlResult> {
  const actionMeta = (await fetchDesktopActions(apiUrl, apiKey)).find(
    (a) => a.action === action,
  );
  if (actionMeta?.consequential) {
    await request(apiUrl, '/v1/approvals/tool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool_name: 'desktop.system_control',
        arguments: { action, params },
      }),
    }, apiKey);
  }
  return request<SystemControlResult>(
    apiUrl,
    '/v1/desktop/system-control/execute',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, params }),
    },
    apiKey,
  );
}

export async function fetchDesktopSettings(
  apiUrl: string,
  apiKey?: string,
): Promise<DesktopSettings> {
  return request<DesktopSettings>(apiUrl, '/v1/desktop/settings', undefined, apiKey);
}

export async function saveDesktopSettings(
  apiUrl: string,
  settings: DesktopSettings,
  apiKey?: string,
): Promise<DesktopSettings> {
  return request<DesktopSettings>(
    apiUrl,
    '/v1/desktop/settings',
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    },
    apiKey,
  );
}
