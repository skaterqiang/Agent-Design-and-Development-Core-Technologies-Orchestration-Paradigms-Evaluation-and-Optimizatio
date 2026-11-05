#!/usr/bin/env python3
"""
测试修复后的 TravelPlanningAgent
验证 process_query 方法是否正常工作
"""

from travel_agent import TravelPlanningAgent

def test_process_query_method():
    """测试 process_query 方法"""
    print("=== 测试 TravelPlanningAgent.process_query 方法 ===")
    
    # 创建智能体实例
    agent = TravelPlanningAgent()
    
    # 测试查询
    test_query = "我想去三亚旅行，3月中旬，预算5000元，帮我规划一下"
    
    try:
        # 调用 process_query 方法
        result = agent.process_query(test_query)
        print("✅ 方法调用成功!")
        print(f"结果: {result}")
        return True
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_available_methods():
    """测试 TravelPlanningAgent 类的所有可用方法"""
    print("\n=== 检查 TravelPlanningAgent 可用方法 ===")
    
    agent = TravelPlanningAgent()
    methods = [method for method in dir(agent) if not method.startswith('_')]
    
    print("可用的公共方法:")
    for method in methods:
        print(f"  - {method}")
    
    # 检查关键方法是否存在
    required_methods = ['process_query', 'react_cycle', 'parse_action', 'execute_tool']
    print("\n关键方法检查:")
    for method in required_methods:
        exists = hasattr(agent, method)
        status = "✅ 存在" if exists else "❌ 缺失"
        print(f"  {method}: {status}")

if __name__ == "__main__":
    # 运行测试
    success = test_process_query_method()
    test_available_methods()
    
    if success:
        print("\n🎉 所有测试通过！process_query 方法已成功添加。")
    else:
        print("\n💥 测试失败，请检查实现。")
