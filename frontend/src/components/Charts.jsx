import { currency } from '../api.js';

export function BarChart({ data, valueKey = 'revenue', labelKey = 'day', compact = false }) {
  const max = Math.max(...data.map(item => Number(item[valueKey] || 0)), 1);
  return (
    <div className={`bar-chart ${compact ? 'compact' : ''}`}>
      {data.map(item => {
        const value = Number(item[valueKey] || 0);
        const height = Math.max(12, Math.round((value / max) * (compact ? 132 : 160)));
        const isPeak = value > max * 0.82;
        return (
          <div className="bar-wrap" key={item[labelKey]}>
            <div className="bar-val">{currency(value).replace(',000', 'k')}</div>
            <div className={`bar ${isPeak ? 'peak' : ''}`} style={{ height }} title={`${item[labelKey]}: ${currency(value)}`} />
            <div className="bar-label">{String(item[labelKey]).slice(0, 3)}</div>
          </div>
        );
      })}
    </div>
  );
}

export function HeatmapGrid({ data }) {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const hours = Array.from(new Set(data.map(item => item.hour))).sort((a, b) => a - b);
  const max = Math.max(...data.map(item => Number(item.revenue || 0)), 1);
  const byKey = new Map(data.map(item => [`${item.day}-${item.hour}`, item]));
  return (
    <div className="heatmap">
      <div className="heatmap-cell label" />
      {days.map(day => <div className="heatmap-cell day-label" key={day}>{day.slice(0, 3)}</div>)}
      {hours.map(hour => (
        <div className="heatmap-row" key={hour}>
          <div className="heat-label">{hour > 12 ? `${hour - 12}p` : `${hour}a`}</div>
          {days.map(day => {
            const item = byKey.get(`${day}-${hour}`);
            const alpha = 0.12 + ((item?.revenue || 0) / max) * 0.78;
            return <div className="heatmap-cell" key={`${day}-${hour}`} style={{ background: `rgba(124,107,255,${alpha})` }} title={`${day} ${hour}:00 - ${currency(item?.revenue || 0)}`} />;
          })}
        </div>
      ))}
    </div>
  );
}
