# 导入LangGraph核心组件：状态图、消息状态类型、流程起点/终点标记
from langgraph.graph import StateGraph, MessagesState, START, END
# 导入LangChain消息类：AI消息（模型回复）和人类消息（用户输入）
from langchain_core.messages import AIMessage, HumanMessage

# 定义模拟LLM节点函数（用于演示流程）
# 接收当前消息状态，返回固定AI回复
def mock_llm(state: MessagesState):
    return {"messages": [AIMessage(content="hello world")]}

# 创建状态图实例，指定状态类型为消息列表（MessagesState）
graph = StateGraph(MessagesState)

# 添加节点：将"mock_llm"作为节点名，关联到mock_llm函数
# （显式命名节点便于流程管理）
graph.add_node("mock_llm", mock_llm)

# 添加流程边：从流程起点(START) → mock_llm节点
graph.add_edge(START, "mock_llm")

# 添加流程边：从mock_llm节点 → 流程终点(END)
graph.add_edge("mock_llm", END)

# 编译状态图：将流程定义转化为可执行的图结构
graph = graph.compile()

# 可视化工作流：打印ASCII格式的流程图（用于调试和理解）
print(graph.get_graph().draw_ascii())

# 创建人类查询输入：包含初始用户消息"Hi"
human_query = {"messages": [HumanMessage(content="Hi")]}

# 执行工作流：传入初始查询，触发流程执行
result = graph.invoke(human_query)

# 打印最终对话状态
print("最终对话状态：")
# 遍历结果中的消息列表
for msg in result["messages"]:
    # 格式化输出：消息类型（如AIMessage） + 内容
    print(f"{msg.__class__.__name__}: {msg.content}")
