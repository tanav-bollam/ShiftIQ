import { Bot, BrainCircuit, CheckCircle2, Cloud, Database, DatabaseZap, GitBranch, Network, ShieldCheck, UsersRound } from 'lucide-react';
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
          <h1>Multi-agent workforce optimization for real store operations</h1>
          <p>
            ShiftIQ connects POS sales patterns, employee day-and-hour availability, weather context, labor targets,
            policy knowledge, and real-time staffing events so small businesses can build smarter schedules and handle
            call-outs with less guesswork.
          </p>
        </div>
        <div className="architecture-cloud">
          <Cloud size={28} />
          <strong>Google Cloud</strong>
          <span>Gemini + ADK + Agent Engine + Cloud Run</span>
        </div>
      </section>

      <div className="architecture-flow">
        <div><Bot size={20} /><strong>Manager Intent</strong><span>Ask, approve, optimize</span></div>
        <div><GitBranch size={20} /><strong>Core Orchestrator</strong><span>Selects the right specialist</span></div>
        <div><Network size={20} /><strong>MCP Tools</strong><span>Live business actions</span></div>
        <div><DatabaseZap size={20} /><strong>Grounded Data</strong><span>CSV, SQLite, weather, policies</span></div>
        <div><ShieldCheck size={20} /><strong>Governance</strong><span>Approval + audit trail</span></div>
      </div>

      <div className="grid three">
        <Card title="Sales">
          <p className="muted">POS-style CSV data is analyzed by day, hour, item mix, and demand pattern.</p>
        </Card>
        <Card title="Labor">
          <p className="muted">Schedules are evaluated against labor percentage targets and employee max-hour constraints.</p>
        </Card>
        <Card title="Coverage">
          <p className="muted">Call-outs and dropped shifts are matched with qualified workers using availability, skills, and fairness.</p>
        </Card>
      </div>

      <section className="architecture-section">
        <div className="section-head">
          <div>
            <div className="section-kicker">System Architecture</div>
            <h2>Separated layers for a safer agentic workflow</h2>
          </div>
          <p>
            The dashboard, business logic, agent orchestration, tool protocol layer, grounding, and cloud deployment are separate
            so each part can evolve without turning the product into one fragile script.
          </p>
        </div>
        <div className="architecture-system-grid">
          <div className="architecture-lane">
            <span>Experience Layer</span>
            <ArchitectureNode icon={UsersRound} title="React / Vite Frontend" body="Admin dashboard, employee portal, availability forms, approvals, audit log, and Manager Chat." accent />
            <ArchitectureNode icon={Cloud} title="FastAPI Backend" body="Owns API contracts, schedule generation, call-outs, data editing, messaging, and runtime state." />
          </div>
          <div className="architecture-lane">
            <span>Agent & Tool Layer</span>
            <ArchitectureNode icon={Bot} title="ADK Core Orchestrator" body="Uses Gemini through Vertex AI to coordinate specialized agents and tools." agent />
            <ArchitectureNode icon={BrainCircuit} title="Specialized Agent Team" body="Schedule explanation, call-out coverage, labor optimization, policy retrieval, and report/export workflows." agent />
            <ArchitectureNode icon={Network} title="MCP Server" body="Publishes schedule, labor, employee, weather, policy, and report tools through Model Context Protocol." accent />
          </div>
          <div className="architecture-lane">
            <span>Data & Governance</span>
            <ArchitectureNode icon={Database} title="CSV Business Data" body="Sales, employees, day-and-hour availability, and role requirements power the MVP." />
            <ArchitectureNode icon={DatabaseZap} title="SQLite Persistence" body="Stores audit logs, approval records, workflow state, and generated operational history." />
            <ArchitectureNode icon={ShieldCheck} title="Policy RAG + Weather" body="Grounded policy docs and Open-Meteo forecasts improve reliability and staffing context." warn />
          </div>
        </div>
      </section>

      <section className="architecture-section">
        <div className="section-head">
          <div>
            <div className="section-kicker">End-To-End Flowchart</div>
            <h2>From user request to governed action</h2>
          </div>
          <p>
            Manager and employee actions move through the app, agent orchestration, MCP tool calls, grounded data,
            approval checkpoints, and final schedule or message updates.
          </p>
        </div>
        <div className="app-flowchart">
          <div className="app-flow-col">
            <div className="app-flow-title">Users</div>
            <FlowBox title="Manager Dashboard" body="Asks Manager Chat, generates schedules, approves actions, reviews labor and call-outs." primary />
            <FlowBox title="Employee Portal" body="Submits day-and-hour availability, reads messages, requests swaps, claims open shifts." primary />
          </div>
          <div className="app-flow-col">
            <div className="app-flow-title">Application Layer</div>
            <FlowBox title="React / Vite Frontend" body="Routes admin and employee workflows through a shared operations UI." />
            <FlowBox title="FastAPI Backend" body="Validates requests, manages state, exposes scheduling, data, chat, audit, and approval APIs." />
          </div>
          <div className="app-flow-col">
            <div className="app-flow-title">Agent Runtime</div>
            <FlowBox title="ADK Core Orchestrator" body="Interprets intent and chooses specialist agents or tools." agent />
            <div className="app-flow-split">
              <FlowBox title="Labor Agent" body="Finds cost risks and savings." agent />
              <FlowBox title="Coverage Agent" body="Ranks backup workers." agent />
            </div>
            <div className="app-flow-split">
              <FlowBox title="Policy Agent" body="Searches grounded rules." agent />
              <FlowBox title="Schedule Agent" body="Explains assignments." agent />
            </div>
          </div>
          <div className="app-flow-col">
            <div className="app-flow-title">Tools & Data</div>
            <FlowBox title="MCP Tool Server" body="Standardizes access to schedule, labor, employee, sales, weather, policy, and report tools." primary />
            <FlowBox title="CSV + SQLite" body="Sales, employees, availability, roles, audit logs, approvals, runtime state." />
            <FlowBox title="Policy RAG + Weather API" body="Grounded scheduling policies and Open-Meteo forecast context." />
            <FlowBox title="Approval + Audit Trail" body="Risky actions are reviewed and every important step is logged." govern />
          </div>
        </div>
      </section>

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

function ArchitectureNode({ icon: Icon, title, body, accent, agent, warn }) {
  return (
    <div className={`architecture-node ${accent ? 'accent' : ''} ${agent ? 'agent' : ''} ${warn ? 'warn' : ''}`}>
      <Icon size={18} />
      <div>
        <strong>{title}</strong>
        <span>{body}</span>
      </div>
    </div>
  );
}

function FlowBox({ title, body, primary, agent, govern }) {
  return (
    <div className={`app-flow-box ${primary ? 'primary' : ''} ${agent ? 'agent' : ''} ${govern ? 'govern' : ''}`}>
      <strong>{title}</strong>
      <span>{body}</span>
    </div>
  );
}
