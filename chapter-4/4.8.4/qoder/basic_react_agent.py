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
from langchain_core.messages import HumanMessage

# 基础工具定义
@tool
def search_restaurants(location: str, cuisine: str = "") -> str:
    """搜索指定地点的餐厅信息"""
    restaurants = {
        "北京": {
            "川菜": ["蜀大侠火锅", "眉州东坡酒楼", "巴国布衣"],
            "粤菜": ["广州酒家", "炳胜品味", "利苑酒家"],
            "本地菜": ["全聚德烤鸭店", "便宜坊烤鸭店", "四季民福"]
        },
        "上海": {
            "本帮菜": ["老正兴菜馆", "绿波廊", "上海老饭店"],
            "粤菜": ["镛舍酒店餐厅", "翡翠36餐厅", "新荣记"],
            "日料": ["鮨一", "久兵卫", "隐泉之语"]
        }
    }
    
    city_restaurants = restaurants.get(location, {})
    if cuisine and cuisine in city_restaurants:
        return f"{location}推荐{cuisine}餐厅：{'、'.join(city_restaurants[cuisine][:3])}"
    elif cuisine:
        return f"{location}暂无{cuisine}餐厅信息，推荐尝试：{'、'.join(list(city_restaurants.keys())[:2])}"
    else:
        all_restaurants = []
        for cuisine_type, rest_list in city_restaurants.items():
            all_restaurants.extend(rest_list[:2])
        return f"{location}热门餐厅推荐：{'、'.join(all_restaurants[:5])}"

@tool
def get_local_attractions(city: str) -> str:
    """获取城市本地特色景点"""
    attractions = {
        "北京": ["故宫博物院", "天安门广场", "颐和园", "天坛公园", "八达岭长城"],
        "上海": ["外滩", "东方明珠塔", "豫园", "田子坊", "上海博物馆"],
        "西安": ["兵马俑", "大雁塔", "古城墙", "华清宫", "回民街"],
        "成都": ["宽窄巷子", "锦里古街", "武侯祠", "杜甫草堂", "大熊猫基地"]
    }
    
    city_attractions = attractions.get(city, [f"{city}本地景点"])
    return f"{city}必游景点：{'、'.join(city_attractions[:3])}，特色体验：{'、'.join(city_attractions[3:])}"

@tool
def estimate_expenses(city: str, days: int) -> str:
    """估算旅行花费"""
    daily_costs = {
        "北京": 800,  # 住宿400 + 餐饮200 + 交通200
        "上海": 950,  # 住宿500 + 餐饮250 + 交通200
        "西安": 600,  # 住宿300 + 餐饮150 + 交通150
        "成都": 550   # 住宿280 + 餐饮120 + 交通150
    }
    
    daily_cost = daily_costs.get(city, 600)
    total_cost = daily_cost * days
    
    return f"{city}{days}天旅行预算：约{total_cost}元（每日{daily_cost}元）"

# 初始化模型
model = ChatTongyi(model_name="qwen-max")

# 工具列表
tools = [search_restaurants, get_local_attractions, estimate_expenses]

# 基础 ReAct 系统提示
system_prompt = """你是一个城市探索助手，使用 ReAct 模式帮助用户了解目的地信息。

**ReAct 格式说明：**
Thought: 分析用户需求，决定要采取的行动
Action: 调用工具 [工具名, 参数]
Observation: 等待并处理工具返回的结果

**可用工具：**
- search_restaurants: 搜索餐厅信息
- get_local_attractions: 获取景点信息  
- estimate_expenses: 估算旅行费用

**工作流程：**
1. 分析用户询问的城市和需求
2. 依次调用相关工具收集信息
3. 整合所有信息给出完整回答

请用中文回复，清晰展示思考过程。"""

# 创建基础 ReAct 代理
agent = create_agent(
    model,
    tools,
    system_prompt=system_prompt
)

# 测试基础 ReAct 代理
if __name__ == "__main__":
    print("=== 基础 ReAct 代理测试 ===")
    
    # 测试用例1：餐厅查询
    print("\n--- 测试1：查询北京川菜餐厅 ---")
    result1 = agent.invoke({
        "messages": [HumanMessage(content="我想在北京吃正宗的川菜，有什么推荐吗？")]
    })
    
    print("最终回答:")
    print(result1["messages"][-1].content)
    
    print("\n完整对话轨迹:")
    for i, msg in enumerate(result1["messages"]):
        msg_type = msg.__class__.__name__
        print(f"Step {i}: {msg_type}")
        print(f"内容: {msg.content}")
        print("-" * 50)
    
    # 测试用例2：综合查询
    print("\n--- 测试2：3天西安旅行规划 ---")
    result2 = agent.invoke({
        "messages": [HumanMessage(content="我要去西安玩3天，想知道必去景点和大概花费")]
    })
    
    print("最终回答:")
    print(result2["messages"][-1].content)
    
    print("\n完整对话轨迹:")
    for i, msg in enumerate(result2["messages"]):
        msg_type = msg.__class__.__name__
        print(f"Step {i}: {msg_type}")
        print(f"内容: {msg.content}")
        print("-" * 50)
