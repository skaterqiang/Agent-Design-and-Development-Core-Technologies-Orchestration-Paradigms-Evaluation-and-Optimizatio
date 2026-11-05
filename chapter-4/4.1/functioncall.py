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


import sys
import os
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi

# === 工具定义 ===
@tool
def calculator(expression: str) -> str:
    """计算数学表达式，例如 '2 + 3 * 4'。支持加减乘除和括号。"""
    try:
        allowed_names = {"__builtins__": {}}
        result = eval(expression, allowed_names)
        return f"结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息（模拟数据）。"""
    weather_data = {
        "北京": "晴天，25°C",
        "上海": "多云，28°C", 
        "西安": "小雨，30°C",
        "深圳": "晴天，32°C"
    }
    return f"{city} 当前天气: {weather_data.get(city, '暂无数据')}"

tools = [calculator, get_weather]
model = ChatTongyi(model_name="qwen-max")

# === 使用 create_agent 创建代理（关键改动）===
system_prompt = """你是一个严谨且乐于助人的助手。
- 如果用户要求计算，请使用 calculator 工具。
- 如果询问天气，请使用 get_weather 工具。
- 回答应清晰、分步，并在最终结论中包含“最终答案是：...”或“已完成”字样以表示满足要求。
- 请用中文回答。"""

agent_executor = create_agent(
    model,
    tools,
    system_prompt=system_prompt
)

# === 状态定义 ===
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    iteration: int
    is_satisfactory: bool

# === 节点：调用 create_agent 生成响应 ===
def generate(state: AgentState):
    # agent_executor 接收 {"messages": [...]} 格式
    response = agent_executor.invoke({"messages": state["messages"]})
    # 提取新消息（LangChain Agent 返回的是完整状态，含历史）
    new_messages = response["messages"][len(state["messages"]):]  # 只取新增部分
    return {
        "messages": new_messages,
        "iteration": state["iteration"] + 1
    }

# === 节点：评估是否满意 ===
def evaluate(state: AgentState):
    last_msg = state["messages"][-1].content
    # 判断是否包含终止关键词（可扩展为 LLM 批评器）
    is_satisfactory = any(keyword in last_msg for keyword in ["最终答案是", "已完成", "满足要求"])
    return {"is_satisfactory": is_satisfactory}

# === 条件路由 ===
def should_continue(state: AgentState) -> Literal["generate", "__end__"]:
    MAX_ITER = 3
    if state["is_satisfactory"]:
        return "__end__"
    elif state["iteration"] >= MAX_ITER:
        print(f"达到最大迭代次数 ({MAX_ITER})，强制终止。")
        return "__end__"
    else:
        return "generate"

# === 构建 LangGraph ===
workflow = StateGraph(AgentState)
workflow.add_node("generate", generate)
workflow.add_node("evaluate", evaluate)

workflow.add_edge(START, "generate")
workflow.add_edge("generate", "evaluate")
workflow.add_conditional_edges("evaluate", should_continue, {"generate": "generate", "__end__": END})

app = workflow.compile()

# === 测试运行 ===
if __name__ == "__main__":
    user_query = "请计算 (15 + 25) * 3，并逐步解释过程，最后明确写出最终答案。"

    initial_state = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ],
        "iteration": 0,
        "is_satisfactory": False
    }

    print("启动迭代精炼流程...\n")

    # 使用 stream 查看每一步
    for event in app.stream(initial_state):
        print(event)
        print("-" * 60)

    # 获取最终结果
    final_state = app.invoke(initial_state)
    print("\n最终输出:")
    print(final_state["messages"][-1].content)
