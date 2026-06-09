import { Send } from 'lucide-react';
import { useState } from 'react';
import { api } from '../api.js';
import { Card } from '../components/UI.jsx';

const chips = [
  'What are my busiest hours?',
  'Am I overstaffed anywhere?',
  'Tell me about Sarah',
  "What's the Saturday forecast?",
  'How can I reduce labor by $200?',
];

export default function Chat({ app }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: "Hi, I'm your ShiftIQ agent. Ask about scheduling, labor costs, call-outs, or sales trends." }]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  const send = async (text = input) => {
    const value = text.trim();
    if (!value || sending) return;
    const next = [...messages, { role: 'user', content: value }];
    setMessages(next);
    setInput('');
    setSending(true);
    try {
      const res = await api.chat({ message: value, history: next.filter(m => m.role !== 'assistant' || m.content !== messages[0].content) });
      setMessages([...next, { role: 'assistant', content: res.reply }]);
      app?.refresh?.();
    } finally {
      setSending(false);
    }
  };

  return (
    <Card title="Manager Assistant" className="chat-card">
      <div className="chat-wrap">
        {messages.map((msg, index) => (
          <div className={`msg ${msg.role === 'user' ? 'user' : 'agent'}`} key={index}>
            <div className="msg-avatar">{msg.role === 'user' ? 'You' : 'AI'}</div>
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
