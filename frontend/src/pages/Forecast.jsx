import { useEffect, useState } from 'react';
import { api, currency } from '../api.js';
import { BarChart } from '../components/Charts.jsx';
import { Card, ErrorState, Loading, Progress } from '../components/UI.jsx';

export default function Forecast() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.forecast(), api.topItems()])
      .then(([forecast, topItems]) => setData({ forecast, topItems }))
      .catch(setError);
  }, []);

  if (error) return <ErrorState error={error} />;
  if (!data) return <Loading />;

  const peak = [...data.forecast].sort((a, b) => b.predicted_revenue - a.predicted_revenue)[0];
  return (
    <div className="page-stack">
      <Card title="Next Week Demand Forecast">
        <BarChart data={data.forecast} valueKey="predicted_revenue" compact />
        <div className="insight-block">
          <strong>Forecast summary:</strong> {peak.day} is projected highest at <strong>{currency(peak.predicted_revenue)}</strong> with {peak.confidence_pct}% confidence.
        </div>
      </Card>

      <div className="grid two">
        <Card title="Staffing Needs">
          <div className="staff-grid">
            {data.forecast.map(day => (
              <div className={`staff-need ${day.staff_needed >= 5 ? 'bad' : day.staff_needed >= 4 ? 'warn' : 'ok'}`} key={day.day}>
                <div className="mini-label">{day.day.slice(0, 3)}</div>
                <div className="mini-value">{day.staff_needed}</div>
                <div className="mini-sub">staff needed</div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Forecast Confidence">
          <div className="conf-list">
            {data.forecast.map(day => (
              <div className="conf-row" key={day.day}>
                <div className="conf-label">{day.day}</div>
                <Progress value={day.confidence_pct} />
                <div className="conf-pct">{day.confidence_pct}%</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Top Selling Items by Period">
        <div className="grid two">
          <ItemList title="Weekdays" items={data.topItems.weekday} />
          <ItemList title="Weekends" items={data.topItems.weekend} />
        </div>
      </Card>
    </div>
  );
}

function ItemList({ title, items }) {
  return (
    <div>
      <div className="section-kicker">{title}</div>
      {items.map((item, index) => (
        <div className="item-row" key={item.item_name}>
          <span>{index + 1}. {item.item_name}</span>
          <strong>{currency(item.revenue)}</strong>
        </div>
      ))}
    </div>
  );
}
