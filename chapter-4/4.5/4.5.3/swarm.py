import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    print("API配置加载成功")
    print("配置信息:", get_all_configs())
except ValueError as e:
    print(f"配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)

# 设置通义千问API Key
os.environ["DASHSCOPE_API_KEY"] = API_KEY

from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

# 初始化模型
model = ChatTongyi(model_name="qwen-max")

# 共享状态模式
class SwarmState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    research: str
    engineering: str
    financial: str
    iteration: int
    max_iterations: int
    current_agent: str  # 当前活跃代理
    consensus_reached: bool

# 模拟工具
@tool
def update_research(query: str) -> str:
    """市场研究工具"""
    return f"关于'{query}'的市场研究：市场规模100亿美元，竞争对手X/Y/Z"

@tool
def update_engineering(query: str) -> str:
    """工程分析工具"""
    return f"关于'{query}'的工程分析：技术可行，开发周期6个月"

@tool
def update_financial(query: str) -> str:
    """财务建模工具"""
    return f"关于'{query}'的财务分析：预计2年内ROI 3倍"

# 创建工作代理节点函数
def create_worker_node(role: str, tool_func):
    def worker_node(state: SwarmState) -> Dict[str, Any]:
        # 所有代理都能看到完整共享状态，实现协作
        context = f"""
当前群智能状态 (第{state['iteration']}轮):
市场研究: {state.get('research', '暂无')}
工程分析: {state.get('engineering', '暂无')}
财务分析: {state.get('financial', '暂无')}

你的角色：{role}
请基于其他代理的工作进行协作、批判和改进。
任务：{state['messages'][-1].content if state['messages'] else ''}

协作要求：
1. 阅读其他代理的输出
2. 提供你的专业分析
3. 指出其他代理的不足或改进建议
4. 更新你的领域分析
"""
        
        messages = state['messages'][-5:] + [HumanMessage(content=context)]  # 限制上下文长度
        bound_model = model.bind_tools([tool_func])
        result = bound_model.invoke(messages)
        
        updates = {
            'messages': [result],
            'iteration': state['iteration'] + 1,
            'current_agent': role
        }
        
        # 处理工具调用
        if hasattr(result, 'tool_calls') and result.tool_calls:
            for tool_call in result.tool_calls:
                tool_result = tool_func.invoke(tool_call['args'])
                updates['messages'].append(ToolMessage(
                    content=tool_result, 
                    tool_call_id=tool_call['id']
                ))
                # 更新对应领域
                if role == "researcher":
                    updates['research'] = tool_result
                elif role == "engineer":
                    updates['engineering'] = tool_result
                elif role == "financial":
                    updates['financial'] = tool_result
        
        return updates
    
    return worker_node

# 调度器节点
def dispatcher_node(state: SwarmState) -> Dict[str, str]:
    """根据任务内容选择第一个代理"""
    task = state['messages'][-1].content.lower() if state['messages'] else ""
    
    if any(word in task for word in ['研究', '市场', 'market']):
        return {"current_agent": "researcher"}
    elif any(word in task for word in ['工程', '技术', '开发', 'build']):
        return {"current_agent": "engineer"}
    elif any(word in task for word in ['财务', '成本', '钱', 'financial']):
        return {"current_agent": "financial"}
    return {"current_agent": "researcher"}  # 默认

# 继续条件
def should_continue(state: SwarmState) -> str:
    """退出条件：最大迭代次数或达成共识"""
    if state['iteration'] >= state['max_iterations']:
        return END
    
    # 简单共识检查：所有领域都有内容
    domains_filled = all([
        bool(state.get('research')),
        bool(state.get('engineering')),
        bool(state.get('financial'))
    ])
    
    if domains_filled:
        state['consensus_reached'] = True
        return END
    
    # 轮询下一个代理
    agent_order = ['researcher', 'engineer', 'financial']
    current_idx = agent_order.index(state['current_agent'])
    next_agent = agent_order[(current_idx + 1) % len(agent_order)]
    return next_agent

# 构建群智能图
swarm = StateGraph(SwarmState)

# 添加节点
swarm.add_node("dispatcher", dispatcher_node)
swarm.add_node("researcher", create_worker_node("researcher", update_research))
swarm.add_node("engineer", create_worker_node("engineer", update_engineering))
swarm.add_node("financial", create_worker_node("financial", update_financial))

# 连接边
swarm.add_edge(START, "dispatcher")

# 每个代理节点都有自己的条件边
for agent in ["researcher", "engineer", "financial"]:
    swarm.add_conditional_edges(
        agent, 
        should_continue,
        {
            "researcher": "researcher",
            "engineer": "engineer",
            "financial": "financial",
            END: END
        }
    )

# 调度器连接到第一个代理
swarm.add_conditional_edges(
    "dispatcher",
    lambda state: state['current_agent'],
    {
        "researcher": "researcher",
        "engineer": "engineer",
        "financial": "financial"
    }
)

# 编译图（添加检查点以支持持久化）
checkpointer = MemorySaver()
app = swarm.compile(checkpointer=checkpointer)
app.get_graph().draw_mermaid_png(output_file_path='swarm.png')

# 使用示例
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "swarm_demo_1"}}
    
    result = app.invoke({
        "messages": [HumanMessage(content="设计一款新的AI健身追踪器")],
        "iteration": 0,
        "max_iterations": 5,
        "current_agent": "",
        "consensus_reached": False
    }, config)
    
    print("群智能最终共识结果:")
    print(f"市场研究: {result['research']}")
    print(f"工程分析: {result['engineering']}")
    print(f"财务模型: {result['financial']}")
    print(f"总迭代次数: {result['iteration']}")
