"""
报表生成器 - report_generator.py
修复JSON序列化和HTML格式化问题（已修复表格列显示问题，增加扣分项列）
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if hasattr(obj, '__dict__'):
            # 处理自定义对象
            return obj.__dict__
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(NumpyEncoder, self).default(obj)

class ReportGenerator:
    """评估报表生成器（新格式）"""
    
    def __init__(self):
        self.color_palette = {
            "primary": "#2563eb",
            "secondary": "#1e40af",
            "accent": "#3b82f6",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
            "info": "#8b5cf6",
            "dark": "#1f2937",
            "light": "#f3f4f6"
        }
    
    def generate_json_report(self, report: Dict) -> str:
        """生成JSON格式报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_report_{timestamp}.json"
        
        # 创建报告的深拷贝以避免修改原始数据
        import copy
        report_copy = copy.deepcopy(report)
        
        # 清理报告，确保所有数据都是可JSON序列化的
        self._clean_report_for_json(report_copy)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_copy, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
        
        return filename
    
    def _clean_report_for_json(self, report: Dict):
        """清理报告数据，确保JSON可序列化"""
        import copy
        
        def clean_obj(obj):
            if obj is None:
                return None
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    cleaned[k] = clean_obj(v)
                return cleaned
            elif isinstance(obj, list):
                return [clean_obj(item) for item in obj]
            elif isinstance(obj, tuple):
                return list(obj)
            elif hasattr(obj, '__dict__'):
                return clean_obj(obj.__dict__)
            elif hasattr(obj, '_asdict'):
                return clean_obj(obj._asdict())
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                try:
                    return str(obj)
                except:
                    return "[无法序列化的对象]"
        
        for key in list(report.keys()):
            report[key] = clean_obj(report[key])
    
    def generate_html_report(self, report: Dict) -> str:
        """生成HTML格式报告（新结构）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_report_{timestamp}.html"
        
        html_content = self._create_structured_html(report)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filename
    
    def generate_csv_report(self, report: Dict) -> str:
        """生成CSV格式报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_report_{timestamp}.csv"
        
        df = self._prepare_dataframe(report)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return filename
    
    def _create_structured_html(self, report: Dict) -> str:
        """创建结构化HTML报告"""
        
        overview_data = self._prepare_overview_data(report)
        distribution_data = self._prepare_distribution_data(report)
        details_data = self._prepare_details_table(report)
        dimension_data = self._prepare_dimension_data(report)
        recommendations_data = self._prepare_recommendations_data(report)
        
        radar_data_json = distribution_data.get("radar_data_json", "{}")
        category_data_json = distribution_data.get("category_data_json", "{}")
        
        formatted_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_id": report.get("report_id", "N/A"),
            "total_score": f"{report.get('summary', {}).get('total_score', 0):.2f}",
            "conversation_count": report.get("conversation_count", 0),
            "success_rate": overview_data.get("success_rate", "0.0%"),
            "avg_response_time": overview_data.get("avg_response_time", "0 ms"),
            "total_problems": overview_data.get("total_problems", 0),
            "serious_problems": overview_data.get("serious_problems", 0),
            "dimension_cards_html": dimension_data.get("dimension_cards_html", ""),
            "problems_table_rows": details_data.get("problems_table_rows", ""),
            "recommendations_html": recommendations_data.get("recommendations_html", ""),
            "radar_data_json": radar_data_json,
            "category_data_json": category_data_json
        }
        
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智能体能力评估报告 | AI Agent Evaluation Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    
    <style>
        :root {{
            --primary-color: #2563eb;
            --secondary-color: #1e40af;
            --accent-color: #3b82f6;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1f2937;
            --text-secondary: #6b7280;
            --border-radius: 12px;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}

        .header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: white;
            border-radius: var(--border-radius);
            margin-bottom: 10px;
        }}

        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .header .subtitle {{
            color: #94a3b8;
            font-size: 1rem;
        }}

        .section {{
            background: var(--card-bg);
            border-radius: var(--border-radius);
            padding: 24px;
            box-shadow: var(--shadow-md);
            margin-bottom: 20px;
        }}

        .section-title {{
            font-size: 1.3rem;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--light);
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-title i {{
            color: var(--primary-color);
        }}

        /* 概况数据区域 */
        .overview-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }}

        @media (max-width: 1200px) {{
            .overview-grid {{
                grid-template-columns: repeat(3, 1fr);
            }}
        }}

        @media (max-width: 768px) {{
            .overview-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        .overview-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-sm);
            text-align: center;
            transition: transform 0.2s;
            border-left: 4px solid var(--primary-color);
        }}

        .overview-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }}

        .overview-card.success {{ border-left-color: var(--success-color); }}
        .overview-card.warning {{ border-left-color: var(--warning-color); }}
        .overview-card.danger {{ border-left-color: var(--danger-color); }}

        .overview-value {{
            font-size: 2rem;
            font-weight: 700;
            margin: 10px 0;
        }}

        .overview-label {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        /* 分布数据区域 */
        .distribution-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }}

        @media (max-width: 1024px) {{
            .distribution-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-container {{
            height: 400px;
            background: var(--card-bg);
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: var(--shadow-sm);
        }}

        /* --- 明细数据表格样式 --- */
        .details-table-container {{
            overflow-x: auto;
            margin-top: 20px;
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }}

        .details-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 0;
            table-layout: fixed;
        }}

        .details-table th {{
            background-color: #f8fafc;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: var(--text-main);
            border-bottom: 2px solid var(--primary-color);
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        /* 重新定义列宽，增加问题点列 */
        .details-table th:nth-child(1) {{ width: 12%; }} /* 问题分类 */
        .details-table th:nth-child(2) {{ width: 29%; }} /* 用户问题 */
        .details-table th:nth-child(3) {{ width: 29%; }} /* 智能体回复 */
        .details-table th:nth-child(4) {{ width: 30%; }} /* 问题点 */

        .details-table td {{
            padding: 15px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: top;
            word-wrap: break-word;
            word-break: break-all;
            color: #334155;
            line-height: 1.6;
        }}

        .details-table tr:hover {{
            background-color: #f8fafc;
        }}
        
        /* 扣分项标签样式 */
        .deduction-tag {{
            display: inline-block;
            background-color: #fef2f2;
            color: #ef4444;
            border: 1px solid #fecaca;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-right: 6px;
            margin-bottom: 6px;
            line-height: 1.4;
        }}

        /* --- Tooltip 样式 --- */
        .cell-wrapper {{
            position: relative;
            cursor: help;
            display: block;
            width: 100%;
        }}

        .cell-wrapper:hover .tooltip-popup {{
            visibility: visible;
            opacity: 1;
        }}

        .tooltip-popup {{
            visibility: hidden;
            width: 400px;
            background-color: rgba(31, 41, 55, 0.95);
            color: white;
            text-align: left;
            padding: 15px;
            border-radius: 8px;
            position: absolute;
            z-index: 100;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-bottom: 10px;
            opacity: 0;
            transition: opacity 0.2s;
            font-size: 0.85rem;
            font-weight: normal;
            box-shadow: var(--shadow-lg);
            line-height: 1.5;
            white-space: pre-wrap;
            pointer-events: none;
        }}
        
        .tooltip-popup::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: rgba(31, 41, 55, 0.95) transparent transparent transparent;
        }}

        /* 维度数据区域 */
        .dimension-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .dimension-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-sm);
            border: 1px solid #e5e7eb;
        }}

        .dimension-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .dimension-name {{
            font-weight: 600;
            font-size: 1.1rem;
        }}

        .dimension-score {{
            font-weight: 700;
            font-size: 1.2rem;
            color: var(--primary-color);
        }}

        .progress-bar {{
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            margin-bottom: 15px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 4px;
        }}

        .metric-item {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px dashed #f3f4f6;
        }}

        .metric-item:last-child {{
            border-bottom: none;
        }}

        /* 建议区域 */
        .recommendations-list {{
            list-style: none;
            margin-top: 20px;
        }}

        .recommendation-item {{
            display: flex;
            align-items: flex-start;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid var(--accent-color);
        }}

        .recommendation-item i {{
            color: var(--accent-color);
            margin-right: 15px;
            margin-top: 3px;
        }}

        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .problem-count {{
            display: inline-block;
            background-color: #f3f4f6;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.85rem;
            color: #6b7280;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        
        <div class="header">
            <h1>智能体能力评估报告</h1>
            <div class="subtitle">
                <i class="far fa-clock"></i> 生成时间: {timestamp} | 
                <i class="fas fa-fingerprint"></i> 报告ID: {report_id} |
                <i class="fas fa-chart-line"></i> 版本: 3.2.0 (Enhanced)
            </div>
        </div>

        <!-- 1. 概况数据 -->
        <div class="section">
            <div class="section-title">
                <i class="fas fa-chart-bar"></i> 概况数据
            </div>
            <div class="overview-grid">
                <div class="overview-card success">
                    <div class="overview-label">成功率 (Success Rate)</div>
                    <div class="overview-value">{success_rate}</div>
                    <div class="overview-label">基于核心意图识别</div>
                </div>
                <div class="overview-card">
                    <div class="overview-label">平均响应时间 (RT)</div>
                    <div class="overview-value">{avg_response_time}</div>
                    <div class="overview-label">系统处理延时</div>
                </div>
                <div class="overview-card">
                    <div class="overview-label">评估对话量</div>
                    <div class="overview-value">{conversation_count}</div>
                    <div class="overview-label">样本总数</div>
                </div>
                <div class="overview-card warning">
                    <div class="overview-label">发现问题数</div>
                    <div class="overview-value">{total_problems}</div>
                    <div class="overview-label">所有评估维度</div>
                </div>
                <div class="overview-card danger">
                    <div class="overview-label">严重问题数</div>
                    <div class="overview-value">{serious_problems}</div>
                    <div class="overview-label">需要优先处理</div>
                </div>
            </div>
        </div>

        <!-- 2. 分布数据 -->
        <div class="section">
            <div class="section-title">
                <i class="fas fa-chart-pie"></i> 分布数据
            </div>
            <div class="distribution-grid">
                <div class="chart-container">
                    <div class="section-title" style="font-size: 1rem; margin-bottom: 15px;">
                        <i class="fas fa-chart-radar"></i> 多维能力模型分析
                    </div>
                    <div id="radarChart" style="height: 320px;"></div>
                </div>
                
                <div class="chart-container">
                    <div class="section-title" style="font-size: 1rem; margin-bottom: 15px;">
                        <i class="fas fa-tachometer-alt"></i> 系统健康度 (SHI)
                    </div>
                    <div id="gaugeChart" style="height: 320px;"></div>
                </div>
                
                <div class="chart-container">
                    <div class="section-title" style="font-size: 1rem; margin-bottom: 15px;">
                        <i class="fas fa-chart-pie"></i> 问题分类分布
                    </div>
                    <div id="categoryPieChart" style="height: 320px;"></div>
                </div>
            </div>
        </div>

        <!-- 3. 问题明细数据 -->
        <div class="section">
            <div class="section-title">
                <i class="fas fa-table"></i> 问题明细数据
                <span class="problem-count">共 {total_problems} 个问题</span>
            </div>
            <div class="details-table-container">
                <table class="details-table">
                    <thead>
                        <tr>
                            <th>问题分类</th>
                            <th>用户问题</th>
                            <th>智能体回复</th>
                            <th>问题点 (Deduction Items)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {problems_table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 4. 维度详细数据拆解 -->
        <div class="section">
            <div class="section-title">
                <i class="fas fa-layer-group"></i> 维度详细数据拆解
            </div>
            <div class="dimension-grid">
                {dimension_cards_html}
            </div>
        </div>

        <!-- 5. 智能诊断与优化建议 -->
        <div class="section">
            <div class="section-title">
                <i class="fas fa-clipboard-check"></i> 智能诊断与优化建议
            </div>
            <ul class="recommendations-list">
                {recommendations_html}
            </ul>
        </div>

        <!-- 页脚 -->
        <div class="footer">
            <p>© AI Agent Evaluation System. 报告生成时间: {timestamp}</p>
            <p>对话数: {conversation_count} | 总体评分: {total_score} | 问题总数: {total_problems}</p>
        </div>
    </div>

    <script>
        const radarData = {radar_data_json};
        const categoryData = {category_data_json};
        const totalScore = {total_score};
        
        function getGrade(score) {{
            if (score >= 0.9) return 'S';
            if (score >= 0.8) return 'A';
            if (score >= 0.7) return 'B';
            if (score >= 0.6) return 'C';
            return 'D';
        }}
        
        const scoreGrade = getGrade(parseFloat(totalScore));

        document.addEventListener('DOMContentLoaded', function() {{
            const radarChart = echarts.init(document.getElementById('radarChart'));
            const radarOption = {{
                color: ['#2563eb'],
                tooltip: {{ trigger: 'item' }},
                radar: {{
                    indicator: radarData.labels.map(label => ({{ name: label, max: 1.0 }})),
                    radius: '70%',
                    splitNumber: 5,
                    axisName: {{
                        color: '#64748b',
                        fontSize: 12
                    }},
                    axisLine: {{ lineStyle: {{ color: '#e2e8f0' }} }},
                    splitLine: {{ lineStyle: {{ color: '#e2e8f0' }} }},
                    splitArea: {{
                        areaStyle: {{ color: ['#f8fafc', '#ffffff'] }}
                    }}
                }},
                series: [{{
                    name: '能力评估',
                    type: 'radar',
                    data: [{{
                        value: radarData.scores,
                        name: '当前模型',
                        areaStyle: {{
                            color: 'rgba(37, 99, 235, 0.2)'
                        }},
                        lineStyle: {{ width: 2, color: '#2563eb' }},
                        itemStyle: {{ color: '#2563eb' }},
                        label: {{
                            show: true,
                            formatter: (p) => p.value.toFixed(2),
                            fontSize: 10
                        }}
                    }}]
                }}]
            }};
            radarChart.setOption(radarOption);
            
            const gaugeChart = echarts.init(document.getElementById('gaugeChart'));
            const gaugeOption = {{
                series: [{{
                    type: 'gauge',
                    startAngle: 180,
                    endAngle: 0,
                    min: 0,
                    max: 1,
                    radius: '90%',
                    center: ['50%', '75%'],
                    axisLine: {{
                        lineStyle: {{
                            width: 20,
                            color: [
                                [0.6, '#ef4444'],
                                [0.8, '#f59e0b'],
                                [1, '#10b981']
                            ]
                        }}
                    }},
                    pointer: {{
                        show: true,
                        length: '60%',
                        width: 6
                    }},
                    axisTick: {{ length: 12, lineStyle: {{ width: 2 }} }},
                    splitLine: {{ length: 20, lineStyle: {{ width: 5 }} }},
                    axisLabel: {{
                        color: '#464646',
                        fontSize: 12,
                        distance: -60,
                        formatter: (val) => (val*100).toFixed(0)
                    }},
                    detail: {{
                        fontSize: 40,
                        offsetCenter: [0, '-30%'],
                        valueAnimation: true,
                        formatter: function (value) {{
                            return parseFloat(totalScore).toFixed(2);
                        }},
                        color: 'inherit'
                    }},
                    data: [{{ value: parseFloat(totalScore), name: '评级: ' + scoreGrade }}]
                }}]
            }};
            gaugeChart.setOption(gaugeOption);
            
            const categoryPieChart = echarts.init(document.getElementById('categoryPieChart'));
            const categoryPieOption = {{
                tooltip: {{
                    trigger: 'item',
                    formatter: '{{a}}<br/>{{b}}: {{c}} ({{d}}%)'
                }},
                legend: {{
                    orient: 'vertical',
                    left: 10,
                    top: 'center',
                    data: categoryData.labels,
                    textStyle: {{
                        fontSize: 12
                    }}
                }},
                series: [{{
                    name: '问题分类',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    center: ['60%', '50%'],
                    avoidLabelOverlap: true,
                    itemStyle: {{
                        borderRadius: 5,
                        borderColor: '#fff',
                        borderWidth: 2
                    }},
                    label: {{
                        show: true,
                        formatter: function(params) {{
                            return params.name + ': ' + params.value + ' (' + params.percent.toFixed(1) + '%)';
                        }},
                        fontSize: 11,
                        color: '#333'
                    }},
                    emphasis: {{
                        label: {{
                            show: true,
                            fontSize: '13',
                            fontWeight: 'bold'
                        }}
                    }},
                    labelLine: {{
                        show: true
                    }},
                    data: categoryData.values.map((value, index) => ({{
                        value: value,
                        name: categoryData.labels[index],
                        itemStyle: {{
                            color: categoryData.colors[index]
                        }}
                    }}))
                }}]
            }};
            categoryPieChart.setOption(categoryPieOption);
            
            window.addEventListener('resize', function() {{
                radarChart.resize();
                gaugeChart.resize();
                categoryPieChart.resize();
            }});
        }});
    </script>
</body>
</html>'''
        
        try:
            html_content = html_template.format(**formatted_data)
        except KeyError as e:
            html_content = html_template
            for key, value in formatted_data.items():
                placeholder = f"{{{key}}}"
                html_content = html_content.replace(placeholder, str(value))
        
        return html_content
    
    def _prepare_overview_data(self, report: Dict) -> Dict:
        """准备概况数据"""
        summary = report.get("summary", {})
        perf_metrics = report.get("performance_metrics", {})
        problems = report.get("problems_summary", {})
        
        success_rate = perf_metrics.get("success_rate", 0)
        avg_response_time = perf_metrics.get("avg_response_time", 0)
        
        return {
            "total_score": f"{summary.get('total_score', 0):.2f}",
            "success_rate": f"{success_rate:.1%}",
            "avg_response_time": f"{avg_response_time:.0f} ms",
            "conversation_count": report.get("conversation_count", 0),
            "total_problems": problems.get("total_problems", 0),
            "serious_problems": problems.get("serious_problems_count", 0),
            "report_id": report.get("report_id", "N/A")
        }
    
    def _prepare_distribution_data(self, report: Dict) -> Dict:
        """准备分布数据"""
        dimension_scores = report.get("summary", {}).get("dimension_scores", {})
        radar_labels = list(dimension_scores.keys())
        radar_scores = list(dimension_scores.values())
        
        problems = report.get("problems_summary", {})
        category_labels = []
        category_values = []
        category_colors = ["#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#84cc16", 
                          "#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#3b82f6",
                          "#ef4444", "#a855f7", "#06b6d4", "#22c55e", "#eab308"]
        
        all_problems = []
        by_severity = problems.get("by_severity", {})
        for severity_level in ["critical", "high", "medium", "low"]:
            all_problems.extend(by_severity.get(severity_level, []))
        
        if not all_problems:
            all_problems = problems.get("top_problems", [])
        
        if all_problems:
            category_counts = {}
            for problem in all_problems:
                category = problem.get("dimension", "未知")
                category_counts[category] = category_counts.get(category, 0) + 1
            
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            category_labels = [item[0] for item in sorted_categories]
            category_values = [item[1] for item in sorted_categories]
        
        if not category_labels:
            category_labels = ["暂无数据"]
            category_values = [1]
            category_colors = ["#cccccc"]
        
        return {
            "radar_data_json": json.dumps({
                "labels": radar_labels,
                "scores": radar_scores
            }, ensure_ascii=False),
            "category_data_json": json.dumps({
                "labels": category_labels,
                "values": category_values,
                "colors": category_colors[:len(category_labels)]
            }, ensure_ascii=False)
        }
    
    def _prepare_details_table(self, report: Dict) -> Dict:
        """准备明细数据表格 - 修复 HTML 结构并增加扣分项"""
        problems = report.get("problems_summary", {})
        
        all_problems = []
        by_severity = problems.get("by_severity", {})
        for severity_level in ["critical", "high", "medium", "low"]:
            all_problems.extend(by_severity.get(severity_level, []))
        
        if not all_problems:
            all_problems = problems.get("top_problems", [])
        
        rows = []
        for i, problem in enumerate(all_problems, 1):
            u_input = str(problem.get('user_input', '')).replace("<", "&lt;").replace(">", "&gt;")
            a_response = str(problem.get('assistant_response', '')).replace("<", "&lt;").replace(">", "&gt;")
            
            u_input_short = u_input[:80] + ('...' if len(u_input) > 80 else '')
            a_response_short = a_response[:80] + ('...' if len(a_response) > 80 else '')
            
            if not u_input:
                user_html = '<span style="color: #9ca3af;">(无问题内容)</span>'
            else:
                user_html = f'''
                    <div class="cell-wrapper">
                        {u_input_short}
                        <div class="tooltip-popup">{u_input}</div>
                    </div>
                '''
            
            if not a_response or a_response == "无回复数据":
                response_html = '<span style="color: #9ca3af; font-style: italic;">(无回复数据)</span>'
            else:
                response_html = f'''
                    <div class="cell-wrapper">
                        {a_response_short}
                        <div class="tooltip-popup">{a_response}</div>
                    </div>
                '''

            # --- 新增：处理扣分项 (Deduction Items) ---
            deduction_items = problem.get('deduction_items', [])
            deduction_html = ""
            
            if deduction_items and isinstance(deduction_items, list):
                for item in deduction_items:
                    item_str = str(item).replace("<", "&lt;")
                    deduction_html += f'<span class="deduction-tag">{item_str}</span>'
            elif deduction_items:
                deduction_html = f'<span class="deduction-tag">{str(deduction_items)}</span>'
            else:
                deduction_html = '<span style="color: #cbd5e1; font-size: 0.8rem;">-</span>'

            rows.append(f"""
            <tr>
                <td>
                    <div style="font-weight: 600; color: #1e40af;">{problem.get('dimension', '未知')}</div>
                    <div style="font-size: 0.85em; color: #64748b; margin-top: 4px;">{problem.get('problem_subtype', '')}</div>
                </td>
                <td>
                    {user_html}
                </td>
                <td>
                    {response_html}
                </td>
                <td>
                    {deduction_html}
                </td>
            </tr>
            """)
        
        if not rows:
            rows = ["""
            <tr>
                <td colspan="4" style="text-align: center; padding: 60px; color: #6b7280; background-color: #f9fafb;">
                    <i class="fas fa-check-circle" style="font-size: 3rem; color: #10b981; margin-bottom: 15px;"></i>
                    <h3 style="margin: 0; color: #374151;">未发现问题</h3>
                    <p style="margin: 5px 0 0 0;">所有评估维度均表现良好</p>
                </td>
            </tr>
            """]
        
        return {
            "problems_table_rows": "\n".join(rows)
        }
    
    def _prepare_dimension_data(self, report: Dict) -> Dict:
        """准备维度详细数据"""
        dimension_scores = report.get("summary", {}).get("dimension_scores", {})
        detailed_results = report.get("detailed_results", {})
        
        cards = []
        for dimension, score in dimension_scores.items():
            metrics = {}
            for evaluator, result in detailed_results.items():
                if isinstance(result, dict) and result.get("dimension") == dimension:
                    metrics = result.get("metrics", {})
                    break
            
            if score >= 0.8:
                color = "#10b981"
            elif score >= 0.6:
                color = "#f59e0b"
            else:
                color = "#ef4444"
            
            metrics_html = ""
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, (int, float)):
                    display_value = f"{metric_value:.2f}"
                else:
                    display_value = str(metric_value)
                
                metrics_html += f"""
                <div class="metric-item">
                    <span>{metric_name}</span>
                    <span style="font-weight: 600;">{display_value}</span>
                </div>
                """
            
            if not metrics_html:
                metrics_html = '<div style="color: #6b7280; font-style: italic;">暂无详细指标数据</div>'
            
            cards.append(f"""
            <div class="dimension-card">
                <div class="dimension-header">
                    <span class="dimension-name">{dimension}</span>
                    <span class="dimension-score" style="color: {color};">{score:.2f}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {score*100}%; background: {color};"></div>
                </div>
                <div style="margin-top: 15px;">
                    <strong>详细指标:</strong>
                    <div style="margin-top: 10px;">
                        {metrics_html}
                    </div>
                </div>
            </div>
            """)
        
        return {
            "dimension_cards_html": "\n".join(cards)
        }
    
    def _prepare_recommendations_data(self, report: Dict) -> Dict:
        """准备建议数据"""
        recommendations = report.get("summary", {}).get("recommendations", [])
        
        if not recommendations:
            total_score = report.get("summary", {}).get("total_score", 0)
            if total_score >= 0.8:
                recommendations = [
                    "系统表现优秀，继续保持当前配置",
                    "可以考虑增加更多复杂场景测试",
                    "定期监控系统性能指标"
                ]
            elif total_score >= 0.6:
                recommendations = [
                    "优化问题识别准确率",
                    "加强异常情况处理能力",
                    "增加用户意图理解训练"
                ]
            else:
                recommendations = [
                    "需要紧急处理严重问题",
                    "全面检查系统配置和逻辑",
                    "增加监控和告警机制"
                ]
        
        recommendations_html = ""
        for i, rec in enumerate(recommendations, 1):
            icon = "🔥" if i == 1 else "⚠️" if i == 2 else "💡"
            recommendations_html += f"""
            <li class="recommendation-item">
                <i class="fas fa-bullhorn"></i>
                <div>
                    <strong>{icon} 建议 {i}:</strong> {rec}
                </div>
            </li>
            """
        
        return {
            "recommendations_html": recommendations_html
        }
    
    def _prepare_dataframe(self, report: Dict) -> pd.DataFrame:
        """准备DataFrame用于CSV导出"""
        data = []
        
        perf_metrics = report.get("performance_metrics", {})
        data.append({
            "数据类别": "概况数据",
            "指标名称": "成功率 (Success Rate)",
            "数值": perf_metrics.get("success_rate", 0),
            "单位": "%",
            "扣分项": ""
        })
        
        data.append({
            "数据类别": "概况数据",
            "指标名称": "平均响应时间 (RT)",
            "数值": perf_metrics.get("avg_response_time", 0),
            "单位": "ms",
            "扣分项": ""
        })
        
        data.append({
            "数据类别": "概况数据",
            "指标名称": "评估对话量",
            "数值": report.get("conversation_count", 0),
            "单位": "个",
            "扣分项": ""
        })
        
        problems = report.get("problems_summary", {})
        data.append({
            "数据类别": "概况数据",
            "指标名称": "发现问题数",
            "数值": problems.get("total_problems", 0),
            "单位": "个",
            "扣分项": ""
        })
        
        data.append({
            "数据类别": "概况数据",
            "指标名称": "严重问题数",
            "数值": problems.get("serious_problems_count", 0),
            "单位": "个",
            "扣分项": ""
        })
        
        dimension_scores = report.get("summary", {}).get("dimension_scores", {})
        for dimension, score in dimension_scores.items():
            data.append({
                "数据类别": "维度数据",
                "指标名称": f"{dimension}得分",
                "数值": score,
                "单位": "分",
                "扣分项": ""
            })
        
        all_problems = []
        by_severity = problems.get("by_severity", {})
        for severity_level in ["critical", "high", "medium", "low"]:
            all_problems.extend(by_severity.get(severity_level, []))
        
        if not all_problems:
            all_problems = problems.get("top_problems", [])
        
        for i, problem in enumerate(all_problems, 1):
            deduction_items = problem.get("deduction_items", [])
            deduction_str = "; ".join([str(item) for item in deduction_items]) if isinstance(deduction_items, list) else str(deduction_items)
            
            data.append({
                "数据类别": "问题明细",
                "指标名称": f"问题{i}_{problem.get('dimension', '')}",
                "数值": problem.get("score", 0),
                "单位": "分",
                "详细描述": f"{problem.get('problem_subtype', '')} - {problem.get('user_input', '')[:50]}",
                "扣分项": deduction_str
            })
        
        return pd.DataFrame(data)
    