import { useState, useEffect } from 'react';
import { Database, RefreshCw, ChevronLeft, ChevronRight, Hash, Trash2 } from 'lucide-react';

interface MemoryItem {
  id: string;
  content: string;
  category: string;
  type: string;
  importance: number;
  created_at: string;
}

interface PaginatedResponse {
  items: MemoryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export default function DatabasePage() {
  const [data, setData] = useState<PaginatedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [showConfirm, setShowConfirm] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/database/items?page=${page}&size=${size}`);
      if (!res.ok) throw new Error('Failed to fetch data');
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setShowConfirm(false);
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/database/reset', {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to reset system');
      const json = await res.json();
      alert(json.message);
      setPage(1);
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Error resetting system: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  return (
    <div className="h-full flex flex-col p-6 space-y-6 relative">
      {/* Custom Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-red-500/20 rounded-lg text-red-500">
                <Trash2 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white">Reset System Memory?</h3>
            </div>
            
            <div className="space-y-3 text-zinc-400 text-sm mb-8">
              <p>This action will <span className="text-red-400 font-bold uppercase underline">permanently delete</span> all entries:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Decentralized Metadata (PostgreSQL)</li>
                <li>Human-readable Markdown Vault</li>
                <li>Semantic Vector Embeddings</li>
              </ul>
              <p className="bg-red-500/10 border border-red-500/20 p-3 rounded-lg text-red-300 mt-4 italic">
                 🚨 Warning: This action cannot be undone.
              </p>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl transition-all font-medium border border-white/5"
              >
                Cancel
              </button>
              <button
                onClick={handleReset}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl transition-all font-bold shadow-lg shadow-red-900/20"
              >
                Reset All Data
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-purple-500/10 rounded-xl">
            <Database className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Database Inspector</h1>
            <p className="text-sm text-zinc-400">Raw memory records from Vector DB</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowConfirm(true)}
            disabled={loading}
            className="flex items-center px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg transition-all text-sm font-medium"
          >
            <Trash2 className={`w-4 h-4 mr-2 ${loading ? 'animate-pulse' : ''}`} />
            Reset System
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors border border-white/5"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-zinc-900/50 rounded-xl border border-white/5 overflow-hidden flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-zinc-400 font-medium">
              <tr>
                <th className="p-4 w-20">Type</th>
                <th className="p-4">Content</th>
                <th className="p-4 w-40">Category</th>
                <th className="p-4 w-24 text-center">Score</th>
                <th className="p-4 w-40">Created At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading && !data ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-zinc-500">
                    Loading records...
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-zinc-500">
                    No records found.
                  </td>
                </tr>
              ) : (
                data?.items.map((item) => (
                  <tr key={item.id} className="text-zinc-300 hover:bg-white/5 transition-colors">
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${
                        item.type === 'fact' 
                          ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' 
                          : item.type === 'reflection'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                      }`}>
                        {item.type}
                      </span>
                    </td>
                    <td className="p-4 max-w-lg">
                      <div className="truncate" title={item.content}>
                        {item.content}
                      </div>
                      <div className="text-[10px] text-zinc-600 font-mono mt-1">
                        ID: {item.id}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="flex items-center text-zinc-400">
                        <Hash className="w-3 h-3 mr-1 opacity-50" />
                        {item.category}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <div className="w-full bg-zinc-800 rounded-full h-1.5 mb-1">
                        <div 
                          className="bg-purple-500 h-1.5 rounded-full" 
                          style={{ width: `${item.importance * 10}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-zinc-500">{item.importance}</span>
                    </td>
                    <td className="p-4 text-zinc-500 text-xs font-mono">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-white/5 flex items-center justify-between bg-zinc-900">
          <span className="text-sm text-zinc-500">
            Page {page} of {data?.pages || 1} • Total {data?.total || 0} items
          </span>
          <div className="flex space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="p-2 border border-white/10 rounded-lg text-zinc-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(data?.pages || 1, p + 1))}
              disabled={page >= (data?.pages || 1) || loading}
              className="p-2 border border-white/10 rounded-lg text-zinc-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
