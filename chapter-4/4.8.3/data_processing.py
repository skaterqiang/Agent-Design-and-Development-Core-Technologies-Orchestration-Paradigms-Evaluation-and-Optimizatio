"""
面向对象的 LangGraph 智能体系统实现
核心设计原则：
1. 每个模块封装为独立类（高内聚）
2. 依赖注入实现解耦（低耦合）
3. 状态管理符合 Pydantic 规范
4. 人机协同通过中断机制实现
5. 反馈循环嵌入状态流转
"""
import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    # 设置通义千问API Key
    os.environ["DASHSCOPE_API_KEY"] = API_KEY
    print("API配置加载成功")
    print("配置信息:", get_all_configs())
except ValueError as e:
    print(f"配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)
from langchain_community.chat_models.tongyi import ChatTongyi
import json
from typing import TypedDict, Annotated, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
import asyncio
from abc import ABC, abstractmethod
import logging
from langchain_core.messages import HumanMessage


# ======================
# 1. 系统状态定义 (Pydantic)
# ======================
class ProcessingState(TypedDict):
    """全流程状态管理"""
    task_id: str
    source_type: str  # "html_file" | "web_url"
    raw_content: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    needs_human_review: bool
    human_feedback: Optional[Dict[str, Any]]
    swift_formatted: Optional[List[Dict[str, Any]]]
    feedback_records: List[Dict[str, Any]]  # 用于迭代优化
    error_log: List[str]
    current_stage: str

# ======================
# 2. 核心组件抽象基类
# ======================
class DataExtractor(ABC):
    """数据提取策略接口"""
    @abstractmethod
    async def extract(self, content: str, context: Dict) -> Dict[str, Any]:
        pass

class Validator(ABC):
    """数据校验策略接口"""
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

# ======================
# 3. 具体实现模块 (面向对象封装)
# ======================
class HTMLFileExtractor(DataExtractor):
    async def extract(self, content: str, context: Dict) -> Dict[str, Any]:
        # 实际实现：BeautifulSoup + 智能选择器
        return {
            "title": "示例标题",
            "content": content[:500],
            "metadata": {"source": "local_html"}
        }

class WebCrawlerExtractor(DataExtractor):
    async def extract(self, content: str, context: Dict) -> Dict[str, Any]:
        # 实际实现：Playwright + 反爬策略
        return {
            "title": "网页标题",
            "content": content[:500],
            "url": context.get("url", ""),
            "metadata": {"source": "web_crawl"}
        }

class ReActEngine:
    """ReAct智能处理引擎（核心创新）"""
    def __init__(self, llm_client, feedback_db):
        self.llm = llm_client
        self.feedback_db = feedback_db  # 依赖注入
    
    async def process(self, state: ProcessingState) -> Dict[str, Any]:
        # 1. 查询历史反馈优化策略
        historical_feedback = await self.feedback_db.query_similar(
            state["raw_content"][:200]
        )
        
        # 2. ReAct循环：Reasoning → Action → Observation
        max_steps = 3
        for step in range(max_steps):
            reasoning = await self._reason(state, historical_feedback, step)
            action_result = await self._execute_action(reasoning, state)
            validation = await self._observe(action_result)
            
            if validation["confidence"] > 0.85:
                return {
                    "extracted_data": action_result,
                    "current_stage": "react_success",
                    "feedback_records": state.get("feedback_records", []) + [{
                        "step": step,
                        "reasoning": reasoning,
                        "success": True
                    }]
                }
        
        # 3. 持续失败：标记需人工介入
        return {
            "needs_human_review": True,
            "current_stage": "react_failed",
            "error_log": state.get("error_log", []) + ["ReAct循环超时"]
        }
    
    async def _reason(self, state, feedback, step):
        """使用标准 LangChain 异步调用方式"""
        prompt = f"""基于历史反馈{feedback}，分析当前HTML结构：
        {state['raw_content'][:300]}... 
        生成提取策略（XPath/CSS/正则）"""
        
        # ✅ 正确：构造消息列表 + 使用 ainvoke
        messages = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages)  # 返回 AIMessage
        
        # ✅ 安全提取文本内容（response 是 AIMessage 对象）
        return response.content if hasattr(response, 'content') else str(response)
    
    async def _execute_action(self, reasoning, state):
        # 动态执行提取策略
        # 实际实现：解析reasoning中的指令并执行
        return {"content": "提取结果", "strategy": "xpath"}
    
    async def _observe(self, result):
        # 验证结果质量
        return {"confidence": 0.9, "issues": []}

