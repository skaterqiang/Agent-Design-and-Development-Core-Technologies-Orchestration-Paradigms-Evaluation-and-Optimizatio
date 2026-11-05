import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    # 设置通义千问API Key
    os.environ["DASHSCOPE_API_KEY"] = API_KEY
    print("API配置加载成功")
    print("配置信息:", get_all_configs())
except ValueError as e:
    print(f"配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)


#审核与评判模式
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models.tongyi import ChatTongyi
from pydantic import BaseModel, Field

llm = ChatTongyi(model="qwen-max")
# 状态（State）用于跟踪生成的内容、反馈和消息记录
class State(TypedDict):
    topic: str
    content: str
    feedback: str
    approved: bool
    messages: list[BaseMessage]

# 批评者（critic）使用的结构化反馈模式
class Feedback(BaseModel):
    grade: Literal["approved", "rejected"] = Field(
        description="如果内容符合标准则批准，否则拒绝。"
    )
    feedback: str = Field(
        description="若被拒绝，请提供详细的改进建议。"
    )

# 生成器节点（generator）：创建初始内容或根据反馈修订内容
def generator(state: State):
    if state.get("feedback"):
        prompt = ChatPromptTemplate.from_template(
            "围绕主题 {topic} 生成内容。上一版本：{content}。"
            "请根据以下反馈进行改进：{feedback}。"
            "仅输出改进后的内容。"
        )
    else:
        prompt = ChatPromptTemplate.from_template(
            "围绕主题 {topic} 生成高质量内容。"
            "要求：准确、安全、格式良好。"
            "仅输出内容本身。"
        )
    
    chain = prompt | llm
    new_content = chain.invoke({
        "topic": state["topic"],
        "content": state.get("content", ""),
        "feedback": state.get("feedback", "")
    }).content
    
    return {
        "content": new_content,
        "messages": state["messages"] + [{"role": "ai", "content": f"已生成：{new_content}"}]
    }

# 批评者节点（critic）：根据标准评估内容
def critic(state: State):
    critic_llm = llm.with_structured_output(Feedback)
    prompt = ChatPromptTemplate.from_template(
        "请评估以下关于 {topic} 的内容：{content}\n\n"
        "评估标准：事实准确性、格式规范、安全性。\n"
        "请返回结构化的反馈。"
    )
    
    chain = prompt | critic_llm
    feedback = chain.invoke({"topic": state["topic"], "content": state["content"]})
    
    return {
        "feedback": feedback.feedback,
        "approved": feedback.grade == "approved",
        "messages": state["messages"] + [{"role": "ai", "content": f"批评者：{feedback.json()}"}]
    }

# 条件路由：若批准则结束流程，否则返回生成器继续迭代
def route_critique(state: State):
    return END if state["approved"] else "generator"

# 构建工作流图
workflow = StateGraph(State)

workflow.add_node("generator", generator)
workflow.add_node("critic", critic)

workflow.add_edge(START, "generator")
workflow.add_edge("generator", "critic")
workflow.add_conditional_edges("critic", route_critique)

app = workflow.compile()
print(app.get_graph().draw_ascii())
# 使用一个主题运行流程（例如：代码生成请求）
result = app.invoke({
    "topic": "编写一个用于计算斐波那契数列的 Python 函数",
    "content": "",
    "feedback": "",
    "approved": False,
    "messages": []
})

print("最终通过的内容：", result["content"])
print("完成的迭代次数：", len([m for m in result["messages"] if "已生成" in m["content"] or "批评者" in m["content"]]))

