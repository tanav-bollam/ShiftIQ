const API_BASES = [
  import.meta.env.VITE_API_BASE,
  'http://127.0.0.1:8000',
  'http://localhost:8000',
].filter(Boolean);

async function request(path, options = {}) {
  let lastError;
  for (const base of API_BASES) {
    try {
      const res = await fetch(`${base}${path}`, {
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return res.json();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('API request failed');
}

export const api = {
  health: () => request('/health'),
  employees: () => request('/employees'),
  summary: () => request('/insights/summary'),
  dailyRevenue: () => request('/insights/daily-revenue'),
  heatmap: () => request('/insights/heatmap'),
  overstaffing: () => request('/insights/overstaffing'),
  topItems: () => request('/insights/top-items'),
  forecast: () => request('/forecast/next-week'),
  generateSchedule: (week = '2024-03-04') => request(`/schedule/generate?week_start=${week}`, { method: 'POST' }),
  currentSchedule: () => request('/schedule/current'),
  labor: () => request('/labor/summary'),
  requestAvailability: (week = '2024-03-04') => request(`/messaging/request-availability?week_start=${week}`, { method: 'POST' }),
  messages: () => request('/messaging/log'),
  findBackups: (body) => request('/callouts/find-backups', { method: 'POST', body: JSON.stringify(body) }),
  confirmBackup: (body) => request('/callouts/confirm-backup', { method: 'POST', body: JSON.stringify(body) }),
  chat: (body) => request('/chat', { method: 'POST', body: JSON.stringify(body) }),
};

export function currency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
