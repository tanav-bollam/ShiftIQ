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

async function upload(path, file) {
  const form = new FormData();
  form.append('file', file);
  let lastError;
  for (const base of API_BASES) {
    try {
      const res = await fetch(`${base}${path}`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return res.json();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('Upload failed');
}

export const api = {
  health: () => request('/health'),
  employees: () => request('/employees'),
  roles: () => request('/roles'),
  dataTable: (type) => request(`/data-tables/${type}`),
  saveDataTable: (type, rows) => request(`/data-tables/${type}`, { method: 'PUT', body: JSON.stringify({ rows }) }),
  staffingThresholds: () => request('/staffing-thresholds'),
  updateStaffingThresholds: (thresholds) => request('/staffing-thresholds', { method: 'PUT', body: JSON.stringify({ thresholds }) }),
  summary: () => request('/insights/summary'),
  dailyRevenue: () => request('/insights/daily-revenue'),
  heatmap: () => request('/insights/heatmap'),
  overstaffing: () => request('/insights/overstaffing'),
  topItems: () => request('/insights/top-items'),
  forecast: () => request('/forecast/next-week'),
  weatherForecast: () => request('/forecast/weather-aware'),
  generateSchedule: (week = '2024-03-04', mode = 'block') => request(`/schedule/generate?week_start=${week}&mode=${mode}`, { method: 'POST' }),
  currentSchedule: () => request('/schedule/current'),
  editShift: (body) => request('/schedule/edit-shift', { method: 'POST', body: JSON.stringify(body) }),
  labor: () => request('/labor/summary'),
  requestAvailability: (week = '2024-03-04') => request(`/messaging/request-availability?week_start=${week}`, { method: 'POST' }),
  messages: () => request('/messaging/log'),
  notifications: (mode = 'admin', employeeId) => request(`/notifications?mode=${mode}${employeeId ? `&employee_id=${employeeId}` : ''}`),
  findBackups: (body) => request('/callouts/find-backups', { method: 'POST', body: JSON.stringify(body) }),
  confirmBackup: (body) => request('/callouts/confirm-backup', { method: 'POST', body: JSON.stringify(body) }),
  shiftRequests: (employeeId) => request(`/employee/shift-requests${employeeId ? `?employee_id=${employeeId}` : ''}`),
  createShiftRequest: (body) => request('/employee/shift-requests', { method: 'POST', body: JSON.stringify(body) }),
  claimShiftRequest: (id, body) => request(`/employee/shift-requests/${id}/claim`, { method: 'POST', body: JSON.stringify(body) }),
  approveShiftRequest: (id) => request(`/employee/shift-requests/${id}/approve`, { method: 'POST' }),
  chatAgents: () => request('/chat/agents'),
  chatArtifacts: () => request('/chat/artifacts'),
  chat: (body) => request('/chat', { method: 'POST', body: JSON.stringify(body) }),
  approvals: (status) => request(`/agent-approvals${status ? `?status=${status}` : ''}`),
  approveAction: (id) => request(`/agent-approvals/${id}/approve`, { method: 'POST' }),
  rejectAction: (id) => request(`/agent-approvals/${id}/reject`, { method: 'POST' }),
  auditLog: () => request('/audit-log'),
  uploadFile: (type, file) => upload(`/upload/${type}`, file),
  previewUpload: (type, file) => upload(`/upload/${type}/preview`, file),
};

export function currency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
