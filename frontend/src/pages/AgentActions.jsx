import { CheckCircle2, CloudSun, ShieldCheck, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card, StatusBadge } from '../components/UI.jsx';

function fmtTime(value) {
  if (!value) return 'Pending';
  return new Date(value).toLocaleString();
}

export default function AgentActions({ app }) {
  const [approvals, setApprovals] = useState([]);
  const [audit, setAudit] = useState([]);
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [approvalData, auditData, weatherData] = await Promise.all([
        api.approvals(),
        api.auditLog(),
        api.weatherForecast(),
      ]);
      setApprovals(approvalData);
      setAudit(auditData);
      setWeather(weatherData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load().catch(() => setLoading(false)); }, []);

  const decide = async (id, action) => {
    if (action === 'approve') await api.approveAction(id);
    else await api.rejectAction(id);
    await app?.refresh?.();
    await load();
  };

  const pending = approvals.filter(item => item.status === 'pending');

  return (
    <div className="ops-page">
      <Card title="Pending Agent Approvals">
        {loading && <div className="empty-state">Loading agent operations...</div>}
        {!loading && !pending.length && <div className="empty-state">No pending approvals. Agent actions are clear.</div>}
        <div className="approval-list">
          {pending.map(item => (
            <div className="approval-row" key={item.id}>
              <div className="approval-icon"><ShieldCheck size={18} /></div>
              <div>
                <div className="section-kicker">Approval #{item.id} - {item.action_type}</div>
                <strong>{item.summary}</strong>
                <p>{item.impact}</p>
                <small>Created by {item.created_by} at {fmtTime(item.ts)}</small>
              </div>
              <div className="approval-actions">
                <button className="btn primary" onClick={() => decide(item.id, 'approve')}><CheckCircle2 size={15} /> Approve</button>
                <button className="btn" onClick={() => decide(item.id, 'reject')}><XCircle size={15} /> Reject</button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Weather-Aware Staffing">
        <div className="weather-grid">
          {weather?.recommendations?.map(item => (
            <div className="weather-card" key={item.day}>
              <div className="weather-head"><CloudSun size={16} /> <strong>{item.day}</strong></div>
              <div className="weather-temp">{item.high_f}°F</div>
              <span>{item.condition} - {item.precip_in} in rain</span>
              <p>{item.action}</p>
              <small>{item.reason}</small>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Audit Log">
        <div className="audit-list">
          {audit.map(item => (
            <div className="audit-row" key={item.id}>
              <div>
                <strong>{item.action}</strong>
                <span>{item.actor} - {item.event_type} - {fmtTime(item.ts)}</span>
              </div>
              <StatusBadge status={item.status === 'ok' || item.status === 'approved' ? 'ok' : item.status === 'pending' ? 'warn' : 'bad'}>
                {item.status}
              </StatusBadge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

