#brain_chattemplate.py
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent, AgentState
import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")
from langchain_core.prompts import (
    ChatPromptTemplate,           # 聊天提示模板：构建多轮对话，支持 system/human/ai 角色消息
    PromptTemplate,               # 字符串提示模板：简单文本模板，支持变量替换
    SystemMessagePromptTemplate,  # 系统消息模板：专门用于 system 角色的提示模板
    HumanMessagePromptTemplate    # 用户消息模板：专门用于 human 角色的提示模板
)
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import SystemMessage


llm = ChatTongyi(
    model_name="qwen-max",         # 指定模型
    dashscope_api_key=API_KEY      # 传入API Key
)

from langchain_core.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)

# 简单字符串模板
prompt_template = PromptTemplate.from_template(
    "请用中文解释 {topic}，不超过 50 字。"
)
system_prompt = "你是一个有用的助手，专业知识渊博。"
# 使用 SystemMessagePromptTemplate 和 HumanMessagePromptTemplate 构建聊天模板
chat_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        system_prompt
    ),
    HumanMessagePromptTemplate.from_template(
        "请用中文解释 {topic}，不超过 50 字。"
    )
])

# 使用字符串模板
formatted_prompt = prompt_template.invoke({"topic": "LangChain"})
print("使用字符串模板")
print(formatted_prompt)
# 输出: 请用中文解释 LangChain，不超过 50 字。

# 使用聊天模板
chat_value = chat_template.invoke({"topic": "LangChain"})
print("使用聊天模板")
print(chat_value)  # ChatPromptValue 对象，包含格式化后的消息列表

# 字符串模板 + LLM,LCEL方式 LangChain Expression Language
result1 = prompt_template | llm
print("字符串模板 + LCEL")
print(result1.invoke({"topic": "LangChain"}))

# 聊天模板 + LLM
chain = chat_template | llm
result2 = chain.invoke({"topic": "LangChain"})
print("聊天模板 + LLM")
print(result2.content)

# 调用模型
agent = create_agent(
            llm
        )
print("聊天模板 + 智能体")
print(agent.invoke(chat_value))
