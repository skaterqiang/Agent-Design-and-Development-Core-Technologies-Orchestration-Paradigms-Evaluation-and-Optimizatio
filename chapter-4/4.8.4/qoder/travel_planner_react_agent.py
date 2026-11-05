import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'common'))
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
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.messages import HumanMessage
import json
from datetime import datetime, timedelta

# 旅行规划工具
@tool
def get_destination_info(destination: str) -> str:
    """获取目的地基本信息和推荐景点"""
    destination_data = {
        "北京": {
            "description": "中国首都，历史文化名城",
            "attractions": ["故宫", "天坛", "颐和园", "长城"],
            "climate": "四季分明，春秋季最佳"
        },
        "上海": {
            "description": "国际化大都市，现代与传统交融",
            "attractions": ["外滩", "东方明珠", "豫园", "迪士尼"],
            "climate": "亚热带季风气候，四季宜人"
        },
        "西安": {
            "description": "古都西安，十三朝古都",
            "attractions": ["兵马俑", "大雁塔", "古城墙", "华清池"],
            "climate": "温带大陆性气候，春秋最佳"
        },
        "成都": {
            "description": "天府之国，美食之都",
            "attractions": ["宽窄巷子", "锦里", "大熊猫基地", "青城山"],
            "climate": "亚热带湿润气候，全年适宜"
        }
    }
    
    info = destination_data.get(destination, {})
    if info:
        attractions_str = "、".join(info.get("attractions", []))
        return f"{destination}：{info.get('description', '')}。推荐景点：{attractions_str}。气候特点：{info.get('climate', '')}"
    else:
        return f"暂无{destination}的详细信息"

@tool
def calculate_travel_budget(destination: str, days: int, persons: int) -> str:
    """计算旅行预算（交通+住宿+餐饮）"""
    # 基础费用标准（每人每天）
    daily_costs = {
        "北京": {"transport": 200, "accommodation": 400, "food": 150},
        "上海": {"transport": 180, "accommodation": 500, "food": 200},
        "西安": {"transport": 150, "accommodation": 300, "food": 120},
        "成都": {"transport": 120, "accommodation": 280, "food": 100}
    }
    
    costs = daily_costs.get(destination, {"transport": 150, "accommodation": 300, "food": 150})
    
    total_transport = costs["transport"] * days * persons
    total_accommodation = costs["accommodation"] * days * persons
    total_food = costs["food"] * days * persons
    total_budget = total_transport + total_accommodation + total_food
    
    return json.dumps({
        "destination": destination,
        "days": days,
        "persons": persons,
        "budget_breakdown": {
            "transport": total_transport,
            "accommodation": total_accommodation,
            "food": total_food,
            "total": total_budget
        }
    }, ensure_ascii=False, indent=2)

@tool
def get_weather_forecast(destination: str, date: str) -> str:
    """获取目的地天气预报"""
    # 模拟天气数据
    weather_patterns = {
        "北京": {"晴": 0.6, "多云": 0.3, "雨": 0.1},
        "上海": {"晴": 0.5, "多云": 0.4, "雨": 0.1},
        "西安": {"晴": 0.7, "多云": 0.2, "雨": 0.1},
        "成都": {"晴": 0.4, "多云": 0.4, "雨": 0.2}
    }
    
    import random
    pattern = weather_patterns.get(destination, {"晴": 0.5, "多云": 0.3, "雨": 0.2})
    
    # 简单的概率选择
    rand = random.random()
    cumulative = 0
    weather = "晴"
    for condition, probability in pattern.items():
        cumulative += probability
        if rand <= cumulative:
            weather = condition
            break
    
    temperatures = {"北京": "15-25°C", "上海": "18-28°C", "西安": "12-26°C", "成都": "16-24°C"}
    temp = temperatures.get(destination, "15-25°C")
    
    return f"{destination} {date} 天气预报：{weather}，温度{temp}"

