/**
 * AgentChat – Multi-agent chat interface (Phase 2).
 *
 * Supports agent modes:
 *   auto      – Orchestrator decides (default)
 *   rag       – Force RAG agent
 *   report    – Generate PDF report
 *   compare   – Compare documents
 *   research  – Web research
 *   action    – Execute action (email, Jira …)
 */

import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8080/api';

type AgentMode = 'auto' | 'rag' | 'report' | 'compare' | 'research' | 'action' | 'engineering';

interface Source {
  document_name: string;
  chunk_text:    string;
  score:         number;
  source_type:   string;
  url?:          string;
}

interface AgentMessage {
  id:          string;
  role:        'user' | 'agent';
  content:     string;
  agent_type?: string;
  sources?:    Source[];
  confidence?: number;
  report_path?: string;
  timestamp:   Date;
}

interface AgentResponse {
  answer:          string;
  agent_type:      string;
  sources:         Source[];
  confidence_score: number;
  action_result?:  Record<string, unknown>;
  report_path?:    string;
}

interface Props {
  token:       string;
  sessionId:   string;
  documentIds: number[];
}

const AGENT_MODE_LABELS: Record<AgentMode, string> = {
  auto:     '🤖 Auto',
  rag:      '📄 RAG',
  report:   '📊 Report',
  compare:  '⚖️ Compare',
  research: '🔍 Research',
  action:   '⚡ Action',
  engineering: 'Engineering',
};

const AGENT_MODE_DESCRIPTIONS: Record<AgentMode, string> = {
  auto:     'Orchestrator tự chọn agent phù hợp',
  rag:      'Q&A trực tiếp từ tài liệu',
  report:   'Tạo báo cáo PDF từ tài liệu',
  compare:  'So sánh nhiều tài liệu',
  research: 'Tìm kiếm thông tin trên web',
  action:   'Thực thi hành động (email, Jira…)',
  engineering: 'Analyze test reports, failures, root cause, corrective actions, and 8D reports',
};

