import { CalendarPlus, Siren } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { api, currency } from '../api.js';
import { Card } from '../components/UI.jsx';

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const shifts = ['Opening', 'Midday', 'Closing'];

export default function Schedule({ app }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState('');
  const schedule = app.schedule?.schedule || [];
  const explanations = app.schedule?.explanations || [];

  const generate = async () => {
    setStatus('Optimizing...');
    await api.generateSchedule();
    await app.refresh();
    setStatus('Schedule generated');
  };

  return (
    <div className="page-stack">
      <div className="action-row">
        <button className="btn primary" onClick={generate}><CalendarPlus size={16} /> Generate Optimized Schedule</button>
        <button className="btn danger" onClick={() => navigate('/callout')}><Siren size={16} /> Simulate Call-Out</button>
        <span className="muted">{status}</span>
      </div>

      <Card title="Week of March 4-10">
        {schedule.length === 0 ? <div className="empty-state">Generate a schedule to fill the weekly grid.</div> : <ScheduleGrid schedule={schedule} />}
        {explanations.length > 0 && (
          <div className="why-panel">
            <div className="card-title">Why These Assignments?</div>
            {explanations.slice(0, 10).map((item, index) => <div className="why-box" key={index}>{item.reason}</div>)}
          </div>
        )}
      </Card>

      <Card title="Live Labor Cost Monitor">
        <div className="guardrail-grid">
          {(app.labor?.daily || []).map(day => (
            <div className={`guardrail ${day.status}`} key={day.day}>
              <div className="mini-label">{day.day.slice(0, 3)}</div>
              <div className="mini-value">{day.labor_pct}%</div>
              <div className="mini-sub">{currency(day.labor_cost)}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ScheduleGrid({ schedule }) {
  return (
    <div className="schedule-grid">
      <div />
      {days.map(day => <div className="sched-header" key={day}>{day.slice(0, 3)}</div>)}
      {shifts.map(shift => (
        <>
          <div className="sched-role" key={`${shift}-label`}>{shift}</div>
          {days.map(day => {
            const cell = schedule.find(item => item.day === day && item.shift === shift);
            return (
              <div className={`sched-cell ${cell?.assigned?.length ? 'filled' : ''}`} key={`${day}-${shift}`}>
                {(cell?.assigned || []).map(person => (
                  <div className="sched-person" key={`${person.employee_id}-${person.role}`}>
                    <strong>{person.name.split(' ')[0]}</strong>
                    <span>{person.role}{person.replacement ? ' replacement' : ''}</span>
                  </div>
                ))}
                {(cell?.unfilled_roles || []).map(role => <div className="sched-empty" key={role}>Open: {role}</div>)}
              </div>
            );
          })}
        </>
      ))}
    </div>
  );
}
