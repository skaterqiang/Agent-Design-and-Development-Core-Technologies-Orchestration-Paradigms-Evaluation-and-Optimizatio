# 多任务并行模式
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage
from typing import Annotated
from langgraph.graph.message import add_messages  # 添加消息合并

# 定义状态 - 使用 Annotated 确保消息正确合并
class ParallelState(MessagesState):
    messages: Annotated[list, add_messages]

# 定义三个代理函数（taskA 和 taskB 将并行执行）
def taskA_agent(state: ParallelState):
    """代理 A：并行任务 - 处理输入的第一个方面"""
    return {"messages": [AIMessage(content="任务 A 已完成：已分析输入")]}

def taskB_agent(state: ParallelState):
    """代理 B：并行任务 - 处理输入的第二个方面"""
    return {"messages": [AIMessage(content="任务 B 已完成：独立分析输入")]}

def taskC_agent(state: ParallelState):
    """代理 C：合并任务 - 使用 taskA 和 taskB 的所有输出"""
    # 现在 state["messages"] 包含 taskA 和 taskB 的所有消息
    recent_messages = state["messages"][-2:]  # 获取最后两条消息（A 和 B）
    combined = " | ".join(msg.content for msg in recent_messages)
    return {"messages": [AIMessage(content=f"任务 C 已完成：合并结果 '{combined}'")]}

# 构建并行工作流（无需 LLM 路由）
graph = StateGraph(ParallelState)
graph.add_node("taskA", taskA_agent)
graph.add_node("taskB", taskB_agent)
graph.add_node("taskC", taskC_agent)

graph.add_edge(START, "taskA")    # START → taskA（并行）
graph.add_edge(START, "taskB")    # START → taskB（并行）
graph.add_edge("taskA", "taskC")  # taskA → taskC
graph.add_edge("taskB", "taskC")  # taskB → taskC
graph.add_edge("taskC", END)

graph = graph.compile()

# 运行并行工作流
human_query = {"messages": [HumanMessage(content="处理这些数据")]}
result = graph.invoke(human_query)

# 可视化并检查完整的执行跟踪
print(graph.get_graph().draw_ascii())
print("最终状态：")
for msg in result["messages"]:
    print(f"{msg.__class__.__name__}: {msg.content}")

