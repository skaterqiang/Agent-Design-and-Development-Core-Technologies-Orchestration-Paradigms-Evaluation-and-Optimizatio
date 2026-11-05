# 旅行规划智能体 (ReAct模式)

这是一个基于ReAct（Reasoning + Acting）模式的旅行规划智能体示例。

## ReAct模式说明

ReAct模式通过结构化的"思考-行动-观察"循环，使智能体能够：
- **思考（Thought）**：分析问题、评估选项、制定行动计划
- **行动（Action）**：调用工具获取信息或执行操作
- **观察（Observation）**：接收结果并用于后续推理

## 功能特点

1. **多步骤规划**：自动分解复杂任务为可执行的子任务
2. **工具集成**：支持航班查询、酒店推荐、景点信息等
3. **预算管理**：智能分配预算到各个旅行环节
4. **动态调整**：根据用户反馈和新信息调整计划

## 使用示例

```python
# 创建智能体
agent = TravelPlanningAgent()

# 用户请求
user_input = "我想去三亚旅行，3月中旬，预算5000元，帮我规划一下"

# 获取响应
response = agent.process(user_input)
print(response)
```

## 核心组件

- `search_flights()`: 查询航班信息
- `search_hotels()`: 查询酒店信息  
- `search_attractions()`: 查询景点信息
- `calculate_budget()`: 计算预算分配
- `write_todos()`: 创建任务清单（TodoListMiddleware）

这个示例展示了如何将ReAct模式应用于实际业务场景，创建一个有用的智能体助手。