"""
主评估系统 - main_evaluation_system.py
集成所有评估智能体，提供完整评估流程
"""
import os
import sys
import json
import numpy as np
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import time

# 导入评估专家
from functional_evaluator import FunctionalEvaluator
from ux_evaluator import UserExperienceEvaluator
from business_evaluator import BusinessValueEvaluator
from technical_evaluator import TechnicalQualityEvaluator

# 导入客服系统
from customer_service import CustomerServiceAgent

# 导入报表生成器
from report_generator import ReportGenerator

class CustomerServiceEvaluationSystem:
    """客服智能体评估系统"""
    
    def __init__(self):
        # 初始化各评估专家
        self.evaluators = {
            "functional": FunctionalEvaluator(),
            "user_experience": UserExperienceEvaluator(),
            "business_value": BusinessValueEvaluator(),
            "technical_quality": TechnicalQualityEvaluator()
        }
        
        # 初始化客服智能体
        self.customer_service_agent = CustomerServiceAgent()
        
        # 初始化报表生成器
        self.report_generator = ReportGenerator()
        
        # 评估配置
        self.evaluation_config = {
            "enable_real_time": True,
            "enable_batch": True,
            "enable_periodic": True,
            "evaluation_interval": 3600,  # 1小时
            "retention_days": 30
        }
        
    async def evaluate_batch_conversations(self, test_cases: List[Dict]) -> Dict:
        """批量评估对话 - 实际调用客服系统"""
        print(f"📚 执行 {len(test_cases)} 个测试用例...")
        
        # 实际调用客服系统生成对话
        conversations = []
        
        for test_case in test_cases:
            user_id = test_case.get("user_id", "cust001")
            user_input = test_case.get("user_input", "")
            
            print(f"  测试用例: {user_id} -> {user_input[:30]}...")
            
            # 实际调用客服系统
            conversation_result = self.customer_service_agent.process_query(user_id, user_input)
            
            # 确保对话包含必要的字段
            conversation_result["test_case"] = test_case.get("test_case", "")
            conversation_result["user_input"] = user_input
            
            # 确保assistant_response字段存在
            if "assistant_response" not in conversation_result:
                conversation_result["assistant_response"] = "无回复数据"
            
            conversations.append(conversation_result)
            
            # 避免调用过快
            await asyncio.sleep(0.1)
        
        print(f"✅ 已完成 {len(conversations)} 个对话")
        
        # 执行各维度评估
        evaluation_results = {}
        
        for name, evaluator in self.evaluators.items():
            print(f"\n📋 开始 {name} 评估...")
            result = await evaluator.evaluate(conversations)
            
            # 获取评估器的问题数据，确保包含智能体回复
            problems = evaluator.export_problems(include_details=True)
            
            # 如果问题中没有智能体回复，从对话中补充
            if "detailed_problems" in problems:
                for problem_type, problem_list in problems["detailed_problems"].items():
                    for problem in problem_list:
                        # 确保问题有用户输入字段
                        if "user_input" not in problem:
                            # 尝试从对话中获取第一个匹配的用户输入
                            if conversations and "user_input" in conversations[0]:
                                problem["user_input"] = conversations[0].get("user_input", "")
                        
                        # 确保问题有智能体回复字段
                        if "assistant_response" not in problem or not problem["assistant_response"]:
                            user_input = problem.get("user_input", "")
                            if user_input:
                                for conv in conversations:
                                    if conv.get("user_input") == user_input:
                                        problem["assistant_response"] = conv.get("assistant_response", "")
                                        break
                            # 如果还是没有，使用默认值
                            if "assistant_response" not in problem or not problem["assistant_response"]:
                                problem["assistant_response"] = "无回复数据"
            
            result["problems"] = problems
            
            evaluation_results[name] = result
        
        # 生成综合报告
        comprehensive_report = await self._generate_comprehensive_report(evaluation_results, conversations)
        
        return comprehensive_report
    
    async def continuous_evaluation(self):
        """持续评估（实际调用客服系统）"""
        print("🔄 启动持续评估监控...")
        
        # 定义测试用例
        test_cases = [
            {"user_id": "cust001", "user_input": "我的订单123456到哪里了？", "test_case": "订单查询"},
            {"user_id": "cust002", "user_input": "智能手机A和智能手机B哪个拍照更好？", "test_case": "产品比较"},
            {"user_id": "cust003", "user_input": "我刚收到的商品有损坏，我要投诉！", "test_case": "投诉处理"},
            {"user_id": "emp001", "user_input": "华东区昨天卖了多少钱？", "test_case": "销售数据查询"},
            {"user_id": "cust004", "user_input": "怎么退货？", "test_case": "退货流程"},
            {"user_id": "cust005", "user_input": "有优惠券吗？", "test_case": "优惠咨询"},
        ]
        
        evaluation_buffer = []
        evaluation_count = 0
        
        try:
            while True:
                # 轮流执行不同的测试用例
                test_case = test_cases[evaluation_count % len(test_cases)]
                evaluation_count += 1
                
                # 调用客服系统
                conversation = self.customer_service_agent.process_query(
                    test_case["user_id"], 
                    test_case["user_input"]
                )
                
                conversation["test_case"] = test_case["test_case"]
                conversation["user_input"] = test_case["user_input"]
                
                # 确保assistant_response字段存在
                if "assistant_response" not in conversation:
                    conversation["assistant_response"] = "无回复数据"
                
                evaluation_buffer.append(conversation)
                
                print(f"✅ 执行测试用例 {evaluation_count}: {test_case['test_case']}")
                print(f"   用户: {test_case['user_input']}")
                print(f"   响应: {conversation['assistant_response'][:200]}...")
                print()
                
                # 检查是否达到评估条件
                if len(evaluation_buffer) >= 3:
                    print(f"⏰ 触发定期评估: {len(evaluation_buffer)} 条对话")
                    
                    # 准备测试用例格式
                    test_cases_for_eval = [
                        {
                            "user_id": conv["user_id"], 
                            "user_input": conv["user_input"], 
                            "test_case": conv["test_case"]
                        }
                        for conv in evaluation_buffer
                    ]
                    
                    # 执行评估
                    results = await self.evaluate_batch_conversations(test_cases_for_eval)
                    
                    # 显示评估结果摘要
                    self._display_evaluation_summary(results)
                    
                    # 导出评估报告
                    print("\n📊 生成评估报告...")
                    report_files = await self.export_report(results, ["json", "html", "csv"])
                    
                    print("📁 报告文件:")
                    for fmt, filename in report_files.items():
                        print(f"  • {fmt.upper()}: {filename}")
                    
                    # 清空缓冲区
                    evaluation_buffer = []
                
                # 等待一段时间后继续
                await asyncio.sleep(5)  # 每5秒执行一个测试用例
                
        except KeyboardInterrupt:
            print("\n🛑 持续评估已停止")
    
    async def _generate_comprehensive_report(self, evaluation_results: Dict, conversations: List[Dict]) -> Dict:
        """生成综合评估报告"""
        print("📈 生成综合评估报告...")
        
        # 计算性能指标
        response_times = [c.get("response_time_ms", 0) for c in conversations]
        errors = [c for c in conversations if c.get("error")]
        
        # 汇总所有评估器的问题，传递对话数据以获取智能体回复
        all_problems_summary = self._consolidate_problems(evaluation_results, conversations)
        
        report = {
            "report_id": f"EVAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "conversation_count": len(conversations),
            "summary": {
                "total_score": 0,
                "dimension_scores": {},
                "ranking": {},
                "recommendations": []
            },
            "conversations": conversations,
            "detailed_results": evaluation_results,
            "performance_metrics": {
                "avg_response_time": np.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "success_rate": 1 - (len(errors) / len(conversations)) if conversations else 0,
                "error_count": len(errors)
            },
            "problems_summary": all_problems_summary
        }
        
        # 计算总分和各维度得分
        dimension_scores = {}
        dimension_weights = {
            "功能性能": 0.3,
            "用户体验": 0.25,
            "业务价值": 0.25,
            "技术质量": 0.2
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for evaluator_name, result in evaluation_results.items():
            dimension = result.get("dimension", "")
            score = result.get("overall_score", 0)
            
            if dimension:
                dimension_scores[dimension] = score
                weight = dimension_weights.get(dimension, 1.0)
                
                weighted_sum += score * weight
                total_weight += weight
        
        # 计算总分
        if total_weight > 0:
            report["summary"]["total_score"] = weighted_sum / total_weight
        
        report["summary"]["dimension_scores"] = dimension_scores
        
        # 生成排名
        sorted_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
        report["summary"]["ranking"] = dict(sorted_dimensions[:3])
        
        # 生成建议
        report["summary"]["recommendations"] = self._generate_recommendations(evaluation_results)
        
        return report
    
    def _consolidate_problems(self, evaluation_results: Dict, conversations: List[Dict]) -> Dict:
            """合并所有评估器的问题，确保包含智能体回复（修复版）"""
            consolidated = {
                "total_problems": 0,
                "serious_problems_count": 0,
                "by_dimension": {},
                "by_severity": { "critical": [], "high": [], "medium": [], "low": [] },
                "top_problems": []
            }
            
            dimension_problem_counts = {}
            
            for evaluator_name, result in evaluation_results.items():
                dimension = result.get("dimension", evaluator_name)
                
                # 获取问题数据
                problems_data = result.get("problems", {})
                detailed_problems = problems_data.get("detailed_problems", {})
                
                # 统计每个维度的问题
                dim_count = 0
                for problem_type, problem_list in detailed_problems.items():
                    dim_count += len(problem_list)
                    
                    # 按严重程度分类
                    for problem in problem_list:
                        score = problem.get("score", 1.0)
                        problem_type_display = self._get_problem_type_display(problem_type)
                        
                        # 1. 获取基础数据
                        problem_user_input = problem.get("user_input", "")
                        problem_response = problem.get("assistant_response", "")
                        
                        # 2. 核心修复：查找匹配的原始对话
                        matched_conv = None
                        
                        # 尝试匹配策略 A: 精确匹配
                        if not matched_conv:
                            for conv in conversations:
                                if conv.get("user_input") == problem_user_input:
                                    matched_conv = conv
                                    break
                        
                        # 尝试匹配策略 B: 原始输入包含在问题描述中 (解决评估器返回全文的问题)
                        if not matched_conv and problem_user_input:
                            for conv in conversations:
                                raw_input = conv.get("user_input", "")
                                # 如果原始输入比较短且存在于问题描述中
                                if raw_input and len(raw_input) > 2 and raw_input in problem_user_input:
                                    matched_conv = conv
                                    break
                                    
                        # 尝试匹配策略 C: 问题描述包含在原始输入中
                        if not matched_conv and problem_user_input:
                            for conv in conversations:
                                if problem_user_input in conv.get("user_input", ""):
                                    matched_conv = conv
                                    break

                        # 3. 数据修正与填充
                        final_user_input = problem_user_input
                        final_response = problem_response
                        
                        if matched_conv:
                            # 找到了原始对话，使用原始的纯净数据覆盖
                            final_user_input = matched_conv.get("user_input", "")
                            
                            # 如果问题里没回复，用原始对话的回复
                            if not final_response:
                                final_response = matched_conv.get("assistant_response", "")
                        
                        # 兜底处理
                        if not final_user_input:
                            final_user_input = f"{problem_type_display}相关问题"
                        if not final_response:
                            final_response = "无回复数据"

                        # 4. 构建问题条目
                        problem_entry = {
                            "dimension": dimension,
                            "problem_type": problem_type_display,
                            "problem_subtype": problem.get("problem_type", ""),
                            "score": score,
                            "deduction_items": problem.get("deduction_items", []),
                            "user_input": final_user_input,       # 使用修正后的纯净输入
                            "assistant_response": final_response  # 使用修正后的回复
                        }
                        
                        if score < 0.3:
                            consolidated["by_severity"]["critical"].append(problem_entry)
                        elif score < 0.5:
                            consolidated["by_severity"]["high"].append(problem_entry)
                        elif score < 0.7:
                            consolidated["by_severity"]["medium"].append(problem_entry)
                        else:
                            consolidated["by_severity"]["low"].append(problem_entry)
                
                dimension_problem_counts[dimension] = dim_count
                
            # ... (后续统计代码保持不变) ...
            # 计算总数
            consolidated["total_problems"] = sum(dimension_problem_counts.values())
            
            # 统计严重问题数（得分 < 0.7）
            serious_count = len(consolidated["by_severity"]["critical"]) + \
                        len(consolidated["by_severity"]["high"]) + \
                        len(consolidated["by_severity"]["medium"])
            consolidated["serious_problems_count"] = serious_count
            
            # 按维度统计
            consolidated["by_dimension"] = dimension_problem_counts
            
            # 获取所有问题，按得分排序（得分越低越严重）
            all_problems = []
            for severity_level in ["critical", "high", "medium", "low"]:
                all_problems.extend(consolidated["by_severity"][severity_level])
            
            # 按得分排序，得分越低越严重
            sorted_problems = sorted(all_problems, key=lambda x: x["score"])
            consolidated["top_problems"] = sorted_problems
            
            return consolidated
    
    def _get_problem_type_display(self, problem_type: str) -> str:
        """获取问题类型显示名称"""
        problem_type_map = {
            "robustness": "稳健性",
            "security": "安全性",
            "accuracy": "准确性",
            "usability": "可用性",
            "performance": "性能",
            "effectiveness": "问题解决率",
            "intervention": "人工干预率",
            "conversion": "转化率",
            "efficiency": "效率",
            "satisfaction": "满意度",
            "response_time": "响应时间",
            "functional_accuracy": "功能准确性",
            "functional_relevance": "功能相关性",
            "functional_completeness": "功能完整性",
            "functional_embedding": "嵌入模型"
        }
        
        return problem_type_map.get(problem_type, problem_type)
    
    def _generate_recommendations(self, evaluation_results: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 收集所有评估专家的改进建议
        all_improvements = []
        
        for evaluator_name, result in evaluation_results.items():
            improvements = result.get("improvements", [])
            all_improvements.extend(improvements)
        
        # 去重并选择最重要的建议
        unique_recommendations = []
        for rec in all_improvements:
            if rec not in unique_recommendations:
                unique_recommendations.append(rec)
        
        # 返回前6个建议
        return unique_recommendations[:6]
    
    def _display_evaluation_summary(self, results: Dict):
        """显示评估结果摘要"""
        print("\n" + "=" * 60)
        print("评估结果摘要")
        print("=" * 60)
        
        summary = results.get("summary", {})
        print(f"📊 总体评分: {summary.get('total_score', 0):.2f}/1.0")
        print(f"🗣️  对话数量: {results.get('conversation_count', 0)}")
        
        # 显示问题统计
        problems_summary = results.get("problems_summary", {})
        if problems_summary:
            print(f"🔴 发现问题: {problems_summary.get('total_problems', 0)} 个")
            print(f"🚨 严重问题: {problems_summary.get('serious_problems_count', 0)} 个")
            
            # 显示问题详情示例
            if problems_summary.get("top_problems"):
                print("\n📝 问题示例:")
                for i, problem in enumerate(problems_summary["top_problems"][:2], 1):
                    print(f"  {i}. [{problem.get('dimension', '')}] {problem.get('problem_subtype', '')[:60]}...")
                    print(f"     用户: {problem.get('user_input', '')[:60]}...")
                    print(f"     回复: {problem.get('assistant_response', '')[:60]}...")
        
        perf_metrics = results.get("performance_metrics", {})
        print(f"\n⚡ 平均响应时间: {perf_metrics.get('avg_response_time', 0):.0f}ms")
        print(f"✅ 成功率: {perf_metrics.get('success_rate', 0):.1%}")
        print(f"❌ 错误数量: {perf_metrics.get('error_count', 0)}")
        
        print("\n📈 各维度评分:")
        for dimension, score in summary.get("dimension_scores", {}).items():
            rating = "★★★★" if score >= 0.8 else "★★★" if score >= 0.6 else "★★" if score >= 0.4 else "★"
            print(f"  • {dimension}: {score:.2f} {rating}")
        
        print("\n🏆 排名前三的维度:")
        for i, (dim, score) in enumerate(summary.get("ranking", {}).items(), 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            print(f"  {medal} {dim}: {score:.2f}")
    
    async def export_report(self, report: Dict, formats: List[str] = None) -> Dict[str, str]:
        """导出评估报告（支持多种格式）"""
        if formats is None:
            formats = ["json", "html", "csv"]
        
        export_files = {}
        
        for format_type in formats:
            try:
                if format_type == "json":
                    filename = self.report_generator.generate_json_report(report)
                    export_files["json"] = filename
                    
                elif format_type == "html":
                    filename = self.report_generator.generate_html_report(report)
                    export_files["html"] = filename
                    
                elif format_type == "csv":
                    filename = self.report_generator.generate_csv_report(report)
                    export_files["csv"] = filename
                    
                else:
                    print(f"⚠️  不支持的报告格式: {format_type}")
                    
            except Exception as e:
                print(f"❌ 导出 {format_type} 报告失败: {e}")
        
        return export_files
    
    def generate_visualization_data(self, report: Dict) -> Dict:
        """生成可视化所需的数据"""
        # 准备仪表盘数据（使用总分）
        total_score = report.get("summary", {}).get("total_score", 0)
        
        # 创建简单的仪表盘数据结构
        gauge_data = {
            "datasets": [{
                "value": float(total_score),
                "minValue": 0,
                "maxValue": 1,
                "data": [
                    {"min": 0, "max": 0.6, "color": "#ef4444"},
                    {"min": 0.6, "max": 0.8, "color": "#f59e0b"},
                    {"min": 0.8, "max": 1.0, "color": "#10b981"}
                ],
                "backgroundColor": ["#ef4444", "#f59e0b", "#10b981"]
            }]
        }
        
        visualization_data = {
            "gauge": gauge_data,
            "problems": report.get("problems_summary", {}),
            "summary": {
                "total_score": float(total_score),
                "dimension_count": len(report.get("summary", {}).get("dimension_scores", {})),
                "recommendations": report.get("summary", {}).get("recommendations", [])
            }
        }
        
        return visualization_data

# 使用示例
async def main():
    """主函数 - 演示评估系统使用"""
    print("=" * 60)
    print("客服智能体评估系统 v2.0")
    print("=" * 60)
    print("✨ 新增功能:")
    print("  • 雷达图可视化")
    print("  • 健康度仪表盘")
    print("  • 专业HTML报告")
    print("  • 问题汇总分析")
    print("=" * 60)
    
    # 初始化评估系统
    evaluation_system = CustomerServiceEvaluationSystem()
    
    # 定义测试用例
    test_cases = [
        {"user_id": "cust001", "user_input": "我的订单123456到哪里了？", "test_case": "订单查询-成功路径"},
        {"user_id": "cust002", "user_input": "智能手机A和智能手机B哪个拍照更好？", "test_case": "产品比较-明确维度"},
        {"user_id": "cust003", "user_input": "我刚收到的商品有损坏，我要投诉！", "test_case": "投诉处理-情感响应"},
        {"user_id": "emp001", "user_input": "华东区昨天卖了多少钱？", "test_case": "销售数据查询-有权限"},
        {"user_id": "cust004", "user_input": "订单999999在哪里？", "test_case": "订单查询-信息错误"},
        {"user_id": "emp002", "user_input": "华北区的销售数据怎么样？", "test_case": "销售数据查询-无权限"},
        {"user_id": "cust005", "user_input": "A手机和B手机哪个好？", "test_case": "产品比较-问题模糊"},
    ]
    
    print(f"📁 执行 {len(test_cases)} 个测试用例...")
    
    # 执行批量评估
    print("\n1. 执行批量评估...")
    results = await evaluation_system.evaluate_batch_conversations(test_cases)
    
    # 显示评估结果摘要
    evaluation_system._display_evaluation_summary(results)
    
    # 导出报告
    print("\n2. 导出评估报告...")
    export_files = await evaluation_system.export_report(results, ["json", "html", "csv"])
    
    print("📁 报告文件:")
    for fmt, filename in export_files.items():
        print(f"  • {fmt.upper()}: {filename}")
    
    # 生成可视化数据
    print("\n3. 生成可视化数据...")
    viz_data = evaluation_system.generate_visualization_data(results)
    print(f"  仪表盘得分: {viz_data['gauge']['datasets'][0]['value']:.2f}")
    print(f"  发现问题: {viz_data['problems'].get('total_problems', 0)}个")
    
    # 持续评估演示
    print("\n4. 启动持续评估演示（按Enter键开始，Ctrl+C停止）...")
    input("按Enter键继续...")
    
    try:
        # 启动持续评估
        await evaluation_system.continuous_evaluation()
        
    except KeyboardInterrupt:
        print("\n\n👋 收到中断信号，停止评估系统")
    
    print("\n" + "=" * 60)
    print("✅ 评估完成！")
    print("=" * 60)

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
