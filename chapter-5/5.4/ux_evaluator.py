"""
用户体验评估智能体 - ux_evaluator.py
评估响应时延、用户满意度等指标
"""
import time
from typing import Dict, List, Any
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
from base_evaluator import BaseEvaluator, BaseProblem, ProblemType

@dataclass
class UserSession:
    """用户会话数据"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: datetime = None
    user_input: str = ""
    assistant_response: str = ""
    response_time_ms: float = 0.0
    metadata: Dict = None
    test_case: str = ""
    user_rating: float = None
    completed: bool = True  # 假设每条记录都是完整的对话
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class UXProblem(BaseProblem):
    """用户体验问题详情"""
    session_id: str = ""
    user_id: str = ""
    response_time_ms: float = 0.0
    user_sentiment_score: float = 0.0
    response_quality_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（扩展基类方法）"""
        base_dict = super().to_dict()
        if self.session_id:
            base_dict["session_id"] = self.session_id
        if self.user_id:
            base_dict["user_id"] = self.user_id
        if self.response_time_ms:
            base_dict["response_time_ms"] = self.response_time_ms
        if self.user_sentiment_score:
            base_dict["user_sentiment_score"] = self.user_sentiment_score
        if self.response_quality_score:
            base_dict["response_quality_score"] = self.response_quality_score
        return base_dict