class AutoValidator(Validator):
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 多维度校验：完整性/合规性/质量评分
        checks = {
            "has_prompt": bool(data.get("prompt")),
            "has_response": bool(data.get("response")),
            "sensitive_check": not self._contains_sensitive(data),
            "length_valid": 50 < len(str(data)) < 5000
        }
        confidence = sum(checks.values()) / len(checks)
        return {
            "passed": confidence > 0.7,
            "confidence": confidence,
            "details": checks,
            "needs_human": confidence < 0.85  # 置信度阈值
        }
    
    def _contains_sensitive(self, data):
        # 敏感词检测（简化）
        sensitive_words = ["密码", "身份证"]
        return any(w in str(data) for w in sensitive_words)

class FeedbackRepository:
    """反馈学习库存储（支持向量检索）"""
    async def save(self, record: Dict[str, Any]):
        # 实际实现：存入向量数据库（如Milvus）
        logging.info(f"保存反馈: {record['task_id']}")
    
    async def query_similar(self, content_snippet: str) -> List[Dict]:
        # 实际实现：向量相似度检索
        return [{"strategy": "xpath_//div[@class='answer']", "success_rate": 0.92}]

class SwiftFormatter:
    """阿里云Swift格式转换器"""
    def format(self, data: Dict[str, Any], human_verified: bool = False) -> List[Dict]:
        # 字段映射 + 格式校验
        base_record = {
            "prompt": data.get("question", data.get("title", "")),
            "response": data.get("answer", data.get("content", "")),
            "source": data.get("metadata", {}).get("source", "unknown"),
            "human_verified": human_verified
        }
        # 添加对话历史（如存在）
        if "history" in data:
            base_record["history"] = data["history"]
        return [base_record]  # 支持单条/多条输出

# ======================
# 4. 智能体节点封装类
# ======================
class ProcessingAgent:
    """全流程智能体（封装LangGraph节点逻辑）"""
    
    def __init__(self, config: Dict[str, Any]):
        # 依赖注入（符合面向对象设计原则）
        self.extractors = {
            "html_file": HTMLFileExtractor(),
            "web_url": WebCrawlerExtractor()
        }
        self.react_engine = ReActEngine(
            llm_client=config["llm_client"],
            feedback_db=FeedbackRepository()
        )
        self.validator = AutoValidator()
        self.formatter = SwiftFormatter()
        self.output_path = config.get("output_path", "./swift_data.jsonl")
    
    # ===== 节点方法（符合LangGraph签名要求）=====
    async def node_task_dispatch(self, state: ProcessingState) -> Dict:
        """智能调度层：路由到对应提取器"""
        extractor = self.extractors.get(state["source_type"])
        if not extractor:
            raise ValueError(f"不支持的数据源类型: {state['source_type']}")
        
        extracted = await extractor.extract(
            state["raw_content"], 
            {"url": state.get("task_id", "")}
        )
        return {
            "extracted_data": extracted,
            "current_stage": "dispatched"
        }
    
    async def node_react_process(self, state: ProcessingState) -> Dict:
        """ReAct智能处理引擎"""
        return await self.react_engine.process(state)
    
    async def node_auto_validate(self, state: ProcessingState) -> Dict:
        """自动校验节点"""
        result = await self.validator.validate(state["extracted_data"])
        return {
            "validation_result": result,
            "needs_human_review": result["needs_human"],
            "current_stage": "validated"
        }
    
    def node_human_decision(self, state: ProcessingState) -> str:
        """人工复核决策（条件路由）"""
        if state.get("needs_human_review", False):
            return "human_annotation"
        return "swift_format"
    
    async def node_human_annotation(self, state: ProcessingState) -> Dict:
        """人工标注平台（触发中断等待人工输入）"""
        # 实际部署：此处设置 interrupt_before=["human_annotation"]
        # 模拟返回人工修正结果
        corrected = {
            **state["extracted_data"],
            "response": "[人工修正]" + state["extracted_data"].get("response", "")
        }
        # 保存反馈记录
        feedback_record = {
            "task_id": state["task_id"],
            "original": state["extracted_data"],
            "corrected": corrected,
            "reason": "置信度不足"
        }
        await self.react_engine.feedback_db.save(feedback_record)
        
        return {
            "extracted_data": corrected,
            "human_feedback": {"applied": True},
            "current_stage": "human_corrected"
        }
    
    def node_swift_format(self, state: ProcessingState) -> Dict:
        """Swift格式生成"""
        formatted = self.formatter.format(
            state["extracted_data"],
            human_verified=state.get("human_feedback") is not None
        )
        return {
            "swift_formatted": formatted,
            "current_stage": "formatted"
        }
    
    async def node_output_storage(self, state: ProcessingState) -> Dict:
        """输出仓库（持久化）"""
        # 实际实现：写入JSONL文件 + OSS上传
        with open(self.output_path, "a", encoding="utf-8") as f:
            for item in state["swift_formatted"]:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        logging.info(f"✅ 任务 {state['task_id']} 完成 | 输出: {len(state['swift_formatted'])}条")
        return {"current_stage": "completed"}

