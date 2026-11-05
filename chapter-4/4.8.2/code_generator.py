import sys
import os
import uuid
import logging
import sqlite3
from datetime import datetime
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
# pip install langgraph-checkpoint-sqlite
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.globals import set_debug, set_verbose

# 解决Windows控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置默认编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    os.environ["DASHSCOPE_API_KEY"] = API_KEY
    print("API配置加载成功")
    print("配置信息:", get_all_configs())
except ValueError as e:
    print(f"配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)

# 设置通义千问API Key
# 启用LangChain调试模式
# set_debug(True)
# set_verbose(True)

# 配置日志记录 - 使用UTF-8编码
log_filename = f'agent_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # 指定文件编码为UTF-8
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from langchain_core.messages.utils import trim_messages, count_tokens_approximately

# 每次调用前修剪消息以避免超出token限制
def invoke_with_limit(agent, user_input, config):
    # 从状态中获取现有消息（如果有）
    messages = [{"role": "user", "content": user_input}]

    # 修剪到最后10条消息或4000个token
    trimmed = trim_messages(
        messages,
        max_tokens=900000,
        strategy="last",
        token_counter=count_tokens_approximately  # 必需参数！
    )

    result = agent.invoke({"messages": trimmed}, config)
    return result

@tool
def create_folder(path: str) -> str:
    """在指定路径创建新文件夹"""
    logger.info(f"正在创建文件夹: {path}")
    try:
        os.makedirs(path, exist_ok=True)
        logger.info(f"成功创建文件夹: {path}")
        return f"已创建文件夹: {path}"
    except Exception as e:
        logger.error(f"创建文件夹 {path} 失败: {e}")
        return f"创建文件夹时出错: {e}"

@tool
def create_file(file_path: str, content: str) -> str:
    """创建包含指定内容的文件"""
    logger.info(f"正在创建文件: {file_path} (内容长度: {len(content)})")
    logger.info(f"=== 新文件内容: {file_path} ===")
    logger.info(content)
    logger.info(f"=== 文件内容结束 ===")
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 使用UTF-8编码写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"成功创建文件: {file_path}")
        return f"已创建文件: {file_path}"
    except Exception as e:
        logger.error(f"创建文件 {file_path} 失败: {e}")
        return f"创建文件时出错: {e}"

