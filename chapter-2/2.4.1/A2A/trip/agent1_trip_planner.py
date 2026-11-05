# agent1_trip_planner.py
import os
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")

os.environ["DASHSCOPE_API_KEY"] = API_KEY

model = ChatTongyi(model_name="qwen-max")

@tool
def research_destination(destination: str) -> str:
    """调研一个旅行目的地"""
    return f"{destination}的热门景点：博物馆、公园、餐厅"

@tool
def create_itinerary(destination: str, days: int) -> str:
    """制定一份旅行行程"""
    return f"{destination}的{days}日行程：第1天——观光，第2天——博物馆……"

trip_planner = create_agent(
    model=model,
    tools=[research_destination, create_itinerary],
    system_prompt="你是一名旅行规划助手，负责规划行程并与机票预订代理协调。"
)

