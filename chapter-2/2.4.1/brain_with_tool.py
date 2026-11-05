#brain_with_tool.py
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field
import sys
import os

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")

# 创建通义千问模型实例
llm = ChatTongyi(
    model_name="qwen-max",
    dashscope_api_key=API_KEY
)

# 定义工具的输入模式
class DistanceInput(BaseModel):
    """Input for distance calculation."""
    location_from: str = Field(description="起始位置 (例如: Earth)")
    location_to: str = Field(description="目标位置 (例如: Moon)")

# Calculate distance between two celestial bodies.
@tool(args_schema=DistanceInput)
def calculate_distance(location_from: str, location_to: str) -> str:
    """Calculate distance between two celestial bodies.
    
    Args:
        location_from: Starting celestial body
        location_to: Destination celestial body
    """
    # 定义不同天体间的距离 (单位: 公里)
    distances = {
        ("earth", "moon"): 384400,
        ("earth", "sun"): 149600000,
        ("moon", "earth"): 384400,
        ("sun", "earth"): 149600000,
    }
    
    key = (location_from.lower(), location_to.lower())
    
    if key in distances:
        dist_km = distances[key]
        dist_miles = dist_km * 0.621371
        return f"{location_from} 到 {location_to} 的距离：{dist_km:,} 公里 ({dist_miles:,.0f} 英里)"
    else:
        return f"暂无 {location_from} 到 {location_to} 的距离数据"

system_prompt = """你是一个严谨且乐于助人的助手。
- 当前你需要辅助同学们学习使用LangChain。
- 你可以使用可用的工具来帮助回答问题。"""

# 创建agent，传入tools列表
agent = create_agent(
    llm,
    tools=[calculate_distance],
    system_prompt=system_prompt
)

# 测试问题
# 测试不同的问题
test_questions = [
    "地球到月球有多远?",
    "月球到地球的距离是多少公里?",
    "太阳到地球的距离?",
]

for question in test_questions:
    print(f"\n问题: {question}")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    # 提取最后一条消息（AI的回答）
    final_message = result["messages"][-1]
    # 打印结果
    print(f"问题: {question}")
    print(f"回答: {final_message.content}")




