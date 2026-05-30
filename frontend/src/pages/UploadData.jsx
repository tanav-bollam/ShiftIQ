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
  const [pendingFiles, setPendingFiles] = useState({});
  const [previews, setPreviews] = useState({});
  const [error, setError] = useState(null);
  const inputs = useRef({});

  const loadRoles = () => api.roles().then(setRoles).catch(setError);

  useEffect(() => {
    loadRoles();
  }, [app.refreshKey]);

  const handleFile = async (type, file) => {
    if (!file) return;
    setStatus(prev => ({ ...prev, [type]: { state: 'uploading', label: `Validating ${file.name}...` } }));
    try {
      const preview = await api.previewUpload(type, file);
      setPreviews(prev => ({ ...prev, [type]: preview }));
      setPendingFiles(prev => ({ ...prev, [type]: file }));
      setStatus(prev => ({
        ...prev,
        [type]: {
          state: preview.valid ? 'ok' : 'error',
          label: preview.valid ? `${file.name} validated - review preview` : preview.errors.join(' '),
        },
      }));
    } catch (uploadError) {
      setStatus(prev => ({ ...prev, [type]: { state: 'error', label: uploadError.message } }));
    }
  };

  const confirmUpload = async (type) => {
    const file = pendingFiles[type];
    if (!file) return;
    setStatus(prev => ({ ...prev, [type]: { state: 'uploading', label: `Uploading ${file.name}...` } }));
    try {
      const result = await api.uploadFile(type, file);
      if (result.status === 'error') {
        setStatus(prev => ({ ...prev, [type]: { state: 'error', label: result.validation.errors.join(' ') } }));
        setPreviews(prev => ({ ...prev, [type]: result.validation }));
        return;
      }
      setStatus(prev => ({ ...prev, [type]: { state: 'ok', label: `${result.file}.csv uploaded` } }));
      setPendingFiles(prev => ({ ...prev, [type]: null }));
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

      {Object.keys(previews).length > 0 && (
        <Card title="Validation Preview">
          <div className="preview-grid">
            {uploadCards.filter(card => previews[card.type]).map(card => (
              <PreviewPanel
                key={card.type}
                card={card}
                preview={previews[card.type]}
                pendingFile={pendingFiles[card.type]}
                onConfirm={() => confirmUpload(card.type)}
              />
            ))}
          </div>
        </Card>
      )}

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

function PreviewPanel({ card, preview, pendingFile, onConfirm }) {
  const columns = preview.columns || [];
  return (
    <div className={`preview-panel ${preview.valid ? 'valid' : 'invalid'}`}>
      <div className="preview-head">
        <div>
          <strong>{card.title}</strong>
          <span>{preview.row_count || 0} rows - {columns.length} columns</span>
        </div>
        <span className={`badge ${preview.valid ? 'green' : 'red'}`}>{preview.valid ? 'Valid' : 'Needs Fix'}</span>
      </div>

      {preview.errors?.length > 0 && (
        <div className="alert-box">{preview.errors.join(' ')}</div>
      )}
      {preview.warnings?.length > 0 && (
        <div className="insight-block">{preview.warnings.join(' ')}</div>
      )}

      <div className="preview-columns">
        <span>Required</span>
        <p>{preview.required_columns?.join(', ')}</p>
        <span>Found</span>
        <p>{columns.join(', ')}</p>
      </div>

      <div className="table-wrap">
        <table className="preview-table">
          <thead>
            <tr>{columns.slice(0, 6).map(column => <th key={column}>{column}</th>)}</tr>
          </thead>
          <tbody>
            {(preview.preview || []).map((row, index) => (
              <tr key={index}>
                {columns.slice(0, 6).map(column => <td key={column}>{String(row[column] ?? '')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button className="btn primary" type="button" disabled={!preview.valid || !pendingFile} onClick={onConfirm}>
        Confirm Upload
      </button>
    </div>
  );
}