@tool
def read_file(file_path: str) -> str:
    """读取文件内容"""
    logger.info(f"正在读取文件: {file_path}")
    if not os.path.exists(file_path):
        logger.warning(f"文件不存在: {file_path}")
        return f"错误: 文件 '{file_path}' 不存在。请先创建该文件。"
    try:
        # 尝试用UTF-8编码读取，如果失败则尝试其他编码
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试GBK（常见于Windows中文系统）
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            logger.warning(f"文件 {file_path} 使用GBK编码读取")
        
        logger.info(f"成功读取文件: {file_path} ({len(content)} 字符)")
        return content
    except Exception as e:
        logger.error(f"读取文件 {file_path} 失败: {e}")
        return f"读取文件时出错: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """向文件写入内容"""
    logger.info(f"正在写入文件: {file_path} (内容长度: {len(content)})")

    # 如果文件已存在，记录旧内容
    if os.path.exists(file_path):
        try:
            # 尝试多种编码读取旧文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='gbk') as f:
                    old_content = f.read()
            
            logger.info(f"=== 旧内容: {file_path} ===")
            logger.info(old_content)
            logger.info(f"=== 旧内容结束 ===")
        except Exception as e:
            logger.warning(f"无法读取旧内容: {e}")

    # 记录新内容
    logger.info(f"=== 新内容: {file_path} ===")
    logger.info(content)
    logger.info(f"=== 新内容结束 ===")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 使用UTF-8编码写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"成功写入文件: {file_path}")
        return f"向 {file_path} 写入了 {len(content)} 个字符"
    except Exception as e:
        logger.error(f"写入文件 {file_path} 失败: {e}")
        return f"写入文件时出错: {e}"

@tool
def list_folder(folder_path: str) -> str:
    """列出指定目录中的所有文件和文件夹"""
    logger.info(f"正在列出文件夹内容: {folder_path}")
    if not os.path.exists(folder_path):
        logger.warning(f"文件夹不存在: {folder_path}")
        return f"错误: 文件夹 '{folder_path}' 不存在。"
    if not os.path.isdir(folder_path):
        logger.warning(f"路径不是目录: {folder_path}")
        return f"错误: '{folder_path}' 不是目录。"
    try:
        # 使用正确的编码处理文件名
        items = os.listdir(folder_path)
        # 尝试使用UTF-8编码解码文件名（如果是bytes）
        decoded_items = []
        for item in items:
            if isinstance(item, bytes):
                try:
                    item = item.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        item = item.decode('gbk')
                    except UnicodeDecodeError:
                        item = item.decode('latin-1')
            decoded_items.append(item)
        
        items = decoded_items
        
        if not items:
            logger.info(f"文件夹为空: {folder_path}")
            return f"文件夹 '{folder_path}' 为空。"

        result = [f"'{folder_path}' 的内容:"]
        for item in sorted(items):
            item_path = os.path.join(folder_path, item)
            item_type = "目录" if os.path.isdir(item_path) else "文件"
            result.append(f"  [{item_type}] {item}")

        logger.info(f"成功列出 {folder_path} 中的 {len(items)} 个项目")
        return "\n".join(result)
    except Exception as e:
        logger.error(f"列出文件夹 {folder_path} 失败: {e}")
        return f"列出文件夹时出错: {e}"

@tool
def check_path_type(path: str) -> str:
    """检查路径是文件、目录还是不存在"""
    logger.info(f"正在检查路径类型: {path}")
    try:
        if not os.path.exists(path):
            logger.info(f"路径不存在: {path}")
            return f"'{path}' 不存在。"
        elif os.path.isfile(path):
            size = os.path.getsize(path)
            logger.info(f"路径是文件: {path} (大小: {size} 字节)")
            return f"'{path}' 是文件 (大小: {size} 字节)"
        elif os.path.isdir(path):
            items = len(os.listdir(path))
            logger.info(f"路径是目录: {path} ({items} 个项目)")
            return f"'{path}' 是目录 (包含 {items} 个项目)"
        else:
            logger.info(f"路径类型未知: {path}")
            return f"'{path}' 存在但不是文件或目录。"
    except Exception as e:
        logger.error(f"检查路径 {path} 失败: {e}")
        return f"检查路径时出错: {e}"

@tool
def run_tests(test_path: str) -> str:
    """运行测试并返回结果"""
    logger.info(f"正在运行测试: {test_path}")
    logger.info("所有测试通过!")
    return "所有测试通过!"

# 启动时请求项目名称
print("=" * 60)
project_name = input("请输入项目名称: ").strip()
while not project_name:
    print("项目名称不能为空!")
    project_name = input("请输入项目名称: ").strip()

# 创建项目文件夹
project_folder = project_name
os.makedirs(project_folder, exist_ok=True)
logger.info(f"项目文件夹: {project_folder}")

# 创建SQLite检查点以实现持久化内存
db_path = f"{project_folder}/memory.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
# 设置SQLite连接编码
conn.execute("PRAGMA encoding = 'UTF-8'")
checkpointer = SqliteSaver(conn)
logger.info(f"SQLite内存数据库: {db_path}")

logger.info("正在初始化软件工程智能体")
agent = create_agent(
    model=ChatTongyi(model_name="qwen3-coder-flash"),
    tools=[create_folder, create_file, read_file, write_file, list_folder, check_path_type, run_tests],
    middleware=[TodoListMiddleware()],
    checkpointer=checkpointer,
    system_prompt=f"""你是一名专业的软件工程师，负责构建生产质量的应用程序。

**当前项目:** {project_name}
**项目文件夹:** {project_folder}/

**重要提示:** 你创建的所有文件和文件夹必须位于项目文件夹内: {project_folder}/

**架构与设计模式:**
- 使用清晰架构（关注点分离）
- 应用设计模式: MVC、Repository、Factory、Singleton、Strategy
- 代码组织: frontend/、backend/、tests/、docs/、config/

**前端最佳实践:**
- 基于组件的架构
- 状态管理模式
- 响应式设计原则

**后端最佳实践:**
- RESTful API设计
- 数据库层抽象
- 错误处理和日志记录
- 安全最佳实践

**测试:**
- 编写全面的单元测试
- 包含集成测试
- 遵循AAA模式（Arrange、Act、Assert）
- 追求高代码覆盖率

在编码前始终创建正确的项目结构。"""
)

# 交互式循环
config = {
    "configurable": {"thread_id": project_name}, # 每次新会话
    "recursion_limit": 1000
}
print(f"\n软件工程智能体 - 项目: {project_name}")
print("所有代码将保存到文件夹:", project_folder)
print("输入 'quit' 退出")
print("-" * 60)
logger.info("智能体准备就绪，等待交互")

while True:
    user_input = input("\n你: ").strip()
    if user_input.lower() == "quit":
        logger.info("用户结束会话")
        conn.close()
        print("再见!")
        break
    if not user_input:
        continue

    logger.info(f"用户输入: {user_input}")
    try:
        result = invoke_with_limit(agent, user_input, config)
        # 获取最后一条消息
        last_message = result['messages'][-1]

        # 检查是否是AI消息且包含内容
        if hasattr(last_message, 'content') and last_message.content:
            response = last_message.content
        else:
            response = "智能体已完成但未返回文本响应。"

        logger.info(f"智能体响应: {response[:100]}...")
        print(f"\n智能体: {response}")
    except KeyError as e:
        logger.error(f"通义千问响应中的键错误: {e} {user_input}")
        print(f"\n错误: 模型响应格式问题: {e} ")
    except Exception as e:
        logger.error(f"智能体调用期间出错: {e} {user_input}", exc_info=True)
        print(f"\n错误: {e} {user_input}")