export default function AgentChat({ token, sessionId, documentIds }: Props) {
  const [messages, setMessages]     = useState<AgentMessage[]>([]);
  const [input, setInput]           = useState('');
  const [mode, setMode]             = useState<AgentMode>('auto');
  const [webSearch, setWebSearch]   = useState(false);
  const [showSources, setShowSources] = useState<string | null>(null);
  const bottomRef                   = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const invokeMutation = useMutation<AgentResponse, Error, string>({
    mutationFn: async (query: string) => {
      const body: Record<string, unknown> = {
        query,
        sessionId,
        documentIds: documentIds.map(String),
        useWebSearch: webSearch,
      };
      if (mode !== 'auto') {
        body.intentOverride = mode;
      }
      const res = await fetch(`${API_BASE_URL}/agent/invoke`, {
        method: 'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { error?: string }).error ?? 'Agent error');
      }
      return res.json() as Promise<AgentResponse>;
    },
    onSuccess: (data, query) => {
      setMessages(prev => [
        ...prev,
        {
          id:           crypto.randomUUID(),
          role:         'user',
          content:      query,
          timestamp:    new Date(),
        },
        {
          id:           crypto.randomUUID(),
          role:         'agent',
          content:      data.answer,
          agent_type:   data.agent_type,
          sources:      data.sources,
          confidence:   data.confidence_score,
          report_path:  data.report_path,
          timestamp:    new Date(),
        },
      ]);
    },
    onError: (err, query) => {
      setMessages(prev => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user',  content: query,         timestamp: new Date() },
        { id: crypto.randomUUID(), role: 'agent', content: `❌ ${err.message}`, timestamp: new Date() },
      ]);
    },
  });

  const handleSend = () => {
    const q = input.trim();
    if (!q || invokeMutation.isPending) return;
    setInput('');
    invokeMutation.mutate(q);
  };

  const agentBadgeColour: Record<string, string> = {
    rag:       'bg-blue-100 text-blue-800',
    report:    'bg-purple-100 text-purple-800',
    compare:   'bg-orange-100 text-orange-800',
    research:  'bg-green-100 text-green-800',
    action:    'bg-red-100 text-red-800',
    engineering: 'bg-cyan-100 text-cyan-800',
    default:   'bg-gray-100 text-gray-800',
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 rounded-xl border border-gray-200 overflow-hidden">

      {/* ── Mode selector toolbar ── */}
      <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-gray-200 overflow-x-auto">
        {(Object.keys(AGENT_MODE_LABELS) as AgentMode[]).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            title={AGENT_MODE_DESCRIPTIONS[m]}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors
              ${mode === m
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {AGENT_MODE_LABELS[m]}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1.5">
          <input
            id="web-search-toggle"
            type="checkbox"
            checked={webSearch}
            onChange={e => setWebSearch(e.target.checked)}
            className="accent-indigo-600"
          />
          <label htmlFor="web-search-toggle" className="text-xs text-gray-500 whitespace-nowrap">
            Web search
          </label>
        </div>
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
            <span className="text-4xl">🤖</span>
            <p className="text-sm font-medium">Multi-Agent Chat</p>
            <p className="text-xs text-center max-w-xs">
              Chọn chế độ agent phù hợp hoặc để <strong>Auto</strong> tự quyết định.
              {documentIds.length > 0 && <> Đang dùng <strong>{documentIds.length}</strong> tài liệu.</>}
            </p>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>

              {/* Agent type badge */}
              {msg.role === 'agent' && msg.agent_type && (
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                    ${agentBadgeColour[msg.agent_type] ?? agentBadgeColour.default}`}>
                    {AGENT_MODE_LABELS[msg.agent_type as AgentMode] ?? msg.agent_type}
                  </span>
                  {msg.confidence !== undefined && (
                    <span className="text-xs text-gray-400">
                      conf: {(msg.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              )}

              {/* Bubble */}
              <div className={`rounded-2xl px-4 py-3 text-sm shadow-sm whitespace-pre-wrap
                ${msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-white text-gray-800 border border-gray-100 rounded-bl-sm'}`}>
                {msg.content}
              </div>

              {/* Report download */}
              {msg.report_path && (
                <div className="mt-1.5 flex items-center gap-1 text-xs text-purple-600">
                  <span>📄</span>
                  <span>Report generated: <code className="bg-purple-50 px-1 rounded">{msg.report_path}</code></span>
                </div>
              )}

              {/* Sources toggle */}
              {msg.role === 'agent' && msg.sources && msg.sources.length > 0 && (
                <button
                  onClick={() => setShowSources(showSources === msg.id ? null : msg.id)}
                  className="mt-1 text-xs text-indigo-500 hover:text-indigo-700"
                >
                  {showSources === msg.id ? '▲ Hide' : `▼ ${msg.sources.length} source${msg.sources.length > 1 ? 's' : ''}`}
                </button>
              )}

              {/* Source citations */}
              {showSources === msg.id && msg.sources && (
                <div className="mt-2 space-y-1.5">
                  {msg.sources.slice(0, 5).map((src, i) => (
                    <div key={i} className="bg-gray-50 border border-gray-200 rounded-lg p-2.5 text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-700 truncate max-w-[60%]">
                          {src.source_type === 'web' ? '🌐' : '📄'} {src.document_name}
                        </span>
                        <span className="text-gray-400 font-mono">{(src.score * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-gray-500 line-clamp-2">{src.chunk_text}</p>
                      {src.url && (
                        <a href={src.url} target="_blank" rel="noopener noreferrer"
                           className="text-blue-500 hover:underline truncate block mt-1">
                          {src.url}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-0.5 text-right text-[10px] text-gray-400">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {invokeMutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input ── */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 flex gap-2">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder={`Nhập câu hỏi… (${AGENT_MODE_DESCRIPTIONS[mode]})`}
          rows={2}
          className="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-gray-50"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || invokeMutation.isPending}
          className="self-end px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium
                     hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {invokeMutation.isPending ? '…' : 'Gửi'}
        </button>
      </div>
    </div>
  );
}
