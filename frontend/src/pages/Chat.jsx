import { Send } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';
import { Card } from '../components/UI.jsx';

const chips = [
  'What are my busiest hours?',
  'Am I overstaffed anywhere?',
  'Tell me about Sarah',
  "What's the Saturday forecast?",
  'How can I reduce labor by $200?',
];

const intro = (label = 'ShiftIQ agent') => `Hi, I'm the ${label}. Ask me to analyze data, explain schedules, find coverage, reduce labor, or create exports.`;

export default function Chat({ app }) {
  const [agents, setAgents] = useState([
    { id: 'orchestrator', label: 'Core Orchestrator', description: 'General manager assistant' },
    { id: 'tool_calling', label: 'Tool Calling Agent', description: 'Live ShiftIQ data access' },
    { id: 'schedule_explanation', label: 'Schedule Explanation Agent', description: 'Assignment explanations' },
    { id: 'coverage', label: 'Coverage Agent', description: 'Backup recommendations' },
    { id: 'labor', label: 'Labor Agent', description: 'Cost optimization' },
    { id: 'exports', label: 'Export Agent', description: 'Reports and files' },
  ]);
  const [activeAgent, setActiveAgent] = useState('orchestrator');
  const [threads, setThreads] = useState({
    orchestrator: [{ role: 'assistant', content: intro('Core Orchestrator') }],
  });
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const activeProfile = useMemo(() => agents.find(agent => agent.id === activeAgent) || agents[0], [agents, activeAgent]);
  const messages = threads[activeAgent] || [{ role: 'assistant', content: intro(activeProfile?.label) }];

  useEffect(() => {
    api.chatAgents()
      .then(setAgents)
      .catch(() => {});
  }, []);

  const switchAgent = (agentId) => {
    const profile = agents.find(agent => agent.id === agentId);
    setActiveAgent(agentId);
    setThreads(prev => prev[agentId] ? prev : {
      ...prev,
      [agentId]: [{ role: 'assistant', content: intro(profile?.label) }],
    });
  };

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || sending) return;
    const next = [...messages, { role: 'user', content: value }];
    setThreads(prev => ({ ...prev, [activeAgent]: next }));
    setInput('');
    setSending(true);
    try {
      const res = await api.chat({
        message: value,
        agent: activeAgent,
        history: next.filter(m => m.role !== 'assistant' || m.content !== messages[0].content),
      });
      setThreads(prev => ({ ...prev, [activeAgent]: [...next, { role: 'assistant', content: res.reply }] }));
      app?.refresh?.();
    } finally {
      setSending(false);
    }
  };

  return (
    <Card title="Manager Assistant" className="chat-card">
      <div className="agent-switcher">
        {agents.map(agent => (
          <button
            className={`agent-pill ${agent.id === activeAgent ? 'active' : ''}`}
            key={agent.id}
            type="button"
            onClick={() => switchAgent(agent.id)}
          >
            <strong>{agent.label}</strong>
            <span>{agent.description}</span>
          </button>
        ))}
      </div>
      <div className="chat-wrap">
        {messages.map((msg, index) => (
          <div className={`msg ${msg.role === 'user' ? 'user' : 'agent'}`} key={index}>
            <div className="msg-avatar">{msg.role === 'user' ? 'You' : activeProfile?.label?.split(' ').map(part => part[0]).join('').slice(0, 2) || 'AI'}</div>
            <div className="msg-bubble">{msg.content}</div>
          </div>
        ))}
      </div>
      <div className="chips">{chips.map(chip => <button className="chip" key={chip} onClick={() => send(chip)}>{chip}</button>)}</div>
      <div className="chat-input-row">
        <input className="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Ask anything about your schedule, labor costs, or staff..." />
        <button className="btn primary" onClick={() => send()} disabled={sending}><Send size={16} /> Send</button>
      </div>
    </Card>
  );
}
