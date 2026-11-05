#!/usr/bin/env python3
"""
旅行规划智能体使用示例
"""

from travel_agent import TravelPlanningAgent

def main():
    # 创建旅行规划智能体实例
    agent = TravelPlanningAgent()
    
    # 示例1: 三亚旅行
    print("=== 示例1: 三亚旅行 ===")
    result1 = agent.process_query("我想去三亚旅行，3月中旬，预算5000元，帮我规划一下")
    print(result1)
    print("\n" + "="*50 + "\n")
    
    # 示例2: 北京出差
    print("=== 示例2: 北京出差 ===")
    result2 = agent.process_query("计划去北京出差，下周，预算3000元")
    print(result2)
    print("\n" + "="*50 + "\n")
    
    # 示例3: 上海游玩
    print("=== 示例3: 上海游玩 ===")
    result3 = agent.process_query("想去上海玩，4月份，预算8000元")
    print(result3)

if __name__ == "__main__":
    main()