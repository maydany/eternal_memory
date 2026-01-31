import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string  // ISO string for serialization
  memoriesRetrieved?: { id: string; content: string; category_path: string; confidence: number }[]
  memoriesStored?: { id: string; content: string; category_path: string }[]
  processingInfo?: { mode: string; model: string; memories_found: number; facts_extracted: number }
}

export interface ChatSession {
  id: string
  name: string
  messages: Message[]
  mode: 'fast' | 'deep'
  selectedMessageId: string | null
  createdAt: string  // ISO string
  lastActiveAt: string  // ISO string
}

interface ChatStore {
  sessions: ChatSession[]
  activeSessionId: string | null
  
  // Session Actions
  createSession: () => void
  deleteSession: (id: string) => void
  setActiveSession: (id: string) => void
  renameSession: (id: string, name: string) => void
  
  // Message Actions
  addMessage: (message: Message) => void
  setMode: (mode: 'fast' | 'deep') => void
  setSelectedMessage: (messageId: string | null) => void
  
  // Helpers
  getActiveSession: () => ChatSession | undefined
}

const MAX_SESSIONS = 5

const createNewSession = (index: number): ChatSession => ({
  id: crypto.randomUUID(),
  name: `Chat ${index}`,
  messages: [
    {
      id: '1',
      role: 'assistant',
      content: '안녕하세요! 저는 당신의 대화를 기억하는 AI 어시스턴트입니다. 무엇이든 이야기해주세요. 중요한 정보는 자동으로 기억합니다. 🧠',
      timestamp: new Date().toISOString(),
    },
  ],
  mode: 'fast',
  selectedMessageId: null,
  createdAt: new Date().toISOString(),
  lastActiveAt: new Date().toISOString(),
})

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [createNewSession(1)],
      activeSessionId: null,
      
      createSession: () => {
        const { sessions } = get()
        if (sessions.length >= MAX_SESSIONS) return
        
        const newSession = createNewSession(sessions.length + 1)
        set({
          sessions: [...sessions, newSession],
          activeSessionId: newSession.id,
        })
      },
      
      deleteSession: (id: string) => {
        const { sessions, activeSessionId } = get()
        
        // Don't delete if it's the only session
        if (sessions.length === 1) {
          // Create a new session and delete the old one
          const newSession = createNewSession(1)
          set({
            sessions: [newSession],
            activeSessionId: newSession.id,
          })
          return
        }
        
        const filtered = sessions.filter(s => s.id !== id)
        const newActiveId = activeSessionId === id 
          ? filtered[0]?.id ?? null
          : activeSessionId
        
        set({
          sessions: filtered,
          activeSessionId: newActiveId,
        })
      },
      
      setActiveSession: (id: string) => {
        const { sessions } = get()
        const session = sessions.find(s => s.id === id)
        if (session) {
          set({
            activeSessionId: id,
            sessions: sessions.map(s => 
              s.id === id 
                ? { ...s, lastActiveAt: new Date().toISOString() }
                : s
            ),
          })
        }
      },
      
      renameSession: (id: string, name: string) => {
        set({
          sessions: get().sessions.map(s =>
            s.id === id ? { ...s, name } : s
          ),
        })
      },
      
      addMessage: (message: Message) => {
        const { sessions, activeSessionId } = get()
        if (!activeSessionId) return
        
        set({
          sessions: sessions.map(s =>
            s.id === activeSessionId
              ? { 
                  ...s, 
                  messages: [...s.messages, message],
                  lastActiveAt: new Date().toISOString(),
                }
              : s
          ),
        })
      },
      
      setMode: (mode: 'fast' | 'deep') => {
        const { sessions, activeSessionId } = get()
        if (!activeSessionId) return
        
        set({
          sessions: sessions.map(s =>
            s.id === activeSessionId ? { ...s, mode } : s
          ),
        })
      },
      
      setSelectedMessage: (messageId: string | null) => {
        const { sessions, activeSessionId } = get()
        if (!activeSessionId) return
        
        set({
          sessions: sessions.map(s =>
            s.id === activeSessionId ? { ...s, selectedMessageId: messageId } : s
          ),
        })
      },
      
      getActiveSession: () => {
        const { sessions, activeSessionId } = get()
        return sessions.find(s => s.id === activeSessionId)
      },
    }),
    {
      name: 'eternal-memory-chat-sessions',
      // Initialize activeSessionId on hydration if null
      onRehydrateStorage: () => (state) => {
        if (state && !state.activeSessionId && state.sessions.length > 0) {
          state.activeSessionId = state.sessions[0].id
        }
      },
    }
  )
)
