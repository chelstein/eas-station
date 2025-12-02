#!/usr/bin/env python3
"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

You should have received a copy of both licenses with this software.
For more information, see LICENSE and LICENSE-COMMERCIAL files.

IMPORTANT: This software cannot be rebranded or have attribution removed.
See NOTICE file for complete terms.

Repository: https://github.com/KR8MER/eas-station
"""

"""
Generate repository statistics and save to HTML file with Chart.js visualizations.

This script analyzes the repository structure and generates statistics including:
- Total files count by type
- Routes count
- Lines of code
- Directory structure metrics
"""

import os
import re
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Tuple


def count_lines_of_code(file_path: Path) -> Tuple[int, int, int]:
    """
    Count lines of code in a file.
    
    Returns:
        Tuple of (total_lines, code_lines, comment_lines)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        code_lines = 0
        comment_lines = 0
        in_multiline_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Python/Shell comments
            if file_path.suffix in ['.py', '.sh']:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_multiline_comment = not in_multiline_comment
                    comment_lines += 1
                elif in_multiline_comment:
                    comment_lines += 1
                elif stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
            # JavaScript/CSS comments
            elif file_path.suffix in ['.js', '.css']:
                if '/*' in stripped:
                    in_multiline_comment = True
                    comment_lines += 1
                elif '*/' in stripped:
                    in_multiline_comment = False
                    comment_lines += 1
                elif in_multiline_comment:
                    comment_lines += 1
                elif stripped.startswith('//'):
                    comment_lines += 1
                else:
                    code_lines += 1
            # HTML/XML comments
            elif file_path.suffix in ['.html', '.xml', '.svg']:
                if '<!--' in stripped or '-->' in stripped:
                    comment_lines += 1
                else:
                    code_lines += 1
            # YAML comments
            elif file_path.suffix in ['.yml', '.yaml']:
                if stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
            # Dockerfile comments
            elif file_path.name.startswith('Dockerfile'):
                if stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
            else:
                code_lines += 1
        
        return total_lines, code_lines, comment_lines
    except Exception:
        return 0, 0, 0


def count_routes(repo_root: Path) -> Dict[str, int]:
    """
    Count Flask routes in the repository.
    
    Returns:
        Dict with route counts by file
    """
    routes = defaultdict(int)
    webapp_dir = repo_root / 'webapp'
    
    if not webapp_dir.exists():
        return routes
    
    route_pattern = re.compile(r'@(?:app|bp)\.route\(["\']([^"\']+)["\']')
    
    for py_file in webapp_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                matches = route_pattern.findall(content)
                if matches:
                    rel_path = py_file.relative_to(repo_root)
                    routes[str(rel_path)] = len(matches)
        except Exception:
            continue
    
    # Also check app.py in root
    app_py = repo_root / 'app.py'
    if app_py.exists():
        try:
            with open(app_py, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                matches = route_pattern.findall(content)
                if matches:
                    routes['app.py'] = len(matches)
        except Exception:
            pass
    
    return routes


def analyze_repository(repo_root: Path) -> Dict:
    """
    Analyze repository structure and gather statistics.
    
    Returns:
        Dict containing all statistics
    """
    stats = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'files_by_type': defaultdict(int),
        'lines_by_type': defaultdict(lambda: {'total': 0, 'code': 0, 'comments': 0}),
        'total_files': 0,
        'total_lines': 0,
        'total_code_lines': 0,
        'total_comment_lines': 0,
        'routes': {},
        'directories': set(),
    }
    
    # Extensions to track
    extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.html': 'HTML',
        '.css': 'CSS',
        '.yml': 'YAML',
        '.yaml': 'YAML',
        '.md': 'Markdown',
        '.sh': 'Shell',
        '.json': 'JSON',
        '.sql': 'SQL',
        '.txt': 'Text',
        '.xml': 'XML',
        '.svg': 'SVG',
    }
    
    # Directories to exclude
    exclude_dirs = {
        '.git', '__pycache__', 'node_modules', '.pytest_cache',
        'venv', 'env', '.venv', 'dist', 'build', '.egg-info'
    }
    
    # Count routes
    stats['routes'] = count_routes(repo_root)
    
    # Walk through repository
    for root, dirs, files in os.walk(repo_root):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        root_path = Path(root)
        rel_dir = root_path.relative_to(repo_root)
        stats['directories'].add(str(rel_dir))
        
        for file in files:
            file_path = root_path / file
            
            # Skip files in excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            
            stats['total_files'] += 1
            
            # Get extension
            ext = file_path.suffix.lower()
            
            # Special handling for Dockerfile
            if file.startswith('Dockerfile'):
                ext = 'Dockerfile'
            
            # Count by extension
            file_type = extensions.get(ext, 'Other')
            stats['files_by_type'][file_type] += 1
            
            # Count lines for tracked extensions
            if ext in extensions or file.startswith('Dockerfile'):
                total, code, comments = count_lines_of_code(file_path)
                stats['lines_by_type'][file_type]['total'] += total
                stats['lines_by_type'][file_type]['code'] += code
                stats['lines_by_type'][file_type]['comments'] += comments
                stats['total_lines'] += total
                stats['total_code_lines'] += code
                stats['total_comment_lines'] += comments
    
    return stats


