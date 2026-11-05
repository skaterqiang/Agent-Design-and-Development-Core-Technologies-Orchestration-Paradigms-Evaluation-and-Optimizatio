"""优化版智能体技能示例 - 支持渐进式PDF技能加载"""
import asyncio
import sys
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentSkillManager:
    """智能体技能管理器"""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.skills_loaded = {
            'basic_tools': False,
            'pdf_basic': False,
            'pdf_advanced': False,
            'agentscope_analysis': False
        }
        
    def _load_api_key(self) -> str:
        """加载API密钥"""
        try:
            api_key = get_api_key("tongyi")
            os.environ["DASHSCOPE_API_KEY"] = api_key
            logger.info("[SUCCESS] API配置加载成功")
            logger.info(f"[CONFIG] 配置信息: {get_all_configs()}")
            return api_key
        except ValueError as e:
            logger.error(f"[ERROR] 配置错误: {e}")
            logger.error("[ERROR] 请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
            raise
    
    def get_available_skills(self) -> List[str]:
        """获取可用技能列表"""
        return [skill for skill, loaded in self.skills_loaded.items() if loaded]
    
    def get_unloaded_skills(self) -> List[str]:
        """获取未加载技能列表"""
        return [skill for skill, loaded in self.skills_loaded.items() if not loaded]

class SkillLoader:
    """技能加载器 - 支持渐进式加载"""
    
    @staticmethod
    async def load_basic_tools(toolkit) -> bool:
        """加载基础工具技能"""
        try:
            from agentscope.tool import (
                execute_shell_command,
                execute_python_code,
                view_text_file,
            )
            
            toolkit.register_tool_function(execute_shell_command)
            toolkit.register_tool_function(execute_python_code)
            toolkit.register_tool_function(view_text_file)
            
            logger.info("[LOADED] 基础工具技能加载成功")
            return True
        except Exception as e:
            logger.error(f"[FAILED] 基础工具技能加载失败: {e}")
            return False
    
    @staticmethod
    async def load_pdf_basic_skills(toolkit) -> bool:
        """加载PDF基础技能"""
        try:
            # 注册PDF技能目录
            toolkit.register_agent_skill("./pdf")
            logger.info("[LOADED] PDF基础技能加载成功")
            return True
        except Exception as e:
            logger.error(f"[FAILED] PDF基础技能加载失败: {e}")
            return False
    
    @staticmethod
    async def load_agentscope_analysis_skills(toolkit) -> bool:
        """加载AgentScope分析技能"""
        try:
            toolkit.register_agent_skill("./analyzing-agentscope-library")
            logger.info("[LOADED] AgentScope分析技能加载成功")
            return True
        except Exception as e:
            logger.error(f"[FAILED] AgentScope分析技能加载失败: {e}")
            return False

class AgentFactory:
    """智能体工厂类"""
    
    @staticmethod
    def create_react_agent(name: str, sys_prompt: str, toolkit, memory) -> Any:
        """创建ReAct智能体"""
        try:
            from agentscope.agent import ReActAgent
            from agentscope.formatter import DashScopeChatFormatter
            from agentscope.model import DashScopeChatModel
            
            agent = ReActAgent(
                name=name,
                sys_prompt=sys_prompt,
                model=DashScopeChatModel(
                    api_key=os.environ.get("DASHSCOPE_API_KEY"),
                    model_name="qwen-max",
                    enable_thinking=False,
                    stream=True,
                ),
                formatter=DashScopeChatFormatter(),
                toolkit=toolkit,
                memory=memory,
            )
            logger.info(f"[CREATED] 智能体 '{name}' 创建成功")
            return agent
        except Exception as e:
            logger.error(f"[FAILED] 智能体创建失败: {e}")
            raise

class InteractiveSession:
    """交互式会话管理器"""
    
    def __init__(self, agent):
        self.agent = agent
        self.session_history = []
    
    async def send_message(self, content: str, role: str = "user") -> Dict[str, Any]:
        """发送消息并记录历史"""
        try:
            from agentscope.message import Msg
            
            message = Msg(role, content, role)
            response = await self.agent(message)
            
            interaction = {
                'request': content,
                'response': str(response),
                'timestamp': asyncio.get_event_loop().time()
            }
            self.session_history.append(interaction)
            
            logger.info(f"[MESSAGE] 发送消息: {content[:50]}...")
            return interaction
        except Exception as e:
            logger.error(f"[ERROR] 消息发送失败: {e}")
            raise
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        return {
            'total_interactions': len(self.session_history),
            'session_duration': len(self.session_history) > 0 and 
                              (self.session_history[-1]['timestamp'] - self.session_history[0]['timestamp']) or 0
        }

async def initialize_agent_with_skills(skill_manager: AgentSkillManager, 
                                     skills_to_load: List[str]) -> tuple:
    """初始化带有指定技能的智能体"""
    try:
        from agentscope.tool import Toolkit
        from agentscope.memory import InMemoryMemory
        
        # 创建工具包和内存
        toolkit = Toolkit()
        memory = InMemoryMemory()
        
        # 渐进式加载技能
        loader = SkillLoader()
        
        # 加载请求的技能
        for skill_name in skills_to_load:
            if skill_name == 'basic_tools':
                success = await loader.load_basic_tools(toolkit)
            elif skill_name == 'pdf_basic':
                success = await loader.load_pdf_basic_skills(toolkit)
            elif skill_name == 'agentscope_analysis':
                success = await loader.load_agentscope_analysis_skills(toolkit)
            else:
                logger.warning(f"[WARNING] 未知技能: {skill_name}")
                continue
                
            if success:
                skill_manager.skills_loaded[skill_name] = True
            else:
                logger.error(f"[FAILED] 技能加载失败: {skill_name}")
        
        # 创建智能体
        agent_factory = AgentFactory()
        agent = agent_factory.create_react_agent(
            name="Friday",
            sys_prompt="""您是一个名为Friday的有用助手。

# 重要提示
- 不要做任何假设。关于AgentScope库的所有知识必须来自您配备的技能。
- 您可以访问各种工具来帮助用户完成任务。
- 请清晰地说明您正在做什么以及为什么这样做。""",
            toolkit=toolkit,
            memory=memory
        )
        
        return agent, toolkit, memory
        
    except Exception as e:
        logger.error(f"[ERROR] 智能体初始化失败: {e}")
        raise

async def run_interactive_demo():
    """运行交互式演示"""
    try:
        # 初始化技能管理器
        skill_manager = AgentSkillManager()
        
        # 分阶段加载技能并测试
        stages = [
            {
                'name': '阶段1 - 基础工具',
                'skills': ['basic_tools'],
                'test_questions': [
                    "What skills do you have?",
                    "Can you show me what tools you can use?"
                ]
            },
            {
                'name': '阶段2 - PDF基础技能',
                'skills': ['basic_tools', 'pdf_basic'],
                'test_questions': [
                    "Can you help me create a PDF file?",
                    "How can I work with PDF documents?"
                ]
            },
            {
                'name': '阶段3 - 完整技能集',
                'skills': ['basic_tools', 'pdf_basic', 'agentscope_analysis'],
                'test_questions': [
                    "How to custom tool function for the agent in agentscope?",
                    "What can you tell me about the AgentScope library?"
                ]
            }
        ]
        
        for stage in stages:
            logger.info(f"\n{'='*50}")
            logger.info(f"[STAGE] {stage['name']}")
            logger.info(f"[SKILLS] 将加载: {', '.join(stage['skills'])}")
            
            # 初始化智能体
            agent, toolkit, memory = await initialize_agent_with_skills(
                skill_manager, stage['skills']
            )
            
            # 创建交互会话
            session = InteractiveSession(agent)
            
            # 显示当前技能状态
            logger.info(f"[STATUS] 已加载技能: {skill_manager.get_available_skills()}")
            logger.info(f"[STATUS] 未加载技能: {skill_manager.get_unloaded_skills()}")
            
            # 执行测试问题
            for i, question in enumerate(stage['test_questions'], 1):
                logger.info(f"\n[TEST {i}] 提问: {question}")
                try:
                    result = await session.send_message(question)
                    logger.info(f"[RESPONSE] 回答: {result['response'][:200]}...")
                except Exception as e:
                    logger.error(f"[ERROR] 测试失败: {e}")
            
            # 显示会话摘要
            summary = session.get_session_summary()
            logger.info(f"[SUMMARY] 本阶段交互次数: {summary['total_interactions']}")
            
            # 等待一小段时间
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"[FATAL] 演示运行失败: {e}")
        raise

def main():
    """主函数"""
    try:
        logger.info("[START] 启动优化版AgentScope技能演示")
        asyncio.run(run_interactive_demo())
        logger.info("[END] 演示完成")
    except KeyboardInterrupt:
        logger.info("[INTERRUPTED] 用户中断程序")
    except Exception as e:
        logger.error(f"[CRITICAL] 程序异常终止: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()