import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Bot, CalendarDays, Gauge, LineChart, Siren, UsersRound } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api.js';
import Insights from './pages/Insights.jsx';
import Forecast from './pages/Forecast.jsx';
import Employees from './pages/Employees.jsx';
import Schedule from './pages/Schedule.jsx';
import Callout from './pages/Callout.jsx';
import Chat from './pages/Chat.jsx';

const nav = [
  { section: 'Analytics', items: [
    { to: '/', label: 'Sales Insights', icon: BarChart3 },
    { to: '/forecast', label: 'Forecast', icon: LineChart },
  ] },
  { section: 'Workforce', items: [
    { to: '/employees', label: 'Employees', icon: UsersRound },
    { to: '/schedule', label: 'Schedule', icon: CalendarDays },
    { to: '/callout', label: 'Call-out Manager', icon: Siren },
  ] },
  { section: 'AI', items: [
    { to: '/chat', label: 'Manager Chat', icon: Bot },
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

function Sidebar({ labor }) {
  return (
    <aside className="sidebar">
      <Link className="logo" to="/">
        <div className="logo-mark">Shift<span>IQ</span></div>
        <div className="logo-sub">POS Scheduling Agent</div>
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
      <div className="sidebar-bottom"><LaborGauge labor={labor} /></div>
    </aside>
  );
}

function Topbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const titles = {
    '/': 'Sales Insights',
    '/forecast': 'Demand Forecast',
    '/employees': 'Employee Roster',
    '/schedule': 'Weekly Schedule',
    '/callout': 'Call-out Manager',
    '/chat': 'Manager Chat',
  };
  return (
    <header className="topbar">
      <div className="topbar-title">{titles[location.pathname] || 'ShiftIQ'}</div>
      <div className="topbar-actions">
        <span className="badge green">Live Data</span>
        <button className="btn" onClick={() => navigate('/chat')}><Bot size={15} /> Ask Agent</button>
        <button className="btn primary" onClick={() => navigate('/schedule')}>View Schedule</button>
      </div>
    </header>
  );
}

export default function App() {
  const [labor, setLabor] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(async () => {
    const [laborData, scheduleData] = await Promise.all([api.labor(), api.currentSchedule()]);
    setLabor(laborData);
    setSchedule(scheduleData);
    setRefreshKey(key => key + 1);
  }, []);

  useEffect(() => { refresh().catch(() => {}); }, [refresh]);

  const context = useMemo(() => ({ labor, schedule, refresh, refreshKey }), [labor, schedule, refresh, refreshKey]);

  return (
    <div className="shell">
      <Sidebar labor={labor} />
      <main className="main">
        <Topbar />
        <section className="content">
          <Routes>
            <Route path="/" element={<Insights app={context} />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/employees" element={<Employees app={context} />} />
            <Route path="/schedule" element={<Schedule app={context} />} />
            <Route path="/callout" element={<Callout app={context} />} />
            <Route path="/chat" element={<Chat />} />
          </Routes>
        </section>
      </main>
    </div>
  );
}
