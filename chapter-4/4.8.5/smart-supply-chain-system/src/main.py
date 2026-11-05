"""
智能供应链管理系统 - 主应用入口
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 使用简化版coordinator避免编码问题
from src.coordinator_simple import SupplyChainCoordinatorSimple
from src.config_loader import load_config

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(project_root / 'logs' / 'system.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("[MAIN] Starting Smart Supply Chain System...")
    
    try:
        # 加载配置
        config_loader = load_config()
        
        # 初始化协调器（使用简化版避免编码问题）
        coordinator = SupplyChainCoordinatorSimple()
        
        # 可以在这里使用配置来初始化其他组件
        system_config = config_loader.get_system_config()
        coordinator_config = config_loader.get_coordinator_config()
        
        logger.info(f"[CONFIG] System configured: {system_config.name} v{system_config.version}")
        logger.info(f"[CONFIG] Coordinator settings: heartbeat={coordinator_config.heartbeat_interval}s, "
                   f"max_tasks={coordinator_config.max_concurrent_tasks}")
        
        # 启动系统
        await coordinator.start()
        
        logger.info("[SUCCESS] Smart Supply Chain System started successfully!")
        logger.info("[RUN] System will run for 60 seconds to demonstrate detailed logging...")
        logger.info("[CTRL+C] Press Ctrl+C to stop early")
        
        # 保持运行一段时间以便观察日志
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 60:  # 运行60秒
            await asyncio.sleep(5)  # 每5秒检查一次
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 15 == 0:  # 每15秒显示一次进度
                logger.info(f"[PROGRESS] System running for {elapsed} seconds...")
            
    except KeyboardInterrupt:
        logger.info("[SHUTDOWN] Shutting down system...")
    except Exception as e:
        logger.error(f"[ERROR] System error: {e}")
        raise
    finally:
        # 确保系统正确关闭
        if 'coordinator' in locals():
            coordinator.stop()

if __name__ == "__main__":
    asyncio.run(main())