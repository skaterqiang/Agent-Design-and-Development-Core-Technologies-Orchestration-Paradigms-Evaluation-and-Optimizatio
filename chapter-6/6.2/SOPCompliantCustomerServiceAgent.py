import os
import sys
import re
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from langgraph.types import Command
from langchain.messages import ToolMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

# 结合 chapter-3/customer_service.py 
# 同时复用 chapter-5/5.4 中面向对象的 CustomerServiceAgent 作为基类

# BASE_DIR 指向整个代码根目录（…/code）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# 导入 chapter-5/5.4 中的 CustomerServiceAgent（注意先插入该路径）
chapter54_path = os.path.join(BASE_DIR, "chapter-5", "5.4")
if chapter54_path not in sys.path:
    sys.path.insert(0, chapter54_path)
from customer_service import CustomerServiceAgent  # type: ignore

# 导入 chapter-3 中的原始工具与运行逻辑
chapter3_path = os.path.join(BASE_DIR, "chapter-3")
if chapter3_path not in sys.path:
    sys.path.insert(0, chapter3_path)
import customer_service as cs_ch3  # type: ignore

# 导入本节策略一：SOP 增强系统提示词
from 策略一 import enhanced_system_prompt  # type: ignore

# 复用 chapter-3 中的订单数据库
ORDER_DATABASE = cs_ch3.ORDER_DATABASE

# 工单存储：创建工单后在此登记，用于跟踪与查询（符合 SOP「工单创建与跟踪」）
TICKET_STORE: Dict[str, Dict[str, Any]] = {}


# ============ 6.2.3 SOP 辅助函数（优化后，满足工单/记录/联系/审核/专员等关键词） ============

