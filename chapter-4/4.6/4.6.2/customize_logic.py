from typing import Literal, Annotated, Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.tools import tool
import operator
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# ============== Mock 数据管理器 ==============
class MockDataManager:
    """管理所有模拟数据"""
    
    def __init__(self):
        self.customer_db = {
            "CUST_123": {
                "name": "张三",
                "email": "zhangsan@example.com",
                "verified": True,
                "purchase_history": [
                    {"order_id": "ORD_456", "amount": 100.0, "date": "2024-01-15"},
                    {"order_id": "ORD_789", "amount": 200.0, "date": "2024-01-10"}
                ]
            },
            "CUST_456": {
                "name": "李四",
                "email": "lisi@example.com",
                "verified": False,  # 未验证用户
                "purchase_history": [
                    {"order_id": "ORD_999", "amount": 150.0, "date": "2024-01-20"}
                ]
            },
            "CUST_789": {
                "name": "王五",
                "email": "wangwu@example.com",
                "verified": True,
                "purchase_history": []  # 无购买记录
            }
        }
        
        self.order_db = {
            "ORD_456": {
                "customer_id": "CUST_123",
                "amount": 100.0,
                "date": "2024-01-15",
                "status": "delivered",
                "product": "无线耳机",
                "refund_window_days": 30,
                "eligible_products": ["无线耳机", "充电宝", "数据线"]
            },
            "ORD_789": {
                "customer_id": "CUST_123",
                "amount": 200.0,
                "date": "2024-01-10",
                "status": "delivered",
                "product": "智能手表",
                "refund_window_days": 30
            },
            "ORD_999": {
                "customer_id": "CUST_456",
                "amount": 150.0,
                "date": "2023-12-01",  # 超过30天
                "status": "delivered",
                "product": "平板电脑",
                "refund_window_days": 30
            },
            "ORD_888": {
                "customer_id": "CUST_123",
                "amount": 80.0,
                "date": "2024-01-20",
                "status": "cancelled",  # 已取消订单
                "product": "手机壳",
                "refund_window_days": 30
            }
        }
        
        self.refund_history = []
        
    def reset_test_data(self, test_case: str):
        """重置测试数据到指定测试场景"""
        if test_case == "eligible_all_pass":
            # 测试用例1：所有条件都通过
            self.customer_db["CUST_123"]["verified"] = True
            self.order_db["ORD_456"]["date"] = "2024-01-15"  # 在有效期内
            self.order_db["ORD_456"]["status"] = "delivered"
            
        elif test_case == "buyer_not_verified":
            # 测试用例2：购买者验证失败
            self.customer_db["CUST_123"]["verified"] = False
            self.order_db["ORD_456"]["date"] = "2024-01-15"
            
        elif test_case == "refund_overdue":
            # 测试用例3：订单超过退款期限
            self.customer_db["CUST_123"]["verified"] = True
            self.order_db["ORD_456"]["date"] = "2023-11-01"  # 超过30天
            
        elif test_case == "both_fail":
            # 测试用例4：两个条件都失败
            self.customer_db["CUST_123"]["verified"] = False
            self.order_db["ORD_456"]["date"] = "2023-11-01"

# 创建全局Mock数据管理器
mock_manager = MockDataManager()

# ============== 工具定义（修改为使用Mock数据） ==============

@tool
def verify_buyer(customer_id: str) -> dict:
    """验证客户身份和购买记录"""
    customer = mock_manager.customer_db.get(customer_id)
    
    if not customer:
        return {
            "verified": False,
            "message": f"Customer {customer_id} not found",
            "customer_data": None
        }
    
    return {
        "verified": customer["verified"],
        "message": f"Customer {'verified' if customer['verified'] else 'not verified'}",
        "customer_data": {
            "name": customer["name"],
            "email": customer["email"],
            "purchase_count": len(customer["purchase_history"])
        }
    }

@tool
def check_refund_eligibility(order_id: str) -> dict:
    """检查订单是否符合退款条件"""
    order = mock_manager.order_db.get(order_id)
    
    if not order:
        return {
            "eligible": False,
            "message": f"Order {order_id} not found",
            "details": {}
        }
    
    # 计算购买天数
    purchase_date = datetime.strptime(order["date"], "%Y-%m-%d")
    days_since_purchase = (datetime.now() - purchase_date).days
    
    # 检查条件
    conditions = {
        "within_refund_window": days_since_purchase <= order["refund_window_days"],
        "order_not_cancelled": order["status"] != "cancelled",
        "order_delivered": order["status"] == "delivered"
    }
    
    eligible = all(conditions.values())
    
    return {
        "eligible": eligible,
        "message": f"Order is {'eligible' if eligible else 'not eligible'} for refund",
        "days_since_purchase": days_since_purchase,
        "refund_window_days": order["refund_window_days"],
        "details": conditions
    }

@tool
def check_refund_conditions(customer_id: str, order_id: str) -> dict:
    """协调器检查总体退款条件"""
    # 调用之前的验证结果（在实际中会读取状态，这里模拟）
    buyer_result = verify_buyer.invoke({"customer_id": customer_id})
    refund_result = check_refund_eligibility.invoke({"order_id": order_id})
    
    eligible = buyer_result["verified"] and refund_result["eligible"]
    
    return {
        "eligible": eligible,
        "reason": "All conditions met" if eligible else "One or more conditions failed",
        "verification_details": {
            "buyer_verified": buyer_result["verified"],
            "refund_eligible": refund_result["eligible"]
        }
    }

@tool
def process_refund(customer_id: str, order_id: str, amount: float) -> dict:
    """执行退款处理"""
    # 生成退款ID
    refund_id = f"REF_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 记录退款历史
    refund_record = {
        "refund_id": refund_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "amount": amount,
        "timestamp": datetime.now().isoformat(),
        "status": "completed"
    }
    mock_manager.refund_history.append(refund_record)
    
    return {
        "status": "success",
        "refund_id": refund_id,
        "amount": amount,
        "message": f"Refund of ${amount:.2f} processed successfully",
        "transaction_id": f"TXN_{refund_id}"
    }

@tool
def award_store_credits(customer_id: str, credits: float) -> dict:
    """奖励店铺积分"""
    customer = mock_manager.customer_db.get(customer_id)
    if customer:
        if "store_credits" not in customer:
            customer["store_credits"] = 0.0
        customer["store_credits"] += credits
    
    return {
        "status": "success",
        "credits_awarded": credits,
        "total_credits": customer.get("store_credits", 0.0) if customer else credits,
        "message": f"${credits:.2f} store credits awarded to customer {customer_id}"
    }

@tool
def process_credits_decision(customer_id: str, credits: float) -> dict:
    """处理积分决策"""
    # 在实际中可能包含更多业务逻辑
    return {
        "status": "success",
        "credits_processed": credits,
        "decision_type": "compensation",
        "message": f"Credit compensation of ${credits:.2f} approved for customer {customer_id}"
    }

# ============== 状态和智能体定义（保持不变） ==============

class RefundState(TypedDict):
    customer_id: str
    order_id: str
    refund_reason: str
    messages: Annotated[list, add_messages]
    
    # 验证结果
    buyer_verified: bool
    refund_eligible: bool
    
    # 中间结果
    verification_details: Dict[str, Any]
    eligibility_details: Dict[str, Any]
    
    # 最终决策
    refund_eligible_decision: bool
    store_credits: float
    refund_details: Dict[str, Any]
    final_response: str

# ============== 子智能体定义（修改为使用状态中的详细数据） ==============

class BuyerVerifierState(TypedDict):
    customer_id: str
    messages: Annotated[list, add_messages]
    verified: bool
    details: Dict[str, Any]

def buyer_verifier_node(state: BuyerVerifierState):
    result = verify_buyer.invoke({"customer_id": state["customer_id"]})
    return {
        "verified": result["verified"],
        "details": result.get("customer_data", {}),
        "messages": [f"Buyer verification: {result['message']}"]
    }

class EligibilityCheckerState(TypedDict):
    order_id: str
    messages: Annotated[list, add_messages]
    eligible: bool
    details: Dict[str, Any]

def eligibility_checker_node(state: EligibilityCheckerState):
    result = check_refund_eligibility.invoke({"order_id": state["order_id"]})
    return {
        "eligible": result["eligible"],
        "details": result,
        "messages": [f"Eligibility check: {result['message']}"]
    }

# ============== 构建子智能体图 ==============

# 购买者验证子智能体
buyer_verifier_graph = StateGraph(BuyerVerifierState)
buyer_verifier_graph.add_node("verify", buyer_verifier_node)
buyer_verifier_graph.add_edge(START, "verify")
buyer_verifier_graph.add_edge("verify", END)
buyer_verifier = buyer_verifier_graph.compile()

