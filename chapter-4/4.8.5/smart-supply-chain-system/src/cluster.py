"""
智能供应链系统 - 集群模块
负责管理分布式节点、任务分配和资源调度
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ClusterNode:
    """集群节点信息"""
    node_id: str
    name: str
    status: str  # active, inactive, maintenance
    capabilities: List[str]  # ['inventory', 'logistics', 'procurement', 'analytics']
    load: float  # 0.0 - 1.0
    last_heartbeat: datetime
    metadata: Dict[str, Any]

@dataclass
class TaskAssignment:
    """任务分配信息"""
    task_id: str
    node_id: str
    priority: int
    assigned_at: datetime
    deadline: datetime
    status: str  # pending, running, completed, failed

class SupplyChainCluster:
    """供应链集群管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nodes: Dict[str, ClusterNode] = {}
        self.task_assignments: Dict[str, TaskAssignment] = {}
        self.logger = logging.getLogger(__name__)
        
    async def register_node(self, node_info: Dict[str, Any]) -> bool:
        """注册新节点到集群"""
        try:
            node_id = node_info.get('node_id')
            if not node_id:
                return False
                
            node = ClusterNode(
                node_id=node_id,
                name=node_info.get('name', f'node-{node_id}'),
                status='active',
                capabilities=node_info.get('capabilities', []),
                load=0.0,
                last_heartbeat=datetime.now(),
                metadata=node_info.get('metadata', {})
            )
            
            self.nodes[node_id] = node
            self.logger.info(f"Node {node_id} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register node: {e}")
            return False
    
    async def heartbeat(self, node_id: str) -> bool:
        """处理节点心跳"""
        if node_id in self.nodes:
            self.nodes[node_id].last_heartbeat = datetime.now()
            return True
        return False
    
    async def get_available_nodes(self, required_capabilities: List[str]) -> List[ClusterNode]:
        """获取具备所需能力的可用节点"""
        available_nodes = []
        current_time = datetime.now()
        
        for node in self.nodes.values():
            # 检查节点是否活跃（最后心跳在5分钟内）
            if (current_time - node.last_heartbeat).total_seconds() > 300:
                node.status = 'inactive'
                continue
                
            if node.status != 'active':
                continue
                
            # 检查能力匹配
            if all(cap in node.capabilities for cap in required_capabilities):
                available_nodes.append(node)
                
        # 按负载排序，优先选择负载较低的节点
        available_nodes.sort(key=lambda x: x.load)
        return available_nodes
    
    async def assign_task(self, task_id: str, task_type: str, 
                         required_capabilities: List[str], 
                         priority: int = 1, 
                         deadline_minutes: int = 60) -> Optional[str]:
        """分配任务给合适的节点"""
        try:
            available_nodes = await self.get_available_nodes(required_capabilities)
            if not available_nodes:
                self.logger.warning(f"No available nodes for task {task_id}")
                return None
                
            # 选择负载最低的节点
            selected_node = available_nodes[0]
            
            assignment = TaskAssignment(
                task_id=task_id,
                node_id=selected_node.node_id,
                priority=priority,
                assigned_at=datetime.now(),
                deadline=datetime.now() + timedelta(minutes=deadline_minutes),
                status='pending'
            )
            
            self.task_assignments[task_id] = assignment
            
            # 更新节点负载
            selected_node.load = min(1.0, selected_node.load + 0.1)
            
            self.logger.info(f"Task {task_id} assigned to node {selected_node.node_id}")
            return selected_node.node_id
            
        except Exception as e:
            self.logger.error(f"Failed to assign task {task_id}: {e}")
            return None
    
    async def complete_task(self, task_id: str, result: Any) -> bool:
        """标记任务完成"""
        if task_id in self.task_assignments:
            assignment = self.task_assignments[task_id]
            assignment.status = 'completed'
            
            # 减少节点负载
            if assignment.node_id in self.nodes:
                self.nodes[assignment.node_id].load = max(0.0, 
                    self.nodes[assignment.node_id].load - 0.1)
            
            self.logger.info(f"Task {task_id} completed successfully")
            return True
        return False
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        active_nodes = sum(1 for node in self.nodes.values() if node.status == 'active')
        total_load = sum(node.load for node in self.nodes.values())
        avg_load = total_load / len(self.nodes) if self.nodes else 0
        
        return {
            'total_nodes': len(self.nodes),
            'active_nodes': active_nodes,
            'average_load': avg_load,
            'nodes': {node_id: {
                'name': node.name,
                'status': node.status,
                'capabilities': node.capabilities,
                'load': node.load,
                'last_heartbeat': node.last_heartbeat.isoformat()
            } for node_id, node in self.nodes.items()}
        }