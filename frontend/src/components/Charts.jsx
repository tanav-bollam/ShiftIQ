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
  const formatHour = (hour) => {
    if (hour === 12) return '12p';
    return hour > 12 ? `${hour - 12}p` : `${hour}a`;
  };

  return (
    <div className="heatmap">
      <div className="heatmap-cell label" />
      {days.map(day => <div className="heatmap-cell day-label" key={day}>{day.slice(0, 3)}</div>)}
      {hours.map(hour => (
        <div className="heatmap-row" key={hour}>
          <div className="heat-label">{formatHour(hour)}</div>
          {days.map(day => {
            const item = byKey.get(`${day}-${hour}`);
            const revenue = item?.revenue || 0;
            const intensity = Math.max(1, Math.round((revenue / max) * 10));
            const alpha = 0.12 + (revenue / max) * 0.78;
            return (
              <div
                className="heatmap-cell heatmap-value"
                key={`${day}-${hour}`}
                style={{ background: `rgba(124,107,255,${alpha})` }}
                aria-label={`${day} ${formatHour(hour)} intensity ${intensity}/10, ${currency(revenue)} revenue`}
              >
                <div className="heat-tooltip">
                  <strong>{day.slice(0, 3)} {formatHour(hour)}: intensity {intensity}/10</strong>
                  <span>{currency(revenue)} avg revenue</span>
                  <span>{Math.round(item?.transaction_count || 0)} avg transactions</span>
                </div>
              </div>
            );
          })}
        </div>
      ))}
      <div className="heat-legend" aria-hidden="true">
        <span>Low</span>
        <div className="heat-legend-bar" />
        <span>High</span>
      </div>
    </div>
  );
}
