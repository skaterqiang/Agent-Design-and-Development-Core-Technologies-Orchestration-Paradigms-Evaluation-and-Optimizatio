import os
import sys
from typing import Optional, List, Dict, Any, Tuple
from langchain_core.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain.messages import ToolMessage
from datetime import datetime, timedelta
import re
import asyncio

# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# ✅ 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    print("🔑 API配置加载成功")
except ValueError as e:
    print(f"❌ 配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)

# 设置通义千问API Key
os.environ["DASHSCOPE_API_KEY"] = API_KEY

# 初始化模型
model = ChatTongyi(model_name="qwen-max")

# 客服机器人状态
class CustomerServiceState:
    def __init__(self, user_id: str, user_type: str, department: Optional[str] = None):
        self.user_id = user_id
        self.user_type = user_type
        self.department = department
        self.current_order_id: Optional[str] = None
        self.complaint_escalated: bool = False
        self.conversation_history: List[Dict[str, str]] = []
        self.session_id: str = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

# 模拟数据库数据（保持不变）
ORDER_DATABASE = {
    "123456": {
        "customer_id": "cust001",
        "product_name": "智能手机A",
        "status": "已发货",
        "shipping_status": "运输中",
        "shipping_nodes": [
            "2024-06-10 09:00:00 订单已接收",
            "2024-06-10 14:30:00 商品已打包",
            "2024-06-11 10:15:00 已发出，正在运输中",
            "2024-06-12 08:45:00 到达目的地配送中心"
        ],
        "estimated_delivery": "2024-06-15",
        "carrier": "顺丰快递",
        "tracking_number": "SF123456789"
    },
    "789012": {
        "customer_id": "cust002",
        "product_name": "笔记本电脑B",
        "status": "待发货",
        "shipping_status": "未发货",
        "shipping_nodes": [
            "2024-06-13 10:30:00 订单已确认",
            "2024-06-13 11:15:00 正在备货中"
        ],
        "estimated_delivery": "2024-06-18",
        "carrier": "京东物流",
        "tracking_number": "JD987654321"
    },
    "345678": {
        "customer_id": "cust003",
        "product_name": "无线耳机C",
        "status": "已签收",
        "shipping_status": "已送达",
        "shipping_nodes": [
            "2024-06-08 14:20:00 订单已接收",
            "2024-06-09 09:45:00 商品已打包",
            "2024-06-10 11:30:00 已发出",
            "2024-06-11 16:15:00 已送达，签收人：张三"
        ],
        "estimated_delivery": "2024-06-11",
        "carrier": "中通快递",
        "tracking_number": "ZT5566778899"
    }
}

# 产品数据（保持不变）
PRODUCT_DATABASE = {
    "智能手机A": {
        "category": "手机",
        "price": 2999.00,
        "camera_pixels": "5000万像素",
        "camera_sensor": "索尼IMX766",
        "camera_aperture": "f/1.8",
        "battery_capacity": "4500mAh",
        "processor": "骁龙888",
        "memory": "12GB+256GB",
        "screen_size": "6.5英寸",
        "weight": "185g"
    },
    "智能手机B": {
        "category": "手机",
        "price": 3999.00,
        "camera_pixels": "1亿像素",
        "camera_sensor": "三星HM2",
        "camera_aperture": "f/1.6",
        "battery_capacity": "5000mAh",
        "processor": "骁龙8 Gen1",
        "memory": "16GB+512GB",
        "screen_size": "6.7英寸",
        "weight": "198g"
    },
    "笔记本电脑B": {
        "category": "电脑",
        "price": 5999.00,
        "processor": "Intel i7",
        "memory": "16GB",
        "storage": "512GB SSD",
        "screen_size": "15.6英寸",
        "graphics": "NVIDIA RTX 3050",
        "battery_life": "8小时",
        "weight": "1.8kg"
    }
}

# 销售数据（保持不变）
SALES_DATABASE = {
    "华东区": {
        "2024-06-10": [
            {"product_name": "智能手机A", "sales_amount": 150000.00, "quantity": 50},
            {"product_name": "智能手机B", "sales_amount": 200000.00, "quantity": 50},
            {"product_name": "笔记本电脑B", "sales_amount": 300000.00, "quantity": 30},
            {"product_name": "无线耳机C", "sales_amount": 50000.00, "quantity": 100},
            {"product_name": "智能手表D", "sales_amount": 75000.00, "quantity": 50},
            {"product_name": "平板电脑E", "sales_amount": 120000.00, "quantity": 20}
        ]
    },
    "华北区": {
        "2024-06-10": [
            {"product_name": "智能手机A", "sales_amount": 120000.00, "quantity": 40},
            {"product_name": "笔记本电脑B", "sales_amount": 180000.00, "quantity": 30},
        ]
    }
}

# 用户权限数据
USER_PERMISSIONS = {
    "cust001": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "cust002": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "cust003": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "cust004": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "cust005": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "cust006": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "cust007": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
    "emp001": {"user_type": "employee", "department": "销售部", "permissions": ["order_query", "product_query", "sales_data_query"]},
    "emp002": {"user_type": "employee", "department": "技术部", "permissions": ["order_query", "product_query"]},
    "emp003": {"user_type": "employee", "department": "客服部", "permissions": ["order_query", "product_query", "complaint_handling"]}
}

# 工具函数（保持不变）
@tool
def query_order_tool(order_query: str, runtime: ToolRuntime) -> Command:
    """查询订单状态和物流信息。"""
    state = runtime.state
    
    order_id_match = re.search(r'订单\s*(\d+)', order_query)
    if not order_id_match:
        order_id_match = re.search(r'(\d{6,})', order_query)
    
    if order_id_match:
        order_id = order_id_match.group(1)
        
        updates = {"current_order_id": order_id}
        messages = []
        
        if order_id in ORDER_DATABASE:
            order_info = ORDER_DATABASE[order_id]
            response = (
                f"订单 {order_id}（产品：{order_info['product_name']}）\n"
                f"当前状态：{order_info['status']}\n"
                f"物流状态：{order_info['shipping_status']}\n"
                f"预计送达时间：{order_info['estimated_delivery']}\n"
                f"承运商：{order_info['carrier']}\n"
                f"运单号：{order_info['tracking_number']}\n\n"
                f"物流节点追踪：\n"
            )
            
            for node in order_info['shipping_nodes']:
                response += f"• {node}\n"
            
            messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        else:
            response = (
                f"未找到订单 {order_id}，请核对订单号是否正确。\n"
                f"您可以提供更多信息吗？或者如果您记得购买的产品，我可以帮您查找相关订单。"
            )
            messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        
        return Command(update={**updates, "messages": messages})
    else:
        response = "请问您要查询的订单号是多少？"
        return Command(update={"messages": [ToolMessage(response, tool_call_id=runtime.tool_call_id)]})

@tool
def compare_products_tool(comparison_query: str, runtime: ToolRuntime) -> Command:
    """比较两个或多个产品的参数。"""
    comparison_dimensions = {
        '拍照': ['camera_pixels', 'camera_sensor', 'camera_aperture'],
        '性能': ['processor', 'memory'],
        '电池': ['battery_capacity', 'battery_life'],
        '价格': ['price'],
        '屏幕': ['screen_size'],
        '重量': ['weight']
    }
    
    detected_products = []
    for product_name in PRODUCT_DATABASE.keys():
        if product_name in comparison_query:
            detected_products.append(product_name)
    
    if len(detected_products) < 2:
        detected_products = ["智能手机A", "智能手机B"]
    
    dimension = None
    for dim in comparison_dimensions:
        if dim in comparison_query:
            dimension = dim
            break
    
    messages = []
    
    if dimension:
        if len(detected_products) >= 2:
            product1 = detected_products[0]
            product2 = detected_products[1]
            
            fields = comparison_dimensions[dimension]
            
            response = f"关于{product1}和{product2}的{dimension}对比：\n\n"
            
            for product in [product1, product2]:
                if product in PRODUCT_DATABASE:
                    response += f"{product}：\n"
                    product_info = PRODUCT_DATABASE[product]
                    for field in fields:
                        if field in product_info:
                            field_names = {
                                'camera_pixels': '像素',
                                'camera_sensor': '传感器',
                                'camera_aperture': '光圈',
                                'processor': '处理器',
                                'memory': '内存',
                                'battery_capacity': '电池容量',
                                'battery_life': '续航',
                                'price': '价格',
                                'screen_size': '屏幕尺寸',
                                'weight': '重量'
                            }
                            chinese_field = field_names.get(field, field)
                            response += f"  • {chinese_field}: {product_info[field]}\n"
                    response += "\n"
                else:
                    response += f"{product}：信息暂不可用\n\n"
            
            messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        else:
            messages.append(ToolMessage("抱歉，无法找到足够的产品信息进行比较。", tool_call_id=runtime.tool_call_id))
    else:
        response = (
            "您是希望比较这两款产品的哪个方面呢？\n"
            "例如：性能、拍照、电池、价格、屏幕或重量？\n"
            "请告诉我您最关注的方面，我可以为您提供详细的对比信息。"
        )
        messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
    
    return Command(update={"messages": messages})

@tool
def handle_complaint_tool(complaint_text: str, runtime: ToolRuntime) -> Command:
    """处理客户投诉，包括情感响应和问题解决流程。"""
    state = runtime.state
    updates = {}
    messages = []
    
    negative_keywords = ['差', '坏', '糟糕', '生气', '愤怒', '投诉', '退货', '赔偿', '损坏', '破']
    
    has_negative = any(keyword in complaint_text for keyword in negative_keywords)
    
    if has_negative:
        response = "非常抱歉给您带来这么糟糕的体验！\n"
        
        order_id_match = re.search(r'订单\s*(\d+)', complaint_text)
        if order_id_match:
            order_id = order_id_match.group(1)
            updates["current_order_id"] = order_id
            
            if order_id in ORDER_DATABASE:
                product_name = ORDER_DATABASE[order_id]["product_name"]
                response += f"我注意到您提到订单 {order_id}（产品：{product_name}）的问题。\n"
        
        response += (
            "请您提供以下信息，我将立即为您创建投诉工单并优先处理：\n"
            "1. 商品损坏的详细情况\n"
            "2. 商品损坏的照片（如果有）\n"
            "3. 您期望的解决方案（退货、换货或维修）\n\n"
        )
        
        if state.get("complaint_escalated", False):
            response += "我注意到您的问题可能需要更专业的处理。"
        else:
            response += "是否需要我立即为您转接高级客服专员进一步处理？"
        
        messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        
        updates["complaint_escalated"] = True
    else:
        response = "请问您遇到了什么问题？我会尽力为您解决。"
        messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
    
    return Command(update={**updates, "messages": messages})

@tool
def query_sales_data_tool(sales_query: str, runtime: ToolRuntime) -> Command:
    """查询销售数据，包括销售总额和Top商品。"""
    state = runtime.state
    user_id = state.get("user_id", "")
    messages = []
    
    if user_id not in USER_PERMISSIONS:
        response = "抱歉，用户身份验证失败，请先登录。"
        messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        return Command(update={"messages": messages})
    
    user_info = USER_PERMISSIONS[user_id]
    
    if "sales_data_query" not in user_info["permissions"]:
        response = "抱歉，您暂无该区域销售数据的访问权限。"
        messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        return Command(update={"messages": messages})
    
    region_match = re.search(r'([华东西南北中]{1,2}[东南西北中]?区)', sales_query)
    region = region_match.group(1) if region_match else "华东区"
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    if "昨天" in sales_query:
        query_date = yesterday.strftime("%Y-%m-%d")
    elif "今天" in sales_query:
        query_date = today.strftime("%Y-%m-%d")
    else:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', sales_query)
        query_date = date_match.group(1) if date_match else yesterday.strftime("%Y-%m-%d")
    
    if region not in SALES_DATABASE or query_date not in SALES_DATABASE[region]:
        response = f"抱歉，未找到{region}{query_date}的销售数据。"
        messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
        return Command(update={"messages": messages})
    
    sales_data = SALES_DATABASE[region][query_date]
    
    total_sales = sum(item["sales_amount"] for item in sales_data)
    total_quantity = sum(item["quantity"] for item in sales_data)
    
    sorted_sales = sorted(sales_data, key=lambda x: x["sales_amount"], reverse=True)
    top_5 = sorted_sales[:5]
    
    response = f"{region} {query_date} 销售数据汇总：\n"
    response += f"• 销售总额：{total_sales:,.2f}元\n"
    response += f"• 总销量：{total_quantity}件\n\n"
    
    response += "Top 5 商品（按销售额排序）：\n"
    for i, item in enumerate(top_5, 1):
        avg_price = item["sales_amount"] / item["quantity"] if item["quantity"] > 0 else 0
        response += f"{i}. {item['product_name']}\n"
        response += f"   销售额：{item['sales_amount']:,.2f}元，销量：{item['quantity']}件，均价：{avg_price:,.0f}元/件\n"
    
    messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
    
    return Command(update={"messages": messages})

@tool
def get_user_orders_tool(runtime: ToolRuntime) -> Command:
    """获取当前用户的所有订单列表。"""
    user_id = runtime.state.get("user_id", "")
    messages = []
    
    user_orders = []
    for order_id, order_info in ORDER_DATABASE.items():
        if order_info["customer_id"] == user_id:
            user_orders.append({
                "order_id": order_id,
                "product_name": order_info["product_name"],
                "status": order_info["status"],
                "estimated_delivery": order_info["estimated_delivery"]
            })
    
    if user_orders:
        response = "您当前的订单列表：\n\n"
        for order in user_orders:
            response += f"订单号：{order['order_id']}\n"
            response += f"产品：{order['product_name']}\n"
            response += f"状态：{order['status']}\n"
            response += f"预计送达：{order['estimated_delivery']}\n"
            response += "-" * 30 + "\n"
    else:
        response = "未找到您的订单记录。"
    
    messages.append(ToolMessage(response, tool_call_id=runtime.tool_call_id))
    return Command(update={"messages": messages})

class CustomerServiceAgent:
    """客服智能体类，可以被外部调用的版本"""
    
    def __init__(self):
        """初始化客服智能体"""
        self.model = ChatTongyi(model_name="qwen-max")
        
        # 客服系统提示词
        self.system_prompt = """
        你是一个智能客服机器人，专门处理客户咨询和内部员工查询。

        ## 用户类型和权限：
        1. **普通客户 (C端用户)**：可以查询订单状态、比较产品、提交投诉
        2. **内部员工 (B端用户)**：除C端功能外，还可以查询销售数据（根据部门权限）

        ## 核心功能：
        1. **订单查询**：帮助用户查询订单状态和物流信息
        2. **产品比较**：比较不同产品的参数和特性
        3. **投诉处理**：处理客户投诉，包括情感安抚和问题解决
        4. **销售数据查询**：为内部员工提供销售数据查询（需要权限）

        ## 交互原则：
        1. 始终保持友好、专业的语气
        2. 对客户投诉要先表达共情和道歉
        3. 当信息不足时要主动询问
        4. 对于复杂问题，适时建议转接人工客服
        5. 严格遵循权限控制，不提供无权限访问的信息
        """
        
        # 创建智能体
        self.agent = create_agent(
            self.model,
            tools=[query_order_tool, compare_products_tool, handle_complaint_tool, 
                   query_sales_data_tool, get_user_orders_tool],
            system_prompt=self.system_prompt,
            checkpointer=InMemorySaver()
        )
        
        print("🤖 客服智能体初始化完成")
    
    def process_query(self, user_id: str, user_input: str) -> Dict[str, Any]:
        """
        处理用户查询
        
        参数:
            user_id: 用户ID
            user_input: 用户输入文本
        
        返回:
            包含响应和元数据的字典
        """
        try:
            start_time = datetime.now()
            
            # 获取用户信息
            user_info = USER_PERMISSIONS.get(user_id, {"user_type": "customer", "department": None})
            user_type = user_info["user_type"]
            department = user_info["department"]
            
            # 创建状态
            state = {
                "user_id": user_id,
                "user_type": user_type,
                "department": department,
                "current_order_id": None,
                "complaint_escalated": False,
                "conversation_history": []
            }
            
            # 配置对话线程
            config = {"configurable": {"thread_id": f"cs-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"}}
            
            # 调用智能体
            result = self.agent.invoke(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    **state
                },
                config
            )
            
            # 计算响应时间
            end_time = datetime.now()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # 获取响应内容
            assistant_response = result['messages'][-1].content if result['messages'] else "抱歉，无法生成响应。"
            
            # 构建返回结果
            conversation_result = {
                "session_id": f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "user_id": user_id,
                "user_input": user_input,
                "assistant_response": assistant_response,
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": response_time_ms,
                "metadata": {
                    "user_type": user_type,
                    "department": department,
                    "current_order_id": result.get("current_order_id"),
                    "complaint_escalated": result.get("complaint_escalated", False)
                }
            }
            
            return conversation_result
            
        except Exception as e:
            print(f"❌ 处理查询时出错: {e}")
            return {
                "session_id": f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "user_id": user_id,
                "user_input": user_input,
                "assistant_response": f"抱歉，处理您的请求时出现错误: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": 0,
                "error": str(e),
                "metadata": {}
            }
    
    async def process_query_async(self, user_id: str, user_input: str) -> Dict[str, Any]:
        """异步处理用户查询"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.process_query, user_id, user_input
        )
    
    def batch_process(self, queries: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        批量处理查询
        
        参数:
            queries: 列表，每个元素是(user_id, user_input)元组
        
        返回:
            对话结果列表
        """
        results = []
        for user_id, user_input in queries:
            result = self.process_query(user_id, user_input)
            results.append(result)
        return results

