#!/usr/bin/env python3
"""
旅行规划助手 - 使用ReAct模式的智能体示例

ReAct模式通过"思考-行动-观察"循环来解决复杂任务：
1. 思考(Thought): 分析当前情况，决定下一步行动
2. 行动(Action): 调用工具或生成最终答案  
3. 观察(Observation): 获取工具结果，更新上下文
"""

import json
import re
from typing import List, Dict, Any, Callable
from datetime import datetime, timedelta

# 模拟工具函数
def search_weather(location: str, date: str) -> str:
    """查询目的地天气"""
    # 这里应该是真实的API调用，现在模拟返回
    weather_data = {
        "三亚": "温暖晴朗，气温25-30°C，适合海滩活动",
        "北京": "春季温和，气温10-20°C，偶有风沙",
        "上海": "春暖花开，气温15-22°C，湿度适中",
        "成都": "多云转晴，气温18-25°C，空气质量良好"
    }
    return weather_data.get(location, f"{location}天气信息暂不可用")

def search_flights(origin: str, destination: str, date: str) -> List[Dict]:
    """查询航班信息"""
    # 模拟航班数据
    flights = [
        {"airline": "中国国航", "flight": "CA1234", "departure": "08:00", "arrival": "11:30", "price": 1200},
        {"airline": "南方航空", "flight": "CZ5678", "departure": "14:20", "arrival": "17:50", "price": 980},
        {"airline": "海南航空", "flight": "HU9012", "departure": "20:15", "arrival": "23:45", "price": 1100}
    ]
    return flights

def search_hotels(location: str, check_in: str, check_out: str, budget: float) -> List[Dict]:
    """查询酒店信息"""
    # 模拟酒店数据
    hotels = [
        {"name": "三亚湾海景酒店", "stars": 4, "price_per_night": 450, "amenities": ["海景", "游泳池", "免费WiFi"]},
        {"name": "亚龙湾度假村", "stars": 5, "price_per_night": 800, "amenities": ["私人海滩", "SPA", "多个餐厅"]},
        {"name": "三亚经济型酒店", "stars": 3, "price_per_night": 280, "amenities": ["免费停车", "早餐", "空调"]}
    ]
    
    # 根据预算过滤
    nights = 3  # 假设3晚
    affordable_hotels = [h for h in hotels if h["price_per_night"] * nights <= budget * 0.4]
    return affordable_hotels[:2]  # 返回前2个

def search_attractions(location: str) -> List[str]:
    """查询景点信息"""
    attractions = {
        "三亚": [
            "亚龙湾热带天堂森林公园",
            "天涯海角",
            "南山文化旅游区", 
            "蜈支洲岛",
            "大东海海滩"
        ],
        "北京": [
            "故宫博物院",
            "天安门广场",
            "颐和园",
            "长城",
            "798艺术区"
        ],
        "上海": [
            "外滩",
            "东方明珠塔",
            "豫园",
            "迪士尼乐园",
            "田子坊"
        ]
    }
    return attractions.get(location, [f"{location}主要景点"])

def calculate_budget_breakdown(total_budget: float, flights_cost: float, hotel_cost: float) -> Dict:
    """计算预算分配"""
    remaining = total_budget - flights_cost - hotel_cost
    activities_budget = remaining * 0.6
    food_budget = remaining * 0.3
    emergency_budget = remaining * 0.1
    
    return {
        "total_budget": total_budget,
        "flights": flights_cost,
        "hotel": hotel_cost,
        "activities": activities_budget,
        "food": food_budget,
        "emergency": emergency_budget,
        "remaining": remaining
    }

