import { ClipboardList, FileBarChart, FileSpreadsheet, ShieldCheck, UsersRound } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { Card, ErrorState, Loading } from '../components/UI.jsx';

const uploadCards = [
  {
    type: 'sales',
    file: 'sales.csv',
    title: 'sales.csv',
    description: 'Transaction history by hour/day',
    icon: FileBarChart,
  },
  {
    type: 'employees',
    file: 'employees.csv',
    title: 'employees.csv',
    description: 'Roster, roles, wages, max hours',
    icon: UsersRound,
  },
  {
    type: 'availability',
    file: 'availability.csv',
    title: 'availability.csv',
    description: 'Weekly availability per employee',
    icon: ClipboardList,
  },
  {
    type: 'roles',
    file: 'roles.csv',
    title: 'roles.csv',
    description: 'Shift role requirements',
    icon: ShieldCheck,
  },
];

export default function UploadData({ app }) {
  const [roles, setRoles] = useState(null);
  const [status, setStatus] = useState({});
  const [error, setError] = useState(null);
  const inputs = useRef({});

  const loadRoles = () => api.roles().then(setRoles).catch(setError);

  useEffect(() => {
    loadRoles();
  }, [app.refreshKey]);

  const handleFile = async (type, file) => {
    if (!file) return;
    setStatus(prev => ({ ...prev, [type]: { state: 'uploading', label: `Uploading ${file.name}...` } }));
    try {
      const result = await api.uploadFile(type, file);
      setStatus(prev => ({ ...prev, [type]: { state: 'ok', label: `${result.file}.csv uploaded` } }));
      await Promise.all([loadRoles(), app.refresh()]);
    } catch (uploadError) {
      setStatus(prev => ({ ...prev, [type]: { state: 'error', label: uploadError.message } }));
    }
  };

  if (error) return <ErrorState error={error} />;
  if (!roles) return <Loading label="Loading upload tools..." />;

  return (
    <div className="page-stack upload-page">
      <Card title="Upload POS Data">
        <div className="upload-grid">
          {uploadCards.map(card => {
            const Icon = card.icon;
            const cardStatus = status[card.type];
            return (
              <button
                className={`upload-tile ${cardStatus?.state || ''}`}
                key={card.type}
                type="button"
                onClick={() => inputs.current[card.type]?.click()}
              >
                <input
                  ref={node => { inputs.current[card.type] = node; }}
                  type="file"
                  accept=".csv,text/csv"
                  hidden
                  onChange={event => handleFile(card.type, event.target.files?.[0])}
                />
                <Icon size={34} />
                <strong>{card.title}</strong>
                <span>{card.description}</span>
                {cardStatus && <em>{cardStatus.label}</em>}
              </button>
            );
          })}
        </div>
      </Card>

      <Card title="Shift Role Requirements">
        <div className="roles-table">
          <div className="roles-row roles-head">
            <span>Shift</span>
            <span>Hours</span>
            <span>Required Roles</span>
            <span>Min Staff</span>
          </div>
          {roles.map(role => (
            <div className="roles-row" key={role.shift_name}>
              <strong>{role.shift_name}</strong>
              <span>{formatHour(role.time_start)}-{formatHour(role.time_end)}</span>
              <div className="role-tags">
                {role.required_roles.map((item, index) => <span className="tag skill" key={`${item}-${index}`}>{item}</span>)}
              </div>
              <strong>{role.required_roles.length}</strong>
            </div>
          ))}
        </div>
        <div className="insight-block">
          <strong>Upload note:</strong> Uploading any CSV replaces the matching file in the backend data folder and clears the generated schedule so the next schedule reflects the new data.
        </div>
      </Card>
    </div>
  );
}

function formatHour(hour) {
  return `${String(hour).padStart(2, '0')}:00`;
}