def generate_ticket_id() -> str:
    """生成工单号（示例：TT20240615123456）"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"TT{timestamp}"


def analyze_complaint_type(complaint_text: str) -> Dict[str, Any]:
    """分析投诉类型和关键信息"""
    damage_keywords = ["损坏", "破损", "摔坏", "裂", "碎", "坏掉"]
    quality_keywords = ["质量", "瑕疵", "次品", "问题", "故障"]
    delivery_keywords = ["延迟", "晚到", "没收到", "丢件", "物流"]
    complaint_type = "general"
    severity = "medium"
    if any(k in complaint_text for k in damage_keywords):
        complaint_type = "damaged_goods"
        severity = "high" if "严重" in complaint_text or "非常" in complaint_text else "medium"
    elif any(k in complaint_text for k in quality_keywords):
        complaint_type = "quality_issue"
        severity = "medium"
    elif any(k in complaint_text for k in delivery_keywords):
        complaint_type = "delivery_issue"
        severity = "medium"
    order_id_match = re.search(r"订单\s*(\d+)", complaint_text) or re.search(r"(\d{6,})", complaint_text)
    order_id = order_id_match.group(1) if order_id_match else None
    return {
        "type": complaint_type,
        "severity": severity,
        "order_id": order_id,
        "requires_photo": complaint_type == "damaged_goods",
        "requires_contact": severity == "high",
    }


def generate_sop_step1_response(complaint_analysis: Dict[str, Any]) -> str:
    """生成 SOP 第一步响应（安抚情绪与承诺负责）"""
    base_response = (
        "非常抱歉给您带来了不愉快的购物体验！\n"
        "我完全理解您的心情，这确实让人很失望。\n"
        "请您放心，我会立即为您记录并处理这个问题。\n\n"
    )
    if complaint_analysis["type"] == "damaged_goods":
        base_response += "收到损坏的商品确实令人烦恼，我们一定会认真处理。\n"
    elif complaint_analysis["type"] == "quality_issue":
        base_response += "产品质量问题我们非常重视，会立即跟进。\n"
    base_response += "为了更快地为您解决，我需要向您核实一些信息。"
    return base_response


def generate_sop_step2_response(ticket_id: str, complaint_analysis: Dict[str, Any]) -> str:
    """生成 SOP 第二步响应（结构化信息收集与工单创建）"""
    response = f"好的，我已经为您创建了正式的售后服务工单，工单号是【{ticket_id}】。\n\n"
    response += "为了准确处理您的投诉，请提供以下信息：\n"
    checklist_items = []
    checklist_items.append("1. 订单编号（如果您还记得）")
    checklist_items.append("2. 您的联系电话（用于后续专员联系）")
    if complaint_analysis["type"] == "damaged_goods":
        checklist_items.append("3. 损坏商品的具体名称和数量")
        checklist_items.append("4. 损坏情况的详细文字描述")
        if complaint_analysis.get("requires_photo", True):
            checklist_items.append("5. 损坏照片（1-3张清晰照片作为凭证）")
        checklist_items.append("6. 您希望的解决方案（补发新品、退款、部分补偿）")
    elif complaint_analysis["type"] == "quality_issue":
        checklist_items.append("3. 出现质量问题的商品名称")
        checklist_items.append("4. 具体质量问题描述（何时发现、表现如何）")
        checklist_items.append("5. 您希望的解决方案（维修、换货、退货退款）")
    elif complaint_analysis["type"] == "delivery_issue":
        checklist_items.append("3. 具体的物流问题（延迟天数、是否收到、包装状况）")
        checklist_items.append("4. 您目前的收货地址")
        checklist_items.append("5. 您希望的解决方案（重新发货、退款、赔偿）")
    for item in checklist_items:
        response += f"   {item}\n"
    response += "\n您提供的信息我都会详细记录在工单中，后续处理都将基于此工单进行。"
    if complaint_analysis.get("order_id"):
        response += f"\n\n（系统检测到订单号：{complaint_analysis['order_id']}，如正确则无需重复提供）"
    return response


def generate_sop_step3_response(ticket_id: str, user_info_provided: bool = True) -> str:
    """生成 SOP 第三步响应（解决方案与时间线）"""
    if user_info_provided:
        return (
            f"感谢您提供的信息，已全部记录到工单【{ticket_id}】。\n\n"
            "接下来，我会将您的工单提交给售后专员进行审核，审核通常需要1-2个工作小时。\n"
            "审核结束后，我们的售后专员会通过电话主动联系您，告知具体的处理方案。\n\n"
            "请您保持手机畅通，并关注订单页面更新。"
        )
    return (
        f"工单【{ticket_id}】已创建，正在等待您的信息。\n\n"
        "一旦您提供上述信息，我们将立即启动处理流程：\n"
        "1. 售后专员审核（1-2个工作小时）\n"
        "2. 电话联系您告知处理方案\n"
        "3. 执行解决方案（补发/退款等）\n\n"
        "请尽快提供所需信息，以便我们为您快速处理。"
    )


def generate_sop_step4_response(ticket_id: str) -> str:
    """生成 SOP 第四步响应（确认与闭环）"""
    return (
        f"请问以上信息是否准确，您是否还有其他补充？\n\n"
        f"这是本次为您生成的工单号【{ticket_id}】，您之后可以通过此编号查询处理进度。\n"
        "我的服务即将结束，后续将由售后专员为您跟进。"
    )


# ============ 6.2.3 优化后的投诉处理工具（直接提示词插入 + 工具函数增强） ============

@tool
def handle_complaint_tool(complaint_text: str, runtime: ToolRuntime) -> Command:
    """
    处理客户投诉，严格按照SOP四步流程执行，并创建可跟踪的工单。
    当用户提及：包裹破损、商品损坏、投诉、质量问题、物流问题等，必须调用本工具以创建工单并跟踪，不得仅用自然语言回复。
    SOP流程：
    1. 安抚情绪与承诺负责
    2. 结构化信息收集与工单创建（生成工单号并写入工单库供后续跟踪）
    3. 提供清晰解决方案与时间线
    4. 确认与闭环
    """
    state = runtime.state
    updates: Dict[str, Any] = {}
    messages = []
    complaint_analysis = analyze_complaint_type(complaint_text)
    ticket_id = generate_ticket_id()

    # 创建工单并登记到 TICKET_STORE，用于后续跟踪（符合「工单创建与跟踪」）
    TICKET_STORE[ticket_id] = {
        "user_id": state.get("user_id", ""),
        "complaint_type": complaint_analysis["type"],
        "complaint_text": complaint_text[:200],
        "created_at": datetime.now().isoformat(),
        "status": "待处理",
        "sop_step": 2,
    }

    step1_response = generate_sop_step1_response(complaint_analysis)
    messages.append(ToolMessage(step1_response, tool_call_id=runtime.tool_call_id))
    updates["current_ticket_id"] = ticket_id
    updates["complaint_type"] = complaint_analysis["type"]
    updates["sop_step"] = 2
    step2_response = generate_sop_step2_response(ticket_id, complaint_analysis)
    messages.append(ToolMessage(step2_response, tool_call_id=runtime.tool_call_id))
    updates["complaint_escalated"] = True
    updates["complaint_timestamp"] = datetime.now().isoformat()
    return Command(update={**updates, "messages": messages})


@tool
def query_ticket_tool(ticket_query: str, runtime: ToolRuntime) -> Command:
    """根据工单号查询工单状态与进度。参数可为工单号（如 TT20240615143022）或用户原话（如「我的工单TT123进度」），会自动解析工单号。"""
    # 从用户输入中解析工单号（TT + 数字）
    tid_match = re.search(r"TT\d+", ticket_query) if ticket_query else None
    ticket_id = (tid_match.group(0) if tid_match else (ticket_query or "").strip()).strip()
    if not ticket_id:
        msg = "请提供您要查询的工单号（格式如 TT 开头）。"
    elif ticket_id in TICKET_STORE:
        t = TICKET_STORE[ticket_id]
        msg = (
            f"工单【{ticket_id}】查询结果：\n"
            f"  状态：{t.get('status', '待处理')}\n"
            f"  类型：{t.get('complaint_type', '')}\n"
            f"  创建时间：{t.get('created_at', '')}\n"
            f"  当前环节：SOP 第{t.get('sop_step', 2)}步（信息收集/专员审核中）"
        )
    else:
        msg = f"未找到工单【{ticket_id}】，请核对工单号是否正确。"
    return Command(update={"messages": [ToolMessage(msg, tool_call_id=runtime.tool_call_id)]})


class SOPCompliantCustomerServiceAgent(CustomerServiceAgent):
    """SOP合规的客服智能体"""

    def __init__(self):
        """初始化SOP合规智能体

        直接复用 chapter-5/5.4 中的 CustomerServiceAgent.__init__，
        该初始化过程已经完成模型与 API Key 的配置。
        """
        super().__init__()

        # 使用增强版系统提示词（包含完整SOP）
        self.system_prompt = enhanced_system_prompt

        # 创建SOP增强的工具集（投诉处理使用本节优化后的 handle_complaint_tool，并支持工单查询跟踪）
        self.sop_tools = [
            cs_ch3.query_order_tool,
            cs_ch3.compare_products_tool,
            handle_complaint_tool,  # 6.2.3 优化后的投诉处理工具，创建工单并写入 TICKET_STORE 跟踪
            query_ticket_tool,  # 工单进度查询，实现「创建工单去跟踪」
            cs_ch3.query_sales_data_tool,
            cs_ch3.get_user_orders_tool,
        ]

        # 重新创建智能体，使用新的系统提示词与工具集
        self.agent = create_agent(
            self.model,
            tools=self.sop_tools,
            system_prompt=self.system_prompt,
            checkpointer=InMemorySaver(),
        )
        print("🤖 SOP合规客服智能体初始化完成")

    # 在实际生产环境中，需要配合状态机（State Machine）或会话记忆（Memory）机制
    # handle_complaint_tool 应仅处理当前 turn 的逻辑，并根据 updates['sop_step'] 标记当前进度，
    # 等待下一轮用户输入触发后续步骤。
    def process_complaint_with_sop(self, user_id: str, complaint_text: str) -> Dict[str, Any]:
        """
        按照SOP流程处理投诉（增强版本，纯本地逻辑，便于单元测试）
        """
        # 分析投诉内容
        complaint_analysis = analyze_complaint_type(complaint_text)
        ticket_id = generate_ticket_id()

        # 创建工单并登记到 TICKET_STORE，用于跟踪（与 handle_complaint_tool 一致）
        TICKET_STORE[ticket_id] = {
            "user_id": user_id,
            "complaint_type": complaint_analysis["type"],
            "complaint_text": complaint_text[:200],
            "created_at": datetime.now().isoformat(),
            "status": "待处理",
            "sop_step": 2,
        }

        # 执行SOP流程
        result: Dict[str, Any] = {
            "user_id": user_id,
            "complaint_text": complaint_text,
            "ticket_id": ticket_id,
            "sop_steps_executed": [],
            "response_sequence": [],
        }

        # SOP 第一步：安抚情绪
        step1_response = generate_sop_step1_response(complaint_analysis)
        result["sop_steps_executed"].append("step1_安抚情绪")
        result["response_sequence"].append(step1_response)

        # SOP 第二步：信息收集与工单创建（工单已写入 TICKET_STORE 可跟踪）
        step2_response = generate_sop_step2_response(ticket_id, complaint_analysis)
        result["sop_steps_executed"].append("step2_工单创建与信息收集")
        result["response_sequence"].append(step2_response)

        # 检查是否有订单信息，若有则自动补充上下文
        order_id = complaint_analysis.get("order_id")
        if order_id:
            order_info = self.get_order_info(order_id)
            if order_info:
                result["order_info"] = order_info
                order_context = f"\n（系统已关联订单{order_id}: {order_info['product_name']}）"
                result["response_sequence"][-1] += order_context

        # 在真实系统中，这里会等待用户补充信息；此处直接进入第三步、第四步
        step3_response = generate_sop_step3_response(ticket_id, user_info_provided=True)
        result["sop_steps_executed"].append("step3_解决方案与时间线")
        result["response_sequence"].append(step3_response)

        step4_response = generate_sop_step4_response(ticket_id)
        result["sop_steps_executed"].append("step4_确认与闭环")
        result["response_sequence"].append(step4_response)

        # 生成完整响应
        result["full_response"] = "\n\n".join(result["response_sequence"])
        return result

    def get_order_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单信息（基于 chapter-3 的 ORDER_DATABASE）"""
        return ORDER_DATABASE.get(order_id)


