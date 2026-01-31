import { useState, useEffect } from 'react'
import { Activity, RefreshCw, Loader2, TrendingUp, Zap, Clock, BarChart3 } from 'lucide-react'
import { api } from '../api/client'

interface MetricsSummary {
  total_pipelines: number
  total_facts: number
  avg_duration: number
  p95_duration: number
  avg_facts_per_pipeline: number
  recent_count: number
}

interface RecentMetric {
  timestamp: string
  duration: number
  facts_extracted: number
  embeddings_generated: number
  text_length: number
}

export default function MetricsPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null)
  const [recent, setRecent] = useState<RecentMetric[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadMetrics = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const [summaryData, recentData] = await Promise.all([
        api.getMetricsSummary(),
        api.getRecentMetrics(20)
      ])
      
      setSummary(summaryData)
      setRecent(recentData)
    } catch (err) {
      console.error('Failed to load metrics:', err)
      setError('Failed to load performance metrics. Please check if the API server is running.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadMetrics()
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadMetrics, 10000)
    return () => clearInterval(interval)
  }, [])

  const formatDuration = (seconds: number) => {
    if (seconds === undefined || seconds === null) return 'N/A'
    return `${seconds.toFixed(2)}s`
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('ko-KR', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    } catch {
      return timestamp
    }
  }

  const StatCard = ({ 
    label, 
    value, 
    icon: Icon, 
    color, 
    tooltip 
  }: { 
    label: string
    value: string | number
    icon: any
    color: string
    tooltip?: string
  }) => (
    <div className={`p-6 rounded-xl bg-gradient-to-br ${color} border border-white/10 relative group`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide relative">
              {label}
              {tooltip && (
                <span className="tooltip absolute left-0 top-6 w-64 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 shadow-xl border border-white/10">
                  {tooltip}
                </span>
              )}
            </p>
          </div>
          <div className="text-3xl font-bold text-white">{value}</div>
        </div>
        <Icon className="w-8 h-8 text-white/40" />
      </div>
    </div>
  )

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Header */}
      <header className="h-16 px-6 flex items-center justify-between border-b border-white/10 bg-[#0f0f18]/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Performance Monitor</h2>
            <p className="text-xs text-gray-500">Real-time pipeline metrics</p>
          </div>
        </div>
        
        <button
          onClick={loadMetrics}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 disabled:opacity-50 transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </header>

      {/* Content */}
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Error Message */}
        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Loading State */}
        {isLoading && !summary && (
          <div className="flex items-center justify-center gap-3 p-12 rounded-xl bg-white/5 border border-white/10">
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
            <span className="text-gray-400">Loading metrics...</span>
          </div>
        )}

        {/* Statistics Grid */}
        {summary && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <StatCard
                label="Total Pipelines"
                value={summary.total_pipelines}
                icon={Zap}
                color="from-blue-500/10 to-blue-600/5"
                tooltip="파이프라인이란? 한 번의 완전한 메모리 저장 프로세스입니다. memorize()를 호출할 때마다 1개씩 증가합니다."
              />
              <StatCard
                label="Total Facts"
                value={summary.total_facts}
                icon={BarChart3}
                color="from-purple-500/10 to-purple-600/5"
                tooltip="팩트란? 파이프라인에서 추출된 개별 정보 조각입니다."
              />
              <StatCard
                label="Avg Duration"
                value={formatDuration(summary.avg_duration)}
                icon={Clock}
                color="from-green-500/10 to-green-600/5"
                tooltip="평균 실행 시간: 파이프라인이 완료되는 데 걸린 평균 시간입니다. 낮을수록 좋습니다."
              />
              <StatCard
                label="P95 Duration"
                value={summary.p95_duration !== undefined ? formatDuration(summary.p95_duration) : 'N/A'}
                icon={TrendingUp}
                color="from-orange-500/10 to-orange-600/5"
                tooltip="P95 실행 시간: 95%의 요청이 이 시간 안에 완료됩니다. 느린 케이스를 추적하는 지표로 2초 이하면 좋습니다."
              />
              <StatCard
                label="Avg Facts/Pipeline"
                value={summary.avg_facts_per_pipeline.toFixed(2)}
                icon={Activity}
                color="from-pink-500/10 to-pink-600/5"
                tooltip="파이프라인당 평균 팩트 수: 일반적으로 2~5개입니다."
              />
              <StatCard
                label="Recent Runs"
                value={summary.recent_count}
                icon={RefreshCw}
                color="from-cyan-500/10 to-cyan-600/5"
                tooltip="최근 실행 횟수: 최대 100개까지의 최근 파이프라인 실행을 추적합니다."
              />
            </div>

            {/* Recent Pipeline Executions Table */}
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/10">
                <h3 className="text-lg font-semibold text-white">Recent Pipeline Executions</h3>
                <p className="text-sm text-gray-500 mt-1">Last 20 pipeline runs</p>
              </div>
              
              {recent.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-white/5 text-gray-400">
                      <tr>
                        <th className="px-6 py-3 font-medium">Timestamp</th>
                        <th className="px-6 py-3 font-medium text-right">Duration</th>
                        <th className="px-6 py-3 font-medium text-right">Facts</th>
                        <th className="px-6 py-3 font-medium text-right">Embeddings</th>
                        <th className="px-6 py-3 font-medium text-right">Text Length</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {recent.map((metric, idx) => (
                        <tr key={idx} className="hover:bg-white/5 transition-colors">
                          <td className="px-6 py-3 text-gray-300">{formatTimestamp(metric.timestamp)}</td>
                          <td className="px-6 py-3 text-right font-mono">
                            <span className={`${
                              metric.duration < 1 ? 'text-green-400' : 
                              metric.duration < 2 ? 'text-yellow-400' : 
                              'text-red-400'
                            }`}>
                              {formatDuration(metric.duration)}
                            </span>
                          </td>
                          <td className="px-6 py-3 text-right text-purple-400 font-semibold">
                            {metric.facts_extracted}
                          </td>
                          <td className="px-6 py-3 text-right text-blue-400 font-semibold">
                            {metric.embeddings_generated}
                          </td>
                          <td className="px-6 py-3 text-right text-gray-400">
                            {metric.text_length.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-12 text-center">
                  <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-500">No metrics yet</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Metrics will appear here after pipeline executions
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