# 退款资格确认子智能体
eligibility_checker_graph = StateGraph(EligibilityCheckerState)
eligibility_checker_graph.add_node("check", eligibility_checker_node)
eligibility_checker_graph.add_edge(START, "check")
eligibility_checker_graph.add_edge("check", END)
eligibility_checker = eligibility_checker_graph.compile()

# ============== 协调器节点（修改为包含详细日志） ==============

def coordinator_parallel_validate(state: RefundState):
    """并行调用两个验证子智能体"""
    
    buyer_result = buyer_verifier.invoke({
        "customer_id": state["customer_id"],
        "messages": [],
        "verified": False,
        "details": {}
    })
    
    eligibility_result = eligibility_checker.invoke({
        "order_id": state["order_id"],
        "messages": [],
        "eligible": False,
        "details": {}
    })
    
    return {
        "buyer_verified": buyer_result["verified"],
        "refund_eligible": eligibility_result["eligible"],
        "verification_details": buyer_result["details"],
        "eligibility_details": eligibility_result["details"],
        "messages": buyer_result["messages"] + eligibility_result["messages"]
    }

def coordinator_check_conditions(state: RefundState):
    """使用自定义逻辑检查退款条件"""
    
    if state["buyer_verified"] and state["refund_eligible"]:
        result = check_refund_conditions.invoke({
            "customer_id": state["customer_id"],
            "order_id": state["order_id"]
        })
        eligible = result["eligible"]
        details = result
    else:
        eligible = False
        details = {
            "reason": f"Buyer verified: {state['buyer_verified']}, Refund eligible: {state['refund_eligible']}"
        }
    
    return {
        "refund_eligible_decision": eligible,
        "messages": [f"Refund eligibility decision: {eligible}. Reason: {details.get('reason', 'N/A')}"]
    }

# ============== 路径节点定义 ==============

class RefundProcessorState(TypedDict):
    customer_id: str
    order_id: str
    amount: float
    messages: Annotated[list, add_messages]
    refund_status: str
    refund_details: Dict[str, Any]

def process_refund_path_node(state: RefundState):
    """调用退款处理子智能体"""
    # 获取订单金额（实际中可能从数据库获取）
    order = mock_manager.order_db.get(state["order_id"], {})
    amount = order.get("amount", 100.0)
    
    result = process_refund.invoke({
        "customer_id": state["customer_id"],
        "order_id": state["order_id"],
        "amount": amount
    })
    
    return {
        "refund_details": result,
        "messages": [f"Refund processed: {result['message']}"]
    }

def process_credits_path_node(state: RefundState):
    """调用积分路径的两个子智能体"""
    
    # 根据订单金额决定积分金额（实际中可能有更复杂的逻辑）
    order = mock_manager.order_db.get(state["order_id"], {})
    base_amount = order.get("amount", 100.0)
    credits_amount = base_amount * 0.5  # 给予50%的积分补偿
    
    # 第一步：奖励积分
    credits_result = award_store_credits.invoke({
        "customer_id": state["customer_id"],
        "credits": credits_amount
    })
    
    # 第二步：处理积分决策
    decision_result = process_credits_decision.invoke({
        "customer_id": state["customer_id"],
        "credits": credits_amount
    })
    
    return {
        "store_credits": credits_amount,
        "messages": [
            f"Store credits awarded: {credits_result['message']}",
            f"Credit decision processed: {decision_result['message']}"
        ]
    }

# ============== 最终回答节点 ==============

def final_answer_node(state: RefundState):
    """生成最终回答"""
    if state.get("refund_eligible_decision"):
        refund_info = state.get("refund_details", {})
        response = f"✅ 退款申请已批准！\n"
        response += f"退款ID: {refund_info.get('refund_id', 'N/A')}\n"
        response += f"退款金额: ${refund_info.get('amount', 0):.2f}\n"
        response += f"交易ID: {refund_info.get('transaction_id', 'N/A')}"
    else:
        response = f"⚠️  您不符合退款条件，但我们为您提供了补偿方案：\n"
        response += f"已向您的账户添加 ${state.get('store_credits', 0):.2f} 店铺积分\n"
        response += "您可以在下次购物时使用这些积分。"
    
    return {
        "final_response": response,
        "messages": [response]
    }

# ============== 条件路由函数 ==============

