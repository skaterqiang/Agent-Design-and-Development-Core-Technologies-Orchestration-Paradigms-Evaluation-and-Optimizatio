import os
from typing import Optional, List, Dict, Any, Tuple, Generator
from langchain_core.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent, AgentState
from langchain.tools import ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, BaseMessage
from datetime import datetime, timedelta
import re
import time
import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# --- 客服机器人状态 (保持不变) ---
class CustomerServiceState(AgentState):
    user_id: str
    user_type: str
    department: Optional[str] = None
    current_order_id: Optional[str] = None
    complaint_escalated: bool = False
    conversation_history: List[Dict[str, str]] = []

# --- 原始的 CustomerServiceAgent 类 (保持不变) ---
class CustomerServiceAgent:
    # ... (保持原有代码不变) ...
    def __init__(self, api_key: str, model_name: str = "qwen-max"):
        """
        初始化客服代理。
        Args:
            api_key (str): 通义千问的API密钥。
            model_name (str): 使用的模型名称。
        """
        os.environ["DASHSCOPE_API_KEY"] = api_key
        self.model = ChatTongyi(model_name=model_name)
        self.agent = None
        self.current_config = None
        self.current_state = {}

        # 初始化模拟数据库
        self.ORDER_DATABASE = {
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

        self.PRODUCT_DATABASE = {
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

        self.SALES_DATABASE = {
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

        self.USER_PERMISSIONS = {
            "cust001": {"user_type": "customer", "department": None, "permissions": ["order_query", "product_query"]},
            "emp001": {"user_type": "employee", "department": "销售部", "permissions": ["order_query", "product_query", "sales_data_query"]},
            "emp002": {"user_type": "employee", "department": "技术部", "permissions": ["order_query", "product_query"]},
            "emp003": {"user_type": "employee", "department": "客服部", "permissions": ["order_query", "product_query", "complaint_handling"]}
        }

        # 定义工具
        self._define_tools()

        # 客服系统提示词
        system_prompt = """
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

## 对话示例：
用户：我的订单123456到哪了？
客服：订单123456（产品：智能手机A）当前状态：已发货，物流状态：运输中...

用户：A手机和B手机哪个拍照更好？
客服：关于智能手机A和智能手机B的拍照对比：智能手机A：像素：5000万...

用户：太差了！刚收到就是坏的！
客服：非常抱歉给您带来这么糟糕的体验！请您提供订单号和商品损坏的照片...

"""

        # 创建客服智能体
        self.agent = create_agent(
            self.model,
            tools=self.tools_list,
            system_prompt=system_prompt,
            state_schema=CustomerServiceState,
            checkpointer=InMemorySaver()
        )

    def _define_tools(self):
        """定义并注册所有客服工具。"""
        # --- 工具1：订单查询 ---
        @tool
        def query_order_tool(order_query: str, runtime: ToolRuntime) -> Command:
            """查询订单状态和物流信息。

            参数:
            order_query: 用户查询订单的文本，可能包含订单号
            """
            return self._query_order_tool_impl(order_query, runtime)

        # --- 工具2：产品比较 ---
        @tool
        def compare_products_tool(comparison_query: str, runtime: ToolRuntime) -> Command:
            """比较两个或多个产品的参数。
    
            参数:
            comparison_query: 用户询问产品比较的文本
            """
            return self._compare_products_tool_impl(comparison_query, runtime)

        # --- 工具3：投诉处理 ---
        @tool
        def handle_complaint_tool(complaint_text: str, runtime: ToolRuntime) -> Command:
            """处理客户投诉，包括情感响应和问题解决流程。
    
            参数:
            complaint_text: 用户的投诉文本
            """
            return self._handle_complaint_tool_impl(complaint_text, runtime)

        # --- 工具4：销售数据查询 ---
        @tool
        def query_sales_data_tool(sales_query: str, runtime: ToolRuntime) -> Command:
            """查询销售数据，包括销售总额和Top商品。
    
            参数:
            sales_query: 用户查询销售数据的文本
            """
            return self._query_sales_data_tool_impl(sales_query, runtime)

        # --- 工具5：获取用户订单列表 ---
        @tool
        def get_user_orders_tool(runtime: ToolRuntime) -> Command:
            """获取当前用户的所有订单列表。"""
            return self._get_user_orders_tool_impl(runtime)

        # Store tools in a list for passing to create_agent
        self.tools_list = [
            query_order_tool, compare_products_tool, handle_complaint_tool,
            query_sales_data_tool, get_user_orders_tool
        ]

    # --- 工具实现方法 ---

    def _query_order_tool_impl(self, order_query: str, runtime: ToolRuntime) -> Command:
        state = runtime.state
        order_id_match = re.search(r'订单\s*(\d+)', order_query) or re.search(r'(\d{6,})', order_query)
        updates = {}
        messages = []

        if order_id_match:
            order_id = order_id_match.group(1)
            updates["current_order_id"] = order_id

            if order_id in self.ORDER_DATABASE:
                order_info = self.ORDER_DATABASE[order_id]
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
                messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
            else:
                response = (
                    f"未找到订单 {order_id}，请核对订单号是否正确。\n"
                    f"您可以提供更多信息吗？或者如果您记得购买的产品，我可以帮您查找相关订单。"
                )
                messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
        else:
            response = "请问您要查询的订单号是多少？"
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))

        return Command(update={**updates, "messages": messages})

    def _compare_products_tool_impl(self, comparison_query: str, runtime: ToolRuntime) -> Command:
        comparison_dimensions = {
            '拍照': ['camera_pixels', 'camera_sensor', 'camera_aperture'],
            '性能': ['processor', 'memory'],
            '电池': ['battery_capacity', 'battery_life'],
            '价格': ['price'],
            '屏幕': ['screen_size'],
            '重量': ['weight']
        }

        detected_products = [p for p in self.PRODUCT_DATABASE.keys() if p in comparison_query]
        if len(detected_products) < 2:
            detected_products = ["智能手机A", "智能手机B"]

        dimension = next((dim for dim in comparison_dimensions if dim in comparison_query), None)
        messages = []

        if dimension and len(detected_products) >= 2:
            product1, product2 = detected_products[0], detected_products[1]
            fields = comparison_dimensions[dimension]
            response = f"关于{product1}和{product2}的{dimension}对比：\n\n"
            for product in [product1, product2]:
                response += f"{product}：\n"
                if product in self.PRODUCT_DATABASE:
                    product_info = self.PRODUCT_DATABASE[product]
                    for field in fields:
                        field_names = {'camera_pixels': '像素', 'camera_sensor': '传感器', 'camera_aperture': '光圈',
                                       'processor': '处理器', 'memory': '内存', 'battery_capacity': '电池容量',
                                       'battery_life': '续航', 'price': '价格', 'screen_size': '屏幕尺寸', 'weight': '重量'}
                        response += f"  • {field_names.get(field, field)}: {product_info.get(field, 'N/A')}\n"
                else:
                    response += f"  • 信息暂不可用\n"
                response += "\n"
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
        else:
            response = ("您是希望比较这两款产品的哪个方面呢？\n"
                        "例如：性能、拍照、电池、价格、屏幕或重量？\n"
                        "请告诉我您最关注的方面，我可以为您提供详细的对比信息。")
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))

        return Command(update={"messages": messages})

    def _handle_complaint_tool_impl(self, complaint_text: str, runtime: ToolRuntime) -> Command:
        state = runtime.state
        updates = {}
        messages = []
        negative_keywords = ['差', '坏', '糟糕', '生气', '愤怒', '投诉', '退货', '赔偿', '损坏', '破']
        has_negative = any(kw in complaint_text for kw in negative_keywords)

        if has_negative:
            response = "非常抱歉给您带来这么糟糕的体验！\n"
            order_id_match = re.search(r'订单\s*(\d+)', complaint_text)
            if order_id_match:
                order_id = order_id_match.group(1)
                updates["current_order_id"] = order_id
                if order_id in self.ORDER_DATABASE:
                    product_name = self.ORDER_DATABASE[order_id]["product_name"]
                    response += f"我注意到您提到订单 {order_id}（产品：{product_name}）的问题。\n"
            response += ("请您提供以下信息，我将立即为您创建投诉工单并优先处理：\n"
                         "1. 商品损坏的详细情况\n"
                         "2. 商品损坏的照片（如果有）\n"
                         "3. 您期望的解决方案（退货、换货或维修）\n\n")
            if state.get("complaint_escalated", False):
                 response += "我注意到您的问题可能需要更专业的处理。"
            else:
                response += "是否需要我立即为您转接高级客服专员进一步处理？"
                updates["complaint_escalated"] = True
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
        else:
            response = "请问您遇到了什么问题？我会尽力为您解决。"
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))

        return Command(update={**updates, "messages": messages})

    def _query_sales_data_tool_impl(self, sales_query: str, runtime: ToolRuntime) -> Command:
        state = runtime.state
        user_id = state.get("user_id", "")
        messages = []

        if user_id not in self.USER_PERMISSIONS:
            response = "抱歉，用户身份验证失败，请先登录。"
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
            return Command(update={"messages": messages})

        user_info = self.USER_PERMISSIONS[user_id]
        if "sales_data_query" not in user_info["permissions"]:
            response = "抱歉，您暂无该区域销售数据的访问权限。"
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
            return Command(update={"messages": messages})

        region_match = re.search(r'([华东西南北中]{1,2}[东南西北中]?区)', sales_query)
        region = region_match.group(1) if region_match else "华东区"

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        query_date = yesterday.strftime("%Y-%m-%d")
        if "昨天" in sales_query:
            query_date = yesterday.strftime("%Y-%m-%d")
        elif "今天" in sales_query:
            query_date = today.strftime("%Y-%m-%d")
        else:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', sales_query)
            query_date = date_match.group(1) if date_match else yesterday.strftime("%Y-%m-%d")

        if region not in self.SALES_DATABASE or query_date not in self.SALES_DATABASE[region]:
            response = f"抱歉，未找到{region}{query_date}的销售数据。"
            messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
            return Command(update={"messages": messages})

        sales_data = self.SALES_DATABASE[region][query_date]
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
        messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))

        return Command(update={"messages": messages})

    def _get_user_orders_tool_impl(self, runtime: ToolRuntime) -> Command:
        user_id = runtime.state.get("user_id", "")
        messages = []
        user_orders = [
            {"order_id": oid, "product_name": info["product_name"], "status": info["status"],
             "estimated_delivery": info["estimated_delivery"]}
            for oid, info in self.ORDER_DATABASE.items() if info["customer_id"] == user_id
        ]

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
        messages.append(ToolMessage(content=response, tool_call_id=runtime.tool_call_id))
        return Command(update={"messages": messages})

    # --- 核心方法：单独调用Agent处理查询 ---
    def process_query(self, user_input: str, user_id: str = None, 
                     reset_state: bool = False) -> Tuple[str, Dict[str, Any]]:
        """
        单独处理用户查询的方法，返回客服回复和更新后的状态。
        
        Args:
            user_input: 用户输入的查询文本
            user_id: 用户ID。为 None 时沿用 set_user() 设置的当前用户，
                     若从未调用过 set_user() 则回退到 "cust001"。
                     注意：不要在已调用 set_user() 的情况下再显式传入
                     其他 user_id，否则会覆盖当前身份并影响权限判定。
            reset_state: 是否重置对话状态，默认为False
            
        Returns:
            Tuple[str, Dict[str, Any]]: (客服回复文本, 更新后的状态字典)
        """
        # 未显式指定用户时，沿用 set_user() 设置的当前身份，
        # 避免默认值把员工身份静默降级为普通客户（导致权限误判）
        if user_id is None:
            user_id = self.current_state.get("user_id") or "cust001"

        # 获取用户信息
        user_info = self.USER_PERMISSIONS.get(user_id, {})
        user_type = user_info.get("user_type", "customer")
        department = user_info.get("department", "")
        
        # 配置对话线程
        if reset_state or not self.current_config:
            self.current_config = {"configurable": {"thread_id": f"cs-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"}}
        
        # 初始化或重置状态
        if reset_state or not self.current_state:
            self.current_state = {
                "user_id": user_id,
                "user_type": user_type,
                "department": department,
                "conversation_history": [],
                "current_order_id": None,
                "complaint_escalated": False
            }
        
        try:
            # 构建消息
            messages = [{"role": "user", "content": user_input}]
            
            # 调用智能体
            result = self.agent.invoke(
                {
                    "messages": messages,
                    **self.current_state
                },
                self.current_config
            )
            
            # 提取回复
            ai_message_content = ""
            for msg in reversed(result['messages']):
                if isinstance(msg, AIMessage):
                    ai_message_content = msg.content
                    break
            if not ai_message_content and result['messages']:
                ai_message_content = result['messages'][-1].content
            
            # 更新状态
            self.current_state.update({
                "current_order_id": result.get("current_order_id", self.current_state.get("current_order_id")),
                "complaint_escalated": result.get("complaint_escalated", self.current_state.get("complaint_escalated")),
                # 更新对话历史
                "conversation_history": self.current_state.get("conversation_history", []) + [
                    {"user": user_input, "assistant": ai_message_content}
                ]
            })
            
            return ai_message_content, self.current_state.copy()
            
        except Exception as e:
            error_msg = f"处理请求时出现错误: {str(e)}"
            return error_msg, self.current_state.copy()
    
    # --- 辅助方法：设置用户 ---
    def set_user(self, user_id: str) -> Dict[str, Any]:
        """
        设置当前用户，并返回初始状态。
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 用户状态信息
        """
        user_info = self.USER_PERMISSIONS.get(user_id, {})
        user_type = user_info.get("user_type", "customer")
        department = user_info.get("department", "")
        
        # 重置状态
        self.current_state = {
            "user_id": user_id,
            "user_type": user_type,
            "department": department,
            "conversation_history": [],
            "current_order_id": None,
            "complaint_escalated": False
        }
        
        # 重置配置
        self.current_config = {"configurable": {"thread_id": f"cs-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"}}
        
        return self.current_state.copy()
    
    # --- 辅助方法：获取用户信息 ---
    def get_user_info(self) -> Dict[str, Any]:
        """
        获取当前用户信息。
        
        Returns:
            Dict[str, Any]: 用户信息
        """
        user_id = self.current_state.get("user_id", "")
        if user_id in self.USER_PERMISSIONS:
            return self.USER_PERMISSIONS[user_id].copy()
        return {}
    
    # --- 运行逻辑（保持原有方法，用于向后兼容） ---
    def start_conversation_loop(self):
        """启动客服对话循环（保持原有功能）。"""
        print("=" * 60)
        print("智能客服机器人系统")
        print("=" * 60)

        print("请选择用户身份：")
        print("1. 普通客户 (C端)")
        print("2. 内部员工 (B端)")

        choice = input("\n请选择 (1/2): ").strip()
        user_id = "cust001"

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
            print("- cust001")
            user_id = input("请输入客户ID (默认: cust001): ").strip() or "cust001"

        # 设置用户
        self.set_user(user_id)
        
        user_info = self.get_user_info()
        user_type = user_info.get("user_type", "customer")
        department = user_info.get("department", "")

        print(f"\n欢迎，{'客户' if user_type == 'customer' else '员工'} {user_id}" +
              (f" ({department})" if department else ""))
        print("输入 '退出' 或 'quit' 结束对话")
        print("-" * 60)

        while True:
            user_input = input("\n您: ").strip()
            if user_input.lower() in ['退出', 'quit', 'exit', 'bye']:
                print("\n客服: 感谢使用智能客服机器人，再见！")
                break
            if not user_input:
                continue

            response, _ = self.process_query(user_input, user_id, reset_state=False)
            print(f"\n客服: {response}")

