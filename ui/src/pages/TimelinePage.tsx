import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { TimelineEntry, TimelineStats } from '../api/client';
import './TimelinePage.css';

type FilterType = 'all' | 'daily' | 'weekly' | 'monthly';

export default function TimelinePage() {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [stats, setStats] = useState<TimelineStats | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [selectedEntry, setSelectedEntry] = useState<TimelineEntry | null>(null);

  useEffect(() => {
    loadTimeline();
    loadStats();
  }, [filter, days]);

  async function loadTimeline() {
    setLoading(true);
    try {
      const typeFilter = filter === 'all' ? undefined : filter;
      const response = await api.getTimeline(typeFilter, days);
      setEntries(response.entries);
    } catch (error) {
      console.error('Failed to load timeline:', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      const response = await api.getTimelineStats();
      setStats(response);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }

  function getTypeLabel(type: string): string {
    switch (type) {
      case 'daily_reflection':
        return '📅 Daily';
      case 'weekly_summary':
        return '📆 Weekly';
      case 'monthly_summary':
        return '🗓️ Monthly';
      default:
        return type;
    }
  }

  function getTypeColor(type: string): string {
    switch (type) {
      case 'daily_reflection':
        return 'var(--color-daily)';
      case 'weekly_summary':
        return 'var(--color-weekly)';
      case 'monthly_summary':
        return 'var(--color-monthly)';
      default:
        return 'var(--color-text-muted)';
    }
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function parseContent(content: string): Record<string, string> {
    const result: Record<string, string> = {};
    const lines = content.split('\n');
    
    for (const line of lines) {
      if (line.includes(':')) {
        const [key, ...valueParts] = line.split(':');
        const cleanKey = key.replace(/[\[\]]/g, '').trim();
        result[cleanKey] = valueParts.join(':').trim();
      }
    }
    
    return result;
  }

  return (
    <div className="timeline-page">
      <header className="timeline-header">
        <h1>📜 Timeline</h1>
        <p className="subtitle">Your memory journey through time</p>
      </header>

      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card daily">
            <span className="stat-emoji">📅</span>
            <div className="stat-info">
              <span className="stat-value">{stats.daily_count_30d}</span>
              <span className="stat-label">Daily (30d)</span>
            </div>
          </div>
          <div className="stat-card weekly">
            <span className="stat-emoji">📆</span>
            <div className="stat-info">
              <span className="stat-value">{stats.weekly_count_90d}</span>
              <span className="stat-label">Weekly (90d)</span>
            </div>
          </div>
          <div className="stat-card monthly">
            <span className="stat-emoji">🗓️</span>
            <div className="stat-info">
              <span className="stat-value">{stats.monthly_count_365d}</span>
              <span className="stat-label">Monthly (1y)</span>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filters">
        <div className="filter-group">
          <label>Type:</label>
          <select value={filter} onChange={(e) => setFilter(e.target.value as FilterType)}>
            <option value="all">All</option>
            <option value="daily">Daily Reflections</option>
            <option value="weekly">Weekly Summaries</option>
            <option value="monthly">Monthly Summaries</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Range:</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      </div>

      {/* Timeline */}
      <div className="timeline-container">
        {loading ? (
          <div className="loading">Loading timeline...</div>
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">🕐</span>
            <p>No reflections or summaries yet.</p>
            <p className="hint">Daily reflections will appear here as the system runs.</p>
          </div>
        ) : (
          <div className="timeline-list">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className={`timeline-item ${selectedEntry?.id === entry.id ? 'selected' : ''}`}
                onClick={() => setSelectedEntry(selectedEntry?.id === entry.id ? null : entry)}
              >
                <div className="timeline-dot" style={{ backgroundColor: getTypeColor(entry.type) }} />
                <div className="timeline-content">
                  <div className="timeline-meta">
                    <span className="type-badge" style={{ color: getTypeColor(entry.type) }}>
                      {getTypeLabel(entry.type)}
                    </span>
                    <span className="date-label">{entry.date_label}</span>
                    <span className="created-at">{formatDate(entry.created_at)}</span>
                  </div>
                  <div className="timeline-summary">
                    {parseContent(entry.content)['Summary'] || entry.content.slice(0, 150) + '...'}
                  </div>
                  
                  {selectedEntry?.id === entry.id && (
                    <div className="timeline-detail">
                      <pre>{entry.content}</pre>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
