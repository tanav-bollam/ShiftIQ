import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Bell, Bot, CalendarDays, Database, Gauge, LayoutDashboard, LineChart, LogIn, MessageSquare, Repeat2, Siren, TableProperties, UserRound, UsersRound, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api.js';
import Overview from './pages/Overview.jsx';
import Insights from './pages/Insights.jsx';
import Forecast from './pages/Forecast.jsx';
import Employees from './pages/Employees.jsx';
import Schedule from './pages/Schedule.jsx';
import Callout from './pages/Callout.jsx';
import Chat from './pages/Chat.jsx';
import EmployeePortal from './pages/EmployeePortal.jsx';
import UploadData from './pages/UploadData.jsx';
import DataManager from './pages/DataManager.jsx';

const adminNav = [
  { section: 'Command', items: [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
  ] },
  { section: 'Analytics', items: [
    { to: '/insights', label: 'Sales Insights', icon: BarChart3 },
    { to: '/forecast', label: 'Forecast', icon: LineChart },
  ] },
  { section: 'Workforce', items: [
    { to: '/employees', label: 'Employees', icon: UsersRound },
    { to: '/schedule', label: 'Schedule', icon: CalendarDays },
    { to: '/callout', label: 'Call-out Manager', icon: Siren },
  ] },
  { section: 'AI Tools', items: [
    { to: '/chat', label: 'Manager Chat', icon: Bot },
    { to: '/upload', label: 'Upload Data', icon: Database },
    { to: '/data', label: 'Data Manager', icon: TableProperties },
  ] },
];

const employeeNav = [
  { section: 'Employee', items: [
    { to: '/employee', label: 'Home', icon: LayoutDashboard },
    { to: '/employee/schedule', label: 'My Schedule', icon: CalendarDays },
    { to: '/employee/availability', label: 'Availability', icon: Bell },
    { to: '/employee/requests', label: 'Requests', icon: Repeat2 },
    { to: '/employee/messages', label: 'Messages', icon: MessageSquare },
    { to: '/employee/profile', label: 'Profile', icon: UserRound },
  ] },
];

function LaborGauge({ labor }) {
  const pct = labor?.weekly?.labor_pct ?? 0;
  const status = labor?.weekly?.status || 'ok';
  return (
    <div className="labor-gauge">
      <div className="gauge-label"><Gauge size={13} /> Labor % of Revenue</div>
      <div className="gauge-row">
        <div className={`gauge-val ${status}`}>{pct}%</div>
        <div className="gauge-target">Target: 30%</div>
      </div>
      <div className="gauge-bar"><div className={`gauge-fill ${status}`} style={{ width: `${Math.min(pct, 60)}%` }} /></div>
    </div>
  );
}

function EmployeeWeekCard({ schedule, employeeId, employee }) {
  const shifts = schedule?.schedule?.flatMap(shift => shift.assigned
    .filter(person => person.employee_id === employeeId)
    .map(() => shift)) || [];
  const hours = shifts.reduce((sum, shift) => sum + (shift.time_end - shift.time_start), 0);
  const next = shifts[0];
  return (
    <div className="employee-week-card">
      <div className="gauge-label"><CalendarDays size={13} /> This Week</div>
      <div className="gauge-row">
        <div className="gauge-val ok">{hours}h</div>
        <div className="gauge-target">{shifts.length} shifts</div>
      </div>
      {employee && <div className="employee-login-name">{employee.name}</div>}
      <div className="login-hint">{next ? `Next: ${next.day} ${next.shift}` : 'Generate schedule for shifts'}</div>
    </div>
  );
}