# ReAct智能体核心类
class TravelPlanningAgent:
    def __init__(self):
        self.tools = {
            "search_weather": search_weather,
            "search_flights": search_flights,
            "search_hotels": search_hotels,
            "search_attractions": search_attractions,
            "calculate_budget_breakdown": calculate_budget_breakdown
        }
        self.execution_history = []
        
    def process_query(self, query: str) -> str:
        """
        处理用户查询的主要入口方法
        确保与外部调用接口的一致性
        """
        return self.react_cycle(query)
    
    def parse_action(self, response: str) -> tuple:
        """解析模型响应，提取思考和行动"""
        thought_match = re.search(r'思考[:：]\s*(.*?)(?:\n|$)', response)
        action_match = re.search(r'行动[:：]\s*(.*?)(?:\n|$)', response)
        observation_match = re.search(r'观察[:：]\s*(.*?)(?:\n|$)', response)
        
        thought = thought_match.group(1) if thought_match else ""
        action = action_match.group(1) if action_match else ""
        observation = observation_match.group(1) if observation_match else ""
        
        return thought.strip(), action.strip(), observation.strip()
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具函数"""
        if tool_name in self.tools:
            try:
                result = self.tools[tool_name](**kwargs)
                return result
            except Exception as e:
                return f"执行工具时出错: {str(e)}"
        else:
            return f"未知工具: {tool_name}"
    
    def generate_prompt(self, user_query: str, context: str = "") -> str:
        """生成系统提示"""
        system_prompt = f"""
你是一个专业的旅行规划助手，使用ReAct（Reasoning + Acting）模式来帮助用户规划旅行。
请严格按照以下格式响应：

思考: [你的推理过程，分析当前信息，决定下一步需要什么信息]
行动: [工具调用指令，格式为 "工具名(参数1=值1, 参数2=值2)" 或 "完成(最终答案)"]
观察: [工具调用的结果，由系统提供]

可用工具：
1. search_weather(location="地点", date="日期") - 查询天气
2. search_flights(origin="出发地", destination="目的地", date="日期") - 查询航班
3. search_hotels(location="地点", check_in="入住日期", check_out="退房日期", budget=预算) - 查询酒店
4. search_attractions(location="地点") - 查询景点
5. calculate_budget_breakdown(total_budget=总预算, flights_cost=机票费用, hotel_cost=酒店费用) - 计算预算分配

用户需求: {user_query}
当前上下文: {context}

请开始规划！
"""
        return system_prompt
    
    def react_cycle(self, user_query: str, max_steps: int = 8) -> str:
        """执行ReAct循环"""
        context = ""
        step = 0
        
        print(f"=== 旅行规划助手演示 ===")
        print(f"用户: {user_query}")
        
        while step < max_steps:
            # 生成提示并获取响应
            prompt = self.generate_prompt(user_query, context)
            
            # 模拟模型响应（在实际应用中这里会调用真正的LLM）
            response = self.simulate_model_response(prompt, context, user_query)
            
            # 解析响应
            thought, action, observation = self.parse_action(response)
            
            if thought:
                print(f"思考: {thought}")
            if action:
                print(f"行动: {action}")
            
            # 检查是否完成
            if action.startswith("完成("):
                final_answer = action[3:-1]  # 去掉"完成("和")"
                print(f"助手: {final_answer}")
                return final_answer
            
            # 执行工具调用
            if action and not action.startswith("完成("):
                # 解析工具调用
                tool_call = self.parse_tool_call(action)
                if tool_call:
                    tool_name, args = tool_call
                    tool_result = self.execute_tool(tool_name, **args)
                    
                    # 更新观察
                    observation_text = str(tool_result)
                    print(f"观察: {observation_text}")
                    
                    # 更新上下文
                    context += f"\n工具调用: {action}\n结果: {observation_text}"
                    self.execution_history.append({
                        "step": step,
                        "thought": thought,
                        "action": action,
                        "observation": observation_text
                    })
            
            step += 1
        
        return "规划超时，请简化需求重试。"
    
    def parse_tool_call(self, action: str) -> tuple:
        """解析工具调用字符串"""
        import ast
        
        # 提取工具名和参数
        match = re.match(r'(\w+)\((.*)\)', action)
        if not match:
            return None
        
        tool_name = match.group(1)
        args_str = match.group(2)
        
        if not args_str:
            return (tool_name, {})
        
        # 解析参数
        args = {}
        try:
            # 尝试用ast解析（适用于简单情况）
            if '=' in args_str:
                for arg in args_str.split(','):
                    key, value = arg.strip().split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 处理字符串值
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # 尝试转换为数字
                    try:
                        value = float(value)
                        if value.is_integer():
                            value = int(value)
                    except ValueError:
                        pass
                    args[key] = value
            else:
                # 单个参数
                value = args_str.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                args["query"] = value
        except Exception as e:
            print(f"解析参数时出错: {e}")
            args = {"raw_args": args_str}
        
        return (tool_name, args)
    
    def simulate_model_response(self, prompt: str, context: str, user_query: str) -> str:
        """模拟模型响应（在实际应用中替换为真实LLM调用）"""
        # 提取用户需求中的关键信息
        import re
        
        location = ""
        date = ""
        budget = 0
        
        # 从用户查询中提取信息
        location_match = re.search(r'(去|到|前往)\s*([北京|上海|广州|深圳|三亚|成都|杭州|西安|重庆|武汉|苏州|南京|天津|郑州|长沙|青岛|宁波|大连|厦门|哈尔滨])', user_query)
        if location_match:
            location = location_match.group(2)
        
        date_match = re.search(r'(\d+月|\d+年\d+月|\d+月\d+日|下个月|这个月|明年|今年)', user_query)
        if date_match:
            date = date_match.group(1)
        
        budget_match = re.search(r'预算(\d+万?|\d+元)', user_query)
        if budget_match:
            budget_str = budget_match.group(1)
            if '万' in budget_str:
                budget = int(budget_str.replace('万', '')) * 10000
            else:
                budget = int(budget_str.replace('元', ''))
        
        # 根据当前上下文决定下一步行动
        if not context:
            # 第一步：创建任务清单
            return f"""思考: 用户需要旅行规划服务。首先需要明确目的地、时间、预算等基本信息，然后依次查询天气、航班、酒店、景点，并进行预算分配。
