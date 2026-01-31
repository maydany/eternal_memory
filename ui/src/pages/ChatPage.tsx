import { useState, useRef, useEffect } from 'react'
import { Send, Zap, Brain, Loader2, Sparkles, MemoryStick, Database, RefreshCw, Trash2, Activity, CheckCircle2, Clock, SkipForward, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { api } from '../api/client'
import type { ProcessStep } from '../api/client'
import { useChatStore } from '../store/chatStore'
import type { Message } from '../store/chatStore'
import SessionTabs from '../components/SessionTabs'

interface BufferStatus {
  message_count: number
  estimated_tokens: number
  threshold_tokens: number
  fill_percentage: number
  auto_flush_enabled: boolean
}

interface BufferMessage {
  role: string
  content: string
  timestamp: string
}

export default function ChatPage() {
  // Zustand store
  const { 
    sessions, 
    activeSessionId, 
    addMessage, 
    setMode: setSessionMode, 
    setSelectedMessage: setSessionSelectedMessage,
    setActiveSession 
  } = useChatStore()
  
  // Initialize active session on first load
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSession(sessions[0].id)
    }
  }, [activeSessionId, sessions, setActiveSession])
  
  // Get active session
  const activeSession = sessions.find(s => s.id === activeSessionId)
  const messages = activeSession?.messages ?? []
  const mode = activeSession?.mode ?? 'fast'
  const selectedMessageId = activeSession?.selectedMessageId
  const selectedMessage = messages.find(m => m.id === selectedMessageId) ?? null
  
  // Local UI state
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Sidebar state (global, not per-session)
  const [activeTab, setActiveTab] = useState<'memory' | 'buffer' | 'process'>('memory')
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [bufferStatus, setBufferStatus] = useState<BufferStatus | null>(null)
  const [bufferMessages, setBufferMessages] = useState<BufferMessage[]>([])
  const [isFlushLoading, setIsFlushLoading] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load buffer status when switching to buffer tab
  useEffect(() => {
    if (activeTab === 'buffer') {
      loadBufferData()
    }
  }, [activeTab])

  // Auto-refresh buffer data every 5 seconds when on buffer tab
  useEffect(() => {
    if (activeTab !== 'buffer') return
    
    const interval = setInterval(loadBufferData, 5000)
    return () => clearInterval(interval)
  }, [activeTab])

  const loadBufferData = async () => {
    try {
      const [status, msgs] = await Promise.all([
        api.getBufferStatus(),
        api.getBufferMessages(10),
      ])
      setBufferStatus(status)
      setBufferMessages(msgs.messages)
    } catch (err) {
      console.error('Failed to load buffer data:', err)
    }
  }

  const handleFlush = async () => {
    setIsFlushLoading(true)
    try {
      await api.flushBuffer()
      await loadBufferData()
    } catch (err) {
      console.error('Flush failed:', err)
    } finally {
      setIsFlushLoading(false)
    }
  }

  const setMode = (newMode: 'fast' | 'deep') => {
    setSessionMode(newMode)
  }

  const handleSelectMessage = (message: Message | null) => {
    setSessionSelectedMessage(message?.id ?? null)
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading || !activeSessionId) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    addMessage(userMessage)
    setInput('')
    setIsLoading(true)

    try {
      // Build conversation history for context
      const conversationHistory = messages
        .filter(m => m.role !== 'system')
        .slice(-10)
        .map(m => ({
          role: m.role,
          content: m.content,
        }))

      // Call the natural conversation endpoint
      const result = await api.conversation(userMessage.content, mode, conversationHistory)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.response,
        timestamp: new Date().toISOString(),
        memoriesRetrieved: result.memories_retrieved,
        memoriesStored: result.memories_stored,
        processingInfo: result.processing_info,
      }

      addMessage(assistantMessage)
      
      // Auto-select the new message to show context
      if (result.memories_retrieved.length > 0 || result.memories_stored.length > 0) {
        handleSelectMessage(assistantMessage)
      }

      // Refresh buffer data if on buffer tab
      if (activeTab === 'buffer') {
        loadBufferData()
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ 오류가 발생했습니다: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      }
      addMessage(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const formatTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return ts
    }
  }

  const formatMessageTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString()
    } catch {
      return ''
    }
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 px-6 flex items-center justify-between border-b border-white/10 bg-[#0f0f18]/80 backdrop-blur-xl">
          {/* Session Tabs */}
          <SessionTabs />
          
          {/* Mode Toggle */}
          <div className="flex items-center gap-2 bg-white/5 rounded-full p-1">
            <button
              onClick={() => setMode('fast')}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                mode === 'fast'
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Zap className="w-4 h-4" />
              Fast
            </button>
            <button
              onClick={() => setMode('deep')}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                mode === 'deep'
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Brain className="w-4 h-4" />
              Deep
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 cursor-pointer transition-all ${
                  message.role === 'user'
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                    : 'bg-white/5 text-gray-100 border border-white/10 hover:border-white/20'
                } ${selectedMessage?.id === message.id ? 'ring-2 ring-purple-500' : ''}`}
                onClick={() => message.role === 'assistant' && handleSelectMessage(message)}
              >
                <div className="whitespace-pre-wrap break-words">
                  {message.content || ''}
                </div>
                
                {/* Memory indicators */}
                {message.role === 'assistant' && (message.memoriesRetrieved?.length || message.memoriesStored?.length) ? (
                  <div className="flex items-center gap-3 mt-2 pt-2 border-t border-white/10 text-xs">
                    {message.memoriesRetrieved && message.memoriesRetrieved.length > 0 && (
                      <span className="flex items-center gap-1 text-cyan-400">
                        <Brain className="w-3 h-3" />
                        {message.memoriesRetrieved.length} 기억 참조
                      </span>
                    )}
                    {message.memoriesStored && message.memoriesStored.length > 0 && (
                      <span className="flex items-center gap-1 text-green-400">
                        <Sparkles className="w-3 h-3" />
                        {message.memoriesStored.length} 새 기억
                      </span>
                    )}
                  </div>
                ) : null}
                
                <div className="text-xs text-gray-500 mt-2">
                  {formatMessageTimestamp(message.timestamp)}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/5 rounded-2xl px-4 py-3 border border-white/10">
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>생각하고 기억을 검색하는 중...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/10">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="무엇이든 이야기해주세요... (엔터로 전송)"
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl text-white hover:shadow-lg hover:shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Context Inspector Sidebar */}
      <aside className="w-96 border-l border-white/10 bg-[#0a0a0f] flex flex-col">
        {/* Tab Header */}
        <header className="h-16 px-3 flex items-center border-b border-white/10">
          <div className="flex w-full bg-white/5 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('memory')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-all ${
                activeTab === 'memory'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <MemoryStick className="w-3.5 h-3.5" />
              Memory
            </button>
            <button
              onClick={() => setActiveTab('buffer')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-all ${
                activeTab === 'buffer'
                  ? 'bg-orange-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Buffer
              {bufferStatus && bufferStatus.message_count > 0 && (
                <span className="ml-0.5 px-1.5 py-0.5 text-[10px] bg-orange-500/30 rounded-full">
                  {bufferStatus.message_count}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('process')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-xs font-medium transition-all ${
                activeTab === 'process'
                  ? 'bg-teal-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              Process
            </button>
          </div>
        </header>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'memory' && (
            /* Memory Tab Content */
            selectedMessage ? (
              <div className="space-y-4">
                {/* Processing Info */}
                {selectedMessage.processingInfo && (
                  <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <h4 className="text-xs font-medium text-gray-400 mb-2">처리 정보</h4>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">모드</span>
                        <span className="text-white">{selectedMessage.processingInfo.mode}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">모델</span>
                        <span className="text-white">{selectedMessage.processingInfo.model}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">참조된 기억</span>
                        <span className="text-cyan-400">{selectedMessage.processingInfo.memories_found}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">저장된 사실</span>
                        <span className="text-green-400">{selectedMessage.processingInfo.facts_extracted}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Retrieved Memories */}
                {selectedMessage.memoriesRetrieved && selectedMessage.memoriesRetrieved.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-cyan-400 mb-2 flex items-center gap-1">
                      <Brain className="w-3 h-3" />
                      참조된 기억
                    </h4>
                    <div className="space-y-2">
                      {selectedMessage.memoriesRetrieved.map((memory, idx) => (
                        <div key={idx} className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-xs">
                          <p className="text-gray-200">{memory.content}</p>
                          <div className="flex justify-between mt-1 text-gray-500">
                            <span>{memory.category_path}</span>
                            <span>{Math.round(memory.confidence * 100)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Stored Memories */}
                {selectedMessage.memoriesStored && selectedMessage.memoriesStored.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-green-400 mb-2 flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      새로 저장된 기억
                    </h4>
                    <div className="space-y-2">
                      {selectedMessage.memoriesStored.map((memory, idx) => (
                        <div key={idx} className="p-2 rounded-lg bg-green-500/10 border border-green-500/20 text-xs">
                          <p className="text-gray-200">{memory.content}</p>
                          <p className="text-gray-500 mt-1">{memory.category_path}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* No memories */}
                {(!selectedMessage.memoriesRetrieved?.length && !selectedMessage.memoriesStored?.length) && (
                  <div className="text-center text-gray-500 text-sm py-8">
                    이 응답에서는 기억이 사용되거나<br />저장되지 않았습니다.
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 text-sm">
                <Brain className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-center">
                  AI 응답을 클릭하면<br />
                  사용된 기억을 확인할 수 있습니다
                </p>
              </div>
            )
          )}

          {activeTab === 'buffer' && (
            /* Buffer Tab Content */
            <div className="space-y-4">
              {/* Buffer Status Card */}
              {bufferStatus && (
                <div className="p-4 rounded-xl bg-gradient-to-br from-orange-500/10 to-red-500/5 border border-orange-500/20">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-white">버퍼 상태</h4>
                    <button
                      onClick={loadBufferData}
                      className="p-1 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">토큰 사용량</span>
                      <span className="text-white">{bufferStatus.estimated_tokens} / {bufferStatus.threshold_tokens}</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all ${
                          bufferStatus.fill_percentage >= 80 
                            ? 'bg-gradient-to-r from-red-500 to-orange-500' 
                            : bufferStatus.fill_percentage >= 50 
                              ? 'bg-gradient-to-r from-orange-500 to-yellow-500'
                              : 'bg-gradient-to-r from-green-500 to-emerald-500'
                        }`}
                        style={{ width: `${bufferStatus.fill_percentage}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-500 mt-1 text-right">
                      {bufferStatus.fill_percentage}% 사용
                    </div>
                  </div>
                  
                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 bg-white/5 rounded-lg">
                      <div className="text-gray-400">메시지 수</div>
                      <div className="text-lg font-bold text-white">{bufferStatus.message_count}</div>
                    </div>
                    <div className="p-2 bg-white/5 rounded-lg">
                      <div className="text-gray-400">자동 플러시</div>
                      <div className={`text-lg font-bold ${bufferStatus.auto_flush_enabled ? 'text-green-400' : 'text-gray-500'}`}>
                        {bufferStatus.auto_flush_enabled ? 'ON' : 'OFF'}
                      </div>
                    </div>
                  </div>
                  
                  {/* Flush Button */}
                  <button
                    onClick={handleFlush}
                    disabled={isFlushLoading || bufferStatus.message_count === 0}
                    className="w-full mt-3 flex items-center justify-center gap-2 py-2 bg-orange-600 hover:bg-orange-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white text-sm font-medium transition-colors"
                  >
                    {isFlushLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        플러시 중...
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        지금 플러시
                      </>
                    )}
                  </button>
                </div>
              )}
              
              {/* Buffer Messages */}
              <div>
                <h4 className="text-xs font-medium text-gray-400 mb-2">최근 버퍼 메시지</h4>
                {bufferMessages.length > 0 ? (
                  <div className="space-y-2">
                    {bufferMessages.map((msg, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-white/5 border border-white/10 text-xs">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                            msg.role === 'user' 
                              ? 'bg-blue-500/20 text-blue-400' 
                              : 'bg-purple-500/20 text-purple-400'
                          }`}>
                            {msg.role === 'user' ? 'USER' : 'AI'}
                          </span>
                          <span className="text-gray-500">{formatTimestamp(msg.timestamp)}</span>
                        </div>
                        <p className="text-gray-300 line-clamp-2">{msg.content}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-gray-500 text-sm py-8">
                    <Database className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    버퍼가 비어있습니다
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'process' && (
            /* Process Tab Content */
            selectedMessage?.processingInfo?.process_steps ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-medium text-teal-400 flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5" />
                    처리 과정
                  </h4>
                  <span className="text-[10px] text-gray-500">
                    총 {selectedMessage.processingInfo.process_steps.reduce((acc: number, s: ProcessStep) => acc + (s.duration_ms || 0), 0)}ms
                  </span>
                </div>

                {selectedMessage.processingInfo.process_steps.map((step: ProcessStep, idx: number) => {
                  const stepLabels: Record<string, string> = {
                    memory_retrieval: '🔍 메모리 검색',
                    context_building: '🏗️ 컨텍스트 구성',
                    llm_generation: '🤖 LLM 응답 생성',
                    fact_extraction: '💡 사실 추출',
                    triple_extraction: '🔗 트리플 추출',
                    buffer_update: '📝 버퍼 업데이트',
                  }
                  
                  const isExpanded = expandedSteps.has(step.step)
                  
                  const toggleExpand = () => {
                    setExpandedSteps(prev => {
                      const next = new Set(prev)
                      if (next.has(step.step)) {
                        next.delete(step.step)
                      } else {
                        next.add(step.step)
                      }
                      return next
                    })
                  }

                  const getStatusIcon = (status: string) => {
                    switch (status) {
                      case 'completed':
                        return <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                      case 'skipped':
                        return <SkipForward className="w-3.5 h-3.5 text-gray-500" />
                      case 'error':
                        return <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                      case 'running':
                        return <Loader2 className="w-3.5 h-3.5 text-teal-400 animate-spin" />
                      default:
                        return <Clock className="w-3.5 h-3.5 text-gray-400" />
                    }
                  }

                  const getStatusColor = (status: string) => {
                    switch (status) {
                      case 'completed': return 'border-green-500/30 bg-green-500/5'
                      case 'skipped': return 'border-gray-500/30 bg-gray-500/5'
                      case 'error': return 'border-red-500/30 bg-red-500/5'
                      default: return 'border-teal-500/30 bg-teal-500/5'
                    }
                  }

                  return (
                    <div
                      key={idx}
                      className={`rounded-lg border ${getStatusColor(step.status)} transition-all`}
                    >
                      {/* Step Header */}
                      <button
                        onClick={toggleExpand}
                        className="w-full p-3 flex items-center justify-between text-left"
                      >
                        <div className="flex items-center gap-2">
                          {getStatusIcon(step.status)}
                          <span className="text-xs font-medium text-white">
                            {stepLabels[step.step] || step.step}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {step.duration_ms !== undefined && (
                            <span className="text-[10px] text-gray-400">
                              {step.duration_ms}ms
                            </span>
                          )}
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
                          )}
                        </div>
                      </button>

                      {/* Step Details (Expandable) */}
                      {isExpanded && step.details && (
                        <div className="px-3 pb-3 pt-0">
                          <div className="border-t border-white/5 pt-2 space-y-1.5 text-[11px]">
                            {step.step === 'memory_retrieval' && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">검색 모드</span>
                                  <span className="text-white">{step.details.mode}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">검색된 항목</span>
                                  <span className="text-cyan-400">{step.details.items_found}개</span>
                                </div>
                                {step.details.categories_matched && step.details.categories_matched.length > 0 && (
                                  <div>
                                    <span className="text-gray-500">매칭 카테고리:</span>
                                    <div className="mt-1 flex flex-wrap gap-1">
                                      {step.details.categories_matched.map((cat: string, i: number) => (
                                        <span key={i} className="px-1.5 py-0.5 bg-white/5 rounded text-gray-300">
                                          {cat}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {/* Retrieved Items Content */}
                                {step.details.retrieved_items && step.details.retrieved_items.length > 0 && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-gray-400 text-[10px] uppercase tracking-wide">검색된 메모리 내용</span>
                                    <div className="mt-1.5 space-y-1.5">
                                      {step.details.retrieved_items.map((item: {content: string; category_path: string; confidence: number}, i: number) => (
                                        <div key={i} className="p-2 bg-cyan-500/10 rounded border border-cyan-500/20">
                                          <p className="text-gray-200 text-[10px] leading-relaxed">{item.content}</p>
                                          <div className="flex justify-between mt-1 text-[9px] text-gray-500">
                                            <span>{item.category_path}</span>
                                            <span>{Math.round(item.confidence * 100)}%</span>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {step.step === 'context_building' && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">시스템 프롬프트</span>
                                  <span className="text-white">{step.details.system_prompt_length} chars</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">메모리 컨텍스트</span>
                                  <span className="text-cyan-400">{step.details.memory_context_length} chars</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">히스토리 메시지</span>
                                  <span className="text-white">{step.details.history_messages}개</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">총 메시지</span>
                                  <span className="text-white">{step.details.total_messages}개</span>
                                </div>
                                {step.details.pruned_messages !== undefined && step.details.pruned_messages > 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">프루닝된 메시지</span>
                                    <span className="text-orange-400">{step.details.pruned_messages}개</span>
                                  </div>
                                )}
                                {/* System Prompt Preview */}
                                {step.details.system_prompt_preview && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-gray-400 text-[10px] uppercase tracking-wide">시스템 프롬프트</span>
                                    <div className="mt-1 p-2 bg-white/5 rounded text-[10px] text-gray-300 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                                      {step.details.system_prompt_preview}
                                    </div>
                                  </div>
                                )}
                                {/* Memory Context Preview */}
                                {step.details.memory_context_preview && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-cyan-400 text-[10px] uppercase tracking-wide">메모리 컨텍스트</span>
                                    <div className="mt-1 p-2 bg-cyan-500/10 rounded border border-cyan-500/20 text-[10px] text-gray-300 whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto">
                                      {step.details.memory_context_preview}
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {step.step === 'llm_generation' && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">모델</span>
                                  <span className="text-purple-400 font-mono">{step.details.model}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">프롬프트 토큰</span>
                                  <span className="text-white">{step.details.tokens_prompt}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">응답 토큰</span>
                                  <span className="text-white">{step.details.tokens_completion}</span>
                                </div>
                                <div className="flex justify-between font-medium">
                                  <span className="text-gray-500">총 토큰</span>
                                  <span className="text-yellow-400">{step.details.tokens_total}</span>
                                </div>
                                {/* Response Preview */}
                                {step.details.response_preview && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-purple-400 text-[10px] uppercase tracking-wide">LLM 응답 미리보기</span>
                                    <div className="mt-1 p-2 bg-purple-500/10 rounded border border-purple-500/20 text-[10px] text-gray-300 leading-relaxed">
                                      {step.details.response_preview}
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {step.step === 'fact_extraction' && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">추출 모델</span>
                                  <span className="text-purple-400 font-mono">{step.details.extraction_model}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">추출된 사실</span>
                                  <span className={step.details.facts_found ? 'text-green-400' : 'text-gray-500'}>
                                    {step.details.facts_found}개
                                  </span>
                                </div>
                                {/* Extracted Facts Content */}
                                {step.details.extracted_facts && step.details.extracted_facts.length > 0 && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-green-400 text-[10px] uppercase tracking-wide">추출된 사실 내용</span>
                                    <div className="mt-1.5 space-y-1">
                                      {step.details.extracted_facts.map((fact: string, i: number) => (
                                        <div key={i} className="p-2 bg-green-500/10 rounded border border-green-500/20">
                                          <p className="text-gray-200 text-[10px] leading-relaxed">💡 {fact}</p>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {/* Raw Extraction Preview (if no facts found) */}
                                {step.details.raw_extraction && step.details.facts_found === 0 && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-gray-400 text-[10px] uppercase tracking-wide">LLM 추출 응답</span>
                                    <div className="mt-1 p-2 bg-white/5 rounded text-[10px] text-gray-400 italic">
                                      {step.details.raw_extraction}
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {step.step === 'triple_extraction' && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">트리플 활성화</span>
                                  <span className={step.details.triples_enabled ? 'text-green-400' : 'text-gray-500'}>
                                    {step.details.triples_enabled ? 'ON' : 'OFF'}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">추출 모드</span>
                                  <span className={`${
                                    step.details.extraction_mode === 'immediate' 
                                      ? 'text-cyan-400' 
                                      : 'text-orange-400'
                                  }`}>
                                    {step.details.extraction_mode === 'immediate' ? '즉시 추출' : '지연 추출'}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">처리된 사실</span>
                                  <span className="text-white">{step.details.facts_processed}개</span>
                                </div>
                                {step.details.estimated_triples !== null && step.details.estimated_triples !== undefined && (
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">추출된 트리플 (추정)</span>
                                    <span className="text-cyan-400">~{step.details.estimated_triples}개</span>
                                  </div>
                                )}
                                {step.details.pending_extraction !== undefined && step.details.pending_extraction > 0 && (
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">대기 중인 추출</span>
                                    <span className="text-orange-400">{step.details.pending_extraction}개</span>
                                  </div>
                                )}
                                {/* Description */}
                                {step.details.description && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <div className="p-2 bg-indigo-500/10 rounded border border-indigo-500/20">
                                      <p className="text-gray-300 text-[10px] leading-relaxed">
                                        🔗 {step.details.description}
                                      </p>
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {step.step === 'buffer_update' && (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">버퍼에 추가</span>
                                  <span className="text-white">{step.details.messages_buffered}개 메시지</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">버퍼 사용량</span>
                                  <span className={`${
                                    (step.details.buffer_fill_percentage ?? 0) >= 80 
                                      ? 'text-red-400' 
                                      : 'text-white'
                                  }`}>
                                    {step.details.buffer_fill_percentage}%
                                  </span>
                                </div>
                                {/* Buffered Messages Content */}
                                {step.details.buffered_messages && step.details.buffered_messages.length > 0 && (
                                  <div className="mt-2 pt-2 border-t border-white/5">
                                    <span className="text-orange-400 text-[10px] uppercase tracking-wide">버퍼에 추가된 메시지</span>
                                    <div className="mt-1.5 space-y-1.5">
                                      {step.details.buffered_messages.map((msg: {role: string; content_preview: string}, i: number) => (
                                        <div key={i} className={`p-2 rounded border ${
                                          msg.role === 'user' 
                                            ? 'bg-blue-500/10 border-blue-500/20' 
                                            : 'bg-purple-500/10 border-purple-500/20'
                                        }`}>
                                          <div className="flex items-center gap-1.5 mb-1">
                                            <span className={`px-1 py-0.5 rounded text-[9px] font-medium ${
                                              msg.role === 'user' 
                                                ? 'bg-blue-500/30 text-blue-300' 
                                                : 'bg-purple-500/30 text-purple-300'
                                            }`}>
                                              {msg.role === 'user' ? 'USER' : 'AI'}
                                            </span>
                                          </div>
                                          <p className="text-gray-200 text-[10px] leading-relaxed">{msg.content_preview}</p>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {step.details.error && (
                              <div className="p-2 bg-red-500/10 rounded text-red-400">
                                ⚠️ {step.details.error}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 text-sm">
                <Activity className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-center">
                  AI 응답을 클릭하면<br />
                  처리 과정을 확인할 수 있습니다
                </p>
              </div>
            )
          )}
        </div>
      </aside>
    </div>
  )
}
