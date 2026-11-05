"""
功能性能评估智能体 - functional_evaluator.py
1. 嵌入模型加载：优先尝试加载本地 Qwen3-Embedding-0.6B，失败则回退到在线模型。
2. 保持直接调用 customer_service.CustomerServiceAgent 的逻辑。
"""
import asyncio
import re
import os
import sys
import json
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import jieba
from rouge import Rouge
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass, field
from base_evaluator import BaseEvaluator, BaseProblem, ProblemType

# -------------------------------------------------------------------------
# 尝试导入业务系统的智能体类和数据
# -------------------------------------------------------------------------
try:
    # 假设 customer_service.py 在当前目录或 python path 中
    from customer_service import (
        CustomerServiceAgent, 
        ORDER_DATABASE, 
        SALES_DATABASE, 
        USER_PERMISSIONS
    )
    print("✅ 成功导入 CustomerServiceAgent 及业务数据")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保 customer_service.py 在同一目录下或 Python 路径中")
    sys.exit(1)

@dataclass
class FunctionalProblem(BaseProblem):
    """功能性能问题详情"""
    conversation_type: str = ""
    metric_type: str = ""
    reference_response: str = ""
    similarity_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（扩展基类方法）"""
        base_dict = super().to_dict()
        if self.conversation_type:
            base_dict["conversation_type"] = self.conversation_type
        if self.metric_type:
            base_dict["metric_type"] = self.metric_type
        if self.reference_response:
            base_dict["reference_response"] = self.reference_response[:200] if len(self.reference_response) > 200 else self.reference_response
        if self.similarity_score:
            base_dict["similarity_score"] = self.similarity_score
        return base_dict

class FunctionalEvaluator(BaseEvaluator):
    """功能性能评估专家"""
    
    def __init__(self, use_customer_agent: bool = True):
        super().__init__()
        self.metrics_config = {
            "accuracy": {"weight": 0.4, "threshold": 0.8},
            "relevance": {"weight": 0.3, "threshold": 0.7},
            "completeness": {"weight": 0.3, "threshold": 0.75}
        }
        
        self.rouge = Rouge()
        self.use_customer_agent = use_customer_agent
        self.customer_service_agent = None
        self.embedding_model = None
        self.embedding_model_loaded = False
        
        # 初始化客服智能体
        if self.use_customer_agent:
            try:
                print("🔄 初始化客服智能体实例...")
                self.customer_service_agent = CustomerServiceAgent()
                print("✅ 客服智能体加载完成")
            except Exception as e:
                print(f"❌ 客服智能体初始化出错: {e}")
                self.use_customer_agent = False
        
        # 初始化嵌入模型 (已修改为优先加载本地 Qwen3)
        self._init_embedding_model()
        
        # 预定义的规则模板
        self._init_templates()

    def _init_embedding_model(self):
        """初始化嵌入模型，优先加载本地 Qwen3"""
        self.embedding_model = None
        self.embedding_model_loaded = False
        
        # ✅ 替换部分：优先加载本地 Qwen3-Embedding 模型
        try:
            # 本地模型路径
            model_path = "D:/model/Qwen/Qwen3-Embedding-0.6B"
            print(f"🔧 尝试加载本地嵌入模型: {model_path}")
            
            # 使用SentenceTransformer加载本地模型
            # 注意：如果模型包含自定义代码，可能需要 trust_remote_code=True，视具体版本而定
            self.embedding_model = SentenceTransformer(model_path, trust_remote_code=True)
            print("✅ 本地嵌入模型加载成功")
            
            # 测试模型是否正常工作
            test_embeddings = self.embedding_model.encode(["测试句子1", "测试句子2"])
            print(f"✅ 模型测试通过，嵌入维度: {test_embeddings.shape}")
            self.embedding_model_loaded = True
            
        except Exception as e:
            print(f"⚠️ 本地 Qwen3 模型加载失败: {e}")
            
            # 添加嵌入模型加载失败的问题
            self.add_problem(ProblemType.FUNCTIONAL_EMBEDDING.value, FunctionalProblem(
                problem_type="本地嵌入模型加载失败",
                score=0.0,
                threshold=0.7,
                deduction_items=[
                    f"加载本地模型路径 {model_path} 失败: {str(e)[:100]}",
                    "将尝试加载在线默认模型"
                ]
            ))
            
            print("🔧 降级方案：尝试加载在线默认模型 (paraphrase-multilingual-MiniLM-L12-v2)...")
            
            # 兜底逻辑：加载轻量级在线模型
            try:
                self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                print("✅ 默认在线嵌入模型加载成功")
                self.embedding_model_loaded = True
            except Exception as e2:
                print("⚠️ 默认模型加载失败，尝试加载极小模型 (all-MiniLM-L6-v2)...")
                try:
                    self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                    self.embedding_model_loaded = True
                except Exception as e3:
                    print("❌ 无法加载任何嵌入模型，相关性评分将不可用")
                    
                    # 添加嵌入模型完全加载失败的问题
                    self.add_problem(ProblemType.FUNCTIONAL_EMBEDDING.value, FunctionalProblem(
                        problem_type="所有嵌入模型加载失败",
                        score=0.0,
                        threshold=0.7,
                        deduction_items=[
                            "本地模型加载失败",
                            "在线默认模型加载失败",
                            "极小模型加载失败",
                            "无法进行相关性评估"
                        ]
                    ))

    def _init_templates(self):
        """初始化规则模板"""
        self.reference_templates = {
            "order_query": "订单{order_id}（产品：{product_name}）状态：{status}，物流：{shipping_status}，预计送达：{estimated_delivery}。",
            "sales_data": "{region} {date} 销售额：{total_sales:,.2f}元，销量：{total_quantity}件。",
            "complaint": "非常抱歉听到您遇到的问题。我们已经记录了您的投诉，编号{complaint_id}。我们的客服专员将在24小时内与您联系处理此事。请保持电话畅通。"
        }

    async def evaluate(self, logs: List[Dict]) -> Dict:
        """执行评估的主入口"""
        print("🔍 开始功能性能评估...")
        
        # 清空前一次评估的问题（保留嵌入模型加载问题）
        # 注意：我们需要保留之前添加的嵌入模型问题，所以只清除功能评估相关的问题
        self._clear_functional_problems_only()
        
        conversation_pairs = self._parse_conversations(logs)
        
        if not conversation_pairs:
            self._add_no_data_problem()
            return self._create_empty_result()
        
        tasks = [
            self._evaluate_accuracy(conversation_pairs),
            self._evaluate_relevance(conversation_pairs),
            self._evaluate_completeness(conversation_pairs)
        ]
        
        results = await asyncio.gather(*tasks)
        
        metrics = {task_name: score for task_name, score, _ in results}
        details = {task_name: detail for task_name, _, detail in results}
        
        overall_score = self._calculate_score(metrics, {k: v["weight"] for k, v in self.metrics_config.items()})
        
        # 检查并添加整体问题
        self._add_overall_problems(metrics, details)
        
        # 打印所有问题
        self._print_all_problems()
        
        return {
            "dimension": "功能性能",
            "overall_score": overall_score,
            "metrics": metrics,
            "strengths": self._identify_strengths(metrics),
            "improvements": self._identify_improvements(metrics),
            "details": details
        }
    
    def _clear_functional_problems_only(self):
        """只清除功能性能相关的问题，保留嵌入模型问题"""
        functional_problem_types = [
            ProblemType.FUNCTIONAL_ACCURACY.value,
            ProblemType.FUNCTIONAL_RELEVANCE.value,
            ProblemType.FUNCTIONAL_COMPLETENESS.value
        ]
        
        for problem_type in functional_problem_types:
            self._all_problems[problem_type] = []
    
    def _add_no_data_problem(self):
        """添加无数据问题"""
        self.add_problem(ProblemType.FUNCTIONAL_ACCURACY.value, FunctionalProblem(
            problem_type="无评估数据",
            score=0.0,
            threshold=0.7,
            deduction_items=[
                "没有提供有效的对话日志数据",
                "无法进行功能性能评估"
            ]
        ))
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            "dimension": "功能性能",
            "overall_score": 0.0,
            "metrics": {
                "accuracy": 0.0,
                "relevance": 0.0,
                "completeness": 0.0
            },
            "strengths": ["无数据可用于评估"],
            "improvements": ["请提供有效的对话日志数据"],
            "details": {}
        }
    
    def _add_overall_problems(self, metrics: Dict[str, float], details: Dict[str, Any]):
        """添加整体指标问题"""
        # 检查准确性指标
        if metrics.get("accuracy", 0) < self.metrics_config["accuracy"]["threshold"]:
            accuracy_details = details.get("accuracy", {})
            self.add_problem(ProblemType.FUNCTIONAL_ACCURACY.value, FunctionalProblem(
                problem_type="整体准确性不足",
                score=metrics["accuracy"],
                threshold=self.metrics_config["accuracy"]["threshold"],
                deduction_items=[
                    f"准确性得分 {metrics['accuracy']:.2f} 低于阈值 {self.metrics_config['accuracy']['threshold']}",
                    f"EM得分: {accuracy_details.get('em', 0):.2f}",
                    f"F1得分: {accuracy_details.get('f1', 0):.2f}",
                    f"ROUGE-L得分: {accuracy_details.get('rouge', 0):.2f}",
                    "回答与参考回答存在较大差异"
                ]
            ))
        
        # 检查相关性指标
        if metrics.get("relevance", 0) < self.metrics_config["relevance"]["threshold"]:
            relevance_details = details.get("relevance", {})
            self.add_problem(ProblemType.FUNCTIONAL_RELEVANCE.value, FunctionalProblem(
                problem_type="整体相关性不足",
                score=metrics["relevance"],
                threshold=self.metrics_config["relevance"]["threshold"],
                deduction_items=[
                    f"相关性得分 {metrics['relevance']:.2f} 低于阈值 {self.metrics_config['relevance']['threshold']}",
                    f"平均相似度: {relevance_details.get('avg_similarity', 0):.2f}",
                    "回答与用户问题相关性不够",
                    "可能需要改进语义理解能力"
                ]
            ))
        
        # 检查完整性指标
        if metrics.get("completeness", 0) < self.metrics_config["completeness"]["threshold"]:
            completeness_details = details.get("completeness", {})
            self.add_problem(ProblemType.FUNCTIONAL_COMPLETENESS.value, FunctionalProblem(
                problem_type="整体完整性不足",
                score=metrics["completeness"],
                threshold=self.metrics_config["completeness"]["threshold"],
                deduction_items=[
                    f"完整性得分 {metrics['completeness']:.2f} 低于阈值 {self.metrics_config['completeness']['threshold']}",
                    f"平均完整性: {completeness_details.get('avg_completeness', 0):.2f}",
                    "回答缺乏必要的信息点",
                    "需要提供更完整的答案"
                ]
            ))
    
    def _print_all_problems(self):
        """打印所有识别到的问题，包括详细的问题和回复"""
        problems = self.get_problems()
        
        print("\n" + "="*80)
        print("功能性能评估问题详情汇总")
        print("="*80)
        
        total_problems = 0
        
        # 打印各类问题
        for problem_type, problem_list in problems.items():
            if problem_list:
                total_problems += len(problem_list)
                
                # 根据问题类型显示不同的标题
                if problem_type == ProblemType.FUNCTIONAL_ACCURACY.value:
                    title = "准确性问题"
                elif problem_type == ProblemType.FUNCTIONAL_RELEVANCE.value:
                    title = "相关性问题"
                elif problem_type == ProblemType.FUNCTIONAL_COMPLETENESS.value:
                    title = "完整性问题"
                elif problem_type == ProblemType.FUNCTIONAL_EMBEDDING.value:
                    title = "嵌入模型问题"
                else:
                    title = f"{problem_type.upper()} 问题"
                
                print(f"\n🔴 {title} (共{len(problem_list)}个):")
                print("-"*80)
                
                for i, problem in enumerate(problem_list, 1):
                    print(f"\n{i}. {problem.problem_type}")
                    print(f"   得分: {problem.score:.2f} (阈值: {problem.threshold})")
                    
                    if hasattr(problem, 'conversation_type') and problem.conversation_type:
                        print(f"   对话类型: {problem.conversation_type}")
                    if hasattr(problem, 'metric_type') and problem.metric_type:
                        print(f"   指标类型: {problem.metric_type}")
                    if hasattr(problem, 'similarity_score') and problem.similarity_score:
                        print(f"   相似度分数: {problem.similarity_score:.2f}")
                    
                    if problem.user_input:
                        print(f"   用户输入: {problem.user_input[:150]}{'...' if len(problem.user_input) > 150 else ''}")
                    if problem.assistant_response:
                        print(f"   助手回复: {problem.assistant_response[:150]}{'...' if len(problem.assistant_response) > 150 else ''}")
                    if hasattr(problem, 'reference_response') and problem.reference_response:
                        print(f"   参考回答: {problem.reference_response[:150]}{'...' if len(problem.reference_response) > 150 else ''}")
                    
                    if problem.deduction_items:
                        print(f"   扣分项:")
                        for deduction in problem.deduction_items:
                            print(f"     - {deduction}")
        
        if total_problems == 0:
            print("\n✅ 未发现功能性能问题")
            
        # 打印问题摘要
        self.print_problems_summary()
    
    def _parse_conversations(self, logs: List[Dict]) -> List[Tuple[str, str, str]]:
        """解析日志"""
        pairs = []
        for log in logs:
            if "user_input" in log and "assistant_response" in log:
                user_id = log.get("user_id", "cust001")
                pairs.append((user_id, log["user_input"], log["assistant_response"]))
        return pairs

    async def _generate_reference_responses(self, pairs: List[Tuple[str, str, str]]) -> List[str]:
        """生成参考回答"""
        references = []
        for user_id, question, _ in pairs:
            ref = ""
            if self.use_customer_agent and self.customer_service_agent:
                try:
                    # 使用 asyncio.to_thread 调用同步 Agent
                    conversation_result = await asyncio.to_thread(
                        self.customer_service_agent.process_query, 
                        user_id, 
                        question
                    )
                    ref = conversation_result.get("assistant_response", "")
                except Exception as e:
                    print(f"    ⚠️ Agent 调用异常: {e}")
            
            if not ref:
                ref = self._generate_by_rules(question)
            
            references.append(ref)
        return references

    async def _evaluate_accuracy(self, pairs: List[Tuple[str, str, str]]) -> Tuple[str, float, Dict]:
        """评估准确性"""
        print("  📐 计算准确性指标...")
        
        references = await self._generate_reference_responses(pairs)
        
        scores = {"em": [], "f1": [], "rouge": []}
        
        for idx, ((user_id, question, response), reference) in enumerate(zip(pairs, references)):
            conversation_type = self._classify_conversation(question)
            
            if not reference:
                # 添加无法生成参考回答的问题
                self.add_problem(ProblemType.FUNCTIONAL_ACCURACY.value, FunctionalProblem(
                    problem_type=f"无法生成参考回答",
                    score=0.0,
                    threshold=0.7,
                    deduction_items=[
                        f"无法为对话生成参考回答",
                        f"对话类型: {conversation_type}",
                        "无法进行准确性评估"
                    ],
                    user_input=question,
                    assistant_response=response,
                    conversation_type=conversation_type,
                    metric_type="accuracy"
                ))
                continue
            
            # 计算准确率指标
            em_score = 1.0 if response.strip() == reference.strip() else 0.0
            scores["em"].append(em_score)
            
            # 计算F1分数
            r_tokens = set(jieba.lcut(response))
            ref_tokens = set(jieba.lcut(reference))
            if r_tokens and ref_tokens:
                intersection = len(r_tokens & ref_tokens)
                precision = intersection / len(r_tokens)
                recall = intersection / len(ref_tokens)
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                scores["f1"].append(f1)
            else:
                scores["f1"].append(0.0)
            
            # 计算ROUGE分数
            try:
                rouge_s = self.rouge.get_scores(response, reference)[0]['rouge-l']['f']
                scores["rouge"].append(rouge_s)
            except:
                rouge_s = 0.0
                scores["rouge"].append(0.0)
            
            # 如果准确性得分低，添加具体问题
            if em_score < 0.5 or f1 < 0.5 or rouge_s < 0.5:
                self.add_problem(ProblemType.FUNCTIONAL_ACCURACY.value, FunctionalProblem(
                    problem_type=f"准确性不足的{conversation_type}对话",
                    score=min(em_score, f1, rouge_s),
                    threshold=0.7,
                    deduction_items=[
                        f"对话类型: {conversation_type}",
                        f"精确匹配(EM): {em_score:.2f}",
                        f"F1分数: {f1:.2f}",
                        f"ROUGE-L分数: {rouge_s:.2f}",
                        "回答与参考回答差异较大"
                    ],
                    user_input=question,
                    assistant_response=response,
                    conversation_type=conversation_type,
                    reference_response=reference,
                    metric_type="accuracy"
                ))

        avg_metrics = {k: np.mean(v) if v else 0.0 for k, v in scores.items()}
        final_score = 0.2 * avg_metrics["em"] + 0.4 * avg_metrics["f1"] + 0.4 * avg_metrics["rouge"]
        
        return "accuracy", final_score, avg_metrics
    
    def _classify_conversation(self, question: str) -> str:
        """对话分类"""
        if re.search(r"订单|物流|发货|快递", question):
            return "order_query"
        elif re.search(r"销售|业绩|数据|总额", question):
            return "sales_data"
        elif re.search(r"投诉|损坏|问题|不满意", question):
            return "complaint"
        elif re.search(r"比较|哪个好|对比|推荐", question):
            return "product_comparison"
        else:
            return "general"

    def _generate_by_rules(self, question: str) -> str:
        """规则生成兜底逻辑"""
        order_match = re.search(r'(\d{6,})', question)
        if order_match:
            order_id = order_match.group(1)
            if order_id in ORDER_DATABASE:
                info = ORDER_DATABASE[order_id]
                return self.reference_templates["order_query"].format(**info, order_id=order_id)
        
        if "华东" in question and "2024-06-10" in question:
            region, date = "华东区", "2024-06-10"
            if region in SALES_DATABASE and date in SALES_DATABASE[region]:
                data = SALES_DATABASE[region][date]
                total_s = sum(x['sales_amount'] for x in data)
                total_q = sum(x['quantity'] for x in data)
                return self.reference_templates["sales_data"].format(
                    region=region, date=date, total_sales=total_s, total_quantity=total_q
                )
        return ""

    async def _evaluate_relevance(self, pairs: List[Tuple[str, str, str]]) -> Tuple[str, float, Dict]:
        """评估相关性 (使用 Qwen3-Embedding)"""
        print("  🔗 计算相关性指标...")
        
        if not self.embedding_model or not self.embedding_model_loaded:
            # 添加嵌入模型不可用的问题
            self.add_problem(ProblemType.FUNCTIONAL_RELEVANCE.value, FunctionalProblem(
                problem_type="嵌入模型不可用",
                score=0.0,
                threshold=0.7,
                deduction_items=[
                    "嵌入模型未加载成功",
                    "无法计算语义相关性",
                    "相关性评估将使用默认值"
                ]
            ))
            return "relevance", 0.5, {"error": "No Model", "avg_similarity": 0.5}
            
        scores = []
        for idx, (user_id, question, response) in enumerate(pairs):
            try:
                emb = self.embedding_model.encode([question, response])
                # 计算余弦相似度
                sim = cosine_similarity([emb[0]], [emb[1]])[0][0]
                score = max(0.0, min(1.0, sim))
                scores.append(score)
                
                # 如果相关性得分低，添加问题
                conversation_type = self._classify_conversation(question)
                if score < 0.5:
                    self.add_problem(ProblemType.FUNCTIONAL_RELEVANCE.value, FunctionalProblem(
                        problem_type=f"相关性不足的{conversation_type}对话",
                        score=score,
                        threshold=0.7,
                        deduction_items=[
                            f"对话类型: {conversation_type}",
                            f"语义相似度: {score:.2f}",
                            "回答与用户问题相关性不够",
                            "可能需要改进语义理解能力"
                        ],
                        user_input=question,
                        assistant_response=response,
                        conversation_type=conversation_type,
                        similarity_score=score,
                        metric_type="relevance"
                    ))
            except Exception as e:
                print(f"计算相似度出错: {e}")
                scores.append(0.0)
                
                # 添加计算失败的问题
                conversation_type = self._classify_conversation(question)
                self.add_problem(ProblemType.FUNCTIONAL_RELEVANCE.value, FunctionalProblem(
                    problem_type=f"相关性计算失败",
                    score=0.0,
                    threshold=0.7,
                    deduction_items=[
                        f"计算语义相似度时出错: {str(e)[:100]}",
                        f"对话类型: {conversation_type}"
                    ],
                    user_input=question,
                    assistant_response=response,
                    conversation_type=conversation_type,
                    metric_type="relevance"
                ))
        
        avg_score = float(np.mean(scores)) if scores else 0.0
        return "relevance", avg_score, {"avg_similarity": avg_score}

    async def _evaluate_completeness(self, pairs: List[Tuple[str, str, str]]) -> Tuple[str, float, Dict]:
        """评估完整性"""
        print("  ✅ 计算完整性指标...")
        keywords_map = {
            "order_query": ["状态", "物流", "时间", "订单", "产品"],
            "sales_data": ["总额", "销量", "元", "销售", "数据"],
            "complaint": ["抱歉", "处理", "工单", "记录", "联系"],
            "product_comparison": ["对比", "参数", "推荐", "建议", "优势"]
        }
        
        scores = []
        for idx, (user_id, question, response) in enumerate(pairs):
            conversation_type = self._classify_conversation(question)
            
            target_words = keywords_map.get(conversation_type, [])
            if not target_words:
                # 对于一般类型，检查响应长度
                score = 1.0 if len(response) > 30 else 0.0
                scores.append(score)
            else:
                # 检查是否包含关键词
                hit = sum(1 for w in target_words if w in response)
                score = hit / len(target_words) if target_words else 1.0
                scores.append(score)
                
                # 如果完整性得分低，添加问题
                if score < 0.6:
                    missing_keywords = [w for w in target_words if w not in response]
                    self.add_problem(ProblemType.FUNCTIONAL_COMPLETENESS.value, FunctionalProblem(
                        problem_type=f"完整性不足的{conversation_type}对话",
                        score=score,
                        threshold=0.7,
                        deduction_items=[
                            f"对话类型: {conversation_type}",
                            f"完整性得分: {score:.2f}",
                            f"缺失关键词: {', '.join(missing_keywords[:5])}" if missing_keywords else "未命中任何关键词",
                            f"目标关键词: {', '.join(target_words[:5])}..."
                        ],
                        user_input=question,
                        assistant_response=response,
                        conversation_type=conversation_type,
                        metric_type="completeness"
                    ))
                
        avg_score = float(np.mean(scores)) if scores else 0.0
        return "completeness", avg_score, {"avg_completeness": avg_score}
    
    def _identify_strengths(self, metrics: Dict[str, float]) -> List[str]:
        """识别优点"""
        strengths = []
        
        if metrics.get("accuracy", 0) > 0.85:
            strengths.append("准确性高，回答与参考标准高度一致")
        elif metrics.get("accuracy", 0) > 0.7:
            strengths.append("准确性良好")
            
        if metrics.get("relevance", 0) > 0.85:
            strengths.append("相关性好，回答紧密围绕用户问题")
        elif metrics.get("relevance", 0) > 0.7:
            strengths.append("相关性良好")
            
        if metrics.get("completeness", 0) > 0.85:
            strengths.append("完整性好，回答包含所有必要信息")
        elif metrics.get("completeness", 0) > 0.7:
            strengths.append("完整性良好")
        
        if not strengths:
            if metrics.get("accuracy", 0) > 0.6 or metrics.get("relevance", 0) > 0.6 or metrics.get("completeness", 0) > 0.6:
                strengths.append("功能性能基本达标")
        
        return strengths
    
    def _identify_improvements(self, metrics: Dict[str, float]) -> List[str]:
        """识别改进点"""
        improvements = []
        
        if metrics.get("accuracy", 0) < 0.7:
            improvements.append("需要提高准确性，使回答更接近参考标准")
        elif metrics.get("accuracy", 0) < 0.8:
            improvements.append("准确性有提升空间")
            
        if metrics.get("relevance", 0) < 0.6:
            improvements.append("需要提高相关性，使回答更贴合用户问题")
        elif metrics.get("relevance", 0) < 0.7:
            improvements.append("相关性可以进一步提升")
            
        if metrics.get("completeness", 0) < 0.6:
            improvements.append("需要提高完整性，确保回答包含所有必要信息")
        elif metrics.get("completeness", 0) < 0.75:
            improvements.append("完整性有优化空间")
        
        return improvements

if __name__ == "__main__":
    # 测试数据
    mock_logs = [
        {
            "user_id": "cust001",
            "user_input": "我的订单123456现在到哪了？",
            "assistant_response": "订单123456（产品：智能手机A）状态：已发货，物流：运输中，预计送达：2024-06-15。"
        },
        {
            "user_id": "emp001",
            "user_input": "查询华东区2024-06-10的销售总额",
            "assistant_response": "华东区 2024-06-10 销售额：895,000.00元，销量：290件。"
        }
    ]

    evaluator = FunctionalEvaluator()
    result = asyncio.run(evaluator.evaluate(mock_logs))
    
    print("\n📊 评估报告:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