@tool
def suggest_travel_itinerary(destination: str, days: int) -> str:
    """生成旅行行程建议"""
    itineraries = {
        "北京": [
            "第1天：抵达北京，游览天安门广场和故宫",
            "第2天：参观颐和园和圆明园",
            "第3天：登长城，游览天坛"
        ],
        "上海": [
            "第1天：外滩夜景，南京路步行街",
            "第2天：东方明珠塔，上海博物馆",
            "第3天：迪士尼乐园一日游"
        ],
        "西安": [
            "第1天：兵马俑博物馆深度游",
            "第2天：古城墙骑行，回民街美食",
            "第3天：华清池，骊山一日游"
        ],
        "成都": [
            "第1天：宽窄巷子，锦里古街",
            "第2天：大熊猫繁育研究基地",
            "第3天：青城山道教文化游"
        ]
    }
    
    base_itinerary = itineraries.get(destination, [f"第{i+1}天：自由探索{destination}" for i in range(days)])
    
    # 调整行程长度
    if days <= len(base_itinerary):
        result = base_itinerary[:days]
    else:
        result = base_itinerary + [f"第{i+1}天：深度体验{destination}当地文化" for i in range(len(base_itinerary), days)]
    
    return "\n".join(result)

# 初始化模型
model = ChatTongyi(model_name="qwen-max")

# 工具列表
tools = [get_destination_info, calculate_travel_budget, get_weather_forecast, suggest_travel_itinerary]

# ReAct + 旅行规划系统提示
system_prompt = """你是一个专业的旅行规划助手，使用 ReAct + TodoList 模式帮助用户制定完美的旅行计划。

**工作流程：**
1. 使用 `write_todos` 生成详细的旅行规划任务清单
2. 按清单顺序执行：Thought → Action → Observation
3. 每完成一项任务就更新 `write_todos` 清单
4. 所有任务完成后给出完整的旅行方案

**可用工具：**
- `get_destination_info`: 获取目的地信息和推荐景点
- `calculate_travel_budget`: 计算详细旅行预算
- `get_weather_forecast`: 查询目的地天气预报
- `suggest_travel_itinerary`: 生成个性化行程建议
- `write_todos`: 制定任务规划清单

**输出要求：**
- 用中文回复，语言友好专业
- 明确展示思考过程和每个步骤的结果
- 最终提供完整的旅行方案包括：目的地介绍、预算明细、行程安排、天气提醒"""

# 创建增强 ReAct 代理
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt,
    middleware=[
        TodoListMiddleware(
            system_prompt="在开始旅行规划前，使用 `write_todos` 创建详细的规划任务清单，包括信息收集、预算计算、行程安排等步骤。"
        )
    ]
)

# 测试旅行规划代理
if __name__ == "__main__":
    print("=== 旅行规划 ReAct 代理测试 ===")
    
    # 测试用例1：简单旅行规划
    print("\n--- 测试1：3天西安家庭旅行规划 ---")
    test_query1 = "帮我规划一家三口去西安3天的旅行，需要了解景点、预算和行程安排"
    
    result1 = agent.invoke({
        "messages": [HumanMessage(content=test_query1)]
    })
    
    print("最终结果:")
    print(result1["messages"][-1].content)
    
    print("\n=== 完整执行轨迹 ===")
    for i, msg in enumerate(result1["messages"]):
        msg_type = msg.__class__.__name__
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"Step {i}: {msg_type}: {content_preview}")
    
    # 测试用例2：复杂旅行规划
    print("\n--- 测试2：5天成都商务旅行规划 ---")
    test_query2 = "我需要一个人去成都出差5天，请帮忙规划行程，重点了解天气情况和合理预算"
    
    result2 = agent.invoke({
        "messages": [HumanMessage(content=test_query2)]
    })
    
    print("最终结果:")
    print(result2["messages"][-1].content)
    
    print("\n=== 完整执行轨迹 ===")
    for i, msg in enumerate(result2["messages"]):
        msg_type = msg.__class__.__name__
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"Step {i}: {msg_type}: {content_preview}")
