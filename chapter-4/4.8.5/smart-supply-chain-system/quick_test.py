"""
快速测试脚本 - 验证编码问题已解决
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from coordinator_simple import SupplyChainCoordinatorSimple

async def quick_test():
    """快速测试coordinator功能"""
    
    # 配置日志（指定UTF-8编码避免问题）
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    print("[TEST] Starting quick coordinator test...")
    
    # 创建coordinator实例
    coordinator = SupplyChainCoordinatorSimple()
    
    # 启动coordinator
    print("[START] Starting coordinator...")
    await coordinator.start()
    
    # 等待10秒观察日志
    print("[WAIT] Waiting 10 seconds...")
    await asyncio.sleep(10)
    
    # 发送一个测试任务
    test_task = {
        "task_id": "QUICK_TEST_001",
        "type": "inventory_check", 
        "priority": "medium",
        "requires_human_judgment": False,
        "description": "Quick test task"
    }
    
    print("[TASK] Dispatching test task...")
    result = coordinator.dispatch_task(test_task)
    print(f"[RESULT] Task assigned to: {result.get('assigned_to', 'N/A')}")
    
    # 停止coordinator
    print("[STOP] Stopping coordinator...")
    coordinator.stop()
    
    print("[DONE] Quick test completed!")

if __name__ == "__main__":
    asyncio.run(quick_test())