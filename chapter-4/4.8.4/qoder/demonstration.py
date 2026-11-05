#!/usr/bin/env python3
"""
ReAct 模式演示脚本
展示了完整的 Reasoning + Acting 循环过程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'common'))
from config import get_api_key

def demonstrate_react_concept():
    """演示 ReAct 模式的概念和优势"""
    
    print("=" * 60)
    print("🤖 ReAct 模式智能体演示")
    print("=" * 60)
    
    print("\n📋 ReAct 模式核心概念:")
    print("""
    ReAct（Reasoning + Acting）模式是一种将AI模型的推理过程
    与外部工具调用能力相结合的方法。
    
    核心循环包含三个关键步骤：
    
    1. 🔍 思考（Thought）
       - 基于当前信息和任务目标进行分析
       - 评估可行选项并制定行动计划
       - 以自然语言形式显式呈现推理过程
    
    2. ⚙️ 行动（Action）  
       - 根据思考结果执行操作：
         * 调用外部工具获取信息
         * 或生成最终答案返回用户
    
    3. 👁️ 观察（Observation）
       - 接收工具调用的结果
       - 将新信息纳入上下文
       - 用于后续推理和决策
    """)
    
    print("\n🎯 ReAct 模式的优势:")
    print("""
    ✅ 透明性: 推理过程可见，便于调试和理解
    ✅ 灵活性: 可动态调用不同工具组合
    ✅ 可靠性: 通过观察反馈不断修正方向
    ✅ 可扩展: 易于添加新的工具和功能
    """)

def demonstrate_tools():
    """演示可用工具"""
    print("\n🛠️  可用工具展示:")
    print("=" * 40)
    
    # 导入工具进行演示
    from basic_react_agent import search_restaurants, get_local_attractions, estimate_expenses
    
    print("\n1. 餐厅搜索工具:")
    result = search_restaurants.invoke({"location": "北京", "cuisine": "川菜"})
    print(f"   输入: 北京川菜")
    print(f"   输出: {result}")
    
    print("\n2. 景点查询工具:")
    result = get_local_attractions.invoke({"city": "西安"})
    print(f"   输入: 西安")
    print(f"   输出: {result}")
    
    print("\n3. 费用估算工具:")
    result = estimate_expenses.invoke({"city": "上海", "days": 3})
    print(f"   输入: 上海3天")
    print(f"   输出: {result}")

def demonstrate_workflow():
    """演示完整工作流程"""
    print("\n🔄 完整工作流程示例:")
    print("=" * 40)
    
    example_query = "我要去成都旅游5天，请帮我规划一下"
    
    print(f"\n用户请求: {example_query}")
    print("\nReAct 循环过程:")
    print("""
    Step 1: Thought - 分析用户需求
           "用户想要5天成都旅游规划，需要提供景点、餐饮、预算信息"
           
    Step 2: Action - 调用 get_local_attractions 工具
           参数: {"city": "成都"}
           
    Step 3: Observation - 收到景点信息
           "成都必游景点：宽窄巷子、锦里古街、武侯祠..."
           
    Step 4: Thought - 继续收集信息
           "还需要了解餐饮和预算信息"
           
    Step 5: Action - 调用 search_restaurants 工具
           参数: {"location": "成都"}
           
    Step 6: Action - 调用 estimate_expenses 工具
           参数: {"city": "成都", "days": 5}
           
    Step 7: Thought - 整合所有信息
           "已收集完所需信息，准备生成完整回答"
           
    Step 8: Final Answer - 生成综合旅行方案
    """)

def main():
    """主演示函数"""
    try:
        demonstrate_react_concept()
        demonstrate_tools()
        demonstrate_workflow()
        
        print("\n" + "=" * 60)
        print("✨ 演示完成！")
        print("\n🚀 下一步建议:")
        print("1. 运行 basic_react_agent.py 查看实际代理执行")
        print("2. 运行 travel_planner_react_agent.py 体验增强版代理")
        print("3. 修改工具或提示词来适应不同业务场景")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        print("请检查环境配置和依赖安装")

if __name__ == "__main__":
    main()
