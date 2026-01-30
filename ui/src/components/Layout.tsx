import { useState, useEffect } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { MessageSquare, LayoutGrid, Settings, Database, RefreshCw, Brain, FolderOpen } from 'lucide-react'
import { api } from '../api/client'

export default function Layout() {
  const [stats, setStats] = useState({ items: 0, categories: 0 })
  const [isLoading, setIsLoading] = useState(false)

  const loadStats = async () => {
    setIsLoading(true)
    try {
      const data = await api.getStats()
      setStats({
        items: data.memory_items || data.resources || 0,
        categories: data.categories || 0,
      })
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
      isActive
        ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/25'
        : 'text-gray-400 hover:text-white hover:bg-white/5'
    }`

  return (
    <div className="flex h-full bg-[#0a0a0f]">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col border-r border-white/10 bg-gradient-to-b from-[#0f0f18] to-[#0a0a0f]">
        {/* Logo */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Eternal Memory</h1>
              <p className="text-xs text-gray-500">AI Memory System</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          <NavLink to="/" className={linkClass}>
            <MessageSquare className="w-5 h-5" />
            <span>Chat</span>
          </NavLink>
          <NavLink to="/vault" className={linkClass}>
            <FolderOpen className="w-5 h-5" />
            <span>Memory Vault</span>
          </NavLink>
          <NavLink to="/database" className={linkClass}>
            <Database className="w-5 h-5" />
            <span>Database</span>
          </NavLink>
          <NavLink to="/settings" className={linkClass}>
            <Settings className="w-5 h-5" />
            <span>Settings</span>
          </NavLink>
        </nav>

        {/* Stats */}
        <div className="p-4 border-t border-white/10">
          <div className="rounded-xl bg-white/5 p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-500">Memory Stats</p>
              <button 
                onClick={loadStats}
                disabled={isLoading}
                className="text-gray-500 hover:text-white transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-center">
                <div className="text-xl font-bold text-blue-400">{stats.items}</div>
                <div className="text-xs text-gray-500">Items</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-purple-400">{stats.categories}</div>
                <div className="text-xs text-gray-500">Categories</div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