# ======================
# 5. 系统构建与执行
# ======================
class DataProcessingSystem:
    """系统主控制器（封装LangGraph构建逻辑）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.agent = ProcessingAgent(config)
        self.checkpointer = MemorySaver()  # 支持中断恢复
        self.graph = self._build_graph()
        print(self.graph.get_graph().draw_ascii())
        
    
    def _build_graph(self) -> StateGraph:
        """构建符合流程图的LangGraph"""
        builder = StateGraph(ProcessingState)
        
        # 添加节点（方法引用，保持对象封装）
        builder.add_node("dispatch", self.agent.node_task_dispatch)
        builder.add_node("react", self.agent.node_react_process)
        builder.add_node("validate", self.agent.node_auto_validate)
        builder.add_node("human_annotation", self.agent.node_human_annotation)
        builder.add_node("swift_format", self.agent.node_swift_format)
        builder.add_node("output", self.agent.node_output_storage)
        
        # 设置入口
        builder.add_edge(START, "dispatch")
        builder.add_edge("dispatch", "react")
        builder.add_edge("react", "validate")
        
        # 条件分支：人工审核决策
        builder.add_conditional_edges(
            "validate",
            self.agent.node_human_decision,  # 返回路由目标
            {
                "human_annotation": "human_annotation",
                "swift_format": "swift_format"
            }
        )
        builder.add_edge("human_annotation", "swift_format")
        builder.add_edge("swift_format", "output")
        builder.add_edge("output", END)
        
        return builder.compile(checkpointer=self.checkpointer)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict:
        """执行单个任务（支持异步）"""
        initial_state = {
            "task_id": task["id"],
            "source_type": task["source_type"],
            "raw_content": task["content"],
            "needs_human_review": False,
            "feedback_records": [],
            "error_log": [],
            "current_stage": "init"
        }
        
        try:
             # ✅ 修复点1：必须提供 configurable 配置（thread_id 是 Checkpointer 强制要求）
            config = {
                "configurable": {
                    "thread_id": task["id"],  # 用任务ID作为会话唯一标识
                    "checkpoint_ns": "data_processing"  # 命名空间（可选但推荐）
                }
            }
            # 流式执行（支持中断）
            final_state = None
            async for chunk in self.graph.astream(
                initial_state, 
                config=config,
                stream_mode="values"  # 返回完整状态快照
            ):
                final_state = chunk
                logging.debug(f"📌 阶段: {chunk.get('current_stage', 'unknown')}")
            
            return {
                "status": "success",
                "task_id": task["id"],
                "output_count": len(final_state.get("swift_formatted", [])),
                "stage": final_state["current_stage"]
            }
        except Exception as e:
            import traceback
            logging.error(
                f"❌ 任务 {task['id']} 失败: {str(e)}\n" 
                f"{''.join(traceback.format_exception(type(e), e, e.__traceback__))}"
            )
            return {"status": "failed", "task_id": task["id"], "error": str(e)}
    
    def get_human_tasks(self) -> List[str]:
        """获取待人工处理的任务ID（运维接口）"""
        # 实际实现：查询中断状态的任务
        return ["task_123"]  # 模拟
    
    async def resume_with_human_input(self, task_id: str, correction: Dict) -> Dict:
        """人工修正后恢复流程"""
        # 实际实现：更新状态并继续执行
        return {"status": "resumed", "task_id": task_id}

# ======================
# 6. 使用示例
# ======================
if __name__ == "__main__":
    import json
    model = ChatTongyi(model_name="qwen-max")
    # 模拟配置（实际替换为真实LLM客户端）
    config = {
        "llm_client": model,  # 注入实际LLM客户端
        "output_path": "./swift_output.jsonl"
    }
    
    # 初始化系统
    system = DataProcessingSystem(config)
    
    # 示例任务
    sample_task = {
        "id": "task_001",
        "source_type": "html_file",
        "content": "<html><body><h1>问题</h1><div>答案内容</div></body></html>"
    }
    
    # 异步执行（生产环境使用asyncio.run）
    result = asyncio.run(system.process_task(sample_task))
    print(f"处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 人机协同示例（当需要人工介入时）
    # pending = system.get_human_tasks()
    # if pending:
    #     system.resume_with_human_input(pending[0], {"response": "修正后的内容"})
