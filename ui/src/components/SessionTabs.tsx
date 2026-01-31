import { Plus, X } from 'lucide-react'
import { useChatStore } from '../store/chatStore'

const MAX_SESSIONS = 5

export default function SessionTabs() {
  const { sessions, activeSessionId, createSession, deleteSession, setActiveSession } = useChatStore()

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    deleteSession(id)
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
      {sessions.map((session) => (
        <button
          key={session.id}
          onClick={() => setActiveSession(session.id)}
          className={`group flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
            activeSessionId === session.id
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg'
              : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
          }`}
        >
          <span className="max-w-[100px] truncate">{session.name}</span>
          <span
            onClick={(e) => handleDelete(e, session.id)}
            className={`p-0.5 rounded hover:bg-white/20 transition-colors ${
              activeSessionId === session.id ? 'text-white/70 hover:text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <X className="w-3 h-3" />
          </span>
        </button>
      ))}
      
      {sessions.length < MAX_SESSIONS && (
        <button
          onClick={createSession}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white transition-all"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">New</span>
        </button>
      )}
    </div>
  )
}
