import { useState } from 'react';

interface AdkDemoCardProps {
  apiBaseUrl: string;
}

export default function AdkDemoCard({ apiBaseUrl }: AdkDemoCardProps) {
  const [request, setRequest] = useState('Summarize the incident report');
  const [documentName, setDocumentName] = useState('demo-report.pdf');
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const runDemo = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/agent/adk/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_request: request, document_name: documentName }),
      });
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (error) {
      setResult(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-indigo-100 bg-white p-4 shadow-sm">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-gray-800">🤖 ADK demo</h3>
        <p className="text-xs text-gray-500">Run a 5-step ADK workflow directly from the UI.</p>
      </div>
      <div className="space-y-2">
        <input
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="What should the agent do?"
        />
        <input
          value={documentName}
          onChange={(e) => setDocumentName(e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          placeholder="Document name"
        />
        <button
          onClick={runDemo}
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-70"
        >
          {loading ? 'Running…' : 'Run ADK Demo'}
        </button>
      </div>
      {result && (
        <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-[11px] text-slate-100">
          {result}
        </pre>
      )}
    </div>
  );
}
