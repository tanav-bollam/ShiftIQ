import { Send } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card, ErrorState, Loading, Progress } from '../components/UI.jsx';

export default function Employees({ app }) {
  const [employees, setEmployees] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);

  const load = () => Promise.all([api.employees(), api.messages()])
    .then(([emp, msg]) => { setEmployees(emp); setMessages(msg); })
    .catch(setError);

  useEffect(() => { load(); }, [app.refreshKey]);

  const requestAvailability = async () => {
    await api.requestAvailability();
    await load();
  };

  if (error) return <ErrorState error={error} />;
  if (!employees) return <Loading />;

  return (
    <div className="page-stack">
      <div className="action-row">
        <button className="btn primary" onClick={requestAvailability}><Send size={16} /> Send Availability Request</button>
      </div>
      <Card title="Employee Roster">
        <div className="table-wrap">
          <table className="emp-table">
            <thead><tr><th>Employee</th><th>Role</th><th>Skills</th><th>Wage</th><th>Scheduled</th><th>Availability</th><th>Status</th></tr></thead>
            <tbody>
              {employees.map(emp => (
                <tr key={emp.id}>
                  <td><strong>{emp.name}</strong><span>Call-outs: {emp.callouts_this_month}/mo</span></td>
                  <td><span className="tag role">{emp.role}</span></td>
                  <td>{emp.skills.map(skill => <span className="tag skill" key={skill}>{skill}</span>)}</td>
                  <td>${emp.hourly_wage}/hr</td>
                  <td><div className="hours-cell"><Progress value={emp.scheduled_hours} max={emp.max_hours} /><span>{emp.scheduled_hours}/{emp.max_hours}h</span></div></td>
                  <td>{emp.availability}</td>
                  <td><span className={`badge ${emp.status === 'active' ? 'green' : 'red'}`}>{emp.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title="Availability Message Log">
        {messages.length === 0 ? <div className="empty-state">No messages sent yet.</div> : (
          <div className="message-list">
            {messages.slice(-10).reverse().map((msg, index) => (
              <div className="message-row" key={`${msg.to}-${index}`}>
                <strong>{msg.to}</strong>
                <span>{msg.body}</span>
                <em>{msg.status}</em>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
