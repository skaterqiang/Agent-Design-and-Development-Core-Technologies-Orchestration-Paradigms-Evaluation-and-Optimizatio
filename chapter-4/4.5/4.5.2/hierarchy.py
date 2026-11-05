# 多智能体分层任务分解模式
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Literal, TypedDict, Optional, List

# 定义分层状态结构
# Literal 类型允许你指定一个变量或参数只能是某个特定的、字面意义上的值。
class HierarchicalState(TypedDict):
    messages: List  # 保留所有层级的消息历史
    level1_decision: Optional[Literal["taskA", "taskB"]]  # 根协调者决策
    level2_decision: Optional[Literal["taskA1", "taskA2", "taskB1", "taskB2"]]  # 第二级决策

# === 根协调者 (第0级): 分解为 TaskA/TaskB ===
def root_coordinator(state: HierarchicalState):
    """根协调者: 将复杂任务分解为 TaskA 或 TaskB"""
    user_input = state["messages"][-1].content.lower()
    
    if "查询" in user_input or "query" in user_input or "数据" in user_input:
        decision = "taskA"
        reasoning = "根协调者分解: 数据相关任务 -> 路由到 TaskA (数据查询分支)"
    elif "处理" in user_input or "process" in user_input or "分析" in user_input:
        decision = "taskB"
        reasoning = "根协调者分解: 分析相关任务 -> 路由到 TaskB (数据处理分支)"
    else:
        decision = "taskA"
        reasoning = "请求不明确，默认路由到 TaskA"
    
    return {
        "messages": [AIMessage(content=reasoning)],
        "level1_decision": decision,
        "level2_decision": None
    }

# === 第一级: TaskA 协调者 -> 分解为 TaskA1/TaskA2 ===
def taskA_coordinator(state: HierarchicalState):
    """TaskA 协调者: 进一步将数据查询分解为具体的查询任务"""
    decision = state["level1_decision"]
    reasoning = f"TaskA 接收到任务 (来自根:{decision}) -> 进一步分解..."
    
    # 模拟 TaskA 内部决策逻辑
    sub_decision = "taskA1" if "用户" in state["messages"][0].content else "taskA2"
    sub_reasoning = "-> 数据库查询子任务" if sub_decision == "taskA1" else "-> API 查询子任务"
    
    return {
        "messages": [AIMessage(content=f"{reasoning}\n{sub_reasoning}")],
        "level2_decision": sub_decision
    }

# === 第一级: TaskB 协调者 -> 分解为 TaskB1/TaskB2 ===
def taskB_coordinator(state: HierarchicalState):
    """TaskB 协调者: 进一步将数据处理分解为具体的分析任务"""
    decision = state["level1_decision"]
    reasoning = f"TaskB 接收到任务 (来自根:{decision}) -> 进一步分解..."
    
    sub_decision = "taskB1" if "订单" in state["messages"][0].content else "taskB2"
    sub_reasoning = "-> 统计分析子任务" if sub_decision == "taskB1" else "-> 预测分析子任务"
    
    return {
        "messages": [AIMessage(content=f"{reasoning}\n{sub_reasoning}")],
        "level2_decision": sub_decision
    }

# === 第二级工作者代理: 执行叶任务 ===
def taskA1_worker(state: HierarchicalState):
    """TaskA1 工作者: 数据库查询"""
    return {"messages": [AIMessage(content="TaskA1 完成: 数据库查询结果已获取 (100条记录)")], 
            "level2_decision": None}

def taskA2_worker(state: HierarchicalState):
    """TaskA2 工作者: API 查询"""
    return {"messages": [AIMessage(content="TaskA2 完成: API 查询结果已获取 (50条记录)")], 
            "level2_decision": None}

def taskB1_worker(state: HierarchicalState):
    """TaskB1 工作者: 统计分析"""
    return {"messages": [AIMessage(content="TaskB1 完成: 订单统计分析报告已生成 (月增长 15%)")], 
            "level2_decision": None}

def taskB2_worker(state: HierarchicalState):
    """TaskB2 工作者: 预测分析"""
    return {"messages": [AIMessage(content="TaskB2 完成: 销售预测模型已训练 (准确率 92%)")], 
            "level2_decision": None}

# === 最终合成器: 聚合所有分层结果 ===
def final_synthesizer(state: HierarchicalState):
    """聚合所有分层结果"""
    all_ai_messages = [msg.content for msg in state["messages"] if isinstance(msg, AIMessage)]
    
    hierarchy_summary = " | ".join(all_ai_messages[-5:])  # 最后5条消息（涵盖完整层级）
    final_result = f"分层任务分解完成！\n执行轨迹: {hierarchy_summary}"
    
    return {"messages": [AIMessage(content=final_result)], 
            "level1_decision": None, "level2_decision": None}

# === 路由函数 ===
def route_to_level1(state: HierarchicalState):
    """根协调者 -> 第一级路由"""
    return state["level1_decision"] or END

def route_to_level2(state: HierarchicalState):
    """第一级 -> 第二级工作者路由"""
    decision = state["level2_decision"]
    return decision or "final_synthesizer"

# 构建分层工作流图
graph = StateGraph(HierarchicalState)

# 添加所有节点
graph.add_node("root_coordinator", root_coordinator)
graph.add_node("taskA_coordinator", taskA_coordinator)
graph.add_node("taskB_coordinator", taskB_coordinator)
graph.add_node("taskA1_worker", taskA1_worker)
graph.add_node("taskA2_worker", taskA2_worker)
graph.add_node("taskB1_worker", taskB1_worker)
graph.add_node("taskB2_worker", taskB2_worker)
graph.add_node("final_synthesizer", final_synthesizer)

# 工作流路径定义
graph.add_edge(START, "root_coordinator")

# 第0级 -> 第1级条件路由
graph.add_conditional_edges(
    "root_coordinator",
    route_to_level1,
    {"taskA": "taskA_coordinator", "taskB": "taskB_coordinator"}
)

# 第1级 -> 第2级条件路由
graph.add_conditional_edges(
    "taskA_coordinator",
    route_to_level2,
    {"taskA1": "taskA1_worker", "taskA2": "taskA2_worker"}
)
graph.add_conditional_edges(
    "taskB_coordinator", 
    route_to_level2,
    {"taskB1": "taskB1_worker", "taskB2": "taskB2_worker"}
)

# 第2级工作者 -> 最终合成器
graph.add_edge("taskA1_worker", "final_synthesizer")
graph.add_edge("taskA2_worker", "final_synthesizer")
graph.add_edge("taskB1_worker", "final_synthesizer")
graph.add_edge("taskB2_worker", "final_synthesizer")

graph.add_edge("final_synthesizer", END)

# 编译并测试分层工作流
graph = graph.compile()
print(graph.get_graph().draw_ascii())
print("=== 多智能体分层任务分解演示 ===\n")

test_cases = [
    "查询用户数据",      # -> 根->TaskA->TaskA1
    "处理订单分析",      # -> 根->TaskB->TaskB1  
    "预测销售趋势"       # -> 根->TaskB->TaskB2
]

for i, query in enumerate(test_cases):
    print(f"\n测试 {i+1}: '{query}'")
    print("=" * 60)
    
    result = graph.invoke({
        "messages": [HumanMessage(content=query)], 
        "level1_decision": None, 
        "level2_decision": None
    })
    
    print("分层执行轨迹:")
    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"  {msg.content}")
    
    print(f"\n最终状态: L1={result.get('level1_decision')}, L2={result.get('level2_decision')}")

print("\n" + "="*60)
print("多级任务分解完成！每个代理只处理其级别的决策和执行")
