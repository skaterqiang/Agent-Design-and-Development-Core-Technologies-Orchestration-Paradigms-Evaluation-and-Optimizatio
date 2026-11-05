# 协调者模式
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Literal, TypedDict, Optional

# 定义状态结构，包含协调者决策信息
class CoordinatorState(TypedDict):
    messages: list
    decision: Optional[Literal["taskA", "taskB", "both", "neither"]]

# 协调者代理：分析请求并决定路由
def coordinator_agent(state: CoordinatorState):
    """协调者：分析用户请求并决定路由到哪个专门代理"""
    user_input = state["messages"][-1].content.lower()
    
    # 基于规则的路由决策（实际应用中可使用LLM进行更智能的路由）
    if "查询" in user_input or "query" in user_input or "数据" in user_input:
        decision = "taskA"
        reasoning = "检测到数据查询请求，路由到数据查询代理"
    elif "处理" in user_input or "process" in user_input or "分析" in user_input:
        decision = "taskB"
        reasoning = "检测到数据处理请求，路由到数据处理代理"
    elif "复杂" in user_input or "complex" in user_input or "全部" in user_input:
        decision = "both"
        reasoning = "检测到复杂请求，需要两个代理协同处理"
    else:
        decision = "neither"
        reasoning = "请求类型不明确，需要人工干预"
    
    # 添加协调者决策消息
    decision_msg = f"协调者分析：{reasoning}\n决策：路由到 {decision}"
    
    return {
        "messages": [AIMessage(content=decision_msg)],
        "decision": decision
    }

# 专门代理A：数据查询专家
def taskA_agent(state: CoordinatorState):
    """专门代理A：处理数据查询任务"""
    user_request = state["messages"][0].content
    return {
        "messages": [AIMessage(content=f"数据查询代理完成：已查询数据库获取 '{user_request}' 的相关信息")],
        "decision": None  # 清除决策以继续流程
    }

# 专门代理B：数据处理专家
def taskB_agent(state: CoordinatorState):
    """专门代理B：处理数据分析任务"""
    user_request = state["messages"][0].content
    return {
        "messages": [AIMessage(content=f"数据处理代理完成：已分析 '{user_request}' 并生成报告")],
        "decision": None
    }

# 最终整合代理：汇总所有代理的结果
def final_integration_agent(state: CoordinatorState):
    """整合代理：汇总并返回最终结果"""
    # 收集所有代理的消息
    all_messages = []
    for msg in state["messages"]:
        if isinstance(msg, AIMessage):
            all_messages.append(msg.content)
    
    summary = " | ".join(all_messages[-3:])  # 取最后三条AI消息
    return {
        "messages": [AIMessage(content=f"整合完成：{summary}")],
        "decision": None
    }

# 定义路由条件函数
def route_decision(state: CoordinatorState):
    """根据协调者决策路由到不同分支"""
    decision = state.get("decision", "neither")
    
    if decision == "taskA":
        return "taskA"
    elif decision == "taskB":
        return "taskB"
    elif decision == "both":
        return "parallel_tasks"
    elif decision == "neither":
        return "human_intervention"
    else:
        return END

# 并行处理分支（当需要两个代理时）
def parallel_tasks(state: CoordinatorState):
    """并行执行两个专门代理"""
    # 在实际应用中，这里可以实现真正的并行执行
    # 这里简化为顺序执行两个代理
    result_a = taskA_agent(state)
    result_b = taskB_agent(state)
    
    combined_content = f"{result_a['messages'][0].content} | {result_b['messages'][0].content}"
    
    return {
        "messages": [AIMessage(content=combined_content)],
        "decision": None
    }

# 人工干预分支
def human_intervention(state: CoordinatorState):
    """当协调者无法确定路由时，请求人工干预"""
    return {
        "messages": [AIMessage(content="协调者无法确定处理路径，需要人工指定处理方式。请提供更具体的请求。")],
        "decision": None
    }

# 构建协调者模式的工作流图
graph = StateGraph(CoordinatorState)

# 添加节点
graph.add_node("coordinator", coordinator_agent)
graph.add_node("taskA", taskA_agent)
graph.add_node("taskB", taskB_agent)
graph.add_node("parallel_tasks", parallel_tasks)
graph.add_node("human_intervention", human_intervention)
graph.add_node("final_integration", final_integration_agent)

# 设置工作流路径
graph.add_edge(START, "coordinator")

# 条件路由：基于协调者的决策动态选择路径
graph.add_conditional_edges(
    "coordinator",
    route_decision,
    {
        "taskA": "taskA",
        "taskB": "taskB",
        "parallel_tasks": "parallel_tasks",
        "human_intervention": "human_intervention",
        END: END
    }
)

# 从专门代理到最终整合的路径
graph.add_edge("taskA", "final_integration")
graph.add_edge("taskB", "final_integration")
graph.add_edge("parallel_tasks", "final_integration")

# 人工干预后重新开始或结束
graph.add_edge("human_intervention", END)

# 最终整合后结束
graph.add_edge("final_integration", END)

# 编译图
graph = graph.compile()

# 运行协调者工作流
print("=== 协调者模式演示 ===\n")

# 测试不同场景
test_cases = [
    "查询用户数据",
    "处理订单分析",
    "复杂的数据查询和处理任务",
    "随便问问"
]

for i, query in enumerate(test_cases):
    print(f"\n测试 {i+1}: '{query}'")
    print("-" * 50)
    
    result = graph.invoke({"messages": [HumanMessage(content=query)], "decision": None})
    
    print("执行轨迹:")
    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"  AI: {msg.content}")
    
    print(f"最终决策状态: {result.get('decision', '完成')}")

# 可视化工作流
print("\n=== 工作流图 ===")
print(graph.get_graph().draw_ascii())

