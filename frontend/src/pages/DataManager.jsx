import { CopyPlus, RefreshCw, Save, Search, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api, currency } from '../api.js';
import { Card, ErrorState, Loading } from '../components/UI.jsx';

const DATASETS = [
  { type: 'sales', label: 'Sales', description: 'POS transactions by date, hour, item, revenue, and count.' },
  { type: 'employees', label: 'Employees', description: 'Roster, skills, wages, hours, priority, and status.' },
  { type: 'availability', label: 'Availability', description: 'Weekly availability flags for each employee.' },
  { type: 'roles', label: 'Roles', description: 'Shift windows and required role templates.' },
];

const NUMERIC_COLUMNS = new Set([
  'id',
  'employee_id',
  'hour',
  'revenue',
  'transaction_count',
  'hourly_wage',
  'max_hours',
  'priority',
  'callouts_this_month',
  'time_start',
  'time_end',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
]);

export default function DataManager({ app }) {
  const [activeType, setActiveType] = useState('sales');
  const [table, setTable] = useState(null);
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [dayFilter, setDayFilter] = useState('all');
  const [hourFilter, setHourFilter] = useState('all');
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  const load = async (type = activeType) => {
    setStatus('');
    setError(null);
    const result = await api.dataTable(type);
    if (result.status === 'error') throw new Error(result.errors.join(' '));
    setTable(result);
    setRows(result.rows || []);
  };

  useEffect(() => {
    load(activeType).catch(setError);
  }, [activeType]);

  const filteredRows = useMemo(() => {
    const text = query.trim().toLowerCase();
    return rows.filter(row => {
      if (activeType === 'sales' && dayFilter !== 'all' && row.day_of_week !== dayFilter) return false;
      if (activeType === 'sales' && hourFilter !== 'all' && String(row.hour) !== hourFilter) return false;
      if (!text) return true;
      return Object.values(row).some(value => String(value ?? '').toLowerCase().includes(text));
    });
  }, [activeType, dayFilter, hourFilter, query, rows]);

  const visibleRows = filteredRows.slice(0, 200);
  const columns = table?.columns || [];
  const salesSummary = useMemo(() => buildSalesSummary(rows), [rows]);

  const updateCell = (rowIndex, column, value) => {
    setRows(current => current.map((row, index) => {
      if (index !== rowIndex) return row;
      return { ...row, [column]: NUMERIC_COLUMNS.has(column) && value !== '' ? Number(value) : value };
    }));
  };

  const addRow = () => {
    const blank = Object.fromEntries(columns.map(column => [column, defaultValueFor(column, rows)]));
    setRows(current => [blank, ...current]);
    setStatus('New row added at the top. Save changes to write it to CSV.');
  };

  const duplicateRow = (rowIndex) => {
    setRows(current => [{ ...current[rowIndex] }, ...current]);
    setStatus('Row duplicated at the top. Save changes to keep it.');
  };

  const deleteRow = (rowIndex) => {
    setRows(current => current.filter((_, index) => index !== rowIndex));
    setStatus('Row removed from the draft. Save changes to update the CSV.');
  };

  const save = async () => {
    setStatus('Validating and saving...');
    const result = await api.saveDataTable(activeType, rows);
    if (result.status === 'error') {
      setStatus(result.errors?.join(' ') || 'Could not save table.');
      return;
    }
    await app.refresh();
    await load(activeType);
    setStatus(`${activeDataset(activeType).label} data saved. Forecasts and schedules will use the updated CSV.`);
  };

  if (error) return <ErrorState error={error} />;
  if (!table) return <Loading label="Loading data manager..." />;

  return (
    <div className="page-stack data-manager-page">
      <Card title="Data Manager">
        <div className="data-tabs">
          {DATASETS.map(dataset => (
            <button className={`data-tab ${activeType === dataset.type ? 'active' : ''}`} type="button" key={dataset.type} onClick={() => setActiveType(dataset.type)}>
              <strong>{dataset.label}</strong>
              <span>{dataset.description}</span>
            </button>
          ))}
        </div>
      </Card>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Rows</div>
          <div className="stat-val">{rows.length.toLocaleString()}</div>
          <div className="stat-sub">CSV records loaded</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Filtered</div>
          <div className="stat-val">{filteredRows.length.toLocaleString()}</div>
          <div className="stat-sub">matching current view</div>
        </div>
        {activeType === 'sales' ? (
          <>
            <div className="stat-card">
              <div className="stat-label">Total Revenue</div>
              <div className="stat-val">{currency(salesSummary.revenue)}</div>
              <div className="stat-sub">{salesSummary.transactions.toLocaleString()} transactions</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Busiest Day</div>
              <div className="stat-val">{salesSummary.peakDay}</div>
              <div className="stat-sub">highest edited revenue</div>
            </div>
          </>
        ) : (
          <>
            <div className="stat-card">
              <div className="stat-label">Columns</div>
              <div className="stat-val">{columns.length}</div>
              <div className="stat-sub">editable fields</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Source</div>
              <div className="stat-val">CSV</div>
              <div className="stat-sub">{activeType}.csv</div>
            </div>
          </>
        )}
      </div>

      <Card title={`${activeDataset(activeType).label} Editor`}>
        <div className="data-toolbar">
          <label className="search-field">
            <Search size={15} />
            <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search rows..." />
          </label>
          {activeType === 'sales' && (
            <>
              <select value={dayFilter} onChange={event => setDayFilter(event.target.value)} aria-label="Filter sales by day">
                <option value="all">All days</option>
                {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => <option value={day} key={day}>{day}</option>)}
              </select>
              <select value={hourFilter} onChange={event => setHourFilter(event.target.value)} aria-label="Filter sales by hour">
                <option value="all">All hours</option>
                {Array.from({ length: 15 }, (_, index) => index + 8).map(hour => <option value={hour} key={hour}>{hour}:00</option>)}
              </select>
            </>
          )}
          <button className="btn" type="button" onClick={() => load(activeType)}><RefreshCw size={15} /> Reload</button>
          <button className="btn" type="button" onClick={addRow}><CopyPlus size={15} /> Add Row</button>
          <button className="btn primary" type="button" onClick={save}><Save size={15} /> Save Changes</button>
        </div>

        <div className="insight-block">
          Showing {visibleRows.length.toLocaleString()} of {filteredRows.length.toLocaleString()} matching rows. Saving validates the full CSV and clears the generated schedule so forecasts and staffing use the edited data.
        </div>

        <div className="table-wrap data-editor-wrap">
          <table className="data-editor-table">
            <thead>
              <tr>
                <th>Actions</th>
                {columns.map(column => <th key={column}>{column}</th>)}
              </tr>
            </thead>
            <tbody>
              {visibleRows.map(row => {
                const rowIndex = rows.indexOf(row);
                return (
                  <tr key={`${activeType}-${rowIndex}`}>
                    <td>
                      <div className="row-actions">
                        <button className="icon-button" type="button" onClick={() => duplicateRow(rowIndex)} aria-label={`Duplicate row ${rowIndex + 1}`}><CopyPlus size={15} /></button>
                        <button className="icon-button danger-icon" type="button" onClick={() => deleteRow(rowIndex)} aria-label={`Delete row ${rowIndex + 1}`}><Trash2 size={15} /></button>
                      </div>
                    </td>
                    {columns.map(column => (
                      <td key={`${rowIndex}-${column}`}>
                        <input
                          type={NUMERIC_COLUMNS.has(column) ? 'number' : column === 'date' || column === 'week_start' ? 'date' : 'text'}
                          value={row[column] ?? ''}
                          onChange={event => updateCell(rowIndex, column, event.target.value)}
                        />
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {status && <div className={status.includes('saved') ? 'success-box' : 'insight-block'}>{status}</div>}
      </Card>
    </div>
  );
}

function activeDataset(type) {
  return DATASETS.find(dataset => dataset.type === type) || DATASETS[0];
}

function defaultValueFor(column, rows) {
  if (column === 'id') {
    const maxId = Math.max(0, ...rows.map(row => Number(row.id || 0)));
    return maxId + 1;
  }
  if (column === 'date' || column === 'week_start') return '2024-03-04';
  if (column === 'day_of_week') return 'Monday';
  if (column === 'hour') return 8;
  if (column === 'item_name') return 'New Item';
  if (column === 'status') return 'active';
  if (column === 'skills' || column === 'required_roles') return 'Cashier';
  if (NUMERIC_COLUMNS.has(column)) return 0;
  return '';
}

function buildSalesSummary(rows) {
  const byDay = {};
  let revenue = 0;
  let transactions = 0;
  rows.forEach(row => {
    const rowRevenue = Number(row.revenue || 0);
    revenue += rowRevenue;
    transactions += Number(row.transaction_count || 0);
    const day = row.day_of_week || 'Unknown';
    byDay[day] = (byDay[day] || 0) + rowRevenue;
  });
  const peakDay = Object.entries(byDay).sort((a, b) => b[1] - a[1])[0]?.[0] || 'None';
  return { revenue, transactions, peakDay };
}
