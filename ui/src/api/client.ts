/**
 * API client for communicating with the Eternal Memory backend.
 */

const API_BASE = '/api';

export interface MemoryItem {
  id: string;
  content: string;
  category_path: string;
  type: string;
  importance: number;
  confidence?: number;
}

export interface RetrieveResponse {
  items: MemoryItem[];
  related_categories: string[];
  suggested_context: string;
  query_evolved: string | null;
  mode: string;
  confidence_score: number;
}

export interface FileNode {
  name: string;
  path: string;
  is_directory: boolean;
  children?: FileNode[];
}

export interface VaultTree {
  root: string;
  tree: FileNode[];
}

class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Chat endpoints
  async memorize(content: string, metadata?: Record<string, unknown>) {
    return this.request<{ success: boolean; item: MemoryItem; processing_steps: string[] }>(
      '/chat/memorize',
      {
        method: 'POST',
        body: JSON.stringify({ content, metadata }),
      }
    );
  }

  async retrieve(query: string, mode: 'fast' | 'deep' = 'fast') {
    return this.request<RetrieveResponse>('/chat/retrieve', {
      method: 'POST',
      body: JSON.stringify({ query, mode }),
    });
  }

  async predictContext(context: Record<string, unknown>) {
    return this.request<{ context: string; source: string }>('/chat/predict-context', {
      method: 'POST',
      body: JSON.stringify(context),
    });
  }

  // Natural conversation with auto-memory
  async conversation(
    message: string,
    mode: 'fast' | 'deep' = 'fast',
    conversationHistory?: { role: string; content: string }[]
  ) {
    return this.request<{
      response: string;
      memories_retrieved: { id: string; content: string; category_path: string; confidence: number }[];
      memories_stored: { id: string; content: string; category_path: string }[];
      processing_info: { mode: string; model: string; memories_found: number; facts_extracted: number };
    }>('/chat/conversation', {
      method: 'POST',
      body: JSON.stringify({
        message,
        mode,
        conversation_history: conversationHistory,
      }),
    });
  }

  // Vault endpoints
  async getVaultTree() {
    return this.request<VaultTree>('/vault/tree');
  }

  async readFile(path: string) {
    return this.request<{ path: string; content: string; name: string }>(
      `/vault/file/${encodeURIComponent(path)}`
    );
  }

  async writeFile(path: string, content: string) {
    return this.request<{ success: boolean; path: string; message: string }>(
      `/vault/file/${encodeURIComponent(path)}`,
      {
        method: 'PUT',
        body: JSON.stringify({ content }),
      }
    );
  }

  async searchVault(query: string) {
    return this.request<{
      query: string;
      results: {
        path: string;
        name: string;
        matches: { line: number; content: string }[];
      }[];
      total_files: number;
    }>(`/vault/search?q=${encodeURIComponent(query)}`);
  }

  // Settings endpoints
  async getSettings() {
    return this.request<{
      llm: { provider: string; model: string; api_key_set: boolean };
      system_prompt: string | null;
    }>('/settings/');
  }

  async setApiKey(provider: string, apiKey: string) {
    return this.request<{ success: boolean; message: string }>(
      `/settings/api-key?provider=${provider}&api_key=${apiKey}`,
      { method: 'POST' }
    );
  }

  async testConnection() {
    return this.request<{ success: boolean; message?: string; error?: string; models_available?: number }>(
      '/settings/test-connection',
      { method: 'POST' }
    );
  }

  async updateSystemPrompt(prompt: string) {
    return this.request<{ success: boolean; message: string }>(
      `/settings/system-prompt?prompt=${encodeURIComponent(prompt)}`,
      { method: 'PUT' }
    );
  }

  // Stats
  async getStats() {
    return this.request<{ resources: number; categories: number; memory_items: number }>('/stats');
  }

  // Get available models from provider
  async getModels(provider: string = 'openai') {
    return this.request<{
      success: boolean;
      provider: string;
      chat_models: { id: string; name: string; owned_by: string }[];
      embedding_models: { id: string; name: string; owned_by: string }[];
      total: number;
      error?: string;
    }>(`/settings/models?provider=${provider}`);
  }

  // Set selected model
  async setModel(model: string) {
    return this.request<{ success: boolean; message: string }>(
      `/settings/model?model=${encodeURIComponent(model)}`,
      { method: 'PUT' }
    );
  }
}

export const api = new ApiClient();
