# 循环模式
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage
import operator

max_iterations = 5 #退出条件是最大迭代次数
# 定义增强的状态，包括迭代计数和自定义退出条件
class LoopState(TypedDict):
    messages: Annotated[list, operator.add]  # 保留消息历史
    iteration: int                          # 迭代次数跟踪
    should_exit: bool                       # 自定义退出条件标志

# 三个顺序执行的代理函数（专门的任务）- 无变化
def taskA_agent(state: LoopState):
    """代理 A：序列中的第一个任务 - 处理初始输入"""
    return {
        "messages": [AIMessage(content="任务 A 已完成：已分析输入")],
        "iteration": state["iteration"] + 1  # 每次循环递增
    }

def taskB_agent(state: LoopState):
    """代理 B：第二个任务 - 使用任务 A 的输出作为输入"""
    last_message = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"任务 B 已完成：已处理 '{last_message}'")]}

def taskC_agent(state: LoopState):
    """代理 C：最终任务 - 使用任务 B 的输出 + 设置退出条件示例"""
    last_message = state["messages"][-1].content
    
    # 示例退出条件逻辑：第3次迭代或特定内容时退出
    content = f"任务 C 已完成：来自 '{last_message}' 的最终结果 (迭代 {state['iteration']})"
    should_exit = state["iteration"] >= max_iterations  # 或其他自定义逻辑如检查内容质量
    
    return {
        "messages": [AIMessage(content=content)],
        "should_exit": should_exit
    }

# 主代理：接收循环输出进行最终处理
def main_agent(state: LoopState):
    """主代理：处理循环完成的最终输出"""
    final_result = state["messages"][-1].content
    return {
        "messages": [AIMessage(content=f"主代理最终输出：{final_result} (总迭代: {state['iteration']})")]
    }

# 退出条件评估函数（循环代理逻辑）
def should_continue(state: LoopState) -> Literal["continue_loop", "main_agent", END]:
    """评估退出条件：不满足则继续循环，满足则转主代理"""
    
    if not state["should_exit"]:
        return "continue_loop"  # 继续循环
    
    # 退出条件满足：转主代理
    return "main_agent"

# 构建循环工作流图
graph = StateGraph(LoopState)

# 添加节点
graph.add_node("taskA", taskA_agent)
graph.add_node("taskB", taskB_agent)
graph.add_node("taskC", taskC_agent)
graph.add_node("main_agent", main_agent)

# 定义循环序列：taskA → taskB → taskC
graph.add_edge(START, "taskA")
graph.add_edge("taskA", "taskB")
graph.add_edge("taskB", "taskC")

# 关键：taskC 后条件边实现循环逻辑
graph.add_conditional_edges(
    "taskC",
    should_continue,                    # 路由函数
    {
        "continue_loop": "taskA",       # 不满足条件：循环回 taskA
        "main_agent": "main_agent"      # 满足条件：转主代理
    }
)

# 主代理完成后结束
graph.add_edge("main_agent", END)

# 初始化迭代计数并编译
graph = graph.compile()

# 运行循环工作流
human_query = {
    "messages": [HumanMessage(content="处理这些数据")],
    "iteration": 0,     # 初始迭代0
    "should_exit": False
}

result = graph.invoke(human_query)

# 可视化并检查完整的执行跟踪
print(graph.get_graph().draw_ascii())
print("最终状态：")
for msg in result["messages"]:
    print(f"{msg.__class__.__name__}: {msg.content}")
print(f"总迭代次数: {result['iteration']}")
print(f"退出条件: {result['should_exit']}")

