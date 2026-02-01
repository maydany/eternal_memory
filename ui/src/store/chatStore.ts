import { create } from 'zustand'
import type { ProcessStep } from '../api/client'
import { api } from '../api/client'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string  // ISO string for serialization
  memoriesRetrieved?: { id: string; content: string; category_path: string; confidence: number }[]
  memoriesStored?: { id: string; content: string; category_path: string }[]
  processingInfo?: { 
    mode: string
    model: string
    memories_found: number
    facts_extracted: number
    process_steps?: ProcessStep[]
  }
}

export interface ChatSession {
  id: string
  name: string
  messages: Message[]
  mode: 'fast' | 'deep'
  selectedMessageId: string | null
  contextSummary: string | null      // Rolling summary cache
  summarizedCount: number            // For stale cache detection
  createdAt: string  // ISO string
  lastActiveAt: string  // ISO string
}

interface ChatStore {
  sessions: ChatSession[]
  activeSessionId: string | null
  isLoading: boolean
  isInitialized: boolean
  
  // Session Actions (now async, server-backed)
  initializeSessions: () => Promise<void>
  createSession: () => Promise<void>
  deleteSession: (id: string) => Promise<void>
  setActiveSession: (id: string) => Promise<void>
  renameSession: (id: string, name: string) => Promise<void>
  
  // Message Actions
  addMessage: (message: Message) => Promise<void>
  setMode: (mode: 'fast' | 'deep') => Promise<void>
  setSelectedMessage: (messageId: string | null) => Promise<void>
  
  // Rolling summary cache actions
  updateSummaryCache: (summary: string | null, count: number) => Promise<void>
  
  // Helpers
  getActiveSession: () => ChatSession | undefined
}

const MAX_SESSIONS = 5

// Convert server response to local ChatSession format
const mapServerSession = (serverSession: {
  id: string;
  name: string;
  messages: { id: string; role: string; content: string; timestamp: string }[];
  mode: string;
  context_summary: string | null;
  summarized_count: number;
  selected_message_id: string | null;
  created_at: string;
  last_active_at: string;
}): ChatSession => ({
  id: serverSession.id,
  name: serverSession.name,
  messages: serverSession.messages as Message[],
  mode: serverSession.mode as 'fast' | 'deep',
  selectedMessageId: serverSession.selected_message_id,
  contextSummary: serverSession.context_summary,
  summarizedCount: serverSession.summarized_count,
  createdAt: serverSession.created_at,
  lastActiveAt: serverSession.last_active_at,
})

