import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'common'))
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

from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware, TodoListMiddleware, HumanInTheLoopMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_community.chat_models.tongyi import ChatTongyi


# 客户支持工具
@tool
def search_knowledge_base(query: str) -> str:
    """搜索内部文档和常见问题解答。"""
    return f"找到关于 '{query}' 的文章"

@tool
def get_order_status(order_id: str) -> str:
    """获取客户订单的当前状态。"""
    return f"订单 {order_id}：已发货"

@tool
def process_refund(order_id: str, amount: float) -> str:
    """处理订单退款。"""
    return f"已处理订单 {order_id} 的 ${amount} 退款"

@tool
def check_inventory(product_id: str) -> str:
    """检查产品库存。"""
    return f"产品 {product_id}：有库存"

@tool
def create_ticket(issue: str) -> str:
    """创建支持工单。"""
    return f"已创建工单：{issue}"

@tool
def get_shipping_info(order_id: str) -> str:
    """获取物流跟踪和配送详情。"""
    return f"订单 {order_id} 的物流信息"

@tool
def update_account(customer_id: str, field: str, value: str) -> str:
    """更新客户账户信息。"""
    return f"已为客户 {customer_id} 更新 {field}"

@tool
def check_warranty(product_id: str) -> str:
    """检查保修状态。"""
    return f"产品 {product_id} 的保修信息"

@tool
def schedule_callback(phone: str, time: str) -> str:
    """安排支持团队回电。"""
    return f"已安排在 {time} 回电至 {phone}"

@tool
def get_return_label(order_id: str) -> str:
    """生成退货物流标签。"""
    return f"已为订单 {order_id} 生成退货标签"


# 使用所有中间件创建代理
agent = create_agent(
    model=ChatTongyi(model_name="qwen-max"),
    tools=[
        search_knowledge_base, get_order_status, process_refund,
        check_inventory, create_ticket, get_shipping_info,
        update_account, check_warranty, schedule_callback, get_return_label
    ],
    middleware=[
        LLMToolSelectorMiddleware(
            # 选择模型用 qwen-plus：该中间件内部走 with_structured_output，
            # 实测 qwen-max 有约 35% 概率直接调用业务工具而非返回选择结果，
            # 导致 parsed=None 被判为 malformed；qwen-plus 实测失败率更低且更快。
            model=ChatTongyi(model_name="qwen-plus"),
            max_tools=3,
            always_include=["search_knowledge_base"], # 总是包含知识库搜索
            # 智能体每轮循环都会重新选择工具，偶发一次格式不合规就会中断整个工作流。
            # 提高重试次数，并在重试仍失败时回退为“选择全部工具”而不是抛错——
            # 工具筛选只是优化手段，退化后主模型仍持有全部工具，工作流可正常完成。
            max_retries=3,
            on_parsing_failure="all",
        ),
        TodoListMiddleware(), # 待办事项列表中间件
        HumanInTheLoopMiddleware( # 人类参与决策中间件
            interrupt_on={
                "process_refund": True,  # 需要审批
                "update_account": True,  # 需要审批
            },
        ),
    ],
    checkpointer=InMemorySaver(),  # 人类参与决策所需
)

# 带线程ID的配置
config = {"configurable": {"thread_id": "workflow_123"}}

print("=== 启动工作流 ===\n")


result = agent.invoke(
    {"messages": [{"role": "user", "content": "处理订单 #12345 的 $50 退款并更新客户账户 "}]},
    config=config
)

# 处理中断的命令循环
while result.get("__interrupt__"):
    interrupts = result["__interrupt__"]

    # 显示待处理操作
    for interrupt in interrupts:
        action_requests = interrupt.value["action_requests"]
        for action in action_requests:
            print(f"\n待处理操作:")
            print(f"  工具: {action['name']}")
            print(f"  参数: {action['args']}")

    # 获取人类决策
    decision_type = input("\n决策 (approve/edit/reject): ").strip().lower()

    decisions = []
    for interrupt in interrupts:
        action_requests = interrupt.value["action_requests"]
        for action in action_requests:
            if decision_type == "approve": # 批准
                decisions.append({"type": "approve"})
            elif decision_type == "edit": # 编辑
                # 根据工具类型进行编辑
                if action['name'] == "process_refund":
                    new_amount = input(f"新的退款金额 (当前: {action['args']['amount']}): ")
                    decisions.append({
                        "type": "edit",
                        "edited_action": {
                            "name": "process_refund",
                            "args": {
                                "order_id": action['args']['order_id'],
                                "amount": float(new_amount)
                            }
                        }
                    })
                elif action['name'] == "update_account":
                    new_value = input(f"{action['args']['field']} 的新值: ")
                    # 注意：这里修正了原代码中可能的拼写错误 'arguments' -> 'args'
                    decisions.append({
                        "type": "edit",
                        "edited_action": {
                            "name": "update_account",
                            "args": {
                                "customer_id": action['args']['customer_id'],
                                "field": action['args']['field'], 
                                "value": new_value
                            }
                        }
                    })
            elif decision_type == "reject": # 拒绝
                message = input("拒绝原因: ")
                decisions.append({"type": "reject", "message": message})

    # 使用决策恢复执行
    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config
    )

print("\n=== 工作流完成 ===")
print(result["messages"][-1].content)

