import { CheckCircle2, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';
import { Card, ErrorState, Loading, Progress } from '../components/UI.jsx';

export default function Callout({ app }) {
  const [employees, setEmployees] = useState(null);
  const [form, setForm] = useState({ employee_id: 2, day: 'Saturday', shift_name: 'Closing' });
  const [callout, setCallout] = useState(null);
  const [confirmed, setConfirmed] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => { api.employees().then(setEmployees).catch(setError); }, [app.refreshKey]);

  const scheduleOptions = useMemo(() => {
    const items = app.schedule?.schedule || [];
    return items.length ? items.map(item => ({ day: item.day, shift: item.shift })) : [
      { day: 'Saturday', shift: 'Closing' }, { day: 'Friday', shift: 'Closing' }, { day: 'Sunday', shift: 'Midday' },
    ];
  }, [app.schedule]);

  const find = async () => {
    const result = await api.findBackups(form);
    setCallout(result);
    setConfirmed(null);
  };

  const confirm = async (candidate) => {
    const result = await api.confirmBackup({
      called_out_id: form.employee_id,
      replacement_id: candidate.employee_id,
      day: form.day,
      shift_name: form.shift_name,
    });
    setConfirmed(result);
    await app.refresh();
  };

  if (error) return <ErrorState error={error} />;
  if (!employees) return <Loading />;

  return (
    <div className="page-stack">
      <Card title="Simulate Employee Call-Out">
        <div className="form-grid">
          <label>Employee<select value={form.employee_id} onChange={e => setForm({ ...form, employee_id: Number(e.target.value) })}>{employees.map(emp => <option value={emp.id} key={emp.id}>{emp.name} - {emp.role}</option>)}</select></label>
          <label>Shift<select value={`${form.day}|${form.shift_name}`} onChange={e => { const [day, shift_name] = e.target.value.split('|'); setForm({ ...form, day, shift_name }); }}>{scheduleOptions.map(opt => <option value={`${opt.day}|${opt.shift}`} key={`${opt.day}-${opt.shift}`}>{opt.day} - {opt.shift}</option>)}</select></label>
          <button className="btn primary" onClick={find}><Search size={16} /> Find Backups</button>
        </div>
      </Card>

      {callout && (
        <Card title={`Active Call-Out - ${callout.employee_name}`}>
          <div className="alert-box">Open shift: {callout.day} {callout.shift_name}. Ranked by availability, skill match, remaining hours, fairness, and priority.</div>
          <div className="backup-list">
            {callout.candidates.map((candidate, index) => (
              <div className={`backup-row ${index === 0 ? 'top' : ''}`} key={candidate.employee_id}>
                <div className="backup-score">{candidate.score}</div>
                <div className="backup-info">
                  <strong>{candidate.name} {index === 0 && <span className="badge green">Recommended</span>}</strong>
                  <span>{candidate.skill_match ? 'Role match' : 'Partial match'} · {candidate.hours_remaining}h left · {candidate.callouts_this_month} call-outs/mo</span>
                  <Progress value={candidate.score} />
                  <p>{candidate.message}</p>
                </div>
                <button className="btn primary" onClick={() => confirm(candidate)}><CheckCircle2 size={16} /> Confirm</button>
              </div>
            ))}
          </div>
          {confirmed && <div className="success-box">{confirmed.message.body}</div>}
        </Card>
      )}
    </div>
  );
}
