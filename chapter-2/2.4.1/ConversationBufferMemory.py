# ConversationBufferMemory.py 
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import sys
import os

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")

# 构建带记忆的聊天模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个友好的助手，记住用户偏好并个性化回复。"),
    MessagesPlaceholder(variable_name="history"),  # 工作记忆占位符
    ("human", "{input}")
])

# 初始化 LLM
llm = ChatTongyi(
    model_name="qwen-max",
    dashscope_api_key=API_KEY
)

# 创建基础链（LLM + Prompt）
chain = prompt | llm

# 初始化聊天历史存储
store = {}  # 简单的内存存储，生产环境使用 Redis 等

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """获取或创建会话历史"""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# 创建带会话历史的Runnable - 自动加载/保存聊天历史到指定session_id
conversation = RunnableWithMessageHistory(
    runnable=chain,                        # 基础链：prompt | llm (必需的第一个参数)
    get_session_history=get_session_history,  # 获取历史记录的函数 - 根据session_id从store中取ChatMessageHistory
    input_messages_key="input",             # 输入消息在输入dict中的键名 - 与prompt中的{input}对应
    history_messages_key="history"          # 历史消息在prompt中的占位符变量名 - 与prompt("history")对应
)

# 测试工作记忆
session_id = "user_session_1"

print("用户: 我的名字是张三")
result1 = conversation.invoke(
    {"input": "我的名字是张三"}, 
    config={"configurable": {"session_id": session_id}}
)
print(result1.content)

print("\n用户: 你记得我叫什么吗？")
result2 = conversation.invoke(
    {"input": "你记得我叫什么吗？"}, 
    config={"configurable": {"session_id": session_id}}
)
print(result2.content)
