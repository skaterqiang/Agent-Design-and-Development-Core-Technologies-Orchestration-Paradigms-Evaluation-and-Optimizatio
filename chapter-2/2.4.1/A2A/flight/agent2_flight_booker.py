# agent2_flight_booker.py
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
def search_flights(origin: str, destination: str, date: str) -> str:
    """搜索可用航班"""
    return f"找到从{origin}飞往{destination}于{date}的航班：航班AA123，450美元；航班UA456，520美元。"

@tool
def book_flight(flight_number: str, passenger_name: str) -> str:
    """Book a flight"""
    return f"已为{passenger_name}预订航班{flight_number}。确认号：ABC123"

flight_booker = create_agent(
    model=model,
    tools=[search_flights, book_flight],
    system_prompt="你是一名航班预订助手，根据旅行计划搜索并预订航班。"
)