export const useChatStore = create<ChatStore>()(
  (set, get) => ({
    sessions: [],
    activeSessionId: null,
    isLoading: false,
    isInitialized: false,
    
    initializeSessions: async () => {
      const { isInitialized } = get()
      if (isInitialized) return
      
      set({ isLoading: true })
      try {
        // Fetch session list from server
        const sessionList = await api.listSessions()
        
        if (sessionList.length === 0) {
          // No sessions exist, create first one
          const newSession = await api.createSession('Chat 1')
          set({
            sessions: [mapServerSession(newSession)],
            activeSessionId: newSession.id,
            isInitialized: true,
            isLoading: false,
          })
        } else {
          // Load full session data for each session
          const fullSessions = await Promise.all(
            sessionList.map(s => api.getSession(s.id))
          )
          set({
            sessions: fullSessions.map(mapServerSession),
            activeSessionId: sessionList[0].id,
            isInitialized: true,
            isLoading: false,
          })
        }
      } catch (error) {
        console.error('Failed to initialize sessions:', error)
        // Fallback: create local session if server unavailable
        const fallbackSession: ChatSession = {
          id: crypto.randomUUID(),
          name: 'Chat 1',
          messages: [{
            id: '1',
            role: 'assistant',
            content: '안녕하세요! 저는 당신의 대화를 기억하는 AI 어시스턴트입니다. 무엇이든 이야기해주세요. 중요한 정보는 자동으로 기억합니다. 🧠',
            timestamp: new Date().toISOString(),
          }],
          mode: 'fast',
          selectedMessageId: null,
          contextSummary: null,
          summarizedCount: 0,
          createdAt: new Date().toISOString(),
          lastActiveAt: new Date().toISOString(),
        }
        set({
          sessions: [fallbackSession],
          activeSessionId: fallbackSession.id,
          isInitialized: true,
          isLoading: false,
        })
      }
    },
    
    createSession: async () => {
      const { sessions } = get()
      if (sessions.length >= MAX_SESSIONS) return
      
      set({ isLoading: true })
      try {
        const newSession = await api.createSession(`Chat ${sessions.length + 1}`)
        set({
          sessions: [...sessions, mapServerSession(newSession)],
          activeSessionId: newSession.id,
          isLoading: false,
        })
      } catch (error) {
        console.error('Failed to create session:', error)
        set({ isLoading: false })
      }
    },
    
    deleteSession: async (id: string) => {
      const { sessions, activeSessionId } = get()
      
      set({ isLoading: true })
      try {
        if (sessions.length === 1) {
          // If last session, delete then create new one
          await api.deleteSession(id)
          const newSession = await api.createSession('Chat 1')
          set({
            sessions: [mapServerSession(newSession)],
            activeSessionId: newSession.id,
            isLoading: false,
          })
        } else {
          await api.deleteSession(id)
          const filtered = sessions.filter(s => s.id !== id)
          const newActiveId = activeSessionId === id 
            ? filtered[0]?.id ?? null
            : activeSessionId
          
          set({
            sessions: filtered,
            activeSessionId: newActiveId,
            isLoading: false,
          })
        }
      } catch (error) {
        console.error('Failed to delete session:', error)
        set({ isLoading: false })
      }
    },
    
    setActiveSession: async (id: string) => {
      const { sessions } = get()
      const session = sessions.find(s => s.id === id)
      if (session) {
        set({ activeSessionId: id })
        // Update server-side last_active_at
        try {
          await api.updateSession(id, {})  // Empty update just triggers last_active_at
        } catch (error) {
          console.error('Failed to update session activity:', error)
        }
      }
    },
    
    renameSession: async (id: string, name: string) => {
      try {
        await api.updateSession(id, { name })
        set({
          sessions: get().sessions.map(s =>
            s.id === id ? { ...s, name } : s
          ),
        })
      } catch (error) {
        console.error('Failed to rename session:', error)
      }
    },
    
    addMessage: async (message: Message) => {
      const { sessions, activeSessionId } = get()
      if (!activeSessionId) return
      
      // Optimistic update
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
      
      // Sync to server
      try {
        await api.addMessageToSession(activeSessionId, message)
      } catch (error) {
        console.error('Failed to sync message to server:', error)
      }
    },
    
    setMode: async (mode: 'fast' | 'deep') => {
      const { sessions, activeSessionId } = get()
      if (!activeSessionId) return
      
      set({
        sessions: sessions.map(s =>
          s.id === activeSessionId ? { ...s, mode } : s
        ),
      })
      
      try {
        await api.updateSession(activeSessionId, { mode })
      } catch (error) {
        console.error('Failed to update mode:', error)
      }
    },
    
    setSelectedMessage: async (messageId: string | null) => {
      const { sessions, activeSessionId } = get()
      if (!activeSessionId) return
      
      set({
        sessions: sessions.map(s =>
          s.id === activeSessionId ? { ...s, selectedMessageId: messageId } : s
        ),
      })
      
      // Optionally sync to server (not critical)
      try {
        await api.updateSession(activeSessionId, { selected_message_id: messageId || undefined })
      } catch (error) {
        // Non-critical, don't log
      }
    },
    
    updateSummaryCache: async (summary: string | null, count: number) => {
      const { sessions, activeSessionId } = get()
      if (!activeSessionId) return
      
      set({
        sessions: sessions.map(s =>
          s.id === activeSessionId 
            ? { ...s, contextSummary: summary, summarizedCount: count }
            : s
        ),
      })
      
      // Sync to server for cross-device persistence
      try {
        await api.updateSession(activeSessionId, {
          context_summary: summary || undefined,
          summarized_count: count,
        })
      } catch (error) {
        console.error('Failed to sync summary cache:', error)
      }
    },
    
    getActiveSession: () => {
      const { sessions, activeSessionId } = get()
      return sessions.find(s => s.id === activeSessionId)
    },
  })
)
