export function Card({ title, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {title && <div className="card-title">{title}</div>}
      {children}
    </section>
  );
}

export function Loading({ label = 'Loading data...' }) {
  return <div className="empty-state">{label}</div>;
}

export function ErrorState({ error }) {
  return <div className="error-state">Could not load data: {error?.message || 'Unknown error'}</div>;
}

export function StatCard({ label, value, sub, tone = '' }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-val">{value}</div>
      {sub && <div className={`stat-sub ${tone}`}>{sub}</div>}
    </div>
  );
}

export function Progress({ value, max = 100, status = 'ok' }) {
  const pct = max ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return <div className="progress"><div className={`progress-fill ${status}`} style={{ width: `${pct}%` }} /></div>;
}

export function StatusBadge({ status = 'ok', children }) {
  return <span className={`status-badge ${status}`}>{children || status}</span>;
}
