import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key

try:
    API_KEY = get_api_key("tongyi")
    os.environ["DASHSCOPE_API_KEY"] = API_KEY
    print("API配置加载成功")
except ValueError as e:
    print(f"配置错误: {e}")
    sys.exit(1)

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware  # ReAct 增强中间件
from langchain_core.messages import HumanMessage

# 原有工具
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
        "北京": "晴天，25°C", "上海": "多云，28°C", 
        "西安": "小雨，30°C", "深圳": "晴天，32°C"
    }
    return f"{city} 当前天气: {weather_data.get(city, '暂无数据')}"

# 初始化模型
model = ChatTongyi(model_name="qwen-max")

# 工具列表
tools = [calculator, get_weather]

# ReAct + TodoList 系统提示
system_prompt = """你是一个有用的助手，使用 ReAct + TodoList 模式解决问题。

**工作流程：**
1. 使用 `write_todos` 生成任务清单
2. 按清单顺序执行：Thought → Action → Observation
3. 执行完一项后更新 `write_todos` 清单
4. 所有任务完成时给出 Final Answer

**工具使用规则：**
- 计算 → `calculator`
- 天气 → `get_weather` 
- 规划 → `write_todos`

请用中文回复，清晰展示每个步骤。"""

# 创建增强 ReAct 代理
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
    middleware=[
        TodoListMiddleware(  # 自动添加规划工具
            system_prompt="在开始复杂任务前，使用 `write_todos` 创建清晰的任务清单。"
        )
    ]
)

# 测试复杂多步任务（展示 TodoList + ReAct）
if __name__ == "__main__":
    print("=== 测试复杂多步任务 (TodoList + ReAct) ===")
    complex_query = "帮我规划周末行程：查西安天气，计算3天餐饮预算(每天300元)，给出总结"
    
    result = agent.invoke({
        "messages": [HumanMessage(content=complex_query)]
    })
    
    print("最终结果:", result["messages"][-1].content)
    print("\n=== 完整执行轨迹 (显示 TodoList 和 ReAct 步骤) ===")
    for i, msg in enumerate(result["messages"]):
        prefix = f"Step {i}: "
        print(f"{prefix}{msg.__class__.__name__}: {msg.content[:150]}...")


