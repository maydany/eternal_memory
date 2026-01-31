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
      llm: { provider: string; model: string; api_key_set: boolean; api_key_masked?: string | null };
      system_prompt: string | null;
    }>('/settings/');
  }

  async setApiKey(provider: string, apiKey: string) {
    return this.request<{ success: boolean; message: string }>(
      `/settings/api-key?provider=${provider}&api_key=${apiKey}`,
      { method: 'POST' }
    );
  }


  async deleteApiKey(provider: string) {
    return this.request<{ success: boolean; message: string }>(
      `/settings/api-key?provider=${provider}`,
      { method: 'DELETE' }
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
    return this.request<{
      resources: number;
      categories: number;
      memory_items: number;
      token_usage?: { model: string; prompt: number; completion: number; total: number }[];
      db_size?: string;
      connected?: boolean;
    }>('/stats');
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

  // Set selected model(s)
  async setModel(options: {
    model?: string;
    chat_model?: string;
    memory_model?: string;
    supersede_model?: string;
    use_llm_importance?: boolean;
    use_memory_supersede?: boolean;
    use_semantic_triples?: boolean;
    triple_extraction_immediate?: boolean;
    triple_extraction_interval_minutes?: number;
  }) {
    const params = new URLSearchParams();
    if (options.model) params.append('model', options.model);
    if (options.chat_model) params.append('chat_model', options.chat_model);
    if (options.memory_model) params.append('memory_model', options.memory_model);
    if (options.supersede_model) params.append('supersede_model', options.supersede_model);
    if (options.use_llm_importance !== undefined) {
      params.append('use_llm_importance', options.use_llm_importance.toString());
    }
    if (options.use_memory_supersede !== undefined) {
      params.append('use_memory_supersede', options.use_memory_supersede.toString());
    }
    if (options.use_semantic_triples !== undefined) {
      params.append('use_semantic_triples', options.use_semantic_triples.toString());
    }
    if (options.triple_extraction_immediate !== undefined) {
      params.append('triple_extraction_immediate', options.triple_extraction_immediate.toString());
    }
    if (options.triple_extraction_interval_minutes !== undefined) {
      params.append('triple_extraction_interval_minutes', options.triple_extraction_interval_minutes.toString());
    }
    return this.request<{
      success: boolean;
      message: string;
      settings: Record<string, unknown>;
    }>(`/settings/model?${params.toString()}`, { method: 'PUT' });
  }

  // Get model configuration
  async getModelConfig() {
    return this.request<{
      model: string;
      chat_model: string | null;
      memory_model: string;
      supersede_model: string;
      use_llm_importance: boolean;
      use_memory_supersede: boolean;
      use_semantic_triples: boolean;
      triple_extraction_immediate: boolean;
      triple_extraction_interval_minutes: number;
      effective_chat_model: string;
      effective_memory_model: string;
      effective_supersede_model: string;
    }>('/settings/model-config');
  }


  // Buffer settings
  async getBufferSettings() {
    return this.request<{
      flush_threshold_tokens: number;
      auto_flush_enabled: boolean;
    }>('/settings/buffer');
  }

  async updateBufferSettings(settings: { flush_threshold_tokens?: number; auto_flush_enabled?: boolean }) {
    const params = new URLSearchParams();
    if (settings.flush_threshold_tokens !== undefined) {
      params.append('flush_threshold_tokens', settings.flush_threshold_tokens.toString());
    }
    if (settings.auto_flush_enabled !== undefined) {
      params.append('auto_flush_enabled', settings.auto_flush_enabled.toString());
    }
    return this.request<{
      success: boolean;
      message: string;
      settings: { flush_threshold_tokens: number; auto_flush_enabled: boolean };
    }>(`/settings/buffer?${params.toString()}`, { method: 'PUT' });
  }

  // Scoring settings (Generative Agents-style)
  async getScoringSettings() {
    return this.request<{
      alpha_relevance: number;
      alpha_recency: number;
      alpha_importance: number;
      recency_decay_factor: number;
      min_relevance_threshold: number;
    }>('/settings/scoring');
  }

  async updateScoringSettings(settings: {
    alpha_relevance?: number;
    alpha_recency?: number;
    alpha_importance?: number;
    recency_decay_factor?: number;
    min_relevance_threshold?: number;
  }) {
    const params = new URLSearchParams();
    if (settings.alpha_relevance !== undefined) {
      params.append('alpha_relevance', settings.alpha_relevance.toString());
    }
    if (settings.alpha_recency !== undefined) {
      params.append('alpha_recency', settings.alpha_recency.toString());
    }
    if (settings.alpha_importance !== undefined) {
      params.append('alpha_importance', settings.alpha_importance.toString());
    }
    if (settings.recency_decay_factor !== undefined) {
      params.append('recency_decay_factor', settings.recency_decay_factor.toString());
    }
    if (settings.min_relevance_threshold !== undefined) {
      params.append('min_relevance_threshold', settings.min_relevance_threshold.toString());
    }
    return this.request<{
      success: boolean;
      message: string;
      settings: {
        alpha_relevance: number;
        alpha_recency: number;
        alpha_importance: number;
        recency_decay_factor: number;
        min_relevance_threshold: number;
      };
    }>(`/settings/scoring?${params.toString()}`, { method: 'PUT' });
  }

  // Schedule endpoints
  async getScheduledJobs() {
    return this.request<ScheduledTask[]>('/schedule/jobs');
  }

  async addScheduledJob(name: string, jobType: string, intervalSeconds: number) {
    return this.request<ScheduledTask>('/schedule/jobs', {
      method: 'POST',
      body: JSON.stringify({
        name,
        job_type: jobType,
        interval_seconds: intervalSeconds,
      }),
    });
  }

  async deleteScheduledJob(name: string) {
    return this.request<{ success: boolean; message: string }>(
      `/schedule/jobs/${encodeURIComponent(name)}`,
      { method: 'DELETE' }
    );
  }

  async triggerScheduledJob(name: string) {
    return this.request<{ success: boolean; message: string }>(
      `/schedule/jobs/${encodeURIComponent(name)}/trigger`,
      { method: 'POST' }
    );
  }

  async getJobTypes() {
    return this.request<{
      job_types: { type: string; description: string }[];
    }>('/schedule/job-types');
  }

  // Timeline endpoints
  async getTimeline(type?: string, days: number = 30) {
    const params = new URLSearchParams();
    if (type) params.append('type', type);
    params.append('days', days.toString());
    return this.request<TimelineResponse>(`/timeline/?${params.toString()}`);
  }

  async getTimelineStats() {
    return this.request<TimelineStats>('/timeline/stats');
  }

  // Metrics endpoints
  async getMetricsSummary() {
    return this.request<{
      total_pipelines: number;
      total_facts: number;
      avg_duration: number;
      p95_duration: number;
      avg_facts_per_pipeline: number;
      recent_count: number;
    }>('/metrics/summary');
  }

  async getRecentMetrics(limit?: number) {
    const params = limit ? `?limit=${limit}` : '';
    // API returns nested structure, transform to flat structure for frontend
    const rawMetrics = await this.request<{
      timestamp: string;
      total_duration: number;
      facts: { extracted: number; stored: number };
      embeddings: { count: number; batched: boolean };
      text_length: number;
    }[]>(`/metrics/recent${params}`);
    
    return rawMetrics.map(m => ({
      timestamp: m.timestamp,
      duration: m.total_duration,
      facts_extracted: m.facts?.extracted ?? 0,
      embeddings_generated: m.embeddings?.count ?? 0,
      text_length: m.text_length ?? 0,
    }));
  }

  // Buffer endpoints
  async getBufferStatus() {
    return this.request<{
      message_count: number;
      estimated_tokens: number;
      threshold_tokens: number;
      fill_percentage: number;
      auto_flush_enabled: boolean;
    }>('/buffer/status');
  }

  async getBufferMessages(limit?: number) {
    const params = limit ? `?limit=${limit}` : '';
    return this.request<{
      messages: { role: string; content: string; timestamp: string }[];
      total: number;
    }>(`/buffer/messages${params}`);
  }

  async flushBuffer() {
    return this.request<{
      success: boolean;
      message: string;
      items_created: number;
      items?: { id: string; content: string; category_path: string }[];
    }>('/buffer/flush', { method: 'POST' });
  }
}

export interface ScheduledTask {
  id?: string;
  name: string;
  job_type: string;
  interval_seconds: number;
  enabled: boolean;
  is_system: boolean;
  last_run?: string | null;
  next_run?: string | null;
  next_run_in?: number | null;
  running?: boolean;
  created_at?: string | null;
}

export interface TimelineEntry {
  id: string;
  type: string;  // daily_reflection, weekly_summary, monthly_summary
  content: string;
  date_label: string;
  created_at: string;
  memory_count?: number;
}

export interface TimelineResponse {
  entries: TimelineEntry[];
  total: number;
}

export interface TimelineStats {
  daily_count_30d: number;
  weekly_count_90d: number;
  monthly_count_365d: number;
  latest_daily: string | null;
  latest_weekly: string | null;
  latest_monthly: string | null;
}

export const api = new ApiClient();
