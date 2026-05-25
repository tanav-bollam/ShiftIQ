import { useEffect, useState } from 'react';
import { api, currency } from '../api.js';
import { BarChart, HeatmapGrid } from '../components/Charts.jsx';
import { Card, ErrorState, Loading, StatCard } from '../components/UI.jsx';

export default function Insights({ app }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.summary(), api.dailyRevenue(), api.heatmap(), api.overstaffing(), api.labor()])
      .then(([summary, daily, heatmap, alerts, labor]) => setData({ summary, daily, heatmap, alerts, labor }))
      .catch(setError);
  }, [app.refreshKey]);

  if (error) return <ErrorState error={error} />;
  if (!data) return <Loading />;

  const topAlert = data.alerts[0];
  const labor = data.labor.weekly;
  return (
    <div className="page-stack">
      <div className="stats-grid">
        <StatCard label="Avg Daily Revenue" value={currency(data.summary.avg_daily_revenue)} sub="8-week POS average" tone="up" />
        <StatCard label="Peak Hour" value={data.summary.peak_hour.split(' ')[1]} sub={`${data.summary.peak_hour.split(' ')[0]} avg ${currency(data.summary.peak_hour_revenue)}/hr`} />
        <StatCard label="Labor This Week" value={currency(labor.labor_cost)} sub={`${labor.labor_pct}% of forecast revenue`} tone={labor.status === 'ok' ? 'up' : 'down'} />
        <StatCard label="Overstaffed Hours" value={`${data.summary.overstaffed_hours} hrs`} sub={topAlert ? `${topAlert.day} mornings lead risk` : 'No active risk'} tone="down" />
      </div>

      <div className="grid two">
        <Card title="Revenue by Day">
          <BarChart data={data.daily} />
          <div className="insight-block">
            <strong>Agent insight:</strong> Friday and Saturday outperform the weekday baseline. Keep peak evening coverage above the weekday staffing pattern.
          </div>
        </Card>
        <Card title="Hourly Traffic Heatmap">
          <HeatmapGrid data={data.heatmap} />
          <div className="insight-block">
            <strong>Agent insight:</strong> Darker cells mark hours where revenue density supports extra cashier or closer coverage.
          </div>
        </Card>
      </div>

      <Card title="Labor Cost Guardrails">
        <div className="guardrail-grid">
          {data.labor.daily.map(day => (
            <div className={`guardrail ${day.status}`} key={day.day}>
              <div className="mini-label">{day.day.slice(0, 3)}</div>
              <div className="mini-value">{day.labor_pct}%</div>
              <div className="mini-sub">{currency(day.labor_cost)}</div>
            </div>
          ))}
        </div>
        <div className="insight-block">
          <strong>Agent insight:</strong> {topAlert ? `${topAlert.day} ${topAlert.hour}:00 is a low-revenue labor risk at ${topAlert.labor_pct}%. ${topAlert.recommendation}` : 'Current generated schedule is within guardrails.'}
        </div>
      </Card>
    </div>
  );
}