# --- 使用示例 ---
if __name__ == "__main__":
    # ✅ 从common/config.py获取API密钥
    try:
        API_KEY = get_api_key("tongyi")
        print("🔑 API配置加载成功")
        print("配置信息:", get_all_configs())
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
        sys.exit(1)
    
    # 创建客服代理
    cs_agent = CustomerServiceAgent(api_key=API_KEY)
    
    # 示例1：使用单独调用方法
    print("=== 示例1：单独调用Agent ===")
    
    # 设置用户为普通客户
    cs_agent.set_user("cust001")
    print(f"当前用户已设置为: cust001")
    
    # 单独处理查询
    query1 = "我的订单123456到哪了？"
    response1, state1 = cs_agent.process_query(query1)
    print(f"用户: {query1}")
    print(f"客服: {response1}")
    print(f"type: type{state1}")
    print(f"当前订单ID: {state1.get('current_order_id')}")
    print()
    
    # 继续处理下一个查询（状态会保持）
    query2 = "物流信息有更新吗？"
    response2, state2 = cs_agent.process_query(query2)
    print(f"用户: {query2}")
    print(f"客服: {response2}")
    print()
    
    # 示例2：切换用户
    print("=== 示例2：切换为员工用户 ===")
    cs_agent.set_user("emp001")
    print(f"当前用户已切换为: emp001 (销售部)")
    
    # 员工查询销售数据
    query3 = "华东区2024-06-10卖了多少钱？卖得最好的五样东西是什么？"
    response3, state3 = cs_agent.process_query(query3)
    print(f"用户: {query3}")
    print(f"客服: {response3}")
    print()
    
    # 示例3：重置状态
    print("=== 示例3：重置状态后查询 ===")
    query4 = "比较智能手机A和智能手机B的拍照"
    response4, state4 = cs_agent.process_query(query4, reset_state=True)
    print(f"用户: {query4}")
    print(f"客服: {response4}")
    print()
    
    # 示例4：使用原有的循环对话（可选）
    print("=== 示例4：启动循环对话 ===")
    use_loop = input("是否启动循环对话？(y/n): ").strip().lower()
    if use_loop == 'y':
        cs_agent.start_conversation_loop()