行动: 完成(正在为您规划{location}的旅行行程，请稍候...)"""
        
        elif "天气" not in context and location:
            return f"""思考: 需要先了解目的地的天气情况，以便给出合适的旅行建议。
行动: search_weather(location="{location}", date="{date}")"""
        
        elif "航班" not in context and location:
            return f"""思考: 接下来需要查询航班信息，了解交通选择和费用。
行动: search_flights(origin="北京", destination="{location}", date="{date}")"""
        
        elif "酒店" not in context and location and budget > 0:
            # 假设3晚住宿
            check_in = "2024-03-15"
            check_out = "2024-03-18"
            return f"""思考: 需要查询符合预算的酒店选项。
行动: search_hotels(location="{location}", check_in="{check_in}", check_out="{check_out}", budget={budget})"""
        
        elif "景点" not in context and location:
            return f"""思考: 查询当地的主要景点，为行程安排提供参考。
行动: search_attractions(location="{location}")"""
        
        elif "预算" not in context:
            # 估算费用
            flights_cost = 1000  # 默认值
            hotel_cost = 1200    # 默认值
            return f"""思考: 进行详细的预算分配，确保各项支出合理。
行动: calculate_budget_breakdown(total_budget={budget}, flights_cost={flights_cost}, hotel_cost={hotel_cost})"""
        
        else:
            # 生成最终行程
            weather_info = "温暖晴朗，适合旅行"
            flights_info = "推荐南方航空CZ5678航班，价格980元"
            hotels_info = "推荐三亚湾海景酒店，450元/晚"
            attractions_info = "必游景点：亚龙湾热带天堂森林公园、天涯海角、蜈支洲岛"
            budget_info = f"总预算{budget}元已合理分配"
            
            final_plan = f"""
🎯 {location}旅行规划完成！

📅 时间：{date}
💰 预算：{budget}元

🌤️ 天气：{weather_info}

✈️ 交通：{flights_info}

🏨 住宿：{hotels_info}

🏞️ 景点推荐：
{attractions_info}

📊 预算分配：{budget_info}

祝您旅途愉快！如有其他需求，请随时告知。
"""
            return f"""思考: 已收集所有必要信息，可以生成完整的旅行规划方案。
行动: 完成({final_plan})"""

# 创建智能体实例
def create_travel_agent():
    """创建旅行规划智能体"""
    return TravelPlanningAgent()

# 演示函数
def demo():
    """演示智能体功能"""
    agent = create_travel_agent()
    
    # 测试用例
    test_queries = [
        "我想去三亚旅行，3月中旬，预算5000元，帮我规划一下",
        "计划去北京出差，下周，预算3000元",
        "想去上海玩，4月份，预算8000元"
    ]
    
    for query in test_queries:
        print("\n" + "="*50)
        result = agent.react_cycle(query)
        print("="*50)

if __name__ == "__main__":
    demo()