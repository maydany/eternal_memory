import { useState, useEffect } from 'react';
import { Database, RefreshCw, ChevronLeft, ChevronRight, Hash, Trash2, Clock, Play, Plus, X, AlertTriangle, Calendar, HelpCircle, Info } from 'lucide-react';
import { api } from '../api/client';
import type { ScheduledTask } from '../api/client';

interface MemoryItem {
  id: string;
  content: string;
  category: string;
  type: string;
  importance: number;
  recency: number;
  mention_count: number;
  is_active: boolean;
  last_accessed: string;
  created_at: string;
}

interface PaginatedResponse {
  items: MemoryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface JobType {
  type: string;
  description: string;
}

interface SemanticTriple {
  id: string;
  memory_item_id: string | null;
  subject: string;
  predicate: string;
  object: string;
  context: string | null;
  importance: number;
  confidence: number;
  is_active: boolean;
  created_at: string;
  last_accessed: string;
}

interface TriplesResponse {
  items: SemanticTriple[];
  total: number;
  page: number;
  page_size: number;
}

type TabType = 'memories' | 'tasks' | 'triples';

export default function DatabasePage() {
  const [activeTab, setActiveTab] = useState<TabType>('memories');
  
  // Memories tab state
  const [data, setData] = useState<PaginatedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [showConfirm, setShowConfirm] = useState(false);

  // Tasks tab state
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [jobTypes, setJobTypes] = useState<JobType[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [showAddTask, setShowAddTask] = useState(false);
  const [newTaskName, setNewTaskName] = useState('');
  const [newTaskType, setNewTaskType] = useState('');
  const [newTaskInterval, setNewTaskInterval] = useState(3600);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [triggeringTask, setTriggeringTask] = useState<string | null>(null);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showScoringModal, setShowScoringModal] = useState(false);

  // Triples tab state
  const [triples, setTriples] = useState<TriplesResponse | null>(null);
  const [loadingTriples, setLoadingTriples] = useState(false);
  const [triplesPage, setTriplesPage] = useState(1);

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

  const fetchTasks = async () => {
    setLoadingTasks(true);
    try {
      const [tasksData, typesData] = await Promise.all([
        api.getScheduledJobs(),
        api.getJobTypes(),
      ]);
      setTasks(tasksData);
      setJobTypes(typesData.job_types);
      if (!newTaskType && typesData.job_types.length > 0) {
        setNewTaskType(typesData.job_types[0].type);
      }
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoadingTasks(false);
    }
  };

  const fetchTriples = async () => {
    setLoadingTriples(true);
    try {
      const res = await fetch(`http://localhost:8000/api/triples?page=${triplesPage}&page_size=20`);
      if (!res.ok) throw new Error('Failed to fetch triples');
      const json = await res.json();
      setTriples(json);
    } catch (err) {
      console.error('Failed to fetch triples:', err);
    } finally {
      setLoadingTriples(false);
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

  const handleAddTask = async () => {
    if (!newTaskName.trim() || !newTaskType) return;
    
    setTaskError(null);
    try {
      await api.addScheduledJob(newTaskName.trim(), newTaskType, newTaskInterval);
      setNewTaskName('');
      setShowAddTask(false);
      fetchTasks();
    } catch (err) {
      setTaskError(err instanceof Error ? err.message : 'Failed to add task');
    }
  };

  const handleDeleteTask = async (name: string) => {
    try {
      await api.deleteScheduledJob(name);
      fetchTasks();
    } catch (err) {
      alert('Failed to delete task: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleTriggerTask = async (name: string) => {
    setTriggeringTask(name);
    try {
      await api.triggerScheduledJob(name);
      fetchTasks();
    } catch (err) {
      alert('Failed to trigger task: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setTriggeringTask(null);
    }
  };

  const formatInterval = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  const formatNextRun = (seconds: number | null | undefined): string => {
    if (seconds === null || seconds === undefined) return 'N/A';
    if (seconds <= 0) return 'Due now';
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  useEffect(() => {
    if (activeTab === 'memories') {
      fetchData();
    } else if (activeTab === 'tasks') {
      fetchTasks();
    } else if (activeTab === 'triples') {
      fetchTriples();
    }
  }, [page, triplesPage, activeTab]);

  // Auto-refresh tasks
  useEffect(() => {
    if (activeTab === 'tasks') {
      const interval = setInterval(fetchTasks, 5000);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  return (
    <div className="h-full flex flex-col p-6 space-y-6 relative">
      {/* Reset Confirmation Modal */}
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

      {/* Scoring Explanation Modal */}
      {showScoringModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl p-6 max-w-2xl w-full shadow-2xl animate-in zoom-in-95 duration-200 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-purple-500/20 rounded-lg text-purple-400">
                  <Info className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold text-white">How Memory Scoring Works</h3>
              </div>
              <button onClick={() => setShowScoringModal(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="overflow-y-auto flex-1 space-y-4 pr-2">
              {/* Formula */}
              <div className="p-4 bg-gradient-to-r from-purple-500/10 to-cyan-500/10 rounded-xl border border-white/10">
                <h4 className="text-white font-medium mb-2">📐 Generative Agents Scoring Formula</h4>
                <code className="text-purple-300 text-sm block bg-black/30 p-3 rounded-lg font-mono">
                  Score = α₁ × Relevance + α₂ × Recency + α₃ × Importance
                </code>
                <p className="text-zinc-400 text-xs mt-2">Based on Stanford/Google's "Generative Agents" paper (Park et al., 2023)</p>
              </div>

              {/* Importance */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                  <span className="text-purple-400 font-medium">Importance (중요도)</span>
                </div>
                <p className="text-zinc-300 text-sm leading-relaxed">
                  기억의 <strong>본질적 중요도</strong>를 나타냅니다. LLM이 기억 저장 시 평가하거나, 기본값 0.5가 사용됩니다.
                </p>
                <ul className="text-zinc-400 text-xs mt-2 space-y-1">
                  <li>• 범위: 0.0 ~ 1.0</li>
                  <li>• 1.0 = 매우 중요 (이름, 생년월일 등)</li>
                  <li>• 0.5 = 보통 (일반적인 선호도)</li>
                  <li>• 0.1 = 낮음 (일시적인 정보)</li>
                </ul>
              </div>

              {/* Recency */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <div className="w-3 h-3 bg-cyan-500 rounded-full"></div>
                  <span className="text-cyan-400 font-medium">Recency (최신성)</span>
                </div>
                <p className="text-zinc-300 text-sm leading-relaxed">
                  <strong>마지막 접근 이후 시간</strong>에 따라 감쇠합니다. 최근에 접근한 기억일수록 높은 점수를 받습니다.
                </p>
                <code className="text-cyan-300 text-xs block bg-black/30 p-2 rounded-lg font-mono mt-2">
                  Recency = 0.995^(hours since last access)
                </code>
                <ul className="text-zinc-400 text-xs mt-2 space-y-1">
                  <li>• 방금 접근: ~1.000</li>
                  <li>• 1일 전: ~0.887</li>
                  <li>• 7일 전: ~0.430</li>
                  <li>• 30일 전: ~0.024</li>
                </ul>
              </div>

              {/* Active Status */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded border border-green-500/30">✓</span>
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30">✗</span>
                  <span className="text-white font-medium">Active Status (활성 상태)</span>
                </div>
                <p className="text-zinc-300 text-sm leading-relaxed">
                  <strong>MemGPT-style Supersede</strong> 시스템입니다. 모순되는 새 정보가 들어오면 이전 기억은 비활성화됩니다.
                </p>
                <ul className="text-zinc-400 text-xs mt-2 space-y-1">
                  <li>• <span className="text-green-400">✓ Active</span>: 현재 유효한 기억 (검색 결과에 포함)</li>
                  <li>• <span className="text-red-400">✗ Superseded</span>: 대체된 기억 (검색 결과에서 제외, 히스토리용 보존)</li>
                </ul>
              </div>

              {/* Settings tip */}
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                <h4 className="text-blue-400 font-medium mb-2 flex items-center gap-2">
                  <span>💡</span> 설정 팁
                </h4>
                <p className="text-zinc-300 text-sm">
                  Settings 페이지에서 가중치(α₁, α₂, α₃)와 감쇠율을 조절할 수 있습니다. 
                  또한 <strong>LLM Importance</strong>와 <strong>Supersede</strong> 기능을 활성화/비활성화할 수 있습니다.
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-white/10">
              <button
                onClick={() => setShowScoringModal(false)}
                className="w-full px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl transition-all font-medium border border-white/5"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Task Modal */}
      {showAddTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400">
                  <Plus className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold text-white">Add Scheduled Task</h3>
              </div>
              <button onClick={() => setShowAddTask(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">Task Name</label>
                <input
                  type="text"
                  value={newTaskName}
                  onChange={(e) => setNewTaskName(e.target.value)}
                  placeholder="e.g., my_hourly_backup"
                  className="w-full bg-zinc-800 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-2">Job Type</label>
                <select
                  value={newTaskType}
                  onChange={(e) => setNewTaskType(e.target.value)}
                  className="w-full bg-zinc-800 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                >
                  {jobTypes.map((jt) => (
                    <option key={jt.type} value={jt.type}>
                      {jt.type} - {jt.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm text-zinc-400 mb-2">Interval (seconds)</label>
                <div className="flex items-center space-x-3">
                  <input
                    type="number"
                    min={60}
                    value={newTaskInterval}
                    onChange={(e) => setNewTaskInterval(Number(e.target.value))}
                    className="flex-1 bg-zinc-800 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                  <span className="text-zinc-400 text-sm">= {formatInterval(newTaskInterval)}</span>
                </div>
                <p className="text-xs text-zinc-500 mt-1">Minimum 60 seconds</p>
              </div>

              {taskError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                  {taskError}
                </div>
              )}
            </div>

            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowAddTask(false)}
                className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl transition-all font-medium border border-white/5"
              >
                Cancel
              </button>
              <button
                onClick={handleAddTask}
                disabled={!newTaskName.trim() || !newTaskType}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-all font-bold shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Task
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help Modal - Task Types */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl p-6 max-w-2xl w-full shadow-2xl animate-in zoom-in-95 duration-200 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-purple-500/20 rounded-lg text-purple-400">
                  <HelpCircle className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold text-white">Available Task Types</h3>
              </div>
              <button onClick={() => setShowHelpModal(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="overflow-y-auto flex-1 space-y-4 pr-2">
              {/* daily_reflection */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded font-mono">daily_reflection</span>
                  <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] rounded">SYSTEM</span>
                </div>
                <h4 className="text-white font-medium mb-1">일일 성찰 (Daily Reflection)</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  최근 24시간 동안 저장된 메모리를 분석하여 '일일 성찰' 요약을 생성합니다. 
                  사용자에 대한 주요 인사이트를 정리하고, 결과를 새로운 메모리로 저장합니다.
                  기본 주기: 24시간 (86400초)
                </p>
              </div>

              {/* maintenance */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded font-mono">maintenance</span>
                  <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] rounded">SYSTEM</span>
                </div>
                <h4 className="text-white font-medium mb-1">유지보수 (Maintenance)</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  통합(Consolidation) 파이프라인을 실행합니다. 카테고리별 요약(Summary)을 최신화하고, 
                  데이터베이스 구조를 최적화합니다. *기억을 삭제하거나 아카이브하지 않습니다.*
                  기본 주기: 12시간 (43200초)
                </p>
              </div>

              {/* vault_backup */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded font-mono">vault_backup</span>
                </div>
                <h4 className="text-white font-medium mb-1">볼트 백업 (Vault Backup)</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  마크다운 볼트의 전체 백업을 생성합니다. 백업은 날짜/시간이 포함된 폴더명으로 
                  <code className="mx-1 px-1 py-0.5 bg-zinc-700 rounded text-xs">vault_backups/</code> 
                  디렉토리에 저장됩니다. 중요한 메모리 데이터를 보호하기 위해 정기적으로 실행하세요.
                </p>
              </div>

              {/* memory_cleanup */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded font-mono">memory_cleanup</span>
                </div>
                <h4 className="text-white font-medium mb-1">메모리 정리 (Memory Cleanup)</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  오래되고 중요도가 낮은 메모리를 삭제합니다. 30일 이상 접근되지 않고 
                  중요도(importance)가 0.3 미만인 항목을 대상으로 합니다. 
                  데이터베이스 크기를 관리하고 검색 성능을 유지하는 데 도움이 됩니다.
                </p>
              </div>

              {/* stats_snapshot */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-1 bg-cyan-500/20 text-cyan-400 text-xs rounded font-mono">stats_snapshot</span>
                </div>
                <h4 className="text-white font-medium mb-1">통계 스냅샷 (Stats Snapshot)</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  현재 시스템 통계를 로그에 기록합니다. 리소스 수, 카테고리 수, 메모리 항목 수, 
                  데이터베이스 크기 등을 포함합니다. 결과는 
                  <code className="mx-1 px-1 py-0.5 bg-zinc-700 rounded text-xs">~/.openclaw/stats_log.txt</code>
                  파일에도 저장됩니다.
                </p>
              </div>

              {/* embedding_refresh */}
              <div className="p-4 bg-zinc-800/50 rounded-xl border border-white/5">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-1 bg-orange-500/20 text-orange-400 text-xs rounded font-mono">embedding_refresh</span>
                </div>
                <h4 className="text-white font-medium mb-1">임베딩 갱신 (Embedding Refresh)</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  오래된 메모리 항목의 벡터 임베딩을 최신 모델로 재생성합니다. 
                  임베딩 모델이 업그레이드되었거나, 오래된 임베딩의 품질이 떨어진 경우에 유용합니다.
                  90일 이상 된 항목을 대상으로 합니다.
                </p>
              </div>

              {/* Usage tips */}
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl mt-4">
                <h4 className="text-blue-400 font-medium mb-2 flex items-center gap-2">
                  <span>💡</span> 사용 팁
                </h4>
                <ul className="text-zinc-300 text-sm space-y-2">
                  <li>• <strong>간격(Interval)</strong>은 최소 60초 이상이어야 합니다.</li>
                  <li>• <strong>시스템 태스크</strong>는 삭제할 수 없지만, 수동 실행은 가능합니다.</li>
                  <li>• <strong>커스텀 태스크</strong>는 서버 재시작 후에도 유지됩니다.</li>
                  <li>• <strong>수동 실행</strong> 버튼(▶️)으로 즉시 태스크를 실행할 수 있습니다.</li>
                </ul>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-white/10">
              <button
                onClick={() => setShowHelpModal(false)}
                className="w-full px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl transition-all font-medium border border-white/5"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-purple-500/10 rounded-xl">
            <Database className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Database Inspector</h1>
            <p className="text-sm text-zinc-400">Raw memory records and scheduled tasks</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {activeTab === 'memories' && (
            <>
              <button
                onClick={() => setShowScoringModal(true)}
                className="flex items-center px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/20 rounded-lg transition-all text-sm font-medium"
              >
                <Info className="w-4 h-4 mr-2" />
                How it works
              </button>
              <button
                onClick={() => setShowConfirm(true)}
                disabled={loading}
                className="flex items-center px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg transition-all text-sm font-medium"
              >
                <Trash2 className={`w-4 h-4 mr-2 ${loading ? 'animate-pulse' : ''}`} />
                Reset System
              </button>
            </>
          )}
          {activeTab === 'tasks' && (
            <>
              <button
                onClick={() => setShowHelpModal(true)}
                className="flex items-center px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white border border-white/10 rounded-lg transition-all text-sm"
                title="Available Task Types"
              >
                <HelpCircle className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowAddTask(true)}
                className="flex items-center px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 rounded-lg transition-all text-sm font-medium"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Task
              </button>
            </>
          )}
          <button
            onClick={activeTab === 'memories' ? fetchData : fetchTasks}
            disabled={loading || loadingTasks}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors border border-white/5"
          >
            <RefreshCw className={`w-5 h-5 ${(loading || loadingTasks) ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-zinc-900/50 rounded-lg p-1 border border-white/5">
        <button
          onClick={() => setActiveTab('memories')}
          className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-all text-sm font-medium ${
            activeTab === 'memories'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Memories</span>
        </button>
        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-all text-sm font-medium ${
            activeTab === 'tasks'
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Scheduled Tasks</span>
        </button>
        <button
          onClick={() => setActiveTab('triples')}
          className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-lg transition-all text-sm font-medium ${
            activeTab === 'triples'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Hash className="w-4 h-4" />
          <span>Semantic Triples</span>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 bg-zinc-900/50 rounded-xl border border-white/5 overflow-hidden flex flex-col">
        {activeTab === 'memories' ? (
          <>
            {/* Memories Table */}
            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-zinc-400 font-medium">
                  <tr>
                    <th className="p-4 w-20">Type</th>
                    <th className="p-4">Content</th>
                    <th className="p-4 w-32">Category</th>
                    <th className="p-4 w-24 text-center">Importance</th>
                    <th className="p-4 w-24 text-center">Recency</th>
                    <th className="p-4 w-16 text-center">Active</th>
                    <th className="p-4 w-36">Last Accessed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {loading && !data ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-zinc-500">
                        Loading records...
                      </td>
                    </tr>
                  ) : data?.items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-zinc-500">
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
                              style={{ width: `${Math.min(100, item.importance * 100)}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-zinc-500">
                            {item.importance.toFixed(2)} 
                            {item.mention_count > 1 && <span className="text-purple-400 ml-1">(x{item.mention_count})</span>}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          <div className="w-full bg-zinc-800 rounded-full h-1.5 mb-1">
                            <div 
                              className="bg-cyan-500 h-1.5 rounded-full" 
                              style={{ width: `${Math.min(100, item.recency * 100)}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-zinc-500">
                            {item.recency.toFixed(3)}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          {item.is_active ? (
                            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded border border-green-500/30">✓</span>
                          ) : (
                            <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30" title="Superseded">✗</span>
                          )}
                        </td>
                        <td className="p-4 text-zinc-500 text-xs font-mono">
                          {new Date(item.last_accessed).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Memories Pagination */}
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
          </>
        ) : activeTab === 'tasks' ? (
          <>
            {/* Tasks Table */}
            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-zinc-400 font-medium">
                  <tr>
                    <th className="p-4 w-48">Name</th>
                    <th className="p-4 w-40">Type</th>
                    <th className="p-4 w-28 text-center">Interval</th>
                    <th className="p-4 w-32 text-center">Next Run</th>
                    <th className="p-4 w-24 text-center">Status</th>
                    <th className="p-4 w-32 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {loadingTasks && tasks.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-zinc-500">
                        Loading tasks...
                      </td>
                    </tr>
                  ) : tasks.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-zinc-500">
                        No scheduled tasks found.
                      </td>
                    </tr>
                  ) : (
                    tasks.map((task) => (
                      <tr key={task.name} className="text-zinc-300 hover:bg-white/5 transition-colors">
                        <td className="p-4">
                          <div className="flex items-center space-x-2">
                            <Clock className="w-4 h-4 text-blue-400" />
                            <span className="font-medium">{task.name}</span>
                            {task.is_system && (
                              <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] rounded font-medium border border-amber-500/30">
                                SYSTEM
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <span className="px-2 py-1 bg-zinc-800 text-zinc-300 text-xs rounded font-mono">
                            {task.job_type}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          <span className="text-zinc-400">{formatInterval(task.interval_seconds)}</span>
                        </td>
                        <td className="p-4 text-center">
                          <span className={`text-sm ${task.next_run_in !== null && task.next_run_in !== undefined && task.next_run_in <= 60 ? 'text-green-400' : 'text-zinc-400'}`}>
                            {formatNextRun(task.next_run_in)}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            task.enabled
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                              : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
                          }`}>
                            {task.enabled ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={() => handleTriggerTask(task.name)}
                              disabled={triggeringTask === task.name}
                              className="p-1.5 text-blue-400 hover:text-blue-300 hover:bg-blue-500/20 rounded-lg transition-all disabled:opacity-50"
                              title="Trigger Now"
                            >
                              <Play className={`w-4 h-4 ${triggeringTask === task.name ? 'animate-pulse' : ''}`} />
                            </button>
                            {!task.is_system && (
                              <button
                                onClick={() => handleDeleteTask(task.name)}
                                className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded-lg transition-all"
                                title="Delete"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                            {task.is_system && (
                              <div 
                                className="p-1.5 text-zinc-600 cursor-not-allowed"
                                title="System tasks cannot be deleted"
                              >
                                <AlertTriangle className="w-4 h-4" />
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Tasks Footer */}
            <div className="p-4 border-t border-white/5 flex items-center justify-between bg-zinc-900">
              <span className="text-sm text-zinc-500">
                {tasks.length} scheduled task{tasks.length !== 1 ? 's' : ''} • Auto-refreshes every 5s
              </span>
              <div className="flex items-center space-x-2 text-zinc-500 text-xs">
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span>Scheduler running</span>
                </div>
              </div>
            </div>
          </>
        ) : activeTab === 'triples' ? (
          <>
            {/* Triples Tab */}
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-sm text-zinc-400">Entity-Level Triples (SPO)</span>
                <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-xs font-medium">
                  LangMem Style
                </span>
              </div>
              <button
                onClick={fetchTriples}
                className="flex items-center space-x-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-zinc-400 hover:text-white transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loadingTriples ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>

            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-zinc-400 font-medium">
                  <tr>
                    <th className="p-4 w-32">Subject</th>
                    <th className="p-4 w-32">Predicate</th>
                    <th className="p-4">Object</th>
                    <th className="p-4 w-24 text-center">Importance</th>
                    <th className="p-4 w-16 text-center">Active</th>
                    <th className="p-4 w-36">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {loadingTriples && !triples ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-zinc-500">
                        Loading triples...
                      </td>
                    </tr>
                  ) : !triples?.items?.length ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-zinc-500">
                        <div className="flex flex-col items-center space-y-2">
                          <Hash className="w-8 h-8 text-zinc-600" />
                          <span>No triples found.</span>
                          <span className="text-xs">Enable "Entity-Level Triples" in Settings to extract SPO triples.</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    triples.items.map((triple) => (
                      <tr key={triple.id} className="text-zinc-300 hover:bg-white/5 transition-colors">
                        <td className="p-4">
                          <span className="px-2 py-1 rounded text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                            {triple.subject}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className="px-2 py-1 rounded text-xs font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            {triple.predicate}
                          </span>
                        </td>
                        <td className="p-4 max-w-lg">
                          <div className="truncate" title={triple.object}>
                            {triple.object}
                          </div>
                          {triple.context && (
                            <div className="text-[10px] text-zinc-600 mt-1">
                              Context: {triple.context}
                            </div>
                          )}
                        </td>
                        <td className="p-4 text-center">
                          <span className="text-emerald-400 font-medium">
                            {(triple.importance * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          {triple.is_active ? (
                            <span className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">✓</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-xs bg-zinc-700 text-zinc-500">×</span>
                          )}
                        </td>
                        <td className="p-4 text-zinc-500 text-xs">
                          {new Date(triple.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Triples Pagination */}
            <div className="p-4 border-t border-white/5 flex items-center justify-between bg-zinc-900">
              <span className="text-sm text-zinc-500">
                {triples?.total || 0} total triples • Page {triplesPage}
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => { setTriplesPage(p => Math.max(1, p - 1)); fetchTriples(); }}
                  disabled={triplesPage === 1}
                  className="p-1.5 rounded hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-zinc-400">Page {triplesPage}</span>
                <button
                  onClick={() => { setTriplesPage(p => p + 1); fetchTriples(); }}
                  disabled={!triples || triplesPage * 20 >= triples.total}
                  className="p-1.5 rounded hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
