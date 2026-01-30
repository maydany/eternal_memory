import { useState, useEffect } from 'react'
import { FolderOpen, FileText, ChevronRight, ChevronDown, Search, Save, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { api } from '../api/client'
import type { FileNode } from '../api/client'

interface TreeNodeProps {
  node: FileNode
  level: number
  selectedPath: string | null
  onSelect: (path: string) => void
}

function TreeNode({ node, level, selectedPath, onSelect }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2)

  const isSelected = selectedPath === node.path

  if (node.is_directory) {
    return (
      <div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all hover:bg-white/5 ${
            isSelected ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400'
          }`}
          style={{ paddingLeft: `${level * 16 + 12}px` }}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 shrink-0" />
          )}
          <FolderOpen className="w-4 h-4 shrink-0 text-yellow-500" />
          <span className="truncate">{node.name}</span>
        </button>
        {isExpanded && node.children && (
          <div>
            {node.children.map((child, idx) => (
              <TreeNode
                key={idx}
                node={child}
                level={level + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <button
      onClick={() => onSelect(node.path)}
      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all hover:bg-white/5 ${
        isSelected ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400'
      }`}
      style={{ paddingLeft: `${level * 16 + 12}px` }}
    >
      <FileText className="w-4 h-4 shrink-0 text-blue-400" />
      <span className="truncate">{node.name}</span>
    </button>
  )
}

export default function VaultPage() {
  const [tree, setTree] = useState<FileNode[]>([])
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [originalContent, setOriginalContent] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<{
    path: string
    name: string
    matches: { line: number; content: string }[]
  }[]>([])

  useEffect(() => {
    loadTree()
  }, [])

  const loadTree = async () => {
    try {
      const data = await api.getVaultTree()
      setTree(data.tree)
    } catch (error) {
      console.error('Failed to load vault tree:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadFile = async (path: string) => {
    try {
      const data = await api.readFile(path)
      setFileContent(data.content)
      setOriginalContent(data.content)
      setSelectedPath(path)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to load file:', error)
    }
  }

  const saveFile = async () => {
    if (!selectedPath) return

    setIsSaving(true)
    try {
      await api.writeFile(selectedPath, fileContent)
      setOriginalContent(fileContent)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to save file:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }

    try {
      const data = await api.searchVault(searchQuery)
      setSearchResults(data.results)
    } catch (error) {
      console.error('Search failed:', error)
    }
  }

  const hasChanges = fileContent !== originalContent

  return (
    <div className="flex h-full">
      {/* File tree sidebar */}
      <aside className="w-72 border-r border-white/10 bg-[#0f0f18]/80 flex flex-col">
        <div className="p-4 border-b border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Memory Vault</h3>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search memories..."
              className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-pulse text-gray-500">Loading...</div>
            </div>
          ) : searchResults.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 px-3 py-2">
                {searchResults.length} results found
              </p>
              {searchResults.map((result, idx) => (
                <button
                  key={idx}
                  onClick={() => loadFile(result.path)}
                  className="w-full text-left p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all"
                >
                  <div className="flex items-center gap-2 text-sm text-white">
                    <FileText className="w-4 h-4 text-blue-400" />
                    {result.name}
                  </div>
                  {result.matches[0] && (
                    <p className="text-xs text-gray-500 mt-1 truncate">
                      Line {result.matches[0].line}: {result.matches[0].content}
                    </p>
                  )}
                </button>
              ))}
              <button
                onClick={() => {
                  setSearchQuery('')
                  setSearchResults([])
                }}
                className="w-full text-center text-xs text-gray-500 py-2 hover:text-white"
              >
                Clear search
              </button>
            </div>
          ) : (
            tree.map((node, idx) => (
              <TreeNode
                key={idx}
                node={node}
                level={0}
                selectedPath={selectedPath}
                onSelect={loadFile}
              />
            ))
          )}
        </div>
      </aside>

      {/* Editor */}
      <div className="flex-1 flex flex-col">
        {/* Editor header */}
        <header className="h-16 px-6 flex items-center justify-between border-b border-white/10 bg-[#0f0f18]/80">
          {selectedPath ? (
            <>
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-blue-400" />
                <span className="text-white font-medium">{selectedPath}</span>
                {hasChanges && (
                  <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                    Unsaved
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={() => {
                        setFileContent(originalContent)
                        setIsEditing(false)
                      }}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-all"
                    >
                      <X className="w-4 h-4" />
                      Cancel
                    </button>
                    <button
                      onClick={saveFile}
                      disabled={isSaving || !hasChanges}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg text-white font-medium hover:bg-blue-500 disabled:opacity-50 transition-all"
                    >
                      <Save className="w-4 h-4" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="px-4 py-2 bg-white/5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
                  >
                    Edit
                  </button>
                )}
              </div>
            </>
          ) : (
            <span className="text-gray-500">Select a file to view</span>
          )}
        </header>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedPath ? (
            isEditing ? (
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                className="w-full h-full bg-transparent text-gray-200 font-mono text-sm leading-relaxed resize-none focus:outline-none"
              />
            ) : (
              <div className="prose prose-invert max-w-none">
                <ReactMarkdown>{fileContent}</ReactMarkdown>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <FolderOpen className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg">Memory Vault Explorer</p>
              <p className="text-sm mt-2">왼쪽 트리에서 파일을 선택하세요</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
