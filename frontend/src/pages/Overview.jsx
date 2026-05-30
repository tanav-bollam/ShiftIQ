import { AlertTriangle, CalendarDays, CheckCircle2, Clock, DollarSign, Send, TrendingUp, UsersRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, currency } from '../api.js';
import { Card, ErrorState, Loading, Progress, StatCard } from '../components/UI.jsx';

const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function Overview({ app }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.summary(),
      api.forecast(),
      api.employees(),
      api.currentSchedule(),
      api.labor(),
      api.overstaffing(),
      api.messages(),
      api.topItems(),
    ])
      .then(([summary, forecast, employees, schedule, labor, alerts, messages, topItems]) => {
        setData({ summary, forecast, employees, schedule, labor, alerts, messages, topItems });
      })
      .catch(setError);
  }, [app.refreshKey]);

  const generateSchedule = async () => {
    await api.generateSchedule();
    await app.refresh();
    const [employees, schedule, labor] = await Promise.all([api.employees(), api.currentSchedule(), api.labor()]);
    setData(prev => ({ ...prev, employees, schedule, labor }));
  };

  const requestAvailability = async () => {
    const sent = await api.requestAvailability();
    const messages = await api.messages();
    setData(prev => ({ ...prev, messages, availabilitySent: sent.length }));
  };

  if (error) return <ErrorState error={error} />;
  if (!data) return <Loading />;

  const weekly = data.labor.weekly;
  const saturday = data.forecast.find(item => item.day === 'Saturday') || data.forecast[0];
  const peakDay = [...data.forecast].sort((a, b) => b.predicted_revenue - a.predicted_revenue)[0];
  const scheduleSlots = data.schedule.schedule || [];
  const openRoles = scheduleSlots.reduce((sum, shift) => sum + shift.unfilled_roles.length, 0);
  const assignedCount = scheduleSlots.reduce((sum, shift) => sum + shift.assigned.length, 0);
  const pendingAvailability = Math.max(0, data.employees.length - availabilityMessageRecipients(data.messages).size);
  const topAlert = data.alerts[0];
  const todayCard = buildTodayCard(data.forecast, scheduleSlots);

  return (
    <div className="overview-page">
      <section className="overview-hero">
        <div>
          <div className="section-kicker">Operations Overview</div>
          <h1>ShiftIQ command center</h1>
          <p>Live sales, staffing, labor, schedule coverage, and employee readiness in one manager view.</p>
        </div>
        <div className="overview-actions">
          <button className="btn primary" onClick={generateSchedule}><CalendarDays size={16} /> Generate Schedule</button>
          <button className="btn" onClick={requestAvailability}><Send size={16} /> Request Availability</button>
        </div>
      </section>

      <div className="stats-grid">
        <StatCard label="Weekly Labor" value={`${weekly.labor_pct}%`} sub={`${currency(weekly.labor_cost)} of ${currency(weekly.revenue)}`} tone={weekly.status === 'ok' ? 'up' : 'down'} />
        <StatCard label="Forecast Peak" value={peakDay.day} sub={`${currency(peakDay.predicted_revenue)} projected`} tone="up" />
        <StatCard label="Schedule Coverage" value={scheduleSlots.length ? `${assignedCount} fills` : 'Not built'} sub={openRoles ? `${openRoles} roles open` : 'All generated roles covered'} tone={openRoles ? 'down' : 'up'} />
        <StatCard label="Availability" value={pendingAvailability ? `${pendingAvailability} pending` : 'Ready'} sub={`${data.messages.length} messages logged`} tone={pendingAvailability ? 'down' : 'up'} />
      </div>

      <div className="overview-grid">
        <Card title="Weekly Health">
          <div className="health-panel">
            <div className={`health-ring ${weekly.status}`}>
              <span>{weekly.labor_pct}%</span>
              <small>Labor</small>
            </div>
            <div className="health-list">
              <HealthItem icon={DollarSign} label="Target" value="30% labor guardrail" ok={weekly.labor_pct <= 30} />
              <HealthItem icon={TrendingUp} label="Peak day" value={`${peakDay.day}, ${currency(peakDay.predicted_revenue)}`} ok />
              <HealthItem icon={UsersRound} label="Saturday staff" value={`${saturday.staff_needed} forecasted staff`} ok={saturday.staff_needed >= 6} />
              <HealthItem icon={AlertTriangle} label="Labor alerts" value={`${data.alerts.length} low-revenue risk hours`} ok={data.alerts.length < 10} />
            </div>
          </div>
        </Card>

        <Card title="Today At A Glance">
          <div className="today-panel">
            <div>
              <div className="today-day">{todayCard.day}</div>
              <div className="today-revenue">{currency(todayCard.revenue)}</div>
              <div className="muted">{todayCard.staffNeeded} staff forecasted · {todayCard.confidence}% confidence</div>
            </div>
            <div className="coverage-stack">
              {todayCard.shifts.length ? todayCard.shifts.map(shift => (
                <div className="coverage-row" key={shift.shift}>
                  <span>{shift.shift}</span>
                  <strong>{shift.assigned.length}/{shift.required_roles.length}</strong>
                </div>
              )) : <div className="empty-state">Generate a schedule to see today’s shift coverage.</div>}
            </div>
          </div>
        </Card>

        <Card title="Forecast Snapshot">
          <div className="forecast-strip">
            {data.forecast.map(day => (
              <div className="forecast-day" key={day.day}>
                <div className="mini-label">{day.day.slice(0, 3)}</div>
                <div className="forecast-bar"><span style={{ height: `${Math.max(18, day.staff_needed * 10)}px` }} /></div>
                <strong>{day.staff_needed}</strong>
                <small>{currency(day.predicted_revenue)}</small>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Action Queue">
          <div className="action-list">
            <ActionItem
              tone={openRoles ? 'warn' : 'ok'}
              icon={openRoles ? AlertTriangle : CheckCircle2}
              title={openRoles ? `${openRoles} open schedule roles` : 'Schedule coverage looks complete'}
              body={openRoles ? 'Review the Schedule page for unfilled shifts before publishing.' : `${assignedCount} role assignments are ready for review.`}
              to="/schedule"
            />
            <ActionItem
              tone={pendingAvailability ? 'warn' : 'ok'}
              icon={Clock}
              title={pendingAvailability ? `${pendingAvailability} availability submissions pending` : 'Availability messages sent'}
              body={pendingAvailability ? 'Send reminders before schedule lock.' : 'The message log is ready for manager review.'}
              to="/employees"
            />
            <ActionItem
              tone={topAlert ? 'warn' : 'ok'}
              icon={AlertTriangle}
              title={topAlert ? `${topAlert.day} ${topAlert.hour}:00 labor risk` : 'No labor risk flagged'}
              body={topAlert ? `${topAlert.labor_pct}% modeled labor load on ${currency(topAlert.revenue)} revenue.` : 'Labor guardrails are currently clean.'}
              to="/"
            />
          </div>
        </Card>

        <Card title="Schedule Preview">
          <div className="overview-schedule">
            {dayOrder.map(day => {
              const shifts = scheduleSlots.filter(item => item.day === day);
              return (
                <div className="overview-day" key={day}>
                  <div className="mini-label">{day.slice(0, 3)}</div>
                  {shifts.length ? shifts.map(shift => (
                    <div className="overview-shift" key={shift.shift}>
                      <span>{shift.shift}</span>
                      <strong>{shift.assigned.length}/{shift.required_roles.length}</strong>
                    </div>
                  )) : <div className="overview-empty">No schedule</div>}
                </div>
              );
            })}
          </div>
        </Card>

        <Card title="Agent Recommendations">
          <div className="recommendation-list">
            <div className="recommendation">
              <strong>Protect the Saturday rush</strong>
              <span>Saturday is projected at {currency(saturday.predicted_revenue)} with {saturday.staff_needed} staff needed. Keep closer, cashier, cake, and ice cream coverage intact.</span>
            </div>
            <div className="recommendation">
              <strong>Watch slow morning labor</strong>
              <span>{topAlert ? `${topAlert.day} ${topAlert.hour}:00 is the clearest reduction candidate at ${topAlert.labor_pct}% labor load.` : 'No major overstaffing alert is currently active.'}</span>
            </div>
            <div className="recommendation">
              <strong>Item mix signal</strong>
              <span>Weekdays lean toward {data.topItems.weekday[0]?.item_name}; weekends lean toward {data.topItems.weekend[0]?.item_name}. Staff specialty roles around those patterns.</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function HealthItem({ icon: Icon, label, value, ok }) {
  return (
    <div className="health-item">
      <Icon size={16} />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <CheckCircle2 className={ok ? 'ok-icon' : 'warn-icon'} size={16} />
    </div>
  );
}

function ActionItem({ icon: Icon, title, body, to, tone }) {
  return (
    <Link className={`action-item ${tone}`} to={to}>
      <Icon size={17} />
      <div>
        <strong>{title}</strong>
        <span>{body}</span>
      </div>
    </Link>
  );
}

function availabilityMessageRecipients(messages) {
  return new Set(messages.filter(message => message.body?.includes('availability')).map(message => message.to));
}

function buildTodayCard(forecast, schedule) {
  const today = forecast.find(item => item.day === 'Saturday') || forecast[0];
  return {
    day: today.day,
    revenue: today.predicted_revenue,
    staffNeeded: today.staff_needed,
    confidence: today.confidence_pct,
    shifts: schedule.filter(item => item.day === today.day),
  };
}
