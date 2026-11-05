"""
智能供应链系统 - 协调器模块测试
"""

import unittest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from coordinator import SupplyChainCoordinator

class TestSupplyChainCoordinator(unittest.TestCase):
    """协调器模块测试"""
    
    def setUp(self):
        """测试前准备"""
        # SupplyChainCoordinator 的构造函数不接收参数，集群/人机代理在 start() 中注册。
        self.coordinator = SupplyChainCoordinator()

    def test_initialize_coordinator(self):
        """测试协调器初始化"""
        self.assertIsNotNone(self.coordinator)
        # 初始状态字段为 system_status，取值 'initialized'
        self.assertEqual(self.coordinator.system_status, 'initialized')

    def test_start_coordinator(self):
        """测试启动协调器"""
        async def run_test():
            await self.coordinator.start()
            self.assertEqual(self.coordinator.system_status, 'running')
            # stop() 是同步方法（非协程），调用后状态置为 'stopped'
            self.coordinator.stop()
            self.assertEqual(self.coordinator.system_status, 'stopped')

        asyncio.run(run_test())

    def test_dispatch_task(self):
        """测试任务分发（dispatch_task 为真实公开接口，同步返回分发结果）"""
        # 注册一个集群，使自动化任务可被分配
        self.coordinator.register_cluster(
            "cluster_test",
            {"type": "optimization", "capacity": 10, "location": "测试数据中心"},
        )
        task = {
            "task_id": "test-001",
            "type": "inventory_check",
            "requires_human_judgment": False,
        }
        result = self.coordinator.dispatch_task(task)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "assigned")
        self.assertEqual(result["assignment_type"], "cluster")

        # 需要人工判断的任务应路由到人机代理
        self.coordinator.add_human_agent("human_test", ["decision_making"])
        human_task = {
            "task_id": "test-002",
            "type": "demand_forecast",
            "requires_human_judgment": True,
        }
        human_result = self.coordinator.dispatch_task(human_task)
        self.assertEqual(human_result["assignment_type"], "human")
        self.assertEqual(human_result["status"], "assigned")


if __name__ == '__main__':
    unittest.main()