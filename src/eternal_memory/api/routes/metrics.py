"""
Metrics and monitoring API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from eternal_memory.monitoring import get_monitor

router = APIRouter()


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """Get aggregated metrics summary."""
    monitor = get_monitor()
    return monitor.get_summary()


@router.get("/recent")
async def get_recent_metrics(limit: Optional[int] = 50) -> List[Dict[str, Any]]:
    """Get recent metrics from memory."""
    monitor = get_monitor()
    return monitor.get_recent_metrics(limit=limit)


@router.get("/logs")
async def list_log_files() -> Dict[str, List[str]]:
    """List available log files."""
    monitor = get_monitor()
    return {"files": monitor.get_log_files()}


@router.get("/logs/{filename}")
async def get_log_file(filename: str, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
    """Get metrics from a specific log file."""
    monitor = get_monitor()
    
    # Security: validate filename
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    try:
        return monitor.read_log_file(filename, limit=limit)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve performance monitoring dashboard."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Performance Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #2d3748;
            min-height: 100vh;
            padding: 2rem;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            color: white;
            margin-bottom: 2rem;
            font-size: 2.5rem;
            text-align: center;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        
        .stat-label {
            color: #718096;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #2d3748;
        }
        
        .stat-unit {
            font-size: 1rem;
            color: #a0aec0;
            margin-left: 0.25rem;
        }
        
        .metrics-table-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        h2 {
            margin-bottom: 1rem;
            color: #2d3748;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        thead {
            background: #f7fafc;
        }
        
        th {
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            font-size: 0.875rem;
        }
        
        td {
            padding: 0.75rem;
            border-top: 1px solid #e2e8f0;
        }
        
        tbody tr:hover {
            background: #f7fafc;
        }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .badge-success {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .badge-warning {
            background: #feebc8;
            color: #744210;
        }
        
        .badge-info {
            background: #bee3f8;
            color: #2c5282;
        }
        
        .refresh-btn {
            background: white;
            border: 2px solid white;
            color: #667eea;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            position: fixed;
            top: 2rem;
            right: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .refresh-btn:hover {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: white;
            font-size: 1.25rem;
        }
        
        .error {
            background: #fed7d7;
            color: #742a2a;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        /* Tooltip styles */
        .stat-label {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        
        .stat-label .tooltip {
            visibility: hidden;
            width: 280px;
            background-color: #2d3748;
            color: white;
            text-align: left;
            border-radius: 8px;
            padding: 12px;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 50%;
            margin-left: -140px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.875rem;
            line-height: 1.5;
            text-transform: none;
            letter-spacing: normal;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .stat-label .tooltip::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #2d3748 transparent transparent transparent;
        }
        
        .stat-label:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        
        .tooltip-title {
            font-weight: bold;
            margin-bottom: 4px;
            color: #63b3ed;
        }
    </style>
</head>
<body>
    <button class="refresh-btn" onclick="loadMetrics()">🔄 Refresh</button>
    
    <div class="container">
        <h1>⚡ Performance Monitor</h1>
        
        <div id="error-container"></div>
        
        <div class="stats-grid" id="stats-grid">
            <div class="loading">Loading metrics...</div>
        </div>
        
        <div class="metrics-table-card">
            <h2>Recent Pipeline Executions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Duration</th>
                        <th>Facts</th>
                        <th>Embeddings</th>
                        <th>Text Length</th>
                    </tr>
                </thead>
                <tbody id="metrics-table">
                    <tr><td colspan="5" class="loading">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadMetrics() {
            try {
                // Load summary
                const summaryRes = await fetch('/api/metrics/summary');
                const summary = await summaryRes.json();
                
                // Load recent metrics
                const recentRes = await fetch('/api/metrics/recent?limit=20');
                const recent = await recentRes.json();
                
                // Update stats grid
                updateStatsGrid(summary);
                
                // Update table
                updateTable(recent);
                
                // Clear errors
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('error-container').innerHTML = 
                    `<div class="error">Failed to load metrics: ${error.message}</div>`;
            }
        }
        
        function updateStatsGrid(summary) {
            const grid = document.getElementById('stats-grid');
            grid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-label">
                        Total Pipelines
                        <span class="tooltip">
                            <div class="tooltip-title">파이프라인이란?</div>
                            한 번의 완전한 메모리 저장 프로세스입니다. memorize()를 호출할 때마다 1개씩 증가합니다.
                        </span>
                    </div>
                    <div class="stat-value">${summary.total_pipelines.toLocaleString()}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-label">
                        Total Facts
                        <span class="tooltip">
                            <div class="tooltip-title">팩트란?</div>
                            파이프라인에서 추출된 개별 정보 조각입니다. 예: "사용자가 Python을 선호함"
                        </span>
                    </div>
                    <div class="stat-value">${summary.total_facts.toLocaleString()}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-label">
                        Avg Duration
                        <span class="tooltip">
                            <div class="tooltip-title">평균 실행 시간</div>
                            파이프라인 1회 실행에 걸리는 평균 시간입니다. 낮을수록 좋습니다.
                        </span>
                    </div>
                    <div class="stat-value">
                        ${summary.avg_duration}
                        <span class="stat-unit">s</span>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-label">
                        Avg Facts/Pipeline
                        <span class="tooltip">
                            <div class="tooltip-title">파이프라인당 평균 팩트</div>
                            파이프라인 1회당 추출되는 평균 fact 개수입니다. 일반적으로 2-5개가 적정합니다.
                        </span>
                    </div>
                    <div class="stat-value">${summary.avg_facts_per_pipeline}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-label">
                        P95 Duration
                        <span class="tooltip">
                            <div class="tooltip-title">P95 실행 시간</div>
                            95%의 요청이 이 시간 안에 완료됩니다. 느린 케이스를 추적하는 지표로 2초 이하면 좋습니다.
                        </span>
                    </div>
                    <div class="stat-value">
                        ${summary.p95_duration}
                        <span class="stat-unit">s</span>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-label">
                        Recent Runs
                        <span class="tooltip">
                            <div class="tooltip-title">최근 실행 수</div>
                            메모리에 저장된 최근 파이프라인 실행 횟수입니다 (최대 100개).
                        </span>
                    </div>
                    <div class="stat-value">${summary.recent_count}</div>
                </div>
            `;
        }
        
        function updateTable(metrics) {
            const tbody = document.getElementById('metrics-table');
            
            if (metrics.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #a0aec0;">No metrics yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = metrics.map(m => {
                const time = new Date(m.timestamp).toLocaleTimeString();
                const durationClass = m.total_duration < 1 ? 'success' : m.total_duration < 3 ? 'info' : 'warning';
                
                return `
                    <tr>
                        <td>${time}</td>
                        <td><span class="badge badge-${durationClass}">${m.total_duration}s</span></td>
                        <td>${m.facts.stored}</td>
                        <td>${m.embeddings.batched ? '✅ Batched' : '❌ Individual'} (${m.embeddings.count})</td>
                        <td>${m.text_length} chars</td>
                    </tr>
                `;
            }).join('');
        }
        
        // Auto-refresh every 10 seconds
        setInterval(loadMetrics, 10000);
        
        // Initial load
        loadMetrics();
    </script>
</body>
</html>
    """
