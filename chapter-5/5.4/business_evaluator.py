"""
业务价值评估智能体 - business_evaluator.py
评估问题解决率、人工干预率、转化率等指标
"""
import re
from typing import Dict, List, Any
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from base_evaluator import BaseEvaluator, BaseProblem, ProblemType

@dataclass
class BusinessProblem(BaseProblem):
    """业务价值问题详情"""
    conversation_type: str = ""
    session_id: str = ""
    opportunity_type: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（扩展基类方法）"""
        base_dict = super().to_dict()
        if self.conversation_type:
            base_dict["conversation_type"] = self.conversation_type
        if self.session_id:
            base_dict["session_id"] = self.session_id
        if self.opportunity_type:
            base_dict["opportunity_type"] = self.opportunity_type
        return base_dict

class BusinessValueEvaluator(BaseEvaluator):
    """业务价值评估专家"""
    
    def __init__(self):
        super().__init__()
        self.metrics_config = {
            "effectiveness": {"weight": 0.5, "threshold": 0.7},
            "intervention_rate": {"weight": 0.3, "threshold": 0.3},  # 越低越好
            "conversion_rate": {"weight": 0.2, "threshold": 0.4}
        }
        
        # 业务目标定义
        self.business_goals = {
            "order_query": {
                "success_keywords": ["订单号", "物流状态", "预计送达", "已发货", "运单号"],
                "failure_keywords": ["未找到", "错误", "无法查询", "未能找到"]
            },
            "complaint": {
                "success_keywords": ["抱歉", "解决", "处理", "照片", "订单号", "损坏"],
                "failure_keywords": ["转人工", "无法处理", "需要人工", "无法解决"]
            },
            "product_comparison": {
                "success_keywords": ["对比", "参数", "推荐", "建议", "优势", "综合", "分析"],
                "failure_keywords": ["无法比较", "信息不足", "不清楚"]
            },
            "sales_data": {
                "success_keywords": ["销售额", "销售数据", "业绩", "统计"],
                "failure_keywords": ["无权限", "无法访问", "需要验证"]
            }
        }
    
    async def evaluate(self, logs: List[Dict]) -> Dict:
        """执行业务价值评估"""
        print("💰 开始业务价值评估...")
        
        # 清空前一次评估的问题
        self.clear_problems()
        
        # 解析对话日志
        conversations = self._parse_conversations(logs)
        
        # 计算各项指标
        effectiveness_metrics = await self._evaluate_effectiveness(conversations)
        intervention_metrics = await self._evaluate_intervention_rate(conversations)
        conversion_metrics = await self._evaluate_conversion_rate(conversations)
        
        # 标准化得分（人工干预率越低越好，需要反转）
        intervention_score = 1.0 - intervention_metrics.get("rate", 0.0)
        
        metrics = {
            "effectiveness": effectiveness_metrics["overall_score"],
            "intervention_rate": intervention_score,
            "conversion_rate": conversion_metrics["rate"]
        }
        
        overall_score = self._calculate_score(
            metrics,
            {k: v["weight"] for k, v in self.metrics_config.items()}
        )
        
        # 检查并添加整体问题
        self._add_overall_problems(metrics, effectiveness_metrics, intervention_metrics, conversion_metrics)
        
        # 打印所有问题
        self._print_all_problems()
        
        return {
            "dimension": "业务价值",
            "overall_score": overall_score,
            "metrics": metrics,
            "strengths": self._identify_strengths(metrics),
            "improvements": self._identify_improvements(metrics),
            "details": {
                "effectiveness": effectiveness_metrics,
                "intervention": intervention_metrics,
                "conversion": conversion_metrics
            }
        }
    
    def _add_overall_problems(self, metrics: Dict[str, float], 
                             effectiveness_metrics: Dict[str, Any],
                             intervention_metrics: Dict[str, Any],
                             conversion_metrics: Dict[str, Any]):
        """添加整体指标问题"""
        # 检查问题解决率
        if metrics.get("effectiveness", 0) < self.metrics_config["effectiveness"]["threshold"]:
            self.add_problem(ProblemType.EFFECTIVENESS.value, BusinessProblem(
                problem_type="整体问题解决率不足",
                score=metrics["effectiveness"],
                threshold=self.metrics_config["effectiveness"]["threshold"],
                deduction_items=[
                    f"问题解决率 {metrics['effectiveness']:.2f} 低于阈值 {self.metrics_config['effectiveness']['threshold']}",
                    f"总体解决率: {effectiveness_metrics.get('resolution_rate', 0):.2f}",
                    f"总对话数: {effectiveness_metrics.get('total_conversations', 0)}",
                    f"已解决对话: {effectiveness_metrics.get('solved_conversations', 0)}"
                ]
            ))
        
        # 检查人工干预率（注意：干预率越低越好，所以我们要检查反转后的分数）
        intervention_rate = 1.0 - metrics.get("intervention_rate", 0.0)
        if intervention_rate > self.metrics_config["intervention_rate"]["threshold"]:
            self.add_problem(ProblemType.INTERVENTION.value, BusinessProblem(
                problem_type="人工干预率过高",
                score=metrics["intervention_rate"],  # 这是反转后的分数
                threshold=0.7,  # 人工干预率越低越好，所以这里阈值是反转后的
                deduction_items=[
                    f"实际干预率 {intervention_rate:.2f} 高于阈值 {self.metrics_config['intervention_rate']['threshold']}",
                    f"干预对话数: {intervention_metrics.get('intervened_conversations', 0)}",
                    f"总对话数: {intervention_metrics.get('total_conversations', 0)}",
                    "需要提高自动化处理能力"
                ]
            ))
        
        # 检查转化率
        if metrics.get("conversion_rate", 0) < self.metrics_config["conversion_rate"]["threshold"]:
            self.add_problem(ProblemType.CONVERSION.value, BusinessProblem(
                problem_type="转化率不足",
                score=metrics["conversion_rate"],
                threshold=self.metrics_config["conversion_rate"]["threshold"],
                deduction_items=[
                    f"转化率 {metrics['conversion_rate']:.2f} 低于阈值 {self.metrics_config['conversion_rate']['threshold']}",
                    f"转化机会数: {conversion_metrics.get('opportunities', 0)}",
                    f"成功转化数: {conversion_metrics.get('conversions', 0)}",
                    "需要优化转化策略和话术"
                ]
            ))
    
    def _print_all_problems(self):
        """打印所有识别到的问题，包括详细的问题和回复"""
        problems = self.get_problems()
        
        print("\n" + "="*80)
        print("业务价值评估问题详情汇总")
        print("="*80)
        
        total_problems = 0
        
        # 打印各类问题
        for problem_type, problem_list in problems.items():
            if problem_list:
                total_problems += len(problem_list)
                
                # 根据问题类型显示不同的标题
                if problem_type == ProblemType.EFFECTIVENESS.value:
                    title = "问题解决率问题"
                elif problem_type == ProblemType.INTERVENTION.value:
                    title = "人工干预率问题"
                elif problem_type == ProblemType.CONVERSION.value:
                    title = "转化率问题"
                else:
                    title = f"{problem_type.upper()} 问题"
                
                print(f"\n🔴 {title} (共{len(problem_list)}个):")
                print("-"*80)
                
                for i, problem in enumerate(problem_list, 1):
                    print(f"\n{i}. {problem.problem_type}")
                    print(f"   得分: {problem.score:.2f} (阈值: {problem.threshold})")
                    
                    if hasattr(problem, 'conversation_type') and problem.conversation_type:
                        print(f"   对话类型: {problem.conversation_type}")
                    if hasattr(problem, 'session_id') and problem.session_id:
                        print(f"   会话ID: {problem.session_id}")
                    if hasattr(problem, 'opportunity_type') and problem.opportunity_type:
                        print(f"   机会类型: {problem.opportunity_type}")
                    
                    if problem.user_input:
                        print(f"   用户输入: {problem.user_input[:150]}{'...' if len(problem.user_input) > 150 else ''}")
                    if problem.assistant_response:
                        print(f"   助手回复: {problem.assistant_response[:150]}{'...' if len(problem.assistant_response) > 150 else ''}")
                    
                    if problem.deduction_items:
                        print(f"   扣分项:")
                        for deduction in problem.deduction_items:
                            print(f"     - {deduction}")
        
        if total_problems == 0:
            print("\n✅ 未发现业务价值问题")
            
        # 打印问题摘要
        self.print_problems_summary()
    
    def _parse_conversations(self, logs: List[Dict]) -> List[List[Dict]]:
        """解析对话日志 - 适配新的日志格式"""
        conversations = []
        
        for log in logs:
            # 每条日志是一个完整的对话（用户输入 + 助手回复）
            # 转换为内部使用的消息格式
            conversation = [
                {
                    "role": "user",
                    "content": log.get("user_input", ""),
                    "timestamp": log.get("timestamp", ""),
                    "session_id": log.get("session_id", "")
                },
                {
                    "role": "assistant",
                    "content": log.get("assistant_response", ""),
                    "timestamp": log.get("timestamp", ""),
                    "response_time_ms": log.get("response_time_ms", 0),
                    "metadata": log.get("metadata", {}),
                    "test_case": log.get("test_case", "")
                }
            ]
            conversations.append(conversation)
        
        return conversations
    
    async def _evaluate_effectiveness(self, conversations: List[List[Dict]]) -> Dict[str, Any]:
        """评估问题解决率"""
        print("  🎯 计算问题解决率...")
        
        if not conversations:
            return {
                "overall_score": 0.0,
                "resolution_rate": 0.0,
                "by_category": {},
                "total_conversations": 0,
                "solved_conversations": 0
            }
        
        # 分类统计解决情况
        category_stats = defaultdict(lambda: {"total": 0, "solved": 0})
        
        for conv in conversations:
            # 获取会话ID
            session_id = ""
            for msg in conv:
                if msg.get("role") == "user":
                    session_id = msg.get("session_id", "")
                    break
            
            # 判断对话类型
            conv_type = self._classify_conversation(conv)
            
            # 判断是否解决
            solved = self._check_if_solved(conv, conv_type)
            
            category_stats[conv_type]["total"] += 1
            if solved:
                category_stats[conv_type]["solved"] += 1
            else:
                # 添加未解决的问题
                user_input = ""
                assistant_response = ""
                for msg in conv:
                    if msg.get("role") == "user":
                        user_input = msg.get("content", "")
                    elif msg.get("role") == "assistant":
                        assistant_response = msg.get("content", "")
                
                self.add_problem(ProblemType.EFFECTIVENESS.value, BusinessProblem(
                    problem_type=f"{conv_type}类型问题未解决",
                    score=0.0,
                    threshold=0.7,
                    deduction_items=[
                        f"{conv_type}类型问题未能成功解决",
                        "助手回复可能未包含必要信息或解决方案"
                    ],
                    user_input=user_input,
                    assistant_response=assistant_response,
                    conversation_type=conv_type,
                    session_id=session_id
                ))
        
        # 计算总体解决率
        total_conversations = sum(stats["total"] for stats in category_stats.values())
        total_solved = sum(stats["solved"] for stats in category_stats.values())
        
        resolution_rate = total_solved / total_conversations if total_conversations > 0 else 0.0
        
        # 计算各类型解决率
        by_category = {}
        for cat, stats in category_stats.items():
            if stats["total"] > 0:
                cat_rate = stats["solved"] / stats["total"]
                by_category[cat] = {
                    "rate": cat_rate,
                    "total": stats["total"],
                    "solved": stats["solved"]
                }
                
                # 如果某类问题解决率低，添加问题
                if cat_rate < 0.6:
                    self.add_problem(ProblemType.EFFECTIVENESS.value, BusinessProblem(
                        problem_type=f"{cat}类型问题解决率低",
                        score=cat_rate,
                        threshold=0.7,
                        deduction_items=[
                            f"{cat}类型解决率 {cat_rate:.2f} 低于预期",
                            f"该类对话总数: {stats['total']}",
                            f"已解决数: {stats['solved']}"
                        ],
                        conversation_type=cat
                    ))
        
        return {
            "overall_score": resolution_rate,
            "resolution_rate": resolution_rate,
            "by_category": dict(by_category),
            "total_conversations": total_conversations,
            "solved_conversations": total_solved
        }
    
    async def _evaluate_intervention_rate(self, conversations: List[List[Dict]]) -> Dict[str, Any]:
        """评估人工干预率"""
        print("  🚨 计算人工干预率...")
        
        if not conversations:
            return {
                "rate": 0.0,
                "total_conversations": 0,
                "intervened_conversations": 0
            }
        
        intervened_count = 0
        
        for conv in conversations:
            if self._check_if_intervened(conv):
                intervened_count += 1
                
                # 获取会话信息
                session_id = ""
                user_input = ""
                assistant_response = ""
                for msg in conv:
                    if msg.get("role") == "user":
                        session_id = msg.get("session_id", "")
                        user_input = msg.get("content", "")
                    elif msg.get("role") == "assistant":
                        assistant_response = msg.get("content", "")
                
                # 添加人工干预问题
                conv_type = self._classify_conversation(conv)
                self.add_problem(ProblemType.INTERVENTION.value, BusinessProblem(
                    problem_type=f"需要人工干预的{conv_type}对话",
                    score=0.0,
                    threshold=0.7,
                    deduction_items=[
                        f"{conv_type}类型对话需要人工干预",
                        "助手未能完全处理用户需求",
                        "可能需要转接人工客服"
                    ],
                    user_input=user_input,
                    assistant_response=assistant_response,
                    conversation_type=conv_type,
                    session_id=session_id
                ))
        
        intervention_rate = intervened_count / len(conversations) if conversations else 0.0
        
        return {
            "rate": intervention_rate,
            "total_conversations": len(conversations),
            "intervened_conversations": intervened_count
        }
    
    async def _evaluate_conversion_rate(self, conversations: List[List[Dict]]) -> Dict[str, Any]:
        """评估转化率（如投诉转工单、咨询转购买等）"""
        print("  📈 计算转化率...")
        
        if not conversations:
            return {
                "rate": 0.0,
                "opportunities": 0,
                "conversions": 0
            }
        
        opportunities = 0
        conversions = 0
        
        for conv in conversations:
            # 识别转化机会
            if self._has_conversion_opportunity(conv):
                opportunities += 1
                
                # 检查是否转化
                if self._check_if_converted(conv):
                    conversions += 1
                else:
                    # 添加未转化的问题
                    session_id = ""
                    user_input = ""
                    assistant_response = ""
                    for msg in conv:
                        if msg.get("role") == "user":
                            session_id = msg.get("session_id", "")
                            user_input = msg.get("content", "")
                        elif msg.get("role") == "assistant":
                            assistant_response = msg.get("content", "")
                    
                    conv_type = self._classify_conversation(conv)
                    opportunity_type = self._identify_opportunity_type(conv)
                    
                    self.add_problem(ProblemType.CONVERSION.value, BusinessProblem(
                        problem_type=f"未成功转化的{conv_type}对话",
                        score=0.0,
                        threshold=0.7,
                        deduction_items=[
                            f"{conv_type}类型对话存在转化机会但未成功转化",
                            f"机会类型: {opportunity_type}",
                            "助手可能未提供足够的转化引导或解决方案"
                        ],
                        user_input=user_input,
                        assistant_response=assistant_response,
                        conversation_type=conv_type,
                        session_id=session_id,
                        opportunity_type=opportunity_type
                    ))
        
        conversion_rate = conversions / opportunities if opportunities > 0 else 0.0
        
        return {
            "rate": conversion_rate,
            "opportunities": opportunities,
            "conversions": conversions
        }
    
    def _identify_opportunity_type(self, conversation: List[Dict]) -> str:
        """识别转化机会类型"""
        conv_type = self._classify_conversation(conversation)
        
        if conv_type == "complaint":
            return "投诉转工单"
        elif conv_type == "product_comparison":
            return "咨询转购买"
        elif conv_type == "order_query":
            return "查询转复购"
        else:
            return "一般转化"
    
    def _classify_conversation(self, conversation: List[Dict]) -> str:
        """对话分类"""
        # 获取用户输入和助手回复
        user_input = ""
        assistant_response = ""
        
        for msg in conversation:
            if msg.get("role") == "user":
                user_input = msg.get("content", "").lower()
            elif msg.get("role") == "assistant":
                assistant_response = msg.get("content", "").lower()
        
        # 结合用户输入和助手回复进行分类
        combined_text = user_input + " " + assistant_response
        
        if re.search(r"订单.*查询|物流.*哪里|订单.*到哪里", user_input):
            return "order_query"
        elif re.search(r"产品.*比较|哪个.*更好|拍照.*更好|a手机.*b手机", user_input):
            return "product_comparison"
        elif re.search(r"投诉|损坏|不满意|质量问题", user_input):
            return "complaint"
        elif re.search(r"销售.*数据|业绩.*查询|卖了多少钱", user_input):
            return "sales_data"
        else:
            return "general"
    
    def _check_if_solved(self, conversation: List[Dict], conv_type: str) -> bool:
        """检查问题是否解决"""
        if conv_type not in self.business_goals:
            # 对于未知类型，检查助手是否有提供有用信息
            assistant_responses = [
                msg.get("content", "") for msg in conversation 
                if msg.get("role") == "assistant"
            ]
            return len(assistant_responses) > 0 and len(assistant_responses[-1]) > 50
        
        goal = self.business_goals[conv_type]
        success_keywords = goal["success_keywords"]
        failure_keywords = goal["failure_keywords"]
        
        # 获取助手的回复
        assistant_responses = [
            msg.get("content", "") for msg in conversation 
            if msg.get("role") == "assistant"
        ]
        
        if not assistant_responses:
            return False
        
        last_response = assistant_responses[-1].lower()
        
        # 检查是否包含成功关键词且不包含失败关键词
        has_success = any(keyword.lower() in last_response for keyword in success_keywords)
        has_failure = any(keyword.lower() in last_response for keyword in failure_keywords)
        
        # 对于投诉处理，还需要检查是否要求提供信息（这是正确的处理流程）
        if conv_type == "complaint":
            # 检查是否要求提供订单号、照片等信息
            info_requested = any(keyword in last_response for keyword in ["订单号", "照片", "具体情况"])
            return info_requested and not has_failure
        
        # 对于销售数据查询，检查是否提供了验证指引
        if conv_type == "sales_data":
            # 检查是否提供了正确的权限指引
            guidance_provided = any(keyword in last_response for keyword in ["登录系统", "权限", "身份验证"])
            return guidance_provided and not has_failure
        
        return has_success and not has_failure
    
    def _check_if_intervened(self, conversation: List[Dict]) -> bool:
        """检查是否有人工干预"""
        # 检查是否有转人工、人工客服等关键词
        intervention_keywords = ["转人工", "人工客服", "专员处理", "高级客服", "联系我们", "联系客服"]
        
        for msg in conversation:
            content = msg.get("content", "").lower()
            if any(keyword in content for keyword in intervention_keywords):
                return True
        
        return False
    
    def _has_conversion_opportunity(self, conversation: List[Dict]) -> bool:
        """识别是否有转化机会"""
        opportunity_keywords = ["投诉", "不满意", "咨询", "购买", "下单", "比较", "推荐"]
        
        user_messages = [msg for msg in conversation if msg.get("role") == "user"]
        if not user_messages:
            return False
        
        user_text = " ".join([msg.get("content", "") for msg in user_messages])
        return any(keyword in user_text for keyword in opportunity_keywords)
    
    def _check_if_converted(self, conversation: List[Dict]) -> bool:
        """检查是否转化成功"""
        # 根据对话类型定义不同的转化标准
        conv_type = self._classify_conversation(conversation)
        
        assistant_responses = [
            msg.get("content", "") for msg in conversation 
            if msg.get("role") == "assistant"
        ]
        
        if not assistant_responses:
            return False
        
        last_response = assistant_responses[-1].lower()
        
        if conv_type == "complaint":
            # 投诉转化：是否创建了处理流程
            conversion_keywords = ["处理", "解决", "记录", "跟进", "反馈"]
            return any(keyword in last_response for keyword in conversion_keywords)
        
        elif conv_type == "product_comparison":
            # 产品比较转化：是否提供了明确的推荐
            conversion_keywords = ["推荐", "建议", "更适合", "选择", "购买"]
            return any(keyword in last_response for keyword in conversion_keywords)
        
        else:
            # 默认转化标准
            conversion_keywords = ["为您", "帮您", "可以", "立即", "马上", "安排"]
            return any(keyword in last_response for keyword in conversion_keywords)
    
    def _identify_strengths(self, metrics: Dict[str, float]) -> List[str]:
        """识别优点"""
        strengths = []
        
        if metrics.get("effectiveness", 0) > 0.8:
            strengths.append("问题解决率高，业务目标达成度好")
        elif metrics.get("effectiveness", 0) > 0.6:
            strengths.append("问题解决率良好")
            
        if metrics.get("intervention_rate", 0) > 0.8:  # 干预率低是优点
            strengths.append("人工干预率低，自动化程度高")
        elif metrics.get("intervention_rate", 0) > 0.7:
            strengths.append("人工干预率控制较好")
            
        if metrics.get("conversion_rate", 0) > 0.5:
            strengths.append("转化率高，业务价值显著")
        elif metrics.get("conversion_rate", 0) > 0.3:
            strengths.append("转化率表现良好")
        
        if not strengths:
            strengths.append("基本业务功能正常")
        
        return strengths
    
    def _identify_improvements(self, metrics: Dict[str, float]) -> List[str]:
        """识别改进点"""
        improvements = []
        
        if metrics.get("effectiveness", 0) < 0.6:
            improvements.append("需要提高问题解决率，优化解决方案")
        elif metrics.get("effectiveness", 0) < 0.8:
            improvements.append("可进一步提升问题解决率")
            
        if metrics.get("intervention_rate", 0) < 0.7:  # 干预率高需要改进
            improvements.append("需要降低人工干预率，提升自动化能力")
        elif metrics.get("intervention_rate", 0) < 0.8:
            improvements.append("人工干预率仍有优化空间")
            
        if metrics.get("conversion_rate", 0) < 0.3:
            improvements.append("需要提升转化率，优化转化策略")
        elif metrics.get("conversion_rate", 0) < 0.5:
            improvements.append("转化率有提升潜力")
        
        return improvements