def route_after_eligibility(state: RefundState) -> Literal["process_refund_path", "credits_path"]:
    """根据退款资格决定路由"""
    if state["refund_eligible_decision"]:
        return "process_refund_path"
    else:
        return "credits_path"

# ============== 构建主图 ==============

refund_graph = StateGraph(RefundState)

# 添加节点
refund_graph.add_node("coordinator_validate", coordinator_parallel_validate)
refund_graph.add_node("coordinator_check", coordinator_check_conditions)
refund_graph.add_node("process_refund_path", process_refund_path_node)
refund_graph.add_node("credits_path", process_credits_path_node)
refund_graph.add_node("final_answer", final_answer_node)

# 添加边
refund_graph.add_edge(START, "coordinator_validate")
refund_graph.add_edge("coordinator_validate", "coordinator_check")
refund_graph.add_conditional_edges(
    "coordinator_check",
    route_after_eligibility,
    {
        "process_refund_path": "process_refund_path",
        "credits_path": "credits_path"
    }
)
refund_graph.add_edge("process_refund_path", "final_answer")
refund_graph.add_edge("credits_path", "final_answer")
refund_graph.add_edge("final_answer", END)

# 编译图
coordinator_graph = refund_graph.compile()

# ============== 测试函数 ==============

def run_test_case(test_name: str, customer_id: str, order_id: str, reason: str = "产品问题"):
    """运行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"测试用例: {test_name}")
    print(f"{'='*60}")
    
    # 重置测试数据
    mock_manager.reset_test_data(test_name)
    
    # 准备输入状态
    input_state = {
        "customer_id": customer_id,
        "order_id": order_id,
        "refund_reason": reason,
        "messages": [],
        "buyer_verified": False,
        "refund_eligible": False,
        "verification_details": {},
        "eligibility_details": {},
        "refund_eligible_decision": False,
        "store_credits": 0.0,
        "refund_details": {},
        "final_response": ""
    }
    
    try:
        # 执行工作流
        result = coordinator_graph.invoke(input_state)
        
        # 打印结果
        print(f"\n📝 处理日志:")
        for i, msg in enumerate(result.get("messages", []), 1):
            print(f"  {i}. {msg}")
        
        print(f"\n✅ 最终结果:")
        print(f"  {result.get('final_response', 'No response')}")
        
        # 打印详细状态
        print(f"\n🔍 详细状态:")
        print(f"  购买者验证: {result.get('buyer_verified', False)}")
        print(f"  退款资格: {result.get('refund_eligible', False)}")
        print(f"  最终决策: {result.get('refund_eligible_decision', False)}")
        if result.get("store_credits", 0) > 0:
            print(f"  授予积分: ${result.get('store_credits', 0):.2f}")
        
        return result
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return None

def run_all_test_cases():
    """运行所有测试用例"""
    print("🧪 开始退款智能体测试套件")
    print("="*60)
    
    # 测试用例1：所有条件都通过
    run_test_case("eligible_all_pass", "CUST_123", "ORD_456", "产品有缺陷")
    
    # 测试用例2：购买者验证失败
    run_test_case("buyer_not_verified", "CUST_123", "ORD_456", "不喜欢商品")
    
    # 测试用例3：订单超过退款期限
    run_test_case("refund_overdue", "CUST_123", "ORD_456", "后悔购买")
    
    # 测试用例4：两个条件都失败
    run_test_case("both_fail", "CUST_123", "ORD_456", "其他原因")
    
    # 测试用例5：无效订单
    run_test_case("eligible_all_pass", "CUST_123", "ORD_888", "订单已取消")

def print_mock_data_summary():
    """打印Mock数据摘要"""
    print(f"\n📊 Mock数据摘要:")
    print(f"  客户数量: {len(mock_manager.customer_db)}")
    print(f"  订单数量: {len(mock_manager.order_db)}")
    print(f"  退款历史记录: {len(mock_manager.refund_history)}")
    
    if mock_manager.refund_history:
        print(f"\n  最近退款:")
        for refund in mock_manager.refund_history[-3:]:  # 显示最近3条
            print(f"    - {refund['refund_id']}: ${refund['amount']}")

# ============== 主程序 ==============

if __name__ == "__main__":
    # 运行所有测试用例
    run_all_test_cases()
    
    # 打印数据摘要
    print_mock_data_summary()
    
    # 可视化图结构
    try:
        print(f"\n📋 工作流结构:")
        print(coordinator_graph.get_graph().draw_ascii())
    except:
        print("无法生成ASCII图表")
