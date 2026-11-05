"""
智能供应链系统 - 全链条覆盖模块
实现从原材料采购到最终交付的全流程管理
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

class SupplyChainStage(Enum):
    """供应链阶段枚举"""
    RAW_MATERIAL = "raw_material"
    PROCUREMENT = "procurement"
    MANUFACTURING = "manufacturing"
    WAREHOUSING = "warehousing"
    LOGISTICS = "logistics"
    DISTRIBUTION = "distribution"
    RETAIL = "retail"
    CUSTOMER_DELIVERY = "customer_delivery"

@dataclass
class SupplyChainEntity:
    """供应链实体"""
    entity_id: str
    name: str
    type: str  # supplier, manufacturer, warehouse, distributor, retailer
    location: Dict[str, Any]
    contact_info: Dict[str, Any]
    capabilities: List[str]
    status: str  # active, inactive, suspended

@dataclass
class SupplyChainProcess:
    """供应链流程"""
    process_id: str
    stage: SupplyChainStage
    entity_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str  # pending, in_progress, completed, delayed, cancelled
    metrics: Dict[str, Any]
    dependencies: List[str]  # 依赖的其他流程ID

class FullCoverageManager:
    """全链条覆盖管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.entities: Dict[str, SupplyChainEntity] = {}
        self.processes: Dict[str, SupplyChainProcess] = {}
        self.stage_transitions: Dict[str, List[str]] = {}  # 流程ID到下一阶段的映射
        self.logger = logging.getLogger(__name__)
        
    async def register_entity(self, entity_data: Dict[str, Any]) -> bool:
        """注册供应链实体"""
        try:
            entity_id = entity_data.get('entity_id')
            if not entity_id:
                return False
                
            entity = SupplyChainEntity(
                entity_id=entity_id,
                name=entity_data.get('name', f'entity-{entity_id}'),
                type=entity_data.get('type', 'unknown'),
                location=entity_data.get('location', {}),
                contact_info=entity_data.get('contact_info', {}),
                capabilities=entity_data.get('capabilities', []),
                status=entity_data.get('status', 'active')
            )
            
            self.entities[entity_id] = entity
            self.logger.info(f"Entity {entity_id} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register entity: {e}")
            return False
    
    async def create_process(self, process_data: Dict[str, Any]) -> str:
        """创建供应链流程"""
        process_id = process_data.get('process_id', f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
        
        process = SupplyChainProcess(
            process_id=process_id,
            stage=SupplyChainStage(process_data['stage']),
            entity_id=process_data['entity_id'],
            start_time=process_data.get('start_time'),
            end_time=process_data.get('end_time'),
            status=process_data.get('status', 'pending'),
            metrics=process_data.get('metrics', {}),
            dependencies=process_data.get('dependencies', [])
        )
        
        self.processes[process_id] = process
        
        # 设置阶段转换关系
        if 'next_stages' in process_data:
            self.stage_transitions[process_id] = process_data['next_stages']
            
        self.logger.info(f"Process {process_id} created for stage {process.stage.value}")
        return process_id
    
    async def start_process(self, process_id: str) -> bool:
        """启动流程"""
        if process_id not in self.processes:
            return False
            
        process = self.processes[process_id]
        if process.status != 'pending':
            return False
            
        process.status = 'in_progress'
        process.start_time = datetime.now()
        self.logger.info(f"Process {process_id} started")
        return True
    
    async def complete_process(self, process_id: str, metrics: Dict[str, Any] = None) -> bool:
        """完成流程"""
        if process_id not in self.processes:
            return False
            
        process = self.processes[process_id]
        if process.status not in ['in_progress', 'delayed']:
            return False
            
        process.status = 'completed'
        process.end_time = datetime.now()
        if metrics:
            process.metrics.update(metrics)
            
        self.logger.info(f"Process {process_id} completed")
        return True
    
    async def get_chain_status(self, product_id: str = None) -> Dict[str, Any]:
        """获取供应链状态"""
        if product_id:
            # 获取特定产品的供应链状态
            product_processes = [p for p in self.processes.values() 
                               if p.metrics.get('product_id') == product_id]
            return self._build_chain_status(product_processes)
        else:
            # 获取整体供应链状态
            return self._build_chain_status(list(self.processes.values()))
    
    def _build_chain_status(self, processes: List[SupplyChainProcess]) -> Dict[str, Any]:
        """构建供应链状态报告"""
        stage_status = {}
        for stage in SupplyChainStage:
            stage_processes = [p for p in processes if p.stage == stage]
            if stage_processes:
                completed = sum(1 for p in stage_processes if p.status == 'completed')
                in_progress = sum(1 for p in stage_processes if p.status == 'in_progress')
                pending = sum(1 for p in stage_processes if p.status == 'pending')
                delayed = sum(1 for p in stage_processes if p.status == 'delayed')
                
                stage_status[stage.value] = {
                    'total': len(stage_processes),
                    'completed': completed,
                    'in_progress': in_progress,
                    'pending': pending,
                    'delayed': delayed,
                    'completion_rate': completed / len(stage_processes) if stage_processes else 0
                }
        
        # 计算整体指标
        total_processes = len(processes)
        completed_processes = sum(1 for p in processes if p.status == 'completed')
        overall_completion = completed_processes / total_processes if total_processes > 0 else 0
        
        return {
            'overall_completion_rate': overall_completion,
            'total_processes': total_processes,
            'stage_status': stage_status,
            'entities_count': len(self.entities),
            'last_updated': datetime.now().isoformat()
        }
    
    async def get_entity_performance(self, entity_id: str) -> Dict[str, Any]:
        """获取实体绩效"""
        if entity_id not in self.entities:
            return {}
            
        entity_processes = [p for p in self.processes.values() if p.entity_id == entity_id]
        if not entity_processes:
            return {}
            
        completed_processes = [p for p in entity_processes if p.status == 'completed']
        if not completed_processes:
            return {'entity_id': entity_id, 'processes_count': len(entity_processes)}
            
        # 计算平均处理时间
        avg_processing_time = sum(
            (p.end_time - p.start_time).total_seconds() 
            for p in completed_processes if p.start_time and p.end_time
        ) / len(completed_processes)
        
        # 计算按时完成率
        on_time_count = sum(1 for p in completed_processes 
                          if p.metrics.get('on_time', True))
        on_time_rate = on_time_count / len(completed_processes)
        
        return {
            'entity_id': entity_id,
            'processes_count': len(entity_processes),
            'completed_processes': len(completed_processes),
            'avg_processing_time_seconds': avg_processing_time,
            'on_time_completion_rate': on_time_rate,
            'performance_score': on_time_rate * 100  # 简单的绩效评分
        }