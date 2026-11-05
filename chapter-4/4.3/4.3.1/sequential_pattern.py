# 顺序模式
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage

# 定义三个顺序执行的代理函数（专门的任务）
def taskA_agent(state: MessagesState):
    """代理 A：序列中的第一个任务 - 处理初始输入"""
    return {"messages": [AIMessage(content="任务 A 已完成：已分析输入")]}

def taskB_agent(state: MessagesState):
    """代理 B：第二个任务 - 使用任务 A 的输出作为输入"""
    last_message = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"任务 B 已完成：已处理 '{last_message}'")]}

def taskC_agent(state: MessagesState):
    """代理 C：最终任务 - 使用任务 B 的输出"""
    last_message = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"任务 C 已完成：来自 '{last_message}' 的最终结果")]}

# 使用显式边构建顺序工作流（无需 LLM 路由）
graph = StateGraph(MessagesState)
graph.add_node("taskA", taskA_agent)
graph.add_node("taskB", taskB_agent)
graph.add_node("taskC", taskC_agent)

graph.add_edge(START, "taskA")
graph.add_edge("taskA", "taskB")      # A 的输出 → B 的输入
graph.add_edge("taskB", "taskC")      # B 的输出 → C 的输入
graph.add_edge("taskC", END)

graph = graph.compile()

# 运行顺序工作流
human_query = {"messages": [HumanMessage(content="处理这些数据")]}
result = graph.invoke(human_query)

# 可视化并检查完整的执行跟踪
print(graph.get_graph().draw_ascii())
print("最终状态：")
for msg in result["messages"]:
    print(f"{msg.__class__.__name__}: {msg.content}")

