import { useQuery } from '@tanstack/react-query';

interface Evaluation {
  id: number;
  name: string;
  prompt: string;
  score: number;
}

interface Props {
  token: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8080/api';

export default function EvaluationLabPage({ token }: Props) {
  const { data = [], isLoading } = useQuery<Evaluation[]>({
    queryKey: ['evaluations', token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/evaluations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load evaluations');
      return res.json();
    },
    enabled: !!token,
  });

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Evaluation Lab</h2>
        <p className="text-sm text-gray-500">Review prompts and scoring snapshots for quality tracking.</p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">Loading evaluations…</div>
      ) : data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">No evaluation runs captured yet.</div>
      ) : (
        <div className="space-y-3">
          {data.map((item) => (
            <div key={item.id} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-semibold text-gray-800">{item.name}</h3>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
                  Score {item.score.toFixed(1)}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-600">{item.prompt}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