def generate_html(stats: Dict) -> str:
    """
    Generate HTML content with Chart.js visualizations from statistics.
    
    Returns:
        HTML formatted string with embedded Chart.js charts
    """
    import json
    
    type_emoji = {
        'Python': '🐍',
        'HTML': '🌐',
        'JavaScript': '⚡',
        'CSS': '🎨',
        'Markdown': '📝',
        'Shell': '🐚',
        'YAML': '⚙️',
        'SQL': '🗄️',
        'SVG': '🖼️',
        'JSON': '📋',
        'XML': '📄',
        'Text': '📃',
        'Other': '📦',
    }
    
    # Prepare data for charts
    sorted_types = sorted(stats['files_by_type'].items(), key=lambda x: x[1], reverse=True)
    sorted_lines = sorted(
        stats['lines_by_type'].items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )
    
    # Code composition data
    code_lines = stats["total_code_lines"]
    comment_lines = stats["total_comment_lines"]
    blank_lines = stats["total_lines"] - code_lines - comment_lines
    
    # Files by type data (top 8 + other)
    files_labels = []
    files_data = []
    files_colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', 
        '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
    ]
    for i, (file_type, count) in enumerate(sorted_types[:8]):
        files_labels.append(f"{type_emoji.get(file_type, '📦')} {file_type}")
        files_data.append(count)
    if len(sorted_types) > 8:
        other_count = sum(count for _, count in sorted_types[8:])
        files_labels.append("📦 Other Types")
        files_data.append(other_count)
    
    # Lines of code by language (top 8)
    lines_labels = []
    lines_data = []
    lines_colors = [
        '#3178C6', '#E34C26', '#F1E05A', '#563D7C', '#F7DF1E',
        '#89E051', '#438CCA', '#B07219', '#555555', '#4F5D95'
    ]
    for i, (lang, counts) in enumerate(sorted_lines[:8]):
        if counts['code'] > 0:
            lines_labels.append(f"{type_emoji.get(lang, '📦')} {lang}")
            lines_data.append(counts['code'])
    
    # Routes data (top 15)
    sorted_routes = sorted(stats['routes'].items(), key=lambda x: x[1], reverse=True)
    routes_labels = []
    routes_data = []
    for file, count in sorted_routes[:15]:
        short_file = file.replace('webapp/', '').replace('.py', '')
        routes_labels.append(short_file)
        routes_data.append(count)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 EAS Station Repository Statistics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --primary-color: #0d6efd;
            --secondary-color: #6c757d;
            --success-color: #198754;
            --info-color: #0dcaf0;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --gradient-start: #667eea;
            --gradient-end: #764ba2;
        }}
        
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 2rem 0;
        }}
        
        .stats-container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 1rem;
        }}
        
        .hero-section {{
            background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.98) 100%);
            border-radius: 20px;
            padding: 3rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            backdrop-filter: blur(10px);
        }}
        
        .hero-section h1 {{
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }}
        
        .hero-section .timestamp {{
            color: var(--secondary-color);
            font-size: 1.1rem;
            font-weight: 500;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: none;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }}
        
        .stat-card-header {{
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }}
        
        .stat-card-header h2 {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #333;
            margin: 0;
        }}
        
        .quick-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .quick-stat-item {{
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            color: white;
            border-radius: 15px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .quick-stat-item:hover {{
            transform: scale(1.05);
        }}
        
        .quick-stat-item .icon {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            opacity: 0.9;
        }}
        
        .quick-stat-item .value {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}
        
        .quick-stat-item .label {{
            font-size: 0.9rem;
            opacity: 0.9;
            font-weight: 500;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 2rem 0;
        }}
        
        .chart-container-large {{
            height: 500px;
        }}
        
        .table-responsive {{
            border-radius: 10px;
            overflow: hidden;
        }}
        
        .stats-table {{
            margin: 0;
        }}
        
        .stats-table thead {{
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            color: white;
        }}
        
        .stats-table thead th {{
            border: none;
            padding: 1rem;
            font-weight: 600;
        }}
        
        .stats-table tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .stats-table td {{
            padding: 0.75rem 1rem;
            vertical-align: middle;
        }}
        
        .progress-bar-custom {{
            background: linear-gradient(90deg, var(--gradient-start), var(--gradient-end));
            height: 8px;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .architecture-card {{
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border-left: 4px solid var(--gradient-start);
            padding: 2rem;
            border-radius: 10px;
            margin: 2rem 0;
        }}
        
        .architecture-card h3 {{
            color: var(--gradient-start);
            margin-bottom: 1rem;
        }}
        
        .architecture-card ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .architecture-card ul li {{
            padding: 0.5rem 0;
            padding-left: 2rem;
            position: relative;
        }}
        
        .architecture-card ul li:before {{
            content: "⚡";
            position: absolute;
            left: 0;
            font-size: 1.2rem;
        }}
        
        .footer-note {{
            text-align: center;
            color: white;
            margin-top: 2rem;
            padding: 1rem;
            font-size: 0.9rem;
            opacity: 0.9;
        }}
        
        @media (max-width: 768px) {{
            .hero-section h1 {{
                font-size: 2rem;
            }}
            
            .chart-container {{
                height: 300px;
            }}
            
            .quick-stats {{
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }}
        }}
    </style>
</head>
<body>
    <div class="stats-container">
        <!-- Hero Section -->
        <div class="hero-section">
            <h1>📊 EAS Station Repository Statistics</h1>
            <p class="timestamp">
                <i class="far fa-clock"></i> Last Updated: {stats["timestamp"]}
            </p>
        </div>
        
        <!-- Quick Stats -->
        <div class="quick-stats">
            <div class="quick-stat-item">
                <div class="icon">📁</div>
                <div class="value">{stats["total_files"]:,}</div>
                <div class="label">Total Files</div>
            </div>
            <div class="quick-stat-item">
                <div class="icon">📂</div>
                <div class="value">{len(stats["directories"]):,}</div>
                <div class="label">Directories</div>
            </div>
            <div class="quick-stat-item">
                <div class="icon">📝</div>
                <div class="value">{stats["total_lines"]:,}</div>
                <div class="label">Total Lines</div>
            </div>
            <div class="quick-stat-item">
                <div class="icon">💻</div>
                <div class="value">{stats["total_code_lines"]:,}</div>
                <div class="label">Code Lines</div>
            </div>
            <div class="quick-stat-item">
                <div class="icon">💬</div>
                <div class="value">{stats["total_comment_lines"]:,}</div>
                <div class="label">Comments</div>
            </div>
            <div class="quick-stat-item">
                <div class="icon">🛤️</div>
                <div class="value">{sum(stats["routes"].values())}</div>
                <div class="label">API Routes</div>
            </div>
        </div>
        
        <!-- Code Composition Chart -->
        <div class="stat-card">
            <div class="stat-card-header">
                <h2><i class="fas fa-chart-pie"></i> Code Composition</h2>
            </div>
            <div class="chart-container">
                <canvas id="codeCompositionChart"></canvas>
            </div>
        </div>
        
        <!-- Files by Type Chart -->
        <div class="stat-card">
            <div class="stat-card-header">
                <h2><i class="fas fa-folder-open"></i> Files by Type</h2>
            </div>
            <div class="chart-container chart-container-large">
                <canvas id="filesByTypeChart"></canvas>
            </div>
        </div>
        
        <!-- Lines of Code by Language Chart -->
        <div class="stat-card">
            <div class="stat-card-header">
                <h2><i class="fas fa-code"></i> Lines of Code by Language</h2>
            </div>
            <div class="chart-container chart-container-large">
                <canvas id="linesByLanguageChart"></canvas>
            </div>
        </div>
        
        <!-- Detailed Statistics Table -->
        <div class="stat-card">
            <div class="stat-card-header">
                <h2><i class="fas fa-table"></i> Detailed Language Statistics</h2>
            </div>
            <div class="table-responsive">
                <table class="table stats-table">
                    <thead>
                        <tr>
                            <th>Language</th>
                            <th class="text-end">Total Lines</th>
                            <th class="text-end">Code Lines</th>
                            <th class="text-end">Comments</th>
                            <th class="text-end">Code %</th>
                            <th>Distribution</th>
                        </tr>
                    </thead>
                    <tbody>'''
    
    for lang, counts in sorted_lines:
        if counts['total'] > 0:
            emoji = type_emoji.get(lang, '📦')
            code_pct = (counts["code"] / counts["total"] * 100) if counts["total"] > 0 else 0
            dist_pct = (counts["code"] / stats["total_code_lines"] * 100) if stats["total_code_lines"] > 0 else 0
            html += f'''
                        <tr>
                            <td><strong>{emoji} {lang}</strong></td>
                            <td class="text-end">{counts["total"]:,}</td>
                            <td class="text-end">{counts["code"]:,}</td>
                            <td class="text-end">{counts["comments"]:,}</td>
                            <td class="text-end">{code_pct:.0f}%</td>
                            <td>
                                <div style="background: #e9ecef; border-radius: 4px; height: 8px; overflow: hidden;">
                                    <div class="progress-bar-custom" style="width: {dist_pct:.1f}%;"></div>
                                </div>
                            </td>
                        </tr>'''
    
    html += '''
                    </tbody>
                </table>
            </div>
        </div>'''
    
    # API Routes Chart
    if stats['routes']:
        html += f'''
        
        <!-- API Routes Chart -->
        <div class="stat-card">
            <div class="stat-card-header">
                <h2><i class="fas fa-route"></i> API Routes by Module</h2>
            </div>
            <div class="chart-container chart-container-large">
                <canvas id="routesByModuleChart"></canvas>
            </div>
        </div>'''
    
    # Architecture Overview
    html += f'''
        
        <!-- Architecture Overview -->
        <div class="stat-card">
            <div class="stat-card-header">
                <h2><i class="fas fa-sitemap"></i> Architecture Overview</h2>
            </div>
            <div class="architecture-card">
                <h3>Separated Service Architecture</h3>
                <ul>
                    <li><strong>app</strong> - Flask web UI, REST API (no hardware access)</li>
                    <li><strong>sdr-service</strong> - SDR capture, SAME decoding, Icecast streaming</li>
                    <li><strong>hardware-service</strong> - GPIO control, OLED/VFD displays, LED signs</li>
                    <li><strong>Redis</strong> - Real-time metrics and inter-service communication</li>
                    <li><strong>PostgreSQL + PostGIS</strong> - Persistent storage and spatial queries</li>
                </ul>
            </div>
        </div>
        
        <div class="footer-note">
            <i class="fas fa-code"></i> Generated by <code>scripts/generate_repo_stats.py</code>
        </div>
    </div>
    
    <script>
        // Chart.js default configuration
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        Chart.defaults.color = '#333';
        
        // Code Composition Pie Chart
        const codeCompositionCtx = document.getElementById('codeCompositionChart').getContext('2d');
        new Chart(codeCompositionCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['💻 Code', '💬 Comments', '⬜ Whitespace'],
                datasets: [{{
                    data: [{code_lines}, {comment_lines}, {blank_lines}],
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(200, 200, 200, 0.5)'
                    ],
                    borderColor: [
                        'rgba(102, 126, 234, 1)',
                        'rgba(118, 75, 162, 1)',
                        'rgba(200, 200, 200, 0.8)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20,
                            font: {{
                                size: 14,
                                weight: 'bold'
                            }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                let label = context.label || '';
                                let value = context.parsed || 0;
                                let total = {stats["total_lines"]};
                                let percentage = ((value / total) * 100).toFixed(1);
                                return label + ': ' + value.toLocaleString() + ' lines (' + percentage + '%)';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Files by Type Bar Chart
        const filesByTypeCtx = document.getElementById('filesByTypeChart').getContext('2d');
        new Chart(filesByTypeCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(files_labels)},
                datasets: [{{
                    label: 'Number of Files',
                    data: {json.dumps(files_data)},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return 'Files: ' + context.parsed.y.toLocaleString();
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            font: {{
                                size: 12,
                                weight: 'bold'
                            }}
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }}
                    }},
                    x: {{
                        ticks: {{
                            font: {{
                                size: 12,
                                weight: 'bold'
                            }}
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
        
        // Lines of Code by Language Horizontal Bar Chart
        const linesByLanguageCtx = document.getElementById('linesByLanguageChart').getContext('2d');
        new Chart(linesByLanguageCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(lines_labels)},
                datasets: [{{
                    label: 'Lines of Code',
                    data: {json.dumps(lines_data)},
                    backgroundColor: 'rgba(118, 75, 162, 0.8)',
                    borderColor: 'rgba(118, 75, 162, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return 'Lines: ' + context.parsed.x.toLocaleString();
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        ticks: {{
                            font: {{
                                size: 12,
                                weight: 'bold'
                            }}
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }}
                    }},
                    y: {{
                        ticks: {{
                            font: {{
                                size: 12,
                                weight: 'bold'
                            }}
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});'''
    
    if stats['routes']:
        html += f'''
        
        // API Routes Bar Chart
        const routesByModuleCtx = document.getElementById('routesByModuleChart').getContext('2d');
        new Chart(routesByModuleCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(routes_labels)},
                datasets: [{{
                    label: 'Number of Routes',
                    data: {json.dumps(routes_data)},
                    backgroundColor: 'rgba(13, 110, 253, 0.8)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return 'Routes: ' + context.parsed.x;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1,
                            font: {{
                                size: 12,
                                weight: 'bold'
                            }}
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }}
                    }},
                    y: {{
                        ticks: {{
                            font: {{
                                size: 11
                            }}
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});'''
    
    html += '''
    </script>
</body>
</html>'''
    
    return html


def main():
    """Main function to generate and save repository statistics."""
    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    print('Analyzing repository...')
    stats = analyze_repository(repo_root)
    
    print('Generating HTML with Chart.js visualizations...')
    html_content = generate_html(stats)
    
    # Save to static directory for frontend access
    output_path = repo_root / 'static' / 'repo_stats.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f'Statistics saved to: {output_path}')
    print(f'Total files: {stats["total_files"]:,}')
    print(f'Total lines: {stats["total_lines"]:,}')
    print(f'Total routes: {sum(stats["routes"].values())}')


if __name__ == '__main__':
    main()
