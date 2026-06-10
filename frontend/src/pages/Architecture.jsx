import { Bot, BrainCircuit, CheckCircle2, Cloud, DatabaseZap, GitBranch, Network, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Card } from '../components/UI.jsx';

const agents = [
  ['Core Orchestrator', 'Routes manager intent to sales, schedule, coverage, labor, export, and policy tools.'],
  ['Tool Calling Agent', 'Fetches exact live ShiftIQ data rather than guessing from model memory.'],
  ['Schedule Explanation Agent', 'Explains assignments, constraints, role coverage, and unfilled slots.'],
  ['Coverage Agent', 'Ranks call-out and dropped-shift replacements using availability, skill match, hours, and fairness.'],
  ['Labor Agent', 'Finds labor percentage risks and concrete cost-saving opportunities.'],
  ['Policy Knowledge Agent', 'Retrieves grounded approval, fairness, weather, and shift-coverage policy excerpts.'],
];

const stack = [
  ['ADK LlmAgent', 'Gemini-backed orchestration with specialist agent profiles, sessions, callbacks, and artifacts.'],
  ['MCP Toolset', 'Standardized access to ShiftIQ schedule, labor, employee, weather, policy, and export tools.'],
  ['Grounding / RAG', 'Policy documents in data/knowledge are retrieved with citations before answering policy questions.'],
  ['Approval Gates', 'Risky agent actions create manager approvals before changing schedules or labor plans.'],
  ['Audit Log', 'Tool calls, approvals, schedule generation, weather lookups, and RAG searches are recorded.'],
  ['Cloud Run', 'Frontend and backend are containerized, built with Cloud Build, and deployed on Google Cloud.'],
];

export default function Architecture() {
  const [knowledge, setKnowledge] = useState(null);
  const [weather, setWeather] = useState(null);

  useEffect(() => {
    api.knowledgeOverview().then(setKnowledge).catch(() => setKnowledge(null));
    api.weatherForecast().then(setWeather).catch(() => setWeather(null));
  }, []);

  const addedCoverage = weather?.recommendations?.filter(item => item.weather_adjusted_staff > item.baseline_staff).length;

  return (
    <div className="page architecture-page">
      <section className="architecture-hero">
        <div>
          <div className="section-kicker">Track 1 Architecture</div>
          <h1>Multi-agent workforce optimization, not a single chatbot</h1>
          <p>
            ShiftIQ coordinates specialist agents, MCP tools, policy retrieval, approval gates, and audit logs so managers
            can ask for outcomes while the system safely gathers context and proposes or executes the right workflow.
          </p>
        </div>
        <div className="architecture-cloud">
          <Cloud size={28} />
          <strong>Google Cloud</strong>
          <span>Gemini + ADK + Cloud Run</span>
        </div>
      </section>

      <div className="architecture-flow">
        <div><Bot size={20} /><strong>Manager Intent</strong><span>Ask, approve, optimize</span></div>
        <div><GitBranch size={20} /><strong>Core Orchestrator</strong><span>Selects the right specialist</span></div>
        <div><Network size={20} /><strong>MCP Tools</strong><span>Live business actions</span></div>
        <div><DatabaseZap size={20} /><strong>Grounded Data</strong><span>CSV, SQLite, weather, policies</span></div>
        <div><ShieldCheck size={20} /><strong>Governance</strong><span>Approval + audit trail</span></div>
      </div>

      <div className="grid two">
        <Card title="Agent Team">
          <div className="architecture-list">
            {agents.map(([name, body]) => (
              <div className="architecture-row" key={name}>
                <BrainCircuit size={18} />
                <div><strong>{name}</strong><span>{body}</span></div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Challenge Technologies">
          <div className="architecture-list">
            {stack.map(([name, body]) => (
              <div className="architecture-row" key={name}>
                <CheckCircle2 size={18} />
                <div><strong>{name}</strong><span>{body}</span></div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid three">
        <Card title="MCP Tool Layer">
          <p className="muted">MCP exposes schedule, labor, employee, sales, coverage, weather, policy, and artifact tools as a standard interface for ADK agents.</p>
          <div className="metric-list">
            <span>Schedule tools</span>
            <span>Labor tools</span>
            <span>Weather tools</span>
            <span>Policy RAG tools</span>
          </div>
        </Card>
        <Card title="Grounding / RAG">
          <p className="muted">The Policy Knowledge Agent retrieves operating rules before answering approval, fairness, dropped-shift, or weather-staffing questions.</p>
          <div className="big-number">{knowledge?.document_count ?? '-' } docs</div>
          <div className="muted">{knowledge?.chunk_count ?? '-' } searchable chunks</div>
        </Card>
        <Card title="External Context">
          <p className="muted">Weather-aware staffing adjusts forecasts using live weather conditions and explains the demand impact.</p>
          <div className="big-number">{addedCoverage ?? '-' } adds</div>
          <div className="muted">extra coverage recommendations this week</div>
        </Card>
      </div>
    </div>
  );
}
