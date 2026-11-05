#SqlChatMessageHistory.py
# ConversationBufferMemory.py - SQLite持久化版本（已修复弃用警告）
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
import sys
import os
from sqlalchemy import create_engine  # 新增：创建数据库连接

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")

# SQLite 数据库文件路径 - 自动创建表
DB_PATH = "chat_history.db"

# 构建带记忆的聊天模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个友好的助手，记住用户偏好并个性化回复。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# 初始化 LLM
llm = ChatTongyi(
    model_name="qwen-max",
    dashscope_api_key=API_KEY
)

# 创建基础链（LLM + Prompt）
chain = prompt | llm

def get_session_history(session_id: str):
    """获取或创建 SQLite 会话历史 - 跨会话持久化（修复弃用警告）"""
    # 使用 connection 参数（SQLAlchemy引擎）
    connection = create_engine(f"sqlite:///{DB_PATH}")
    return SQLChatMessageHistory(
        session_id=session_id,
        connection=connection  # 1.0 新规范：使用 connection 而非 connection_string
    )

# 创建带会话历史的Runnable
conversation = RunnableWithMessageHistory(
    runnable=chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 测试跨会话持久化
session_id = "user_session_1"

print("=== 会话1：介绍自己 ===")
result1 = conversation.invoke(
    {"input": "我的名字是张三"},
    config={"configurable": {"session_id": session_id}}
)
print("AI:", result1.content)

print("\n=== 会话2：验证记忆（模拟重启后）===")
result2 = conversation.invoke(
    {"input": "你记得我叫什么吗？"},
    config={"configurable": {"session_id": session_id}}
)
print("AI:", result2.content)

print(f"\n 记忆已持久化到 {DB_PATH}，重启程序后仍有效")
