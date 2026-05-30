import { Bell, CalendarDays, CheckCircle2, Clock, MessageSquare, Repeat2, Send, UserRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useLocation } from 'react-router-dom';
import { api } from '../api.js';
import { Card, ErrorState, Loading, Progress } from '../components/UI.jsx';

const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function EmployeePortal({ app, employeeId = 1 }) {
  const location = useLocation();
  const section = location.pathname.split('/')[2] || 'home';
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [availability, setAvailability] = useState(Object.fromEntries(days.map(day => [day, day !== 'sunday'])));
  const [requestType, setRequestType] = useState('Shift swap');
  const [requestNote, setRequestNote] = useState('');
  const [submittedRequest, setSubmittedRequest] = useState(null);
  const [availabilityStatus, setAvailabilityStatus] = useState('Not submitted');

  useEffect(() => {
    const currentOrGeneratedSchedule = async () => {
      const schedule = await api.currentSchedule();
      return schedule.schedule?.length ? schedule : api.generateSchedule();
    };

    Promise.all([api.employees(), currentOrGeneratedSchedule(), api.messages(), api.forecast()])
      .then(([employees, schedule, messages, forecast]) => setData({ employees, schedule, messages, forecast }))
      .catch(setError);
  }, [app.refreshKey]);

  const employee = data?.employees.find(item => Number(item.id) === employeeId);
  const shifts = useMemo(() => {
    if (!data?.schedule?.schedule) return [];
    return data.schedule.schedule
      .flatMap(shift => shift.assigned
        .filter(person => person.employee_id === employeeId)
        .map(person => ({ ...shift, assignedRole: person.role, replacement: person.replacement })))
      .sort((a, b) => dayIndex(a.day) - dayIndex(b.day) || a.time_start - b.time_start);
  }, [data, employeeId]);

  if (error) return <ErrorState error={error} />;
  if (!data || !employee) return <Loading label="Loading employee dashboard..." />;

  const nextShift = shifts[0];
  const weeklyHours = shifts.reduce((sum, shift) => sum + (shift.time_end - shift.time_start), 0);
  const employeeMessages = data.messages.filter(message => message.to === employee.name || /availability|covering|called out/i.test(message.body || ''));
  const pendingCoverage = employeeMessages.filter(message => /called out|cover/i.test(message.body || '')).length;

  const commonProps = {
    employee,
    shifts,
    weeklyHours,
    nextShift,
    employeeMessages,
    pendingCoverage,
    availability,
    setAvailability,
    availabilityStatus,
    setAvailabilityStatus,
    requestType,
    setRequestType,
    requestNote,
    setRequestNote,
    submittedRequest,
    setSubmittedRequest,
  };

  return (
    <div className="employee-page">
      <section className="employee-hero">
        <div>
          <div className="section-kicker">Employee Portal</div>
          <h1>Hi, {employee.name.split(' ')[0]}</h1>
          <p>Your shifts, availability, requests, and manager messages are all in one place.</p>
        </div>
        <div className="employee-hero-card">
          <span>Next Shift</span>
          <strong>{nextShift ? `${nextShift.day} ${nextShift.shift}` : 'No shift scheduled'}</strong>
          <small>{nextShift ? `${nextShift.time} · ${nextShift.assignedRole}` : 'Check back after schedule publish'}</small>
        </div>
      </section>

      {section === 'home' && <EmployeeHome {...commonProps} />}
      {section === 'schedule' && <EmployeeSchedule {...commonProps} />}
      {section === 'availability' && <EmployeeAvailability {...commonProps} />}
      {section === 'requests' && <EmployeeRequests {...commonProps} />}
      {section === 'messages' && <EmployeeMessages {...commonProps} />}
      {section === 'profile' && <EmployeeProfile {...commonProps} />}
    </div>
  );
}

function EmployeeHome({ employee, weeklyHours, nextShift, shifts, pendingCoverage, availabilityStatus, employeeMessages }) {
  return (
    <>
      <div className="employee-stats">
        <EmployeeStat icon={CalendarDays} label="Next Shift" value={nextShift ? nextShift.day : 'None'} sub={nextShift ? `${nextShift.time} · ${nextShift.assignedRole}` : 'Schedule not published'} />
        <EmployeeStat icon={Clock} label="This Week" value={`${weeklyHours}/${employee.max_hours}h`} sub="Scheduled hours" />
        <EmployeeStat icon={Bell} label="Action Needed" value={pendingCoverage ? `${pendingCoverage} request` : 'Clear'} sub={availabilityStatus} />
        <EmployeeStat icon={MessageSquare} label="Messages" value={employeeMessages.length} sub="Manager and agent messages" />
      </div>

      <div className="employee-grid">
        <Card title="My Week">
          <ShiftList shifts={shifts.slice(0, 5)} empty="No assigned shifts yet." />
        </Card>
        <Card title="Quick Actions">
          <div className="quick-actions">
            <Link className="quick-action" to="/employee/availability"><Send size={18} /><span>Submit Availability</span></Link>
            <Link className="quick-action" to="/employee/requests"><Repeat2 size={18} /><span>Request Swap</span></Link>
            <Link className="quick-action" to="/employee/messages"><MessageSquare size={18} /><span>View Messages</span></Link>
          </div>
        </Card>
      </div>
    </>
  );
}

function EmployeeSchedule({ shifts }) {
  return (
    <Card title="My Schedule">
      <ShiftList shifts={shifts} empty="No assigned shifts in the current generated schedule." />
    </Card>
  );
}

