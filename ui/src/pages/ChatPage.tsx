import { useState, useRef, useEffect } from 'react'
import { Send, Zap, Brain, Loader2, Sparkles, MemoryStick } from 'lucide-react'
import { api } from '../api/client'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  memoriesRetrieved?: { id: string; content: string; category_path: string; confidence: number }[]
  memoriesStored?: { id: string; content: string; category_path: string }[]
  processingInfo?: { mode: string; model: string; memories_found: number; facts_extracted: number }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '안녕하세요! 저는 당신의 대화를 기억하는 AI 어시스턴트입니다. 무엇이든 이야기해주세요. 중요한 정보는 자동으로 기억합니다. 🧠',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mode, setMode] = useState<'fast' | 'deep'>('fast')
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
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
        timestamp: new Date(),
        memoriesRetrieved: result.memories_retrieved,
        memoriesStored: result.memories_stored,
        processingInfo: result.processing_info,
      }

      setMessages(prev => [...prev, assistantMessage])
      
      // Auto-select the new message to show context
      if (result.memories_retrieved.length > 0 || result.memories_stored.length > 0) {
        setSelectedMessage(assistantMessage)
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ 오류가 발생했습니다: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 px-6 flex items-center justify-between border-b border-white/10 bg-[#0f0f18]/80 backdrop-blur-xl">
          <div>
            <h2 className="text-lg font-semibold text-white">Memory-Augmented Chat</h2>
            <p className="text-xs text-gray-500">대화하면서 자동으로 기억합니다</p>
          </div>
          
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
                onClick={() => message.role === 'assistant' && setSelectedMessage(message)}
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
                  {message.timestamp.toLocaleTimeString()}
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
      <aside className="w-80 border-l border-white/10 bg-[#0a0a0f] flex flex-col">
        <header className="h-16 px-4 flex items-center border-b border-white/10">
          <h3 className="text-sm font-medium text-white flex items-center gap-2">
            <MemoryStick className="w-4 h-4 text-purple-400" />
            Memory Inspector
          </h3>
        </header>

        <div className="flex-1 overflow-y-auto p-4">
          {selectedMessage ? (
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
          )}
        </div>
      </aside>
    </div>
  )
}
