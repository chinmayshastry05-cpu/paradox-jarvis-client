import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  executeSystemControl,
  fetchDesktopSettings,
} from './systemControlApi';

describe('systemControlApi', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('read-only actions skip the approval grant', async () => {
    const calls: string[] = [];
    vi.stubGlobal('fetch', async (url: string) => {
      calls.push(url);
      if (url.endsWith('/actions')) {
        return {
          ok: true,
          json: async () => ({
            actions: [{ action: 'list_windows', consequential: false, params: {} }],
          }),
        };
      }
      return { ok: true, json: async () => ({ action: 'list_windows', result: {} }) };
    });
    await executeSystemControl('', 'list_windows', {});
    expect(calls.some((u) => u.includes('/approvals/tool'))).toBe(false);
    expect(calls.some((u) => u.includes('/system-control/execute'))).toBe(true);
  });

  it('consequential actions grant an exact approval before executing', async () => {
    const calls: { url: string; body?: string }[] = [];
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      calls.push({ url, body: init?.body as string | undefined });
      if (url.endsWith('/actions')) {
        return {
          ok: true,
          json: async () => ({
            actions: [{ action: 'close_window', consequential: true, params: { window_id: 'string' } }],
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    });
    await executeSystemControl('', 'close_window', { window_id: 'w1' });
    const grant = calls.find((c) => c.url.includes('/approvals/tool'));
    expect(grant).toBeDefined();
    expect(JSON.parse(grant!.body!).arguments).toEqual({
      action: 'close_window',
      params: { window_id: 'w1' },
    });
    expect(calls.some((c) => c.url.includes('/system-control/execute'))).toBe(true);
  });

  it('fetches desktop settings', async () => {
    vi.stubGlobal('fetch', async () => ({
      ok: true,
      json: async () => ({ theme: 'dark', accent: 'violet' }),
    }));
    const settings = await fetchDesktopSettings('');
    expect(settings.theme).toBe('dark');
  });
});
