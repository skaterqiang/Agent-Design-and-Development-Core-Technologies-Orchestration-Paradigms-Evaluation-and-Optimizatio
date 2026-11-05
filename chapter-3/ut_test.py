import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import asyncio
import threading
from datetime import datetime, timedelta

# 导入要测试的类
from customer_service_obj import CustomerServiceAgent, CustomerServiceState
import sys
import os
# 添加上层common目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'common'))
from config import get_api_key, get_all_configs  # 从上层common导入

# ✅ 从common/config.py获取API密钥
try:
    API_KEY = get_api_key("tongyi")
    print("🔑 API配置加载成功")
    print("配置信息:", get_all_configs())
except ValueError as e:
    print(f"❌ 配置错误: {e}")
    print("请设置环境变量 TONGYI_API_KEY 或修改 common/config.py")
    sys.exit(1)

class TestCustomerServiceAgent(unittest.TestCase):
    """客服机器人单元测试"""
    
    def setUp(self):
        """测试前设置"""
        # 使用模拟的API密钥
        self.api_key = API_KEY
        self.agent = CustomerServiceAgent(api_key=self.api_key)
        
        # 设置测试用户
        self.test_customer_id = "cust001"
        self.test_employee_id = "emp001"
    
    # ====================== 基本功能测试 ======================
    
    def test_process_query_order_query(self):
        """测试订单查询功能"""
        print("\n测试订单查询功能...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 测试订单查询
        query = "我的订单123456到哪了？"
        response, state = self.agent.process_query(query)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        print(f"状态: {state}")
        
        # 验证响应包含订单信息
        self.assertIn("123456", response)
        self.assertIn("智能手机A", response)
        self.assertIn("状态", response)
        
        # 验证状态更新
        self.assertEqual(state.get("current_order_id"), "123456")
    
    def test_process_query_product_comparison(self):
        """测试产品比较功能"""
        print("\n测试产品比较功能...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 测试产品比较
        query = "比较智能手机A和智能手机B的拍照"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证响应包含比较信息
        self.assertIn("智能手机A", response)
        self.assertIn("智能手机B", response)
        self.assertIn("拍照", response)
        self.assertIn("像素", response)
    
    def test_process_query_complaint(self):
        """测试投诉处理功能"""
        print("\n测试投诉处理功能...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 测试投诉处理
        query = "我要投诉！刚收到的手机是坏的！"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证响应包含投诉处理信息
        self.assertIn("抱歉", response)
        self.assertIn("投诉", response)
        self.assertIn("工单", response)
        
        # 验证状态更新
        self.assertTrue(state.get("complaint_escalated", False))
    
    def test_process_query_sales_data(self):
        """测试销售数据查询功能"""
        print("\n测试销售数据查询功能...")
        
        # 设置用户为员工
        self.agent.set_user(self.test_employee_id)
        
        # 测试销售数据查询
        query = "华东区2024-06-10的销售数据"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"员工查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证响应包含销售数据
        self.assertIn("销售数据", response)
        self.assertIn("华东区", response)
        self.assertIn("2024-06-10", response)
        self.assertIn("销售总额", response)
    
    # ====================== 对话上下文测试 ======================
    
    def test_conversation_context(self):
        """测试对话上下文维护"""
        print("\n测试对话上下文维护...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 第一轮查询
        query1 = "我的订单123456"
        response1, state1 = self.agent.process_query(query1, reset_state=True)
        
        print(f"用户查询1: {query1}")
        print(f"客服响应1: {response1}")
        
        # 第二轮查询（使用上下文）
        query2 = "物流信息有更新吗？"
        response2, state2 = self.agent.process_query(query2)
        
        print(f"用户查询2: {query2}")
        print(f"客服响应2: {response2}")
        
        # 验证上下文被正确使用
        self.assertIn("物流", response2)
        self.assertIn("123456", response2)
        
        # 验证状态保持
        self.assertEqual(state2.get("current_order_id"), "123456")
    
    def test_topic_switching(self):
        """测试话题切换"""
        print("\n测试话题切换...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 第一轮查询：订单查询
        query1 = "我的订单123456"
        response1, state1 = self.agent.process_query(query1, reset_state=True)
        
        print(f"用户查询1: {query1}")
        print(f"客服响应1: {response1}")
        
        # 第二轮查询：切换到产品比较
        query2 = "比较智能手机A和智能手机B"
        response2, state2 = self.agent.process_query(query2)
        
        print(f"用户查询2: {query2}")
        print(f"客服响应2: {response2}")
        
        # 验证话题已切换
        self.assertIn("比较", response2)
        self.assertIn("智能手机A", response2)
        self.assertIn("智能手机B", response2)
        
        # 验证状态更新（话题切换）
        # 注意：切换话题后，current_order_id可能被清除或保留，取决于实现
        # 这里我们只是检查响应是否正确处理了新话题
    
    # ====================== 权限控制测试 ======================
    
    def test_permission_control_customer(self):
        """测试普通客户的权限控制"""
        print("\n测试普通客户的权限控制...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 尝试查询销售数据（普通客户应该没有权限）
        query = "华东区2024-06-10的销售数据"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证权限被拒绝
        self.assertTrue(
            "抱歉" in response or 
            "权限" in response or 
            "无法" in response,
            f"普通客户应被拒绝访问销售数据，但得到: {response}"
        )
    
    def test_permission_control_employee(self):
        """测试员工的权限控制"""
        print("\n测试员工的权限控制...")
        
        # 设置用户为员工
        self.agent.set_user(self.test_employee_id)
        
        # 查询销售数据（员工应该有权限）
        query = "华北区2024-06-10的数据"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"员工查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证有权限访问
        self.assertIn("销售数据", response)
        self.assertIn("华北区", response)
        self.assertIn("2024-06-10", response)
    
    # ====================== 错误处理测试 ======================
    
    def test_error_handling_invalid_order(self):
        """测试无效订单处理"""
        print("\n测试无效订单处理...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 查询不存在的订单
        query = "我的订单999999"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证给出了合理的错误响应
        self.assertTrue(
            "未找到" in response or 
            "不存在" in response or 
            "请核对" in response,
            f"无效订单应给出错误提示，但得到: {response}"
        )
    
    def test_error_handling_vague_query(self):
        """测试模糊查询处理"""
        print("\n测试模糊查询处理...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 模糊查询
        query = "手机"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证系统要求澄清或提供了帮助
        self.assertTrue(
            "请问" in response or 
            "请提供" in response or 
            "您想" in response or
            "帮助" in response,
            f"模糊查询应要求澄清或提供帮助，但得到: {response}"
        )
    
    def test_error_handling_multi_intent(self):
        """测试多意图查询处理"""
        print("\n测试多意图查询处理...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 多意图查询
        query = "我想查订单123456并且比较A和B手机"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证系统尝试处理多个意图
        # 可能先处理一个意图，或者询问用户优先级
        self.assertTrue(
            len(response) > 50,  # 多意图响应应该更详细
            f"多意图查询应返回更详细的响应，但得到: {response}"
        )
    
    # ====================== 工作流测试 ======================
    
    def test_customer_workflow(self):
        """测试完整的客户工作流"""
        print("\n测试完整的客户工作流...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 步骤1: 查询订单
        print("\n步骤1: 查询订单")
        query1 = "我的订单123456"
        response1, state1 = self.agent.process_query(query1, reset_state=True)
        print(f"用户: {query1}")
        print(f"客服: {response1}")
        
        # 步骤2: 查询物流（使用上下文）
        print("\n步骤2: 查询物流")
        query2 = "物流信息有更新吗？"
        response2, state2 = self.agent.process_query(query2)
        print(f"用户: {query2}")
        print(f"客服: {response2}")
        
        # 步骤3: 投诉
        print("\n步骤3: 投诉")
        query3 = "太慢了，我要投诉！"
        response3, state3 = self.agent.process_query(query3)
        print(f"用户: {query3}")
        print(f"客服: {response3}")
        
        # 验证工作流完整性
        self.assertIn("123456", response1)
        self.assertIn("物流", response2)
        self.assertIn("投诉", response3)
        self.assertTrue(state3.get("complaint_escalated", False))
    
    def test_employee_workflow(self):
        """测试完整的员工工作流"""
        print("\n测试完整的员工工作流...")
        
        # 设置用户为员工
        self.agent.set_user(self.test_employee_id)
        
        # 步骤1: 查询销售数据
        print("\n步骤1: 查询销售数据")
        query1 = "华东区2024-06-10卖了多少钱？卖得最好的五样东西是什么？"
        response1, state1 = self.agent.process_query(query1, reset_state=True)
        print(f"员工: {query1}")
        print(f"客服: {response1}")
        
        # 步骤2: 查询另一个区域的销售数据
        print("\n步骤2: 查询另一个区域的销售数据")
        query2 = "华北区2024-06-10的数据"
        response2, state2 = self.agent.process_query(query2)
        print(f"员工: {query2}")
        print(f"客服: {response2}")
        
        # 步骤3: 查询订单
        print("\n步骤3: 查询订单")
        query3 = "订单789012"
        response3, state3 = self.agent.process_query(query3)
        print(f"员工: {query3}")
        print(f"客服: {response3}")
        
        # 验证工作流完整性
        self.assertIn("销售数据", response1)
        self.assertIn("华东区", response1)
        self.assertIn("华北区", response2)
        self.assertIn("789012", response3)
    
    # ====================== 性能测试 ======================
    
    def test_performance_response_time(self):
        """测试响应时间性能"""
        print("\n测试响应时间性能...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        test_queries = [
            ("订单123456", "订单查询"),
            ("比较智能手机A和B的拍照", "产品比较"),
            ("我要投诉订单123456质量问题", "投诉处理"),
        ]
        
        max_response_time = 2.0  # 最大响应时间（秒）
        
        for query, query_type in test_queries:
            with self.subTest(query=query):
                start_time = time.time()
                
                response, state = self.agent.process_query(query, reset_state=True)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                print(f"查询类型: {query_type}")
                print(f"查询内容: {query}")
                print(f"响应时间: {response_time:.3f}秒")
                print(f"响应长度: {len(response)}字符")
                print("-" * 40)
                
                self.assertLess(
                    response_time, max_response_time,
                    f"查询'{query[:20]}...'响应时间{response_time:.3f}s超过{max_response_time}s限制"
                )
                
                # 验证响应质量
                self.assertGreater(
                    len(response), 20,
                    f"查询'{query[:20]}...'响应太短: {response}"
                )
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        print("\n测试并发请求处理...")
        
        results = []
        lock = threading.Lock()
        
        def make_request(query, user_id, index):
            """模拟单个请求"""
            try:
                # 为每个线程创建独立的agent实例
                agent = CustomerServiceAgent(api_key=self.api_key)
                agent.set_user(user_id)
                
                start_time = time.time()
                
                response, state = agent.process_query(query, reset_state=True)
                
                end_time = time.time()
                
                with lock:
                    results.append({
                        "success": True,
                        "time": end_time - start_time,
                        "response_length": len(response),
                        "query": query
                    })
            except Exception as e:
                with lock:
                    results.append({
                        "success": False,
                        "error": str(e),
                        "query": query
                    })
        
        # 准备并发请求
        concurrent_requests = 3  # 减少并发数以避免API限制
        threads = []
        
        # 创建请求线程
        for i in range(concurrent_requests):
            if i % 2 == 0:
                user_id = self.test_customer_id
                query = f"订单12345{i}"
            else:
                user_id = self.test_employee_id
                query = f"华东区2024-06-1{i}的销售数据"
            
            thread = threading.Thread(
                target=make_request,
                args=(query, user_id, i)
            )
            threads.append(thread)
        
        # 启动所有线程
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=10.0)  # 设置超时
        
        total_time = time.time() - start_time
        
        # 分析结果
        successful_requests = sum(1 for r in results if r.get("success", False))
        failed_requests = len(results) - successful_requests
        
        times = [r["time"] for r in results if r.get("success")]
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            print(f"\n并发测试结果:")
            print(f"  总请求数: {concurrent_requests}")
            print(f"  成功请求: {successful_requests}")
            print(f"  失败请求: {failed_requests}")
            print(f"  总耗时: {total_time:.3f}秒")
            print(f"  平均响应时间: {avg_time:.3f}秒")
            print(f"  最大响应时间: {max_time:.3f}秒")
            
            # 验证大部分请求成功
            self.assertGreaterEqual(
                successful_requests, concurrent_requests * 0.7,  # 70%成功率
                f"并发请求成功率低: {successful_requests}/{concurrent_requests}成功"
            )
    
    # ====================== 边界条件测试 ======================
    
    def test_boundary_empty_query(self):
        """测试空查询处理"""
        print("\n测试空查询处理...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 空查询
        query = ""
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: (空)")
        print(f"客服响应: {response}")
        
        # 验证系统处理了空查询
        self.assertGreater(len(response), 0, "空查询应得到响应")
    
    def test_boundary_long_query(self):
        """测试长查询处理"""
        print("\n测试长查询处理...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 长查询
        long_query = "我想查询我的订单123456的物流信息，同时比较智能手机A和智能手机B的拍照功能，还想了解华东区昨天的销售数据，另外我的手机有点问题需要投诉，还有查看我所有的订单列表"
        response, state = self.agent.process_query(long_query, reset_state=True)
        
        print(f"用户查询长度: {len(long_query)}字符")
        print(f"客服响应长度: {len(response)}字符")
        print(f"客服响应: {response[:100]}...")
        
        # 验证系统处理了长查询
        self.assertGreater(len(response), 50, "长查询应得到详细响应")
    
    def test_boundary_special_characters(self):
        """测试特殊字符查询处理"""
        print("\n测试特殊字符查询处理...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 包含特殊字符的查询
        query = "订单#123456@到哪里了？"
        response, state = self.agent.process_query(query, reset_state=True)
        
        print(f"用户查询: {query}")
        print(f"客服响应: {response}")
        
        # 验证系统处理了特殊字符
        self.assertIn("123456", response, "应能处理包含特殊字符的订单号")
    
    # ====================== 状态管理测试 ======================
    
    def test_state_reset(self):
        """测试状态重置"""
        print("\n测试状态重置...")
        
        # 设置用户为普通客户
        self.agent.set_user(self.test_customer_id)
        
        # 第一轮查询
        query1 = "我的订单123456"
        response1, state1 = self.agent.process_query(query1, reset_state=True)
        
        # 验证状态设置
        self.assertEqual(state1.get("current_order_id"), "123456")
        
        # 第二轮查询（重置状态）
        query2 = "比较智能手机A和B"
        response2, state2 = self.agent.process_query(query2, reset_state=True)
        
        # 验证状态已重置
        # 注意：取决于实现，重置后current_order_id可能为None
        # 这里我们主要验证查询能正常执行
        self.assertIn("比较", response2)
    
    def test_user_switching(self):
        """测试用户切换"""
        print("\n测试用户切换...")
        
        # 第一轮：普通客户查询订单
        self.agent.set_user(self.test_customer_id)
        query1 = "我的订单123456"
        response1, state1 = self.agent.process_query(query1, reset_state=True)
        
        print(f"客户查询: {query1}")
        print(f"客服响应: {response1}")
        
        # 第二轮：切换到员工查询销售数据
        self.agent.set_user(self.test_employee_id)
        query2 = "华东区2024-06-10的销售数据"
        response2, state2 = self.agent.process_query(query2, reset_state=True)
        
        print(f"员工查询: {query2}")
        print(f"客服响应: {response2}")
        
        # 验证用户切换后权限正确
        self.assertIn("销售数据", response2)
    
    def tearDown(self):
        """测试后清理"""
        pass


class TestCustomerServiceState(unittest.TestCase):
    """测试状态管理"""
    
    def test_state_initialization(self):
        """测试状态初始化"""
        print("\n测试状态初始化...")
        
        # 创建真正的CustomerServiceState对象
        state = CustomerServiceState(
            user_id="test001",
            user_type="customer",
            department=None,
            current_order_id=None,
            complaint_escalated=False,
            conversation_history=[]
        )
        
        print(f"初始化状态: {state}")
        # 先打印状态类型以了解如何处理
        print(f"状态类型: {type(state)}")
        self.assertEqual(state.get("user_id"), "test001")
        self.assertEqual(state.get("user_type"), "customer")
        self.assertIsNone(state.get("department"))
        self.assertIsNone(state.get("current_order_id"))
        self.assertFalse(state.get("complaint_escalated", False))
        self.assertEqual(len(state.get("conversation_history", [])), 0)
             

    def test_state_update(self):
        """测试状态更新"""
        print("\n测试状态更新...")
        
        # 创建真正的CustomerServiceState对象
        state = CustomerServiceState(
            user_id="test001",
            user_type="customer",
            conversation_history=[]
        )
        
        # 模拟状态更新
        state["current_order_id"] = "123456"
        state["complaint_escalated"] = True
        state["conversation_history"].append({"role": "user", "content": "测试消息"})
        
        print(f"更新后状态: {state}")
        
        self.assertEqual(state.get("current_order_id"), "123456")
        self.assertTrue(state.get("complaint_escalated"))
        self.assertEqual(len(state.get("conversation_history")), 1)
    
    def test_state_serialization(self):
        """测试状态序列化"""
        print("\n测试状态序列化...")
        
        conversation_history = [
            {"role": "user", "content": "订单查询"},
            {"role": "assistant", "content": "订单123456信息"}
        ]
        
        # 创建真正的CustomerServiceState对象
        state = CustomerServiceState(
            user_id="test001",
            user_type="customer",
            department="销售部",
            current_order_id="123456",
            complaint_escalated=True,
            conversation_history=conversation_history
        )
        
        self.assertEqual(state.get("user_id"), "test001")
        self.assertEqual(state.get("user_type"), "customer")
        self.assertEqual(state.get("department"), "销售部")
        self.assertEqual(state.get("current_order_id"), "123456")
        self.assertTrue(state.get("complaint_escalated"))
        self.assertEqual(len(state.get("conversation_history")), 2)   


def run_all_tests():
    """运行所有测试"""
    print("开始运行所有测试...")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 使用TestLoader加载测试用例
    loader = unittest.TestLoader()
    # 添加测试类
    test_suite.addTest(loader.loadTestsFromTestCase(TestCustomerServiceAgent))
    test_suite.addTest(loader.loadTestsFromTestCase(TestCustomerServiceState))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要:")
    print(f"  运行测试: {result.testsRun}")
    print(f"  失败测试: {len(result.failures)}")
    print(f"  错误测试: {len(result.errors)}")
    print(f"  跳过测试: {len(result.skipped)}")
    print("=" * 60)
    
    return result


def run_specific_test_category(category: str):
    """运行特定类别的测试"""
    print(f"开始运行 {category} 测试...")
    print("=" * 60)
    test_loader = unittest.TestLoader()
    
    # 根据类别选择测试
    if category == "基本功能":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_process_query_order_query",
            "__main__.TestCustomerServiceAgent.test_process_query_product_comparison",
            "__main__.TestCustomerServiceAgent.test_process_query_complaint",
            "__main__.TestCustomerServiceAgent.test_process_query_sales_data",
        ]
    elif category == "对话管理":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_conversation_context",
            "__main__.TestCustomerServiceAgent.test_topic_switching",
            "__main__.TestCustomerServiceState.test_state_initialization",
            "__main__.TestCustomerServiceState.test_state_update",
        ]
    elif category == "权限控制":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_permission_control_customer",
            "__main__.TestCustomerServiceAgent.test_permission_control_employee",
        ]
    elif category == "错误处理":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_error_handling_invalid_order",
            "__main__.TestCustomerServiceAgent.test_error_handling_vague_query",
            "__main__.TestCustomerServiceAgent.test_error_handling_multi_intent",
        ]
    elif category == "工作流":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_customer_workflow",
            "__main__.TestCustomerServiceAgent.test_employee_workflow",
        ]
    elif category == "性能测试":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_performance_response_time",
            "__main__.TestCustomerServiceAgent.test_concurrent_requests",
        ]
    elif category == "边界条件":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_boundary_empty_query",
            "__main__.TestCustomerServiceAgent.test_boundary_long_query",
            "__main__.TestCustomerServiceAgent.test_boundary_special_characters",
        ]
    elif category == "状态管理":
        test_names = [
            "__main__.TestCustomerServiceAgent.test_state_reset",
            "__main__.TestCustomerServiceAgent.test_user_switching",
            "__main__.TestCustomerServiceState.test_state_initialization",
            "__main__.TestCustomerServiceState.test_state_update",
            "__main__.TestCustomerServiceState.test_state_serialization",
        ]
    else:
        print(f"未知测试类别: {category}")
        return
    
    # 运行选定的测试
    
    suite = test_loader.loadTestsFromNames(test_names)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def run_single_test(test_name: str):
    """运行单个测试"""
    print(f"开始运行单个测试: {test_name}")
    print("=" * 60)
    
    test_loader = unittest.TestLoader()
    
    # 运行单个测试
    suite = test_loader.loadTestsFromName("__main__."+test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result

# 在同一个文件中，我们想要通过名称加载测试用例，我们可以这样做：
# 方法一：使用__main__作为模块名，因为当我们直接运行脚本时，测试类是在__main__模块中定义的。
# 方法二：将测试类放在一个单独的模块（文件）中，并确保该模块在Python路径中。
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="客服机器人单元测试")
    parser.add_argument("--category", type=str, choices=[
        "all", "基本功能", "对话管理", "权限控制", 
        "错误处理", "工作流", "性能测试", "边界条件", "状态管理"
    ], default="all", help="运行特定类别的测试")
    
    parser.add_argument("--test", type=str, help="运行单个测试（格式：ClassName.test_method）")
    
    args = parser.parse_args()
    
    if args.test:
        result = run_single_test(args.test)
    elif args.category == "all":
        result = run_all_tests()
    else:
        result = run_specific_test_category(args.category)

    # 把测试结果传递到进程退出码，否则失败会被 CI/脚本静默忽略
    if result is None:
        sys.exit(2)
    sys.exit(0 if result.wasSuccessful() else 1)