def test_sop_compliance():
    """测试SOP合规性"""
    print("=" * 60)
    print("SOP合规性测试")
    print("=" * 60)
    agent = SOPCompliantCustomerServiceAgent()
    test_cases = [
        ("cust001", "我刚收到的商品有损坏，我要投诉！"),
        ("cust002", "订单123456的商品屏幕碎了，怎么处理？"),
        ("cust003", "收到的耳机一边不响了，质量有问题！"),
        ("cust001", "说明了包裹破损了"),  # 明确覆盖「包裹破损」场景，须创建工单并跟踪
    ]
    for user_id, complaint in test_cases:
        print(f"\n测试用例: {user_id} - '{complaint}'")
        print("-" * 40)
        result = agent.process_complaint_with_sop(user_id, complaint)
        # 检查SOP关键词覆盖
        required_keywords = ["工单", "记录", "联系", "审核", "专员"]
        response_text = result["full_response"]
        print(f"工单号: {result['ticket_id']}")
        print(f"执行的SOP步骤: {', '.join(result['sop_steps_executed'])}")
        print("\n智能体回复:")
        print(response_text)

        # 关键词覆盖检查
        print("\n✅ SOP合规检查:")
        for keyword in required_keywords:
            if keyword in response_text:
                print(f" 包含关键词: '{keyword}'")
            else:
                print(f"缺失关键词: '{keyword}'")

    # 验证工单已创建并可跟踪（符合 handle_complaint_tool 的「创建工单去跟踪」）
    print("\n" + "=" * 60)
    print(f"工单跟踪：当前共 {len(TICKET_STORE)} 个工单已创建并登记，可查询进度")
    for tid, t in list(TICKET_STORE.items())[:5]:
        print(f"  - {tid} | {t.get('status')} | {t.get('complaint_type')} | {t.get('created_at', '')[:19]}")


if __name__ == "__main__":
    # 运行SOP合规测试
    test_sop_compliance()
    # 运行原始客服系统（对比）
    print("\n" + "=" * 60)
    print("对比：原始客服系统")
    print("=" * 60)
    cs_ch3.run_customer_service()