function EmployeeAvailability({ availability, setAvailability, availabilityStatus, setAvailabilityStatus }) {
  const selected = Object.values(availability).filter(Boolean).length;
  return (
    <div className="employee-grid">
      <Card title="Submit Weekly Availability">
        <div className="availability-grid">
          {days.map((day, index) => (
            <button
              className={`availability-day ${availability[day] ? 'active' : ''}`}
              key={day}
              onClick={() => setAvailability(prev => ({ ...prev, [day]: !prev[day] }))}
            >
              <strong>{labels[index]}</strong>
              <span>{availability[day] ? 'Available' : 'Unavailable'}</span>
            </button>
          ))}
        </div>
        <button className="btn primary" onClick={() => setAvailabilityStatus(`Submitted · ${selected} days available`)}>
          <Send size={16} /> Submit Availability
        </button>
      </Card>
      <Card title="Submission Status">
        <div className="employee-status-card">
          <CheckCircle2 size={28} />
          <strong>{availabilityStatus}</strong>
          <span>For this MVP, the submission is simulated in the employee portal. The admin availability workflow still uses the backend message log.</span>
        </div>
      </Card>
    </div>
  );
}

function EmployeeRequests({ shifts, requestType, setRequestType, requestNote, setRequestNote, submittedRequest, setSubmittedRequest }) {
  const firstShift = shifts[0];
  return (
    <div className="employee-grid">
      <Card title="New Shift Request">
        <div className="employee-form">
          <label>Request type
            <select value={requestType} onChange={event => setRequestType(event.target.value)}>
              <option>Shift swap</option>
              <option>Request cover</option>
              <option>Time off</option>
              <option>Pick up open shift</option>
            </select>
          </label>
          <label>Shift
            <select>
              {shifts.length ? shifts.map(shift => <option key={`${shift.day}-${shift.shift}`}>{shift.day} {shift.shift} · {shift.time}</option>) : <option>No shifts available</option>}
            </select>
          </label>
          <label>Note
            <textarea value={requestNote} onChange={event => setRequestNote(event.target.value)} placeholder="Add a short note for your manager..." />
          </label>
          <button className="btn primary" onClick={() => setSubmittedRequest({ type: requestType, shift: firstShift, note: requestNote || 'No note added' })}>Submit Request</button>
        </div>
      </Card>
      <Card title="Request Status">
        {submittedRequest ? (
          <div className="request-card pending">
            <strong>{submittedRequest.type}</strong>
            <span>{submittedRequest.shift ? `${submittedRequest.shift.day} ${submittedRequest.shift.shift}` : 'General request'}</span>
            <p>{submittedRequest.note}</p>
            <em>Pending manager approval</em>
          </div>
        ) : <div className="empty-state">No active requests.</div>}
      </Card>
    </div>
  );
}

function EmployeeMessages({ employeeMessages }) {
  return (
    <Card title="Messages">
      {employeeMessages.length ? (
        <div className="employee-message-list">
          {employeeMessages.slice().reverse().map((message, index) => (
            <div className="employee-message" key={`${message.to}-${index}`}>
              <strong>{message.status}</strong>
              <span>{message.body}</span>
              {/called out|cover/i.test(message.body || '') && (
                <div className="message-actions">
                  <button className="btn primary">Accept</button>
                  <button className="btn">Decline</button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : <div className="empty-state">No messages yet.</div>}
    </Card>
  );
}

function EmployeeProfile({ employee, weeklyHours }) {
  return (
    <div className="employee-grid">
      <Card title="Profile">
        <div className="profile-card">
          <div className="profile-avatar"><UserRound size={30} /></div>
          <div>
            <h2>{employee.name}</h2>
            <span>{employee.role}</span>
          </div>
        </div>
        <div className="profile-list">
          <ProfileRow label="Skills" value={employee.skills.join(', ')} />
          <ProfileRow label="Max weekly hours" value={`${employee.max_hours}h`} />
          <ProfileRow label="Scheduled this week" value={`${weeklyHours}h`} />
          <ProfileRow label="Hourly wage" value={`$${employee.hourly_wage}/hr`} />
          <ProfileRow label="Call-out covers" value={`${employee.callouts_this_month}/mo`} />
          <ProfileRow label="Availability" value={employee.availability} />
        </div>
      </Card>
      <Card title="Hours Progress">
        <div className="employee-status-card">
          <strong>{weeklyHours}/{employee.max_hours}h</strong>
          <Progress value={weeklyHours} max={employee.max_hours} />
          <span>{Math.max(0, employee.max_hours - weeklyHours)} hours remaining before cap.</span>
        </div>
      </Card>
    </div>
  );
}

function EmployeeStat({ icon: Icon, label, value, sub }) {
  return (
    <div className="employee-stat">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{sub}</small>
    </div>
  );
}

function ShiftList({ shifts, empty }) {
  if (!shifts.length) return <div className="empty-state">{empty}</div>;
  return (
    <div className="shift-list">
      {shifts.map(shift => (
        <div className="shift-row" key={`${shift.day}-${shift.shift}-${shift.assignedRole}`}>
          <div>
            <strong>{shift.day} · {shift.shift}</strong>
            <span>{shift.time} · {shift.assignedRole}</span>
          </div>
          <em>{shift.replacement ? 'Replacement' : 'Scheduled'}</em>
        </div>
      ))}
    </div>
  );
}

function ProfileRow({ label, value }) {
  return (
    <div className="profile-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function dayIndex(day) {
  return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].indexOf(day);
}
