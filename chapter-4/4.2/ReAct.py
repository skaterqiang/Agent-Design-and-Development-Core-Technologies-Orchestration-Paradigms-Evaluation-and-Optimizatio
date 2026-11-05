import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs

try:
    API_KEY = get_api_key("tongyi")
    os.environ["DASHSCOPE_API_KEY"] = API_KEY
    print("API配置加载成功")
except ValueError as e:
    print(f"配置错误: {e}")
    sys.exit(1)

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from langchain.agents import create_agent  # v1 ReAct 代理
from langchain_core.messages import HumanMessage

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

# 初始化模型（qwen-max 支持工具调用，实现 ReAct 循环）
model = ChatTongyi(model_name="qwen-max")

# 创建工具列表
tools = [calculator, get_weather]

# ReAct 系统提示 - 指导模型使用 Thought/Action/Observation
system_prompt = """你是一个有用的助手。
使用以下格式进行 ReAct 推理：
Thought: 分析问题并决定下一步行动
Action: 使用工具名称和参数，如 ["calculator", {"expression": "2+2"}]
Observation: 等待工具结果

当任务完成时，直接给出 Final Answer。

当用户要求计算时，使用 calculator 工具。
当用户询问天气时，使用 get_weather 工具。
请用中文回复，并解释计算过程。"""

# 创建 ReAct 代理（自动实现 Thought → Action → Observation 循环）
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt
)

# 测试 ReAct 循环
if __name__ == "__main__":
    print("=== 测试数学计算 (ReAct 循环) ===")
    result1 = agent.invoke({
        "messages": [HumanMessage(content="计算 (15 + 25) * 3")]
    })
    final_message = result1["messages"][-1]
    print("最终结果:", final_message.content)
    
    # 查看完整 ReAct 轨迹（Thought/Action/Observation）
    print("\n完整对话历史:")
    for msg in result1["messages"]:
        print(f"- {msg.__class__.__name__}: {msg.content[:100]}...")
    
    print("\n=== 测试天气查询 (ReAct 循环) ===")
    result2 = agent.invoke({
        "messages": [HumanMessage(content="上海今天天气怎么样？")]
    })
    final_message2 = result2["messages"][-1]
    print("最终结果:", final_message2.content)

    # 查看完整 ReAct 轨迹（Thought/Action/Observation）
    print("\n完整对话历史:")
    for msg in result2["messages"]:
        print(f"- {msg.__class__.__name__}: {msg.content[:100]}...")