class UserExperienceEvaluator(BaseEvaluator):
    """用户体验评估专家"""
    
    def __init__(self):
        super().__init__()
        self.metrics_config = {
            "efficiency": {"weight": 0.4, "threshold": 0.8},
            "satisfaction": {"weight": 0.6, "threshold": 0.75}
        }
        
        # 响应时间阈值定义（单位：毫秒）
        self.response_time_thresholds = {
            "excellent": 2000,  # 2秒以内
            "good": 5000,       # 5秒以内
            "acceptable": 10000, # 10秒以内
            "poor": 20000,      # 20秒以内
        }
        
        # 会话数据存储
        self.sessions: Dict[str, UserSession] = {}
        
    async def evaluate(self, logs: List[Dict]) -> Dict:
        """执行用户体验评估"""
        print("😊 开始用户体验评估...")
        
        # 清空前一次评估的问题
        self.clear_problems()
        
        # 从日志中提取会话数据
        sessions = self._extract_sessions(logs)
        
        # 计算各项指标
        efficiency_metrics = await self._evaluate_efficiency(sessions)
        satisfaction_metrics = await self._evaluate_satisfaction(sessions)
        
        # 计算综合得分
        metrics = {
            "efficiency": efficiency_metrics["overall_score"],
            "satisfaction": satisfaction_metrics["overall_score"]
        }
        
        overall_score = self._calculate_score(
            metrics,
            {k: v["weight"] for k, v in self.metrics_config.items()}
        )
        
        # 检查并添加整体问题
        self._add_overall_problems(metrics, efficiency_metrics, satisfaction_metrics)
        
        # 打印所有问题
        self._print_all_problems()
        
        return {
            "dimension": "用户体验",
            "overall_score": overall_score,
            "metrics": metrics,
            "strengths": self._identify_strengths(metrics),
            "improvements": self._identify_improvements(metrics),
            "details": {
                "efficiency": efficiency_metrics,
                "satisfaction": satisfaction_metrics
            }
        }
    
    def _add_overall_problems(self, metrics: Dict[str, float],
                             efficiency_metrics: Dict[str, Any],
                             satisfaction_metrics: Dict[str, Any]):
        """添加整体指标问题"""
        # 检查效率指标
        if metrics.get("efficiency", 0) < self.metrics_config["efficiency"]["threshold"]:
            self.add_problem(ProblemType.EFFICIENCY.value, UXProblem(
                problem_type="整体效率不足",
                score=metrics["efficiency"],
                threshold=self.metrics_config["efficiency"]["threshold"],
                deduction_items=[
                    f"效率得分 {metrics['efficiency']:.2f} 低于阈值 {self.metrics_config['efficiency']['threshold']}",
                    f"P50响应时间: {efficiency_metrics.get('p50_response_time', 0):.0f}ms",
                    f"P95响应时间: {efficiency_metrics.get('p95_response_time', 0):.0f}ms",
                    f"会话完成率: {efficiency_metrics.get('completion_rate', 0):.2f}",
                    "响应速度或完成率需要优化"
                ]
            ))
        
        # 检查满意度指标
        if metrics.get("satisfaction", 0) < self.metrics_config["satisfaction"]["threshold"]:
            self.add_problem(ProblemType.SATISFACTION.value, UXProblem(
                problem_type="整体满意度不足",
                score=metrics["satisfaction"],
                threshold=self.metrics_config["satisfaction"]["threshold"],
                deduction_items=[
                    f"满意度得分 {metrics['satisfaction']:.2f} 低于阈值 {self.metrics_config['satisfaction']['threshold']}",
                    f"平均用户评分: {satisfaction_metrics.get('avg_user_rating', 0):.2f}",
                    f"情感分析得分: {satisfaction_metrics.get('sentiment_score', 0):.2f}",
                    f"响应质量得分: {satisfaction_metrics.get('response_quality_score', 0):.2f}",
                    "需要提升用户满意度和情感体验"
                ]
            ))
    
    def _print_all_problems(self):
        """打印所有识别到的问题，包括详细的问题和回复"""
        problems = self.get_problems()
        
        print("\n" + "="*80)
        print("用户体验评估问题详情汇总")
        print("="*80)
        
        total_problems = 0
        
        # 打印各类问题
        for problem_type, problem_list in problems.items():
            if problem_list:
                total_problems += len(problem_list)
                
                # 根据问题类型显示不同的标题
                if problem_type == ProblemType.EFFICIENCY.value:
                    title = "效率问题"
                elif problem_type == ProblemType.SATISFACTION.value:
                    title = "满意度问题"
                elif problem_type == ProblemType.RESPONSE_TIME.value:
                    title = "响应时间问题"
                else:
                    title = f"{problem_type.upper()} 问题"
                
                print(f"\n🔴 {title} (共{len(problem_list)}个):")
                print("-"*80)
                
                for i, problem in enumerate(problem_list, 1):
                    print(f"\n{i}. {problem.problem_type}")
                    print(f"   得分: {problem.score:.2f} (阈值: {problem.threshold})")
                    
                    if hasattr(problem, 'session_id') and problem.session_id:
                        print(f"   会话ID: {problem.session_id}")
                    if hasattr(problem, 'user_id') and problem.user_id:
                        print(f"   用户ID: {problem.user_id}")
                    if hasattr(problem, 'response_time_ms') and problem.response_time_ms > 0:
                        print(f"   响应时间: {problem.response_time_ms:.0f}ms")
                    if hasattr(problem, 'user_sentiment_score') and problem.user_sentiment_score:
                        print(f"   用户情感分: {problem.user_sentiment_score:.2f}")
                    if hasattr(problem, 'response_quality_score') and problem.response_quality_score:
                        print(f"   响应质量分: {problem.response_quality_score:.2f}")
                    
                    if problem.user_input:
                        print(f"   用户输入: {problem.user_input[:150]}{'...' if len(problem.user_input) > 150 else ''}")
                    if problem.assistant_response:
                        print(f"   助手回复: {problem.assistant_response[:150]}{'...' if len(problem.assistant_response) > 150 else ''}")
                    
                    if problem.deduction_items:
                        print(f"   扣分项:")
                        for deduction in problem.deduction_items:
                            print(f"     - {deduction}")
        
        if total_problems == 0:
            print("\n✅ 未发现用户体验问题")
            
        # 打印问题摘要
        self.print_problems_summary()
    
    def _extract_sessions(self, logs: List[Dict]) -> List[UserSession]:
        """从日志中提取用户会话 - 适配新的日志格式"""
        sessions = []
        
        for log in logs:
            # 解析时间戳
            timestamp_str = log.get("timestamp", "")
            try:
                if "T" in timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now()
            except:
                timestamp = datetime.now()
            
            # 创建会话对象
            session = UserSession(
                session_id=log.get("session_id", f"session_{len(sessions)}"),
                user_id=log.get("user_id", "anonymous"),
                start_time=timestamp,
                end_time=timestamp,
                user_input=log.get("user_input", ""),
                assistant_response=log.get("assistant_response", ""),
                response_time_ms=log.get("response_time_ms", 0),
                metadata=log.get("metadata", {}),
                test_case=log.get("test_case", ""),
                user_rating=self._extract_user_rating(log),
                completed=True  # 假设每条记录都是完整的对话
            )
            
            sessions.append(session)
        
        return sessions
    
    def _extract_user_rating(self, log: Dict) -> float:
        """从日志中提取用户评分"""
        # 这里可以添加逻辑从metadata或其他字段提取用户评分
        # 暂时使用默认值，实际应用中可以根据需要修改
        metadata = log.get("metadata", {})
        if "user_rating" in metadata:
            return float(metadata["user_rating"])
        return None  # 或者返回一个默认评分，如0.8
    
    async def _evaluate_efficiency(self, sessions: List[UserSession]) -> Dict[str, Any]:
        """评估效率（响应时延、会话完成率）"""
        print("  ⚡ 计算效率指标...")
        
        if not sessions:
            return {
                "overall_score": 0.0,
                "p50_response_time": 0.0,
                "p95_response_time": 0.0,
                "completion_rate": 0.0,
                "total_sessions": 0,
                "response_time_stats": {}
            }
        
        # 收集所有响应时间
        all_response_times = [s.response_time_ms for s in sessions if s.response_time_ms > 0]
        
        # 如果没有任何响应时间数据
        if not all_response_times:
            self.add_problem(ProblemType.EFFICIENCY.value, UXProblem(
                problem_type="缺乏响应时间数据",
                score=0.0,
                threshold=0.7,
                deduction_items=[
                    "日志中未包含响应时间数据",
                    "无法准确评估系统效率"
                ]
            ))
            return {
                "overall_score": 0.5,  # 默认中等分数
                "p50_response_time": 0.0,
                "p95_response_time": 0.0,
                "completion_rate": 0.0,
                "total_sessions": len(sessions),
                "completed_sessions": sum(1 for s in sessions if s.completed),
                "response_time_stats": {}
            }
        
        # 计算响应时间统计
        response_time_stats = {}
        if all_response_times:
            response_time_stats = {
                "min": float(np.min(all_response_times)),
                "max": float(np.max(all_response_times)),
                "mean": float(np.mean(all_response_times)),
                "std": float(np.std(all_response_times))
            }
            
            # 计算百分位数响应时间
            p50 = np.percentile(all_response_times, 50)
            p95 = np.percentile(all_response_times, 95)
        else:
            p50 = p95 = 0.0
        
        # 检查并添加响应时间过长的问题
        for session in sessions:
            if session.response_time_ms > self.response_time_thresholds["poor"]:
                self.add_problem(ProblemType.RESPONSE_TIME.value, UXProblem(
                    problem_type="响应时间过长",
                    score=0.0,
                    threshold=0.7,
                    deduction_items=[
                        f"响应时间 {session.response_time_ms:.0f}ms 超过可接受阈值",
                        f"用户等待时间过长，影响体验",
                        f"建议优化系统性能或网络延迟"
                    ],
                    user_input=session.user_input,
                    assistant_response=session.assistant_response,
                    session_id=session.session_id,
                    user_id=session.user_id,
                    response_time_ms=session.response_time_ms
                ))
        
        # 计算会话完成率
        completed_sessions = sum(1 for s in sessions if s.completed)
        completion_rate = completed_sessions / len(sessions) if sessions else 0.0
        
        # 检查会话完成率问题
        if completion_rate < 0.9:
            self.add_problem(ProblemType.EFFICIENCY.value, UXProblem(
                problem_type="会话完成率较低",
                score=completion_rate,
                threshold=0.9,
                deduction_items=[
                    f"会话完成率 {completion_rate:.2f} 低于预期",
                    f"总会话数: {len(sessions)}",
                    f"已完成会话: {completed_sessions}",
                    "可能存在用户中途放弃或系统错误"
                ]
            ))
        
        # 标准化评分
        # 响应时间越短越好，使用分段函数评分
        if p50 <= self.response_time_thresholds["excellent"]:  # 2秒以内
            p50_score = 1.0
        elif p50 <= self.response_time_thresholds["good"]:  # 5秒以内
            p50_score = 0.8
        elif p50 <= self.response_time_thresholds["acceptable"]:  # 10秒以内
            p50_score = 0.6
        else:
            p50_score = max(0, 1 - p50 / 30000)  # 超过10秒线性下降
        
        if p95 <= self.response_time_thresholds["good"]:  # 5秒以内
            p95_score = 1.0
        elif p95 <= self.response_time_thresholds["acceptable"]:  # 10秒以内
            p95_score = 0.8
        elif p95 <= self.response_time_thresholds["poor"]:  # 20秒以内
            p95_score = 0.6
        else:
            p95_score = max(0, 1 - p95 / 60000)  # 超过20秒线性下降
        
        # 效率综合得分
        efficiency_score = 0.4 * p50_score + 0.3 * p95_score + 0.3 * completion_rate
        
        return {
            "overall_score": efficiency_score,
            "p50_response_time": float(p50),
            "p95_response_time": float(p95),
            "completion_rate": completion_rate,
            "total_sessions": len(sessions),
            "completed_sessions": completed_sessions,
            "response_time_stats": response_time_stats
        }
    
    async def _evaluate_satisfaction(self, sessions: List[UserSession]) -> Dict[str, Any]:
        """评估满意度（用户评分、情感分析）"""
        print("  😊 计算满意度指标...")
        
        if not sessions:
            return {
                "overall_score": 0.0,
                "avg_user_rating": 0.0,
                "sentiment_score": 0.0,
                "rated_sessions": 0,
                "response_quality_score": 0.0
            }
        
        # 计算用户评分平均值（如果有的话）
        user_ratings = [s.user_rating for s in sessions if s.user_rating is not None]
        
        if not user_ratings:
            # 如果没有用户评分数据，添加问题
            self.add_problem(ProblemType.SATISFACTION.value, UXProblem(
                problem_type="缺乏用户评分数据",
                score=0.0,
                threshold=0.7,
                deduction_items=[
                    "日志中未包含用户评分数据",
                    "无法准确评估用户满意度",
                    "建议在系统中添加用户反馈机制"
                ]
            ))
        
        avg_rating = np.mean(user_ratings) if user_ratings else 0.0
        
        # 检查低分评价
        low_ratings = [r for r in user_ratings if r is not None and r < 3.0]
        for low_rating in low_ratings:
            # 找到对应的会话
            for session in sessions:
                if session.user_rating == low_rating:
                    self.add_problem(ProblemType.SATISFACTION.value, UXProblem(
                        problem_type="用户评分过低",
                        score=low_rating/5.0,  # 转换为0-1的分数
                        threshold=0.6,
                        deduction_items=[
                            f"用户评分: {low_rating:.1f}/5.0",
                            "用户对服务不满意",
                            "需要分析具体原因并改进"
                        ],
                        user_input=session.user_input,
                        assistant_response=session.assistant_response,
                        session_id=session.session_id,
                        user_id=session.user_id
                    ))
                    break
        
        # 分析对话情感
        sentiment_scores = []
        response_quality_scores = []
        
        for session in sessions:
            # 分析用户输入的情感
            user_sentiment = self._analyze_user_sentiment(session.user_input)
            sentiment_scores.append(user_sentiment)
            
            # 如果用户情感负面，添加问题
            if user_sentiment < 0.3:
                self.add_problem(ProblemType.SATISFACTION.value, UXProblem(
                    problem_type="用户情感负面",
                    score=user_sentiment,
                    threshold=0.5,
                    deduction_items=[
                        f"用户情感分析得分: {user_sentiment:.2f}",
                        "用户表达不满、愤怒或紧急情绪",
                        "需要关注用户情绪并改进响应"
                    ],
                    user_input=session.user_input,
                    assistant_response=session.assistant_response,
                    session_id=session.session_id,
                    user_id=session.user_id,
                    user_sentiment_score=user_sentiment
                ))
            
            # 评估助手响应质量
            response_quality = self._evaluate_response_quality(session)
            response_quality_scores.append(response_quality)
            
            # 如果响应质量低，添加问题
            if response_quality < 0.6:
                self.add_problem(ProblemType.SATISFACTION.value, UXProblem(
                    problem_type="响应质量不足",
                    score=response_quality,
                    threshold=0.7,
                    deduction_items=[
                        f"响应质量得分: {response_quality:.2f}",
                        "助手回复可能不够相关、完整或有帮助",
                        "需要提升响应质量和专业性"
                    ],
                    user_input=session.user_input,
                    assistant_response=session.assistant_response,
                    session_id=session.session_id,
                    user_id=session.user_id,
                    response_quality_score=response_quality
                ))
        
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.5
        avg_response_quality = np.mean(response_quality_scores) if response_quality_scores else 0.5
        
        # 如果没有用户评分，主要依赖情感分析和响应质量
        if user_ratings:
            satisfaction_score = 0.4 * (avg_rating/5.0) + 0.3 * avg_sentiment + 0.3 * avg_response_quality
        else:
            satisfaction_score = 0.6 * avg_sentiment + 0.4 * avg_response_quality
        
        return {
            "overall_score": satisfaction_score,
            "avg_user_rating": avg_rating,
            "sentiment_score": avg_sentiment,
            "rated_sessions": len(user_ratings),
            "total_sessions": len(sessions),
            "response_quality_score": avg_response_quality
        }
    
    def _analyze_user_sentiment(self, user_input: str) -> float:
        """分析用户输入情感"""
        positive_keywords = ["谢谢", "很好", "满意", "不错", "感谢", "帮到", "请问", "您好", "好的", "明白了"]
        negative_keywords = ["差", "糟糕", "生气", "投诉", "不满意", "失望", "损坏", "问题", "错误", "垃圾", "太差", "失望"]
        urgent_keywords = ["紧急", "立即", "马上", "尽快", "赶紧", "着急", "急", "快点"]
        
        user_input_lower = user_input.lower()
        
        positive_count = sum(1 for word in positive_keywords if word in user_input_lower)
        negative_count = sum(1 for word in negative_keywords if word in user_input_lower)
        urgent_count = sum(1 for word in urgent_keywords if word in user_input_lower)
        
        # 如果有紧急词汇，情感分数会降低（用户可能着急）
        urgent_factor = 0.8 if urgent_count > 0 else 1.0
        
        total = positive_count + negative_count
        if total == 0:
            # 如果没有明显情感词，默认中性
            return 0.5 * urgent_factor
        
        # 计算基础情感分数
        base_sentiment = positive_count / total
        
        # 调整情感分数（负向词权重更高）
        if negative_count > 0:
            adjusted_sentiment = base_sentiment * 0.7  # 负向词有更强的负面影响
        else:
            adjusted_sentiment = base_sentiment
        
        return min(1.0, adjusted_sentiment * urgent_factor)
    
    def _evaluate_response_quality(self, session: UserSession) -> float:
        """评估助手响应质量"""
        response = session.assistant_response.lower()
        user_input = session.user_input.lower()
        
        quality_score = 0.5  # 基础分数
        
        # 1. 检查响应是否相关
        if self._check_response_relevance(response, user_input):
            quality_score += 0.2
        else:
            # 如果响应不相关，分数会大幅降低
            quality_score -= 0.3
        
        # 2. 检查响应是否完整
        if len(response) > 50 and len(response) < 1000:  # 响应长度适中
            quality_score += 0.1
        elif len(response) <= 30:  # 响应过短
            quality_score -= 0.1
        
        # 3. 检查是否有结构化的信息
        if any(marker in response for marker in ["**", "- ", "1.", "2.", "3.", "首先", "其次", "最后"]):
            quality_score += 0.1
        
        # 4. 检查是否有明确的行动指引
        if any(action in response for action in ["您可以", "请提供", "建议您", "需要您", "请按照", "请点击"]):
            quality_score += 0.1
        
        # 5. 检查是否有礼貌用语
        if any(polite in response for polite in ["抱歉", "感谢", "请", "您好", "谢谢", "对不起", "不好意思"]):
            quality_score += 0.05
        
        # 6. 检查是否有提供进一步帮助
        if any(offer in response for offer in ["随时告诉我", "需要帮助", "可以帮您", "其他问题", "还有疑问"]):
            quality_score += 0.05
        
        return max(0.0, min(1.0, quality_score))
    
    def _check_response_relevance(self, response: str, user_input: str) -> bool:
        """检查响应相关性"""
        # 简单关键词匹配检查
        relevance_keywords = []
        
        if "订单" in user_input or "物流" in user_input or "发货" in user_input:
            relevance_keywords = ["订单", "物流", "发货", "快递", "运单", "物流信息", "订单号"]
        elif "拍照" in user_input or "比较" in user_input or "哪个好" in user_input:
            relevance_keywords = ["像素", "拍照", "对比", "建议", "推荐", "优势", "特点", "参数"]
        elif "投诉" in user_input or "损坏" in user_input or "问题" in user_input:
            relevance_keywords = ["抱歉", "处理", "解决", "订单号", "照片", "情况", "反馈"]
        elif "销售" in user_input or "业绩" in user_input or "数据" in user_input:
            relevance_keywords = ["销售", "数据", "权限", "登录", "验证", "系统", "查看"]
        
        if not relevance_keywords:
            return True  # 如果没有特定关键词，假设相关
        
        # 检查响应中是否包含相关关键词
        return any(keyword in response for keyword in relevance_keywords)
    
    def _identify_strengths(self, metrics: Dict[str, float]) -> List[str]:
        """识别优点"""
        strengths = []
        
        if metrics.get("efficiency", 0) > 0.85:
            strengths.append("响应速度快，用户体验流畅")
        elif metrics.get("efficiency", 0) > 0.7:
            strengths.append("响应效率良好")
            
        if metrics.get("satisfaction", 0) > 0.85:
            strengths.append("用户满意度高，情感体验积极")
        elif metrics.get("satisfaction", 0) > 0.7:
            strengths.append("用户满意度良好")
        
        if not strengths:
            if metrics.get("efficiency", 0) > 0.5 or metrics.get("satisfaction", 0) > 0.5:
                strengths.append("用户体验基本合格")
        
        return strengths
    
    def _identify_improvements(self, metrics: Dict[str, float]) -> List[str]:
        """识别改进点"""
        improvements = []
        
        if metrics.get("efficiency", 0) < 0.6:
            improvements.append("需要优化响应速度，减少用户等待时间")
        elif metrics.get("efficiency", 0) < 0.8:
            improvements.append("响应速度有优化空间")
            
        if metrics.get("satisfaction", 0) < 0.6:
            improvements.append("需要提升用户满意度，改善对话体验")
        elif metrics.get("satisfaction", 0) < 0.75:
            improvements.append("用户满意度可以进一步提升")
        
        return improvements
