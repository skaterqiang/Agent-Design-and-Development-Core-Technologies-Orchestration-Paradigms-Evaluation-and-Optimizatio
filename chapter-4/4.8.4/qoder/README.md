# 旅行规划 ReAct 智能体

## 概述

这是一个基于 ReAct（Reasoning + Acting）模式的旅行规划智能体，能够帮助用户制定完整的旅行计划。该智能体结合了 LangChain 的 ReAct 代理框架和 TodoList 中间件，实现了结构化的思考-行动-观察循环。

## 核心特性

### ReAct 模式实现
- **思考（Thought）**: 分析用户需求，制定解决策略
- **行动（Action）**: 调用适当的工具获取信息
- **观察（Observation）**: 整合工具返回的结果用于下一步决策

### 中间件增强
- **TodoListMiddleware**: 自动生成任务规划清单
- **结构化工作流**: 确保规划步骤的完整性和逻辑性

## 可用工具

1. **`get_destination_info`**: 获取目的地基本信息和推荐景点
2. **`calculate_travel_budget`**: 计算详细的旅行预算（交通、住宿、餐饮）
3. **`get_weather_forecast`**: 查询目的地天气预报
4. **`suggest_travel_itinerary`**: 生成个性化的行程建议

## 使用示例

```python
# 简单使用
result = agent.invoke({
    "messages": [HumanMessage(content="帮我规划一家三口去西安3天的旅行")]
})

# 复杂查询
result = agent.invoke({
    "messages": [HumanMessage(content="我需要一个人去成都出差5天，请帮忙规划行程")]
})
```

## 输出格式

智能体会生成包含以下内容的完整旅行方案：

- 🎯 **目的地介绍**: 城市特色和推荐景点
- 💰 **预算明细**: 交通、住宿、餐饮的详细费用
- 📅 **行程安排**: 每日活动建议
- 🌤️ **天气提醒**: 出行期间的天气预报

## 技术架构

```
ReAct Agent (qwen-max)
    ↓
TodoList Middleware (任务规划)
    ↓
Tools Execution Loop:
    → Thought (分析)
    → Action (工具调用)  
    → Observation (结果整合)
    → Repeat until completion
```

## 运行要求

- Python 3.9+
- LangChain 相关依赖
- 通义千问 API 密钥配置

## 测试用例

文件包含了两个测试场景：
1. 家庭旅行规划（西安3天）
2. 商务旅行规划（成都5天）

运行方式：
```bash
python travel_planner_react_agent.py
```

## 扩展建议

可以进一步扩展的功能：
- 添加更多目的地数据
- 集成真实的天气API
- 增加酒店预订工具
- 添加交通票务查询
- 支持多语言输出
