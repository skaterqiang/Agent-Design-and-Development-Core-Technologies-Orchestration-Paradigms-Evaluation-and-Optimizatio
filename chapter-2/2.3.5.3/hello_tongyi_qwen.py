#hello_tongyi_qwen.py
from langchain_community.chat_models.tongyi import ChatTongyi
import sys
import os

# 添加上层 common 目录到 Python 路径（从 chapter-2/2.3.5.3 回到 code/common）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key  # 从上层 common 导入
# 从common/config.py获取API密钥
API_KEY = get_api_key("tongyi")
# 创建通义千问模型实例
# 此处以 qwen-max 模型为例，你可以在百炼控制台查看所有可用模型
llm = ChatTongyi(
    model_name="qwen-max",  # 指定模型
    dashscope_api_key=API_KEY  # 传入API Key
)
# 调用模型
question = "你是谁？"
response = llm.invoke(question) # 或者使用 llm(question)
# 打印模型回答
print(f"问题: {question}")
print(f"回答: {response}")
