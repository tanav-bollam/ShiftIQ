import { CalendarPlus, Plus, Save, Siren, Trash2, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Fragment } from 'react';
import { useEffect, useState } from 'react';
import { api, currency } from '../api.js';
import { Card, ErrorState } from '../components/UI.jsx';

const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const shifts = ['Opening', 'Midday', 'Closing'];

export default function Schedule({ app }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState('');
  const [employees, setEmployees] = useState([]);
  const [editingShift, setEditingShift] = useState(null);
  const [draftAssignments, setDraftAssignments] = useState([]);
  const [error, setError] = useState(null);
  const schedule = app.schedule?.schedule || [];
  const explanations = app.schedule?.explanations || [];

  useEffect(() => {
    api.employees().then(setEmployees).catch(setError);
  }, [app.refreshKey]);

  const generate = async () => {
    setStatus('Optimizing...');
    await api.generateSchedule();
    await app.refresh();
    setStatus('Schedule generated');
  };

  const openEditor = (shift) => {
    if (!shift) return;
    setEditingShift(shift);
    setDraftAssignments(shift.assigned.map(person => ({ employee_id: person.employee_id, role: person.role })));
  };

  const addAssignment = () => {
    const firstEmployee = employees[0];
    const firstRole = editingShift?.required_roles?.[0] || 'Cashier';
    if (!firstEmployee) return;
    setDraftAssignments(current => [...current, { employee_id: firstEmployee.id, role: firstRole }]);
  };

  const saveEdit = async () => {
    setStatus('Saving manual edit...');
    await api.editShift({
      day: editingShift.day,
      shift_name: editingShift.shift,
      assignments: draftAssignments,
    });
    setEditingShift(null);
    await app.refresh();
    setStatus('Manual edit saved');
  };

  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack">
      <div className="action-row">
        <button className="btn primary" onClick={generate}><CalendarPlus size={16} /> Generate Optimized Schedule</button>
        <button className="btn danger" onClick={() => navigate('/callout')}><Siren size={16} /> Simulate Call-Out</button>
        <span className="muted">{status}</span>
      </div>

      <Card title="Week of March 4-10">
        {schedule.length === 0 ? <div className="empty-state">Generate a schedule to fill the weekly grid.</div> : <ScheduleGrid schedule={schedule} onEdit={openEditor} />}
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

      {editingShift && (
        <ShiftEditor
          shift={editingShift}
          employees={employees}
          assignments={draftAssignments}
          setAssignments={setDraftAssignments}
          onAdd={addAssignment}
          onSave={saveEdit}
          onClose={() => setEditingShift(null)}
        />
      )}
    </div>
  );
}

function ScheduleGrid({ schedule, onEdit }) {
  return (
    <div className="schedule-grid">
      <div />
      {days.map(day => <div className="sched-header" key={day}>{day.slice(0, 3)}</div>)}
      {shifts.map(shift => (
        <Fragment key={shift}>
          <div className="sched-role" key={`${shift}-label`}>{shift}</div>
          {days.map(day => {
            const cell = schedule.find(item => item.day === day && item.shift === shift);
            return (
              <button className={`sched-cell ${cell?.assigned?.length ? 'filled' : ''} ${cell?.manual_override ? 'manual' : ''}`} key={`${day}-${shift}`} onClick={() => onEdit(cell)} type="button">
                {cell?.manual_override && <div className="manual-badge">Manual</div>}
                {(cell?.assigned || []).map(person => (
                  <div className="sched-person" key={`${person.employee_id}-${person.role}`}>
                    <strong>{person.name.split(' ')[0]}</strong>
                    <span>{person.role}{person.replacement ? ' replacement' : ''}{person.manual_override ? ' override' : ''}</span>
                  </div>
                ))}
                {(cell?.unfilled_roles || []).map(role => <div className="sched-empty" key={role}>Open: {role}</div>)}
              </button>
            );
          })}
        </Fragment>
      ))}
    </div>
  );
}

function ShiftEditor({ shift, employees, assignments, setAssignments, onAdd, onSave, onClose }) {
  const updateAssignment = (index, patch) => {
    setAssignments(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  };

  const removeAssignment = (index) => {
    setAssignments(current => current.filter((_, itemIndex) => itemIndex !== index));
  };

  return (
    <div className="modal-backdrop" role="presentation">
      <div className="shift-editor-modal" role="dialog" aria-modal="true" aria-labelledby="shift-editor-title">
        <div className="modal-head">
          <div>
            <div className="section-kicker">Manual Schedule Edit</div>
            <h2 id="shift-editor-title">{shift.day} {shift.shift}</h2>
            <p>{shift.time} - Required roles: {shift.required_roles.join(', ')}</p>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close schedule editor"><X size={18} /></button>
        </div>

        <div className="shift-editor-body">
          <div className="editor-rows">
            {assignments.map((assignment, index) => (
              <div className="editor-row" key={`${assignment.employee_id}-${assignment.role}-${index}`}>
                <label>Employee
                  <select value={assignment.employee_id} onChange={event => updateAssignment(index, { employee_id: Number(event.target.value) })}>
                    {employees.map(employee => <option value={employee.id} key={employee.id}>{employee.name} - {employee.role}</option>)}
                  </select>
                </label>
                <label>Role
                  <select value={assignment.role} onChange={event => updateAssignment(index, { role: event.target.value })}>
                    {[...new Set([...shift.required_roles, 'Opener', 'Cashier', 'Cake', 'IceCream', 'Closer', 'Manager'])].map(role => <option value={role} key={role}>{role}</option>)}
                  </select>
                </label>
                <button className="icon-button danger-icon" type="button" onClick={() => removeAssignment(index)} aria-label="Remove assignment"><Trash2 size={17} /></button>
              </div>
            ))}
            {assignments.length === 0 && <div className="empty-state">No assignments in this shift. Add one below.</div>}
          </div>

          <div className="editor-actions">
            <button className="btn" type="button" onClick={onAdd}><Plus size={16} /> Add Assignment</button>
            <button className="btn primary" type="button" onClick={onSave}><Save size={16} /> Save Manual Edit</button>
          </div>
        </div>
      </div>
    </div>
  );
}
