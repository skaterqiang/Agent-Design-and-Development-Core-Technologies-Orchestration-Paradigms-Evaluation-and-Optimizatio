import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    print("API配置加载成功")
    print("配置信息:", get_all_configs())
except ValueError as e:
    print(f"配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)

# 设置通义千问API Key
os.environ["DASHSCOPE_API_KEY"] = API_KEY

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Dict, Any
import json

# 定义工具（保持不变）
@tool
def calculator(expression: str) -> str:
    """计算数学表达式，例如 '2 + 3 * 4'。支持加减乘除和括号。"""
    try:
        allowed_names = {"__builtins__": {}}
        result = eval(expression, allowed_names)
        return f"结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息（模拟数据）。"""
    weather_data = {
        "北京": "晴天，25°C",
        "上海": "多云，28°C", 
        "西安": "小雨，30°C",
        "深圳": "晴天，32°C"
    }
    return f"{city} 当前天气: {weather_data.get(city, '暂无数据')}"

# ====================================
# 动态系统提示词生成器
# ====================================
class DynamicSystemPromptGenerator:
    def __init__(self):
        self.user_profiles = {}  # 用户偏好缓存
        
    def generate_prompt(self, messages: List[Any], user_id: str = "default") -> str:
        """根据对话历史动态生成系统提示词"""
        message_count = len(messages)
        user_queries = [msg.content.lower() for msg in messages if isinstance(msg, HumanMessage)]
        
        # 分析用户偏好
        profile = self._analyze_user_profile(user_queries, user_id)
        
        # 根据条件选择提示策略
        if message_count > 10:
            base_prompt = self._get_concise_prompt(profile)
        elif any("详细" in q or "解释" in q for q in user_queries):
            base_prompt = self._get_detailed_prompt(profile)
        elif any("计算" in q or "数学" in q for q in user_queries[-3:]):
            base_prompt = self._get_math_focused_prompt(profile)
        else:
            base_prompt = self._get_default_prompt(profile)
        
        # 添加状态提示
        state_hint = self._get_state_hint(messages)
        final_prompt = f"{base_prompt}\n\n{state_hint}"
        
        print(f"动态生成提示词 (对话轮数: {message_count}, 策略: {profile['style']})")
        return final_prompt
    
    def _analyze_user_profile(self, queries: List[str], user_id: str) -> Dict[str, Any]:
        """分析用户偏好"""
        if user_id in self.user_profiles:
            return self.user_profiles[user_id]
        
        math_count = sum(1 for q in queries if any(word in q for word in ["计算", "数学", "+", "-", "*"]))
        weather_count = sum(1 for q in queries if "天气" in q)
        
        profile = {
            "math_preference": math_count / max(len(queries), 1),
            "weather_preference": weather_count / max(len(queries), 1),
            "style": "详细" if any("详细" in q for q in queries) else "简洁",
            "total_queries": len(queries)
        }
        
        self.user_profiles[user_id] = profile
        return profile
    
    def _get_default_prompt(self, profile: Dict) -> str:
        return """你是一个智能助手。
计算问题 → calculator 工具
天气查询 → get_weather 工具  
其他问题 → 直接回答
用中文回复，简洁明了。"""
    
    def _get_detailed_prompt(self, profile: Dict) -> str:
        return f"""你是一个详细解释的智能助手 (用户偏好详细解答)。
数学计算：使用 calculator 工具，并解释步骤
天气查询：使用 get_weather 工具，提供建议
其他问题：提供完整分析和背景
回复结构：结论 → 解释 → 建议
用户数学偏好：{profile['math_preference']:.1%}"""
    
    def _get_concise_prompt(self, profile: Dict) -> str:
        return f"""你是一个高效助手 (对话已超过10轮)。
直接给出结果，不赘述
计算 → calculator
天气 → get_weather  
其他 → 一句话回答
用户累计查询：{profile['total_queries']}次"""
    
    def _get_math_focused_prompt(self, profile: Dict) -> str:
        return f"""你是一个数学专家 (用户近期专注计算)。
优先使用 calculator 工具
计算后解释公式和步骤
用户数学偏好：{profile['math_preference']:.1%}
其他查询也保持精确性。"""
    
    def _get_state_hint(self, messages: List[Any]) -> str:
        """根据对话状态添加提示"""
        recent_tools = [msg for msg in messages[-5:] if hasattr(msg, 'name') and msg.name]
        if recent_tools:
            return f"最近工具调用：{', '.join(t.name for t in recent_tools[-2:])}"
        return "对话刚开始，请仔细阅读用户需求"

# 初始化动态提示生成器
prompt_generator = DynamicSystemPromptGenerator()

# 初始化模型
model = ChatTongyi(model_name="qwen-max")

# 创建工具列表
tools = [calculator, get_weather]

# ====================================
# 创建带动态提示的代理执行函数
# ====================================
def create_dynamic_agent(messages: List[Any]) -> Any:
    """创建带动态系统提示的代理"""
    # 动态生成系统提示
    dynamic_system_prompt = prompt_generator.generate_prompt(messages)
    
    agent = create_agent(
        model,
        tools,
        system_prompt=dynamic_system_prompt
    )
    return agent

# 测试调用
if __name__ == "__main__":
    # 模拟多轮对话历史
    conversation_history = []
    
    print("动态提示词代理测试开始")
    print("=" * 60)
    
    # 测试1：首次对话 - 默认提示
    print("\n1. 测试首次数学计算")
    result1 = create_dynamic_agent([]).invoke({
        "messages": [HumanMessage(content="计算 (15 + 25) * 3")]
    })
    final_msg1 = result1["messages"][-1]
    print("结果:", final_msg1.content[:100] + "..." if len(final_msg1.content) > 100 else final_msg1.content)
    
    # 测试2：天气查询 - 触发天气专注提示
    print("\n2. 测试天气查询")
    result2 = create_dynamic_agent(result1["messages"]).invoke({
        "messages": result1["messages"] + [HumanMessage(content="西安今天天气怎么样？")]
    })
    final_msg2 = result2["messages"][-1]
    print("结果:", final_msg2.content[:100] + "..." if len(final_msg2.content) > 100 else final_msg2.content)
    
    # 测试3：连续计算 - 触发数学专注提示
    print("\n3. 测试连续计算 (触发数学专注模式)")
    result3 = create_dynamic_agent(result2["messages"]).invoke({
        "messages": result2["messages"] + [HumanMessage(content="刚才西安温度乘以2.5")]
    })
    final_msg3 = result3["messages"][-1]
    print("结果:", final_msg3.content[:100] + "..." if len(final_msg3.content) > 100 else final_msg3.content)
    
    # 测试4：要求详细解释 - 触发详细模式
    print("\n4. 测试详细解释要求")
    result4 = create_dynamic_agent(result3["messages"]).invoke({
        "messages": result3["messages"] + [HumanMessage(content="详细解释一下刚才的计算过程")]
    })
    final_msg4 = result4["messages"][-1]
    print("结果:", final_msg4.content[:100] + "..." if len(final_msg4.content) > 100 else final_msg4.content)
    
    print("\n" + "=" * 60)
    print("动态提示词测试完成！")
    print("用户偏好分析:", prompt_generator.user_profiles)
