import { useState, useEffect } from 'react'
import { Key, CheckCircle, XCircle, Loader2, Server, Save, RefreshCw, Database, HardDrive, Trash2, Zap } from 'lucide-react'
import { api } from '../api/client'

interface ModelInfo {
  id: string
  name: string
  owned_by: string
}

interface TokenUsage {
  model: string
  prompt: number
  completion: number
  total: number
}

interface DbStats {
  resources: number
  categories: number
  memory_items: number
  token_usage?: TokenUsage[]
  db_size?: string
  connected?: boolean
}

interface BufferSettings {
  flush_threshold_tokens: number
  auto_flush_enabled: boolean
}

interface ScoringSettings {
  alpha_relevance: number
  alpha_recency: number
  alpha_importance: number
  recency_decay_factor: number
  min_relevance_threshold: number
}

// Scoring Section Component
function ScoringSection() {
  const [settings, setSettings] = useState<ScoringSettings>({
    alpha_relevance: 1.0,
    alpha_recency: 1.0,
    alpha_importance: 1.0,
    recency_decay_factor: 0.995,
    min_relevance_threshold: 0.3,
  })
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    loadScoringSettings()
  }, [])

  const loadScoringSettings = async () => {
    try {
      const data = await api.getScoringSettings()
      setSettings(data)
    } catch (error) {
      console.error('Failed to load scoring settings:', error)
    }
  }

  const handleUpdate = async (key: keyof ScoringSettings, value: number) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async (key: keyof ScoringSettings, value: number) => {
    setIsSaving(true)
    try {
      await api.updateScoringSettings({ [key]: value })
    } catch (error) {
      console.error('Failed to update scoring settings:', error)
    }
    setTimeout(() => setIsSaving(false), 1500)
  }

  return (
    <section className="space-y-4">
      <h3 className="text-lg font-medium text-white flex items-center gap-2">
        <Server className="w-5 h-5 text-cyan-400" />
        Memory Scoring
        <span className="ml-2 px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-xs">
          Generative Agents
        </span>
      </h3>
      <p className="text-sm text-gray-500">
        메모리 검색 시 Relevance, Recency, Importance의 가중치를 조절합니다.
      </p>
      
      <div className="space-y-6 p-4 rounded-xl bg-white/5 border border-white/10">
        {/* Alpha Relevance */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-400 rounded-full" />
              Relevance (관련성)
            </span>
            <span className="text-lg font-bold text-blue-400">{settings.alpha_relevance.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="3"
            step="0.1"
            value={settings.alpha_relevance}
            onChange={(e) => handleUpdate('alpha_relevance', parseFloat(e.target.value))}
            onMouseUp={(e) => handleSave('alpha_relevance', parseFloat((e.target as HTMLInputElement).value))}
            onTouchEnd={(e) => handleSave('alpha_relevance', parseFloat((e.target as HTMLInputElement).value))}
            className="w-full h-2 bg-blue-500/20 rounded-lg appearance-none cursor-pointer accent-blue-400"
          />
          <p className="text-xs text-gray-600">질문과 기억의 의미적 유사도 가중치</p>
        </div>

        {/* Alpha Recency */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-2">
              <span className="w-2 h-2 bg-green-400 rounded-full" />
              Recency (최신성)
            </span>
            <span className="text-lg font-bold text-green-400">{settings.alpha_recency.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="3"
            step="0.1"
            value={settings.alpha_recency}
            onChange={(e) => handleUpdate('alpha_recency', parseFloat(e.target.value))}
            onMouseUp={(e) => handleSave('alpha_recency', parseFloat((e.target as HTMLInputElement).value))}
            onTouchEnd={(e) => handleSave('alpha_recency', parseFloat((e.target as HTMLInputElement).value))}
            className="w-full h-2 bg-green-500/20 rounded-lg appearance-none cursor-pointer accent-green-400"
          />
          <p className="text-xs text-gray-600">최근 접근한 기억일수록 높은 점수</p>
        </div>

        {/* Alpha Importance */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-2">
              <span className="w-2 h-2 bg-purple-400 rounded-full" />
              Importance (중요도)
            </span>
            <span className="text-lg font-bold text-purple-400">{settings.alpha_importance.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="3"
            step="0.1"
            value={settings.alpha_importance}
            onChange={(e) => handleUpdate('alpha_importance', parseFloat(e.target.value))}
            onMouseUp={(e) => handleSave('alpha_importance', parseFloat((e.target as HTMLInputElement).value))}
            onTouchEnd={(e) => handleSave('alpha_importance', parseFloat((e.target as HTMLInputElement).value))}
            className="w-full h-2 bg-purple-500/20 rounded-lg appearance-none cursor-pointer accent-purple-400"
          />
          <p className="text-xs text-gray-600">LLM이 평가한 기억의 중요도 가중치</p>
        </div>

        {/* Decay Factor */}
        <div className="space-y-2 pt-4 border-t border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Decay Factor</span>
            <span className="text-lg font-bold text-yellow-400">{settings.recency_decay_factor.toFixed(3)}</span>
          </div>
          <input
            type="range"
            min="0.9"
            max="0.999"
            step="0.001"
            value={settings.recency_decay_factor}
            onChange={(e) => handleUpdate('recency_decay_factor', parseFloat(e.target.value))}
            onMouseUp={(e) => handleSave('recency_decay_factor', parseFloat((e.target as HTMLInputElement).value))}
            onTouchEnd={(e) => handleSave('recency_decay_factor', parseFloat((e.target as HTMLInputElement).value))}
            className="w-full h-2 bg-yellow-500/20 rounded-lg appearance-none cursor-pointer accent-yellow-400"
          />
          <p className="text-xs text-gray-600">시간당 Recency 감쇠율 (0.995 = 기본값)</p>
        </div>

        {isSaving && (
          <div className="flex items-center gap-2 text-sm text-green-400 animate-pulse">
            <CheckCircle className="w-4 h-4" />
            저장됨
          </div>
        )}
      </div>
    </section>
  )
}

export default function SettingsPage() {
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [isKeySet, setIsKeySet] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [isSavingPrompt, setIsSavingPrompt] = useState(false)
  const [model, setModel] = useState('gpt-4o-mini')
  const [settings, setSettings] = useState<any>(null)
  
  // Dynamic model loading
  const [chatModels, setChatModels] = useState<ModelInfo[]>([])
  const [embeddingModels, setEmbeddingModels] = useState<ModelInfo[]>([])
  const [isLoadingModels, setIsLoadingModels] = useState(false)
  const [modelsError, setModelsError] = useState<string | null>(null)
  
  // Database stats
  const [dbStats, setDbStats] = useState<DbStats | null>(null)
  const [isLoadingDbStats, setIsLoadingDbStats] = useState(false)

  // Model config (dual models + supersede)
  const [chatModel, setChatModel] = useState('gpt-4o-mini')
  const [memoryModel, setMemoryModel] = useState('gpt-4o-mini')
  const [supersedeModel, setSupersedeModel] = useState('gpt-4o-mini')
  const [useLLMImportance, setUseLLMImportance] = useState(false)
  const [useMemorySupersede, setUseMemorySupersede] = useState(false)

  // Buffer settings
  const [bufferSettings, setBufferSettings] = useState<BufferSettings>({ flush_threshold_tokens: 4000, auto_flush_enabled: true })
  const [isSavingBuffer, setIsSavingBuffer] = useState(false)

  useEffect(() => {
    loadSettings()
    loadDbStats()
    loadBufferSettings()
    loadModelConfig()
  }, [])

  // Load models when API key is set
  useEffect(() => {
    if (isKeySet) {
      loadModels()
    }
  }, [isKeySet, provider])

  const loadDbStats = async () => {
    setIsLoadingDbStats(true)
    try {
      const data = await api.getStats()
      setDbStats(data)
    } catch (error) {
      console.error('Failed to load DB stats:', error)
    } finally {
      setIsLoadingDbStats(false)
    }
  }

  const loadSettings = async () => {
    try {
      const data = await api.getSettings()
      setSettings(data)
      setProvider(data.llm.provider)
      setModel(data.llm.model)
      setIsKeySet(data.llm.api_key_set)
      setSystemPrompt(data.system_prompt || '')
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const loadModelConfig = async () => {
    try {
      const data = await api.getModelConfig()
      setChatModel(data.effective_chat_model)
      setMemoryModel(data.memory_model)
      setSupersedeModel(data.supersede_model)
      setUseLLMImportance(data.use_llm_importance)
      setUseMemorySupersede(data.use_memory_supersede)
      setModel(data.effective_chat_model)
    } catch (error) {
      console.error('Failed to load model config:', error)
    }
  }

  const loadBufferSettings = async () => {
    try {
      const data = await api.getBufferSettings()
      setBufferSettings(data)
    } catch (error) {
      console.error('Failed to load buffer settings:', error)
    }
  }

  const handleUpdateBufferSettings = async (newThreshold: number) => {
    setIsSavingBuffer(true)
    try {
      const result = await api.updateBufferSettings({ flush_threshold_tokens: newThreshold })
      if (result.success) {
        setBufferSettings(prev => ({ ...prev, flush_threshold_tokens: newThreshold }))
      }
    } catch (error) {
      console.error('Failed to update buffer settings:', error)
    }
    // Keep "저장됨" visible for at least 1.5 seconds
    setTimeout(() => setIsSavingBuffer(false), 1500)
  }

  const loadModels = async () => {
    setIsLoadingModels(true)
    setModelsError(null)
    
    try {
      const data = await api.getModels(provider)
      
      if (data.success) {
        setChatModels(data.chat_models || [])
        setEmbeddingModels(data.embedding_models || [])
      } else {
        setModelsError(data.error || 'Failed to load models')
        setChatModels([])
        setEmbeddingModels([])
      }
    } catch (error) {
      console.error('Failed to load models:', error)
      setModelsError('Failed to load models from API')
      setChatModels([])
      setEmbeddingModels([])
    } finally {
      setIsLoadingModels(false)
    }
  }

  const handleSaveApiKey = async () => {
    if (!apiKey.trim()) return

    try {
      await api.setApiKey(provider, apiKey)
      setIsKeySet(true)
      setApiKey('')
      setTestResult({ success: true, message: 'API key saved successfully' })
      
      // Automatically load models after saving API key
      setTimeout(() => loadModels(), 500)
    } catch (error) {
      setTestResult({ success: false, message: 'Failed to save API key' })
    }
  }

  const handleDeleteApiKey = async () => {
    if (!confirm('정말로 API 키를 삭제하시겠습니까?')) return

    try {
      await api.deleteApiKey(provider)
      setIsKeySet(false)
      setApiKey('')
      setChatModels([])
      setEmbeddingModels([])
      setTestResult({ success: true, message: 'API key deleted successfully' })
    } catch (error) {
      setTestResult({ success: false, message: 'Failed to delete API key' })
    }
  }

  const handleTestConnection = async () => {
    setIsTesting(true)
    setTestResult(null)

    try {
      const result = await api.testConnection()
      setTestResult({
        success: result.success,
        message: result.success
          ? `Connection successful! ${result.models_available} models available.`
          : result.error || 'Connection failed',
      })
      
      // Load models on successful connection
      if (result.success) {
        loadModels()
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to test connection',
      })
    } finally {
      setIsTesting(false)
    }
  }

  const handleModelChange = async (type: 'chat' | 'memory' | 'supersede', newModel: string) => {
    if (type === 'chat') {
      setChatModel(newModel)
      setModel(newModel)
      try {
        await api.setModel({ chat_model: newModel })
      } catch (error) {
        console.error('Failed to save chat model:', error)
      }
    } else if (type === 'memory') {
      setMemoryModel(newModel)
      try {
        await api.setModel({ memory_model: newModel })
      } catch (error) {
        console.error('Failed to save memory model:', error)
      }
    } else if (type === 'supersede') {
      setSupersedeModel(newModel)
      try {
        await api.setModel({ supersede_model: newModel })
      } catch (error) {
        console.error('Failed to save supersede model:', error)
      }
    }
  }

  const handleLLMImportanceToggle = async (enabled: boolean) => {
    setUseLLMImportance(enabled)
    try {
      await api.setModel({ use_llm_importance: enabled })
    } catch (error) {
      console.error('Failed to save LLM importance setting:', error)
    }
  }

  const handleMemorySupersededToggle = async (enabled: boolean) => {
    setUseMemorySupersede(enabled)
    try {
      await api.setModel({ use_memory_supersede: enabled })
    } catch (error) {
      console.error('Failed to save memory supersede setting:', error)
    }
  }

  const handleSaveSystemPrompt = async () => {
    setIsSavingPrompt(true)
    try {
      await api.updateSystemPrompt(systemPrompt)
    } catch (error) {
      console.error('Failed to save system prompt:', error)
    } finally {
      setIsSavingPrompt(false)
    }
  }

  const providers = [
    { id: 'openai', name: 'OpenAI', description: 'GPT-4o, GPT-4, GPT-3.5' },
    { id: 'anthropic', name: 'Anthropic', description: 'Claude 3.5, Claude 3' },
    { id: 'google', name: 'Google', description: 'Gemini Pro, Gemini Ultra' },
    { id: 'ollama', name: 'Ollama (Local)', description: 'LLaMA, Mistral, etc.' },
  ]

  return (


    <div className="flex-1 overflow-y-auto">
      <header className="h-16 px-6 flex items-center border-b border-white/10 bg-[#0f0f18]/80 backdrop-blur-xl">
        <h2 className="text-lg font-semibold text-white">Settings</h2>
      </header>

      <div className="p-6 max-w-3xl mx-auto space-y-8">
        {/* Database Status */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-green-400" />
              Database Status
            </h3>
            <button
              onClick={loadDbStats}
              disabled={isLoadingDbStats}
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-all"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingDbStats ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
          
          {dbStats ? (
            <div className="grid grid-cols-5 gap-4">
              {/* Connection Status */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col items-center justify-center text-center">
                <div className="mb-2">
                  {dbStats.connected ? (
                    <CheckCircle className="w-6 h-6 text-green-400" />
                  ) : (
                    <XCircle className="w-6 h-6 text-red-400" />
                  )}
                </div>
                <div className="text-xs text-gray-400">Connection</div>
                <div className={`text-sm font-bold ${dbStats.connected ? 'text-green-400' : 'text-red-400'}`}>
                  {dbStats.connected ? 'Active' : 'Offline'}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 text-center">
                <div className="flex flex-col items-center justify-center h-full">
                  <span className="text-xs text-gray-400 mb-1">Resources</span>
                  <div className="text-xl font-bold text-blue-400">{dbStats.resources}</div>
                </div>
              </div>
              
              <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 text-center">
                <div className="flex flex-col items-center justify-center h-full">
                  <span className="text-xs text-gray-400 mb-1">Categories</span>
                  <div className="text-xl font-bold text-purple-400">{dbStats.categories}</div>
                </div>
              </div>
              
              <div className="p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-green-600/5 border border-green-500/20 text-center">
                <div className="flex flex-col items-center justify-center h-full">
                  <span className="text-xs text-gray-400 mb-1">Memories</span>
                  <div className="text-xl font-bold text-green-400">{dbStats.memory_items}</div>
                </div>
              </div>

              {/* DB Size */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                <div className="flex flex-col items-center justify-center h-full">
                  <HardDrive className="w-4 h-4 text-gray-400 mb-2" />
                  <span className="text-xs text-gray-400 mb-1">Storage</span>
                  <div className="text-sm font-bold text-white">{dbStats.db_size || '0 MB'}</div>
                </div>
              </div>
            </div>
          ) : isLoadingDbStats ? (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
              <span className="text-gray-400">데이터베이스 상태 로딩 중...</span>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm">
              데이터베이스 연결을 확인할 수 없습니다.
            </div>
          )}
        </section>

        {/* Token Usage Tracking */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-white flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-purple-400" />
            Token Usage Tracking
          </h3>
          
          {dbStats?.token_usage && dbStats.token_usage.length > 0 ? (
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 text-gray-400">
                  <tr>
                    <th className="px-4 py-3 font-medium">Model</th>
                    <th className="px-4 py-3 font-medium text-right">Prompt</th>
                    <th className="px-4 py-3 font-medium text-right">Completion</th>
                    <th className="px-4 py-3 font-medium text-right font-bold text-white">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {dbStats.token_usage.map((usage, idx) => (
                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3 font-mono text-blue-400">{usage.model}</td>
                      <td className="px-4 py-3 text-right text-gray-400">{usage.prompt.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-gray-400">{usage.completion.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right font-bold text-white">{usage.total.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="p-3 bg-white/5 border-t border-white/10">
                 <p className="text-[11px] text-gray-500 italic">
                  * Cumulative token counts across all sessions.
                </p>
              </div>
            </div>
          ) : (
             <div className="p-8 text-center bg-white/5 border border-white/10 rounded-xl">
               <p className="text-gray-500">No token usage data recorded yet.</p>
             </div>
          )}
        </section>

        {/* LLM Provider */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-white flex items-center gap-2">
            <Server className="w-5 h-5 text-blue-400" />
            LLM Provider
          </h3>
          
          <div className="grid grid-cols-2 gap-4">
            {providers.map((p) => (
              <button
                key={p.id}
                onClick={() => setProvider(p.id)}
                className={`p-4 rounded-xl border text-left transition-all ${
                  provider === p.id
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="font-medium text-white">{p.name}</div>
                <div className="text-sm text-gray-500 mt-1">{p.description}</div>
              </button>
            ))}
          </div>
        </section>

        {/* API Key */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-white flex items-center gap-2">
            <Key className="w-5 h-5 text-purple-400" />
            API Key
            {isKeySet && (
              <span className="ml-2 px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">
                Configured
              </span>
            )}
          </h3>
          
          <div className="flex gap-4">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={isKeySet ? (settings?.llm?.api_key_masked || '••••••••') : 'Enter your API key'}
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
            <button
              onClick={handleSaveApiKey}
              disabled={!apiKey.trim()}
              className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl text-white font-medium hover:shadow-lg hover:shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Save
            </button>
            {isKeySet && (
              <button
                onClick={handleDeleteApiKey}
                className="px-4 py-3 bg-red-600/20 border border-red-500/30 rounded-xl text-red-400 hover:bg-red-600/30 hover:text-red-300 transition-all flex items-center gap-2"
                title="Delete API Key"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            )}
          </div>

          {/* Test connection */}
          <div className="flex items-center gap-4">
            <button
              onClick={handleTestConnection}
              disabled={isTesting}
              className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 disabled:opacity-50 transition-all"
            >
              {isTesting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Server className="w-4 h-4" />
              )}
              Test Connection
            </button>

            {testResult && (
              <div
                className={`flex items-center gap-2 text-sm ${
                  testResult.success ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {testResult.success ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <XCircle className="w-4 h-4" />
                )}
                {testResult.message}
              </div>
            )}
          </div>
        </section>

        {/* Model Selection - Dual Models */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white">Model Configuration</h3>
            {isKeySet && (
              <button
                onClick={loadModels}
                disabled={isLoadingModels}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingModels ? 'animate-spin' : ''}`} />
                Refresh Models
              </button>
            )}
          </div>
          
          {!isKeySet ? (
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm">
              API 키를 먼저 설정하면 사용 가능한 모델 목록을 자동으로 불러옵니다.
            </div>
          ) : isLoadingModels ? (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
              <span className="text-gray-400">모델 목록을 불러오는 중...</span>
            </div>
          ) : modelsError ? (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {modelsError}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Chat Model */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-400 rounded-full" />
                  <span className="text-gray-300 font-medium">Chat Model</span>
                  <span className="text-xs text-gray-500">(대화 및 추론)</span>
                </div>
                <select
                  value={chatModel}
                  onChange={(e) => handleModelChange('chat', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                >
                  {chatModels.length > 0 ? (
                    chatModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.id}</option>
                    ))
                  ) : (
                    <>
                      <option value="gpt-4o">gpt-4o</option>
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                      <option value="gpt-4-turbo">gpt-4-turbo</option>
                    </>
                  )}
                </select>
              </div>

              {/* Memory Model */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-purple-400 rounded-full" />
                  <span className="text-gray-300 font-medium">Memory Model</span>
                  <span className="text-xs text-gray-500">(Importance 평가)</span>
                </div>
                <select
                  value={memoryModel}
                  onChange={(e) => handleModelChange('memory', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                >
                  {chatModels.length > 0 ? (
                    chatModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.id}</option>
                    ))
                  ) : (
                    <>
                      <option value="gpt-4o-mini">gpt-4o-mini (권장)</option>
                      <option value="gpt-4o">gpt-4o</option>
                    </>
                  )}
                </select>

                {/* LLM Importance Toggle */}
                <div className="flex items-center justify-between pt-3 border-t border-white/10">
                  <div>
                    <span className="text-gray-400">LLM Importance 평가</span>
                    <p className="text-xs text-gray-600">새 기억 저장 시 LLM으로 중요도 평가</p>
                  </div>
                  <button
                    onClick={() => handleLLMImportanceToggle(!useLLMImportance)}
                    className={`relative w-12 h-6 rounded-full transition-colors ${
                      useLLMImportance ? 'bg-purple-500' : 'bg-white/10'
                    }`}
                  >
                    <span
                      className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                        useLLMImportance ? 'translate-x-6' : ''
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Supersede Model (MemGPT-style) */}
              <div className="p-4 rounded-xl bg-white/5 border border-orange-500/30 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-orange-400 rounded-full" />
                  <span className="text-gray-300 font-medium">Supersede Model</span>
                  <span className="text-xs text-gray-500">(모순 감지 - MemGPT)</span>
                </div>
                <select
                  value={supersedeModel}
                  onChange={(e) => handleModelChange('supersede', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                >
                  {chatModels.length > 0 ? (
                    chatModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.id}</option>
                    ))
                  ) : (
                    <>
                      <option value="gpt-4o-mini">gpt-4o-mini (권장)</option>
                      <option value="gpt-4o">gpt-4o</option>
                    </>
                  )}
                </select>

                {/* Memory Supersede Toggle */}
                <div className="flex items-center justify-between pt-3 border-t border-white/10">
                  <div>
                    <span className="text-gray-400">모순 감지 & 대체</span>
                    <p className="text-xs text-gray-600">정정된 기억 자동 대체 (MemGPT 방식)</p>
                  </div>
                  <button
                    onClick={() => handleMemorySupersededToggle(!useMemorySupersede)}
                    className={`relative w-12 h-6 rounded-full transition-colors ${
                      useMemorySupersede ? 'bg-orange-500' : 'bg-white/10'
                    }`}
                  >
                    <span
                      className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                        useMemorySupersede ? 'translate-x-6' : ''
                      }`}
                    />
                  </button>
                </div>
              </div>

              <p className="text-xs text-gray-500">
                💡 Chat: 고성능 | Memory/Supersede: gpt-4o-mini 권장
              </p>
            </div>
          )}
        </section>

        {/* System Prompt */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-white">System Prompt</h3>
          <p className="text-sm text-gray-500">
            AI의 페르소나와 기본 동작을 정의합니다.
          </p>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="예: 당신은 친절하고 전문적인 AI 어시스턴트입니다..."
            rows={6}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
          />
          <button
            onClick={handleSaveSystemPrompt}
            disabled={isSavingPrompt}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl text-white font-medium hover:shadow-lg hover:shadow-purple-500/25 disabled:opacity-50 transition-all"
          >
            <Save className="w-4 h-4" />
            {isSavingPrompt ? 'Saving...' : 'Save System Prompt'}
          </button>
        </section>

        {/* Buffer Settings */}
        <section className="space-y-4">
          <h3 className="text-lg font-medium text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Memory Buffer
          </h3>
          <p className="text-sm text-gray-500">
            대화 버퍼가 플러시되는 토큰 임계값을 설정합니다. 낮을수록 더 자주 메모리가 저장됩니다.
          </p>
          
          <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Flush Threshold</span>
              <span className="text-lg font-bold text-yellow-400">{bufferSettings.flush_threshold_tokens.toLocaleString()} tokens</span>
            </div>
            
            <input
              type="range"
              min="1000"
              max="10000"
              step="500"
              value={bufferSettings.flush_threshold_tokens}
              onChange={(e) => {
                const newValue = parseInt(e.target.value)
                setBufferSettings(prev => ({ ...prev, flush_threshold_tokens: newValue }))
              }}
              onMouseUp={(e) => handleUpdateBufferSettings(parseInt((e.target as HTMLInputElement).value))}
              onTouchEnd={(e) => handleUpdateBufferSettings(parseInt((e.target as HTMLInputElement).value))}
              className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-yellow-400"
            />
            
            {/* Tick marks with actual positions */}
            <div className="relative h-4 text-xs text-gray-500">
              <span className="absolute left-0">1K</span>
              <span className="absolute" style={{ left: '33.3%', transform: 'translateX(-50%)' }}>4K (권장)</span>
              <span className="absolute" style={{ left: '66.6%', transform: 'translateX(-50%)' }}>7K</span>
              <span className="absolute right-0">10K</span>
            </div>
            
            {isSavingBuffer && (
              <div className="flex items-center gap-2 text-sm text-green-400 animate-pulse">
                <CheckCircle className="w-4 h-4" />
                저장됨
              </div>
            )}
          </div>
        </section>

        {/* Memory Scoring Settings */}
        <ScoringSection />

        {/* About */}
        <section className="mt-12 pt-8 border-t border-white/10">
          <div className="text-center text-gray-500 text-sm">
            <p>Eternal Memory System v0.1.0</p>
            <p className="mt-1">Built with ❤️ for AI Memory</p>
          </div>
        </section>
      </div>
    </div>
  )
}
