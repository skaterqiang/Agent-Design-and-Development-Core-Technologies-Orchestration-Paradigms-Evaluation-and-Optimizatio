# base_evaluator.py

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import os
from enum import Enum

class ProblemType(Enum):
    """问题类型枚举"""
    ROBUSTNESS = "robustness"
    SECURITY = "security"
    USABILITY = "usability"
    EFFECTIVENESS = "effectiveness"  # 业务价值评估 - 问题解决率
    INTERVENTION = "intervention"    # 业务价值评估 - 人工干预率
    CONVERSION = "conversion"        # 业务价值评估 - 转化率
    EFFICIENCY = "efficiency"        # 用户体验评估 - 效率
    SATISFACTION = "satisfaction"    # 用户体验评估 - 满意度
    RESPONSE_TIME = "response_time"  # 用户体验评估 - 响应时间问题
    FUNCTIONAL_ACCURACY = "functional_accuracy"      # 功能性能评估 - 准确性
    FUNCTIONAL_RELEVANCE = "functional_relevance"    # 功能性能评估 - 相关性
    FUNCTIONAL_COMPLETENESS = "functional_completeness"  # 功能性能评估 - 完整性
    FUNCTIONAL_EMBEDDING = "functional_embedding"    # 功能性能评估 - 嵌入模型问题

@dataclass
class BaseProblem:
    """问题基类"""
    problem_type: str
    score: float
    threshold: float
    deduction_items: List[str] = field(default_factory=list)
    user_input: str = ""
    assistant_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "problem_type": self.problem_type,
            "score": self.score,
            "threshold": self.threshold,
            "deduction_items": self.deduction_items,
            "user_input": self.user_input[:200] if self.user_input else "",
            "assistant_response": self.assistant_response[:200] if self.assistant_response else ""
        }

# 各职能评估专家基类
class BaseEvaluator:
    """评估专家基类"""
    
    def __init__(self):
        self.model_name = "qwen-max"
        self.api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        
        # 统一的问题存储
        self._all_problems: Dict[str, List[BaseProblem]] = {}
        # 初始化所有问题类型
        for problem_type in ProblemType:
            self._all_problems[problem_type.value] = []
    
    async def evaluate(self, logs: List[Dict]) -> Dict:
        """评估方法（需子类实现）"""
        raise NotImplementedError
    
    def _calculate_score(self, metrics: Dict[str, float], weights: Dict[str, float]) -> float:
        """计算加权得分"""
        if not metrics:
            return 0.0
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(metrics.get(k, 0) * weights.get(k, 0) for k in weights)
        return weighted_sum / total_weight
    
    # 统一的问题管理方法
    
    def add_problem(self, problem_type: str, problem: BaseProblem):
        """添加问题到指定类别"""
        if problem_type not in self._all_problems:
            self._all_problems[problem_type] = []
        self._all_problems[problem_type].append(problem)
    
    def get_problems(self, problem_type: Optional[str] = None) -> Dict[str, List[BaseProblem]]:
        """获取问题
        
        Args:
            problem_type: 问题类型，如果为None则返回所有问题
            
        Returns:
            问题字典，键为问题类型，值为问题列表
        """
        if problem_type:
            return {problem_type: self._all_problems.get(problem_type, [])}
        return self._all_problems.copy()
    
    def get_problems_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取问题摘要统计"""
        summary = {}
        for problem_type, problems in self._all_problems.items():
            if problems:
                avg_score = sum(p.score for p in problems) / len(problems)
                summary[problem_type] = {
                    "count": len(problems),
                    "avg_score": avg_score,
                    "min_score": min(p.score for p in problems) if problems else 0,
                    "max_score": max(p.score for p in problems) if problems else 0,
                    "serious_problems": [p for p in problems if p.score < p.threshold]
                }
        return summary
    
    def clear_problems(self):
        """清空所有问题"""
        for problem_type in self._all_problems:
            self._all_problems[problem_type] = []
    
    def has_serious_problems(self, threshold: float = 0.7) -> bool:
        """检查是否有严重问题（得分低于阈值）"""
        for problems in self._all_problems.values():
            for problem in problems:
                if problem.score < threshold:
                    return True
        return False
    
    def get_total_problems_count(self) -> int:
        """获取问题总数"""
        return sum(len(problems) for problems in self._all_problems.values())
    
    def get_problems_by_severity(self, severity_threshold: float = 0.7) -> Dict[str, List[BaseProblem]]:
        """按严重程度筛选问题
        
        Args:
            severity_threshold: 严重程度阈值，得分低于此阈值的问题被认为是严重的
            
        Returns:
            按问题类型分组的严重问题
        """
        severe_problems = {}
        for problem_type, problems in self._all_problems.items():
            severe = [p for p in problems if p.score < severity_threshold]
            if severe:
                severe_problems[problem_type] = severe
        return severe_problems
    
    def print_problems_summary(self):
        """打印问题摘要"""
        summary = self.get_problems_summary()
        
        print("\n" + "="*80)
        print("问题摘要统计")
        print("="*80)
        
        if not any(summary.values()):
            print("✅ 未发现任何问题")
            print("="*80)
            return
        
        for problem_type, stats in summary.items():
            if stats["count"] > 0:
                print(f"\n{problem_type.upper()} 问题:")
                print(f"  问题数量: {stats['count']}")
                print(f"  平均得分: {stats['avg_score']:.2f}")
                print(f"  最低得分: {stats['min_score']:.2f}")
                print(f"  最高得分: {stats['max_score']:.2f}")
                print(f"  严重问题: {len(stats['serious_problems'])}个")
        
        print("="*80)
    
    def export_problems(self, include_details: bool = True) -> Dict[str, Any]:
        """导出问题数据
        
        Args:
            include_details: 是否包含详细的问题信息
            
        Returns:
            问题数据字典
        """
        export_data = {
            "summary": self.get_problems_summary(),
            "total_problems": self.get_total_problems_count(),
            "has_serious_problems": self.has_serious_problems()
        }
        
        if include_details:
            export_data["detailed_problems"] = {
                problem_type: [p.to_dict() for p in problems]
                for problem_type, problems in self._all_problems.items()
                if problems
            }
        
        return export_data