def run_customer_service():
    """交互式客服系统（原始功能保持不变）"""
    print("=" * 60)
    print("智能客服机器人系统")
    print("=" * 60)
    
    # 创建客服智能体
    agent = CustomerServiceAgent()
    
    # 用户身份选择
    print("请选择用户身份：")
    print("1. 普通客户 (C端)")
    print("2. 内部员工 (B端)")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "2":
        print("\n可用的员工ID：")
        print("- emp001 (销售部)")
        print("- emp002 (技术部)")
        print("- emp003 (客服部)")
        user_id = input("请输入员工ID: ").strip()
        if user_id not in ["emp001", "emp002", "emp003"]:
            user_id = "emp001"
            print(f"使用默认员工ID: {user_id}")
    else:
        print("\n可用的客户ID：")
        print("- cust001, cust002, cust003, cust004, cust005, cust006, cust007")
        user_id = input("请输入客户ID (默认: cust001): ").strip() or "cust001"
    
    # 获取用户类型
    user_info = USER_PERMISSIONS.get(user_id, {"user_type": "customer", "department": ""})
    user_type = user_info["user_type"]
    department = user_info["department"]
    
    print(f"\n欢迎，{'客户' if user_type == 'customer' else '员工'} {user_id}" + 
          (f" ({department})" if department else ""))
    print("输入 '退出' 或 'quit' 结束对话")
    print("-" * 60)
    
    # 对话循环
    while True:
        user_input = input("\n您: ").strip()
        
        if user_input.lower() in ['退出', 'quit', 'exit', 'bye']:
            print("\n客服: 感谢使用智能客服机器人，再见！")
            break
        
        if not user_input:
            continue
        
        # 处理查询
        result = agent.process_query(user_id, user_input)
        print(f"\n客服: {result['assistant_response']}")


if __name__ == "__main__":
    run_customer_service()
