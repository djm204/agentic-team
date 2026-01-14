"""
Web dashboard for viewing agent metrics and usage.
"""
from flask import Flask, render_template_string, jsonify
from metrics_engine import MetricsEngine
import os
from datetime import datetime


# HTML template for dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Agentic Team Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .metric:last-child {
            border-bottom: none;
        }
        .metric-label {
            color: #666;
        }
        .metric-value {
            font-weight: bold;
            color: #333;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .status-good { background: #10b981; color: white; }
        .status-warning { background: #f59e0b; color: white; }
        .status-bad { background: #ef4444; color: white; }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 10px;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
        .agent-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .agent-item {
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Agentic Team Dashboard</h1>
            <p>Real-time metrics and performance tracking</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>

        <div class="grid">
            <!-- Token Usage Summary -->
            <div class="card">
                <h2>💰 Token Usage</h2>
                <div class="metric">
                    <span class="metric-label">Total Tokens:</span>
                    <span class="metric-value" id="total-tokens">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Input Tokens:</span>
                    <span class="metric-value" id="input-tokens">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Output Tokens:</span>
                    <span class="metric-value" id="output-tokens">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Calls:</span>
                    <span class="metric-value" id="total-calls">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Est. Cost:</span>
                    <span class="metric-value" id="total-cost">$0.00</span>
                </div>
            </div>

            <!-- Project Metrics -->
            <div class="card">
                <h2>📊 Project Metrics</h2>
                <div class="metric">
                    <span class="metric-label">Projects Started:</span>
                    <span class="metric-value" id="projects-started">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Projects Completed:</span>
                    <span class="metric-value" id="projects-completed">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Projects Failed:</span>
                    <span class="metric-value" id="projects-failed">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Iterations:</span>
                    <span class="metric-value" id="total-iterations">0</span>
                </div>
            </div>

            <!-- Code Quality -->
            <div class="card">
                <h2>✨ Code Quality</h2>
                <div class="metric">
                    <span class="metric-label">DRY Violations:</span>
                    <span class="metric-value" id="dry-violations">0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Complexity:</span>
                    <span class="metric-value" id="avg-complexity">0.0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Readability:</span>
                    <span class="metric-value" id="avg-readability">0.0</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Maintainability:</span>
                    <span class="metric-value" id="avg-maintainability">0.0</span>
                </div>
            </div>
        </div>

        <!-- Agent Performance -->
        <div class="card" style="margin-top: 20px;">
            <h2>👥 Agent Performance</h2>
            <div class="agent-list" id="agent-list">
                <!-- Agents will be populated here -->
            </div>
        </div>

        <!-- Token Usage Chart -->
        <div class="card" style="margin-top: 20px;">
            <h2>📈 Token Usage by Agent</h2>
            <div class="chart-container">
                <canvas id="token-chart"></canvas>
            </div>
        </div>

        <!-- Stage Metrics -->
        <div class="card" style="margin-top: 20px;">
            <h2>🔄 Stage Performance</h2>
            <div class="chart-container">
                <canvas id="stage-chart"></canvas>
            </div>
        </div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                
                // Update token usage
                const tokenTotal = data.token_usage?.total || {};
                document.getElementById('total-tokens').textContent = (tokenTotal.total_tokens || 0).toLocaleString();
                document.getElementById('input-tokens').textContent = (tokenTotal.input_tokens || 0).toLocaleString();
                document.getElementById('output-tokens').textContent = (tokenTotal.output_tokens || 0).toLocaleString();
                document.getElementById('total-calls').textContent = (tokenTotal.total_calls || 0).toLocaleString();
                document.getElementById('total-cost').textContent = '$' + (tokenTotal.total_cost_estimate || 0).toFixed(2);
                
                // Update project metrics
                const projects = data.project_metrics || {};
                document.getElementById('projects-started').textContent = projects.projects_started || 0;
                document.getElementById('projects-completed').textContent = projects.projects_completed || 0;
                document.getElementById('projects-failed').textContent = projects.projects_failed || 0;
                document.getElementById('total-iterations').textContent = projects.total_iterations || 0;
                
                // Update code quality
                const quality = data.code_quality || {};
                let totalDry = 0, totalComplexity = 0, totalReadability = 0, totalMaintainability = 0, count = 0;
                Object.values(quality).forEach(q => {
                    totalDry += q.dry_violations || 0;
                    totalComplexity += q.complexity_score || 0;
                    totalReadability += q.readability_score || 0;
                    totalMaintainability += q.maintainability_score || 0;
                    if (q.code_reviews > 0) count++;
                });
                document.getElementById('dry-violations').textContent = totalDry;
                document.getElementById('avg-complexity').textContent = (totalComplexity / Math.max(count, 1)).toFixed(2);
                document.getElementById('avg-readability').textContent = (totalReadability / Math.max(count, 1)).toFixed(2);
                document.getElementById('avg-maintainability').textContent = (totalMaintainability / Math.max(count, 1)).toFixed(2);
                
                // Update agent list
                const agentList = document.getElementById('agent-list');
                agentList.innerHTML = '';
                const agents = data.agent_metrics || {};
                Object.entries(agents).forEach(([name, metrics]) => {
                    const tokenStats = metrics.token_stats || {};
                    const efficiency = metrics.efficiency_score || 0;
                    const statusClass = efficiency >= 70 ? 'status-good' : efficiency >= 40 ? 'status-warning' : 'status-bad';
                    agentList.innerHTML += `
                        <div class="agent-item">
                            <h3>${name}</h3>
                            <div class="metric">
                                <span class="metric-label">Efficiency:</span>
                                <span class="status-badge ${statusClass}">${efficiency.toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Tokens Used:</span>
                                <span class="metric-value">${(tokenStats.total_tokens || 0).toLocaleString()}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Tasks Completed:</span>
                                <span class="metric-value">${metrics.tasks_completed || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Actions:</span>
                                <span class="metric-value">${(metrics.actions || []).length}</span>
                            </div>
                        </div>
                    `;
                });
                
                // Update charts
                updateCharts(data);
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }
        
        function updateCharts(data) {
            // Token usage chart
            const tokenCtx = document.getElementById('token-chart').getContext('2d');
            const tokenData = data.token_usage?.by_agent || {};
            new Chart(tokenCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(tokenData),
                    datasets: [{
                        label: 'Total Tokens',
                        data: Object.values(tokenData).map(t => t.total_tokens || 0),
                        backgroundColor: 'rgba(102, 126, 234, 0.6)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
            
            // Stage duration chart
            const stageCtx = document.getElementById('stage-chart').getContext('2d');
            const stageData = data.stage_metrics || {};
            new Chart(stageCtx, {
                type: 'line',
                data: {
                    labels: Object.keys(stageData),
                    datasets: [{
                        label: 'Duration (seconds)',
                        data: Object.values(stageData).map(s => s.duration || 0),
                        backgroundColor: 'rgba(118, 75, 162, 0.2)',
                        borderColor: 'rgba(118, 75, 162, 1)',
                        borderWidth: 2,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // Load dashboard on page load
        loadDashboard();
        // Auto-refresh every 5 seconds
        setInterval(loadDashboard, 5000);
    </script>
</body>
</html>
"""


app = Flask(__name__)
# Metrics engine will be set by team.py when dashboard is started
# If not set, create a default one (for standalone dashboard runs)
metrics_engine = None

def get_metrics_engine():
    """Get the metrics engine instance."""
    global metrics_engine
    if metrics_engine is None:
        metrics_engine = MetricsEngine()
        metrics_engine.start()  # Start database connection
    return metrics_engine


@app.route('/')
def dashboard():
    """Render the dashboard."""
    return render_template_string(DASHBOARD_TEMPLATE)


@app.route('/api/metrics')
def get_metrics():
    """Get metrics data as JSON."""
    engine = get_metrics_engine()
    return jsonify(engine.get_dashboard_data())


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """
    Run the dashboard server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    print(f"🚀 Starting dashboard server at http://{host}:{port}")
    print(f"📊 View metrics at http://localhost:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_dashboard()