function Sidebar({ labor, mode, onToggleMode, onOpenEmployeeSelector, schedule, employeeId, employee }) {
  const nav = mode === 'admin' ? adminNav : employeeNav;
  return (
    <aside className="sidebar">
      <Link className="logo" to={mode === 'admin' ? '/' : '/employee'}>
        <div className="logo-mark">Shift<span>IQ</span></div>
        <div className="logo-sub">{mode === 'admin' ? 'POS Scheduling Agent' : 'Employee Portal'}</div>
      </Link>
      <nav className="nav">
        {nav.map(group => (
          <div key={group.section}>
            <div className="nav-section">{group.section}</div>
            {group.items.map(item => {
              const Icon = item.icon;
              return (
                <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                  <Icon size={16} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="sidebar-bottom">
        {mode === 'admin' ? <LaborGauge labor={labor} /> : <EmployeeWeekCard schedule={schedule} employeeId={employeeId} employee={employee} />}
        <button className="login-button" type="button" onClick={onToggleMode}>
          <LogIn size={16} />
          <span>{mode === 'admin' ? 'Employee Login' : 'Admin Login'}</span>
        </button>
        {mode === 'employee' && (
          <button className="switch-employee-button" type="button" onClick={onOpenEmployeeSelector}>
            <UsersRound size={15} />
            <span>Switch Employee</span>
          </button>
        )}
        <div className="login-hint">{mode === 'admin' ? 'Switch to employee dashboard' : 'Switch back to admin dashboard'}</div>
      </div>
    </aside>
  );
}

function EmployeeLoginModal({ employees, selectedEmployeeId, onSelect, onClose }) {
  return (
    <div className="modal-backdrop" role="presentation">
      <div className="employee-login-modal" role="dialog" aria-modal="true" aria-labelledby="employee-login-title">
        <div className="modal-head">
          <div>
            <div className="section-kicker">Employee Login</div>
            <h2 id="employee-login-title">Choose your employee profile</h2>
            <p>Select a staff member to preview the employee dashboard. Real authentication can replace this later.</p>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close employee login"><X size={18} /></button>
        </div>
        <div className="employee-picker-list">
          {employees.map(employee => (
            <button
              className={`employee-picker-card ${Number(employee.id) === selectedEmployeeId ? 'active' : ''}`}
              type="button"
              key={employee.id}
              onClick={() => onSelect(Number(employee.id))}
            >
              <div className="employee-picker-avatar">{employee.name.split(' ').map(part => part[0]).join('').slice(0, 2)}</div>
              <div>
                <strong>{employee.name}</strong>
                <span>{employee.role} - {employee.skills.slice(0, 3).join(', ')}</span>
                <small>{employee.scheduled_hours}/{employee.max_hours}h scheduled - {employee.availability}</small>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Topbar({ mode, employeeId, refreshKey }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const adminTitles = {
    '/': 'Overview',
    '/insights': 'Sales Insights',
    '/forecast': 'Demand Forecast',
    '/employees': 'Employee Roster',
    '/schedule': 'Weekly Schedule',
    '/callout': 'Call-out Manager',
    '/chat': 'Manager Chat',
    '/upload': 'Upload Data',
    '/data': 'Data Manager',
  };
  const employeeTitles = {
    '/employee': 'Employee Home',
    '/employee/schedule': 'My Schedule',
    '/employee/availability': 'Availability',
    '/employee/requests': 'Shift Requests',
    '/employee/messages': 'Messages',
    '/employee/profile': 'Profile',
  };
  const titles = mode === 'admin' ? adminTitles : employeeTitles;
  useEffect(() => {
    api.notifications(mode, mode === 'employee' ? employeeId : undefined)
      .then(setNotifications)
      .catch(() => setNotifications({ counts: { all: 0 }, notifications: [] }));
  }, [mode, employeeId, refreshKey, location.pathname]);

  const notificationItems = notifications?.notifications || [];
  const notificationCount = notifications?.counts?.all || 0;

  const openNotification = (item) => {
    setShowNotifications(false);
    if (item.action_url) navigate(item.action_url);
  };

  return (
    <header className="topbar">
      <div className="topbar-title">{titles[location.pathname] || 'ShiftIQ'}</div>
      <div className="topbar-actions">
        <span className="badge green">{mode === 'admin' ? 'Admin View' : 'Employee View'}</span>
        <button
          className={`notification-button ${showNotifications ? 'active' : ''}`}
          type="button"
          aria-label="Notifications"
          onClick={() => setShowNotifications(open => !open)}
        >
          <Bell size={16} />
          {notificationCount > 0 && <span>{notificationCount}</span>}
        </button>
        {showNotifications && (
          <div className="notification-panel">
            <div className="notification-head">
              <strong>Notifications</strong>
              <span>{notificationCount} active</span>
            </div>
            <div className="notification-summary">
              {['Schedule', 'Shift Requests', 'Coverage', 'Messages'].map(category => (
                <div key={category}>
                  <strong>{notifications?.counts?.[category] || 0}</strong>
                  <span>{category}</span>
                </div>
              ))}
            </div>
            <div className="notification-list">
              {notificationItems.map(item => (
                <button className={`notification-item ${item.priority}`} type="button" key={item.id} onClick={() => openNotification(item)}>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.body}</p>
                  </div>
                  <span>{item.category}</span>
                </button>
              ))}
              {!notificationItems.length && <div className="empty-state">No notifications right now.</div>}
            </div>
          </div>
        )}
        {mode === 'admin' ? (
          <>
            <button className="btn" onClick={() => navigate('/chat')}><Bot size={15} /> Ask Agent</button>
            <button className="btn primary" onClick={() => navigate('/schedule')}>View Schedule</button>
          </>
        ) : (
          <>
            <button className="btn" onClick={() => navigate('/employee/messages')}><MessageSquare size={15} /> Messages</button>
            <button className="btn primary" onClick={() => navigate('/employee/availability')}>Submit Availability</button>
          </>
        )}
      </div>
    </header>
  );
}

export default function App() {
  const [labor, setLabor] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [mode, setMode] = useState('admin');
  const [employees, setEmployees] = useState([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState(1);
  const [showEmployeeLogin, setShowEmployeeLogin] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const refresh = useCallback(async () => {
    const [laborData, scheduleData, employeeData] = await Promise.all([api.labor(), api.currentSchedule(), api.employees()]);
    setLabor(laborData);
    setSchedule(scheduleData);
    setEmployees(employeeData);
    setRefreshKey(key => key + 1);
  }, []);

  useEffect(() => { refresh().catch(() => {}); }, [refresh]);
  useEffect(() => {
    const isEmployeePortalRoute = location.pathname === '/employee' || location.pathname.startsWith('/employee/');
    if (isEmployeePortalRoute) setMode('employee');
  }, [location.pathname]);

  const context = useMemo(() => ({ labor, schedule, refresh, refreshKey }), [labor, schedule, refresh, refreshKey]);
  const selectedEmployee = employees.find(employee => Number(employee.id) === selectedEmployeeId);
  const toggleMode = useCallback(() => {
    if (mode === 'admin') {
      setShowEmployeeLogin(true);
      return;
    }
    setMode('admin');
    navigate('/');
  }, [mode, navigate]);

  const selectEmployee = useCallback((employeeId) => {
    setSelectedEmployeeId(employeeId);
    setMode('employee');
    setShowEmployeeLogin(false);
    navigate('/employee');
    if (!schedule?.schedule?.length) {
      api.generateSchedule().then(refresh).catch(() => {});
    }
  }, [navigate, refresh, schedule]);

  return (
    <div className="shell">
      <Sidebar
        labor={labor}
        mode={mode}
        onToggleMode={toggleMode}
        onOpenEmployeeSelector={() => setShowEmployeeLogin(true)}
        schedule={schedule}
        employeeId={selectedEmployeeId}
        employee={selectedEmployee}
      />
      <main className="main">
        <Topbar mode={mode} employeeId={selectedEmployeeId} refreshKey={refreshKey} />
        <section className="content">
          <Routes>
            <Route path="/" element={<Overview app={context} />} />
            <Route path="/insights" element={<Insights app={context} />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/employees" element={<Employees app={context} />} />
            <Route path="/schedule" element={<Schedule app={context} />} />
            <Route path="/callout" element={<Callout app={context} />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/upload" element={<UploadData app={context} />} />
            <Route path="/data" element={<DataManager app={context} />} />
            <Route path="/employee" element={<EmployeePortal app={context} employeeId={selectedEmployeeId} />} />
            <Route path="/employee/schedule" element={<EmployeePortal app={context} employeeId={selectedEmployeeId} />} />
            <Route path="/employee/availability" element={<EmployeePortal app={context} employeeId={selectedEmployeeId} />} />
            <Route path="/employee/requests" element={<EmployeePortal app={context} employeeId={selectedEmployeeId} />} />
            <Route path="/employee/messages" element={<EmployeePortal app={context} employeeId={selectedEmployeeId} />} />
            <Route path="/employee/profile" element={<EmployeePortal app={context} employeeId={selectedEmployeeId} />} />
          </Routes>
        </section>
      </main>
      {showEmployeeLogin && (
        <EmployeeLoginModal
          employees={employees}
          selectedEmployeeId={selectedEmployeeId}
          onSelect={selectEmployee}
          onClose={() => setShowEmployeeLogin(false)}
        />
      )}
    </div>
  );
}
