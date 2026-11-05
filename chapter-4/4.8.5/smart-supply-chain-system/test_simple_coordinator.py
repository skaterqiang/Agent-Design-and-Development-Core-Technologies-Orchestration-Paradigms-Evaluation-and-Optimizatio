"""
测试简化版coordinator的详细日志功能
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from coordinator_simple import SupplyChainCoordinatorSimple

async def test_simple_coordinator():
    """测试简化版coordinator的详细日志功能"""
    
    # 配置详细的日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("[TEST] Starting simplified coordinator logging test...")
    
    # 创建coordinator实例
    coordinator = SupplyChainCoordinatorSimple()
    
    # 启动coordinator
    logger.info("[START] Starting coordinator...")
    await coordinator.start()
    
    # 等待几秒钟观察日志
    logger.info("[WAIT] Waiting 45 seconds to observe detailed logging...")
    await asyncio.sleep(45)
    
    # 获取系统健康状态
    health = coordinator.get_system_health()
    logger.info("[REPORT] Final system health:")
    for key, value in health.items():
        logger.info(f"   {key}: {value}")
    
    # 停止coordinator
    logger.info("[STOP] Stopping coordinator...")
    coordinator.stop()
    
    logger.info("[COMPLETE] Test completed!")

if __name__ == "__main__":
    asyncio.run(test_simple_coordinator())