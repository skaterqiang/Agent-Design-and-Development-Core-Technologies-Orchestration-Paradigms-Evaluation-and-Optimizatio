"""
智能供应链管理系统 - 协调器模块（简化版）
负责协调各个集群组件，实现人机协同模式
"""
import json
import time
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime


class SupplyChainCoordinatorSimple:
    """供应链协调器主类（简化版）"""
    
    def __init__(self):
        self.clusters = {}
        self.human_agents = []
        self.system_status = "initialized"
        self.last_update = datetime.now()
        self.running = False
        self.logger = logging.getLogger(__name__)
        self.task_counter = 0
        self.heartbeat_interval = 30  # 心跳间隔秒数
        
    async def start(self):
        """启动协调器"""
        self.running = True
        self.system_status = "running"
        self.last_update = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info("[START] SupplyChainCoordinator STARTING...")
        self.logger.info("=" * 60)
        self.logger.info(f"[TIME] Start time: {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("[INIT] Initializing system components...")
        
        # 注册一些示例集群和人机代理
        self.logger.info("[CLUSTER] Registering cluster components...")
        self.register_cluster("cluster_1", {"type": "optimization", "capacity": 100, "location": "数据中心A"})
        self.register_cluster("cluster_2", {"type": "risk_monitoring", "capacity": 50, "location": "数据中心B"})
        self.register_cluster("cluster_3", {"type": "demand_forecasting", "capacity": 75, "location": "云端"})
        
        self.logger.info("[HUMAN] Adding human agents...")
        self.add_human_agent("human_1", ["decision_making", "quality_control", "crisis_management"])
        self.add_human_agent("human_2", ["strategic_planning", "exception_handling", "supplier_negotiation"])
        self.add_human_agent("human_3", ["data_analysis", "performance_monitoring", "report_generation"])
        
        self.logger.info("[SUCCESS] System initialization completed!")
        self.logger.info(f"[STATS] Registered clusters: {len(self.clusters)}")
        self.logger.info(f"[STATS] Human agents available: {len(self.human_agents)}")
        self.logger.info("=" * 60)
        
        # 启动心跳监控任务
        asyncio.create_task(self._heartbeat_monitor())
        
        # 启动定期任务分发
        asyncio.create_task(self._periodic_task_dispatch())
        
    async def _heartbeat_monitor(self):
        """心跳监控任务"""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.running:
                    self._send_heartbeats()
                    self._check_system_health()
            except Exception as e:
                self.logger.error(f"[ERROR] Heartbeat monitor error: {e}")
                
    def _send_heartbeats(self):
        """发送心跳信号"""
        current_time = datetime.now()
        self.logger.debug(f"[HEARTBEAT] Sending heartbeats at {current_time.strftime('%H:%M:%S')}")
        
        # 更新集群心跳
        for cluster_id, cluster in self.clusters.items():
            cluster['last_heartbeat'] = current_time
            self.logger.debug(f"   [CLUSTER] {cluster_id} heartbeat sent")
            
        # 更新人机代理心跳
        for agent in self.human_agents:
            agent['last_active'] = current_time
            self.logger.debug(f"   [AGENT] {agent['id']} status: {agent['status']}")
            
    def _check_system_health(self):
        """检查系统健康状态"""
        health_info = self.get_system_health()
        self.logger.info("[HEALTH] SYSTEM HEALTH REPORT:")
        self.logger.info(f"   Status: {health_info['system_status'].upper()}")
        self.logger.info(f"   Active Clusters: {health_info['active_clusters']}/{health_info['total_clusters']}")
        self.logger.info(f"   Available Agents: {health_info['available_human_agents']}/{health_info['total_human_agents']}")
        self.logger.info(f"   Tasks Processed: {health_info['tasks_processed']}")
        self.logger.info(f"   Last Update: {health_info['last_update']}")
        
    async def _periodic_task_dispatch(self):
        """定期任务分发"""
        task_templates = [
            {"type": "inventory_check", "priority": "medium", "requires_human_judgment": False},
            {"type": "demand_forecast", "priority": "high", "requires_human_judgment": True},
            {"type": "supplier_evaluation", "priority": "medium", "requires_human_judgment": True},
            {"type": "risk_assessment", "priority": "high", "requires_human_judgment": False},
            {"type": "performance_report", "priority": "low", "requires_human_judgment": True}
        ]
        
        while self.running:
            try:
                await asyncio.sleep(15)  # 每15秒分发一个任务
                if self.running and len(self.clusters) > 0:
                    # 随机选择一个任务模板
                    import random
                    task_template = random.choice(task_templates)
                    self.task_counter += 1
                    
                    task = {
                        "task_id": f"TASK_{self.task_counter:04d}",
                        "type": task_template["type"],
                        "priority": task_template["priority"],
                        "requires_human_judgment": task_template["requires_human_judgment"],
                        "created_at": datetime.now().isoformat(),
                        "description": f"Automated {task_template['type']} task #{self.task_counter}"
                    }
                    
                    self.logger.info(f"[TASK] NEW TASK RECEIVED: {task['task_id']}")
                    self.logger.info(f"   Type: {task['type']}")
                    self.logger.info(f"   Priority: {task['priority'].upper()}")
                    self.logger.info(f"   Requires Human: {'Yes' if task['requires_human_judgment'] else 'No'}")
                    
                    # 分发任务
                    result = self.dispatch_task(task)
                    self.logger.info(f"[DISPATCH] TASK DISPATCH RESULT:")
                    self.logger.info(f"   Assigned to: {result.get('assigned_to', 'N/A')}")
                    self.logger.info(f"   Assignment type: {result.get('assignment_type', 'N/A')}")
                    self.logger.info(f"   Status: {result.get('status', 'N/A')}")
                    
                    if 'error' in result:
                        self.logger.warning(f"   [WARNING] Error: {result['error']}")
                        
            except Exception as e:
                self.logger.error(f"[ERROR] Periodic task dispatch error: {e}")
        
    def stop(self):
        """停止协调器"""
        self.running = False
        self.system_status = "stopped"
        self.last_update = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info("[STOP] SupplyChainCoordinator STOPPING...")
        self.logger.info("=" * 60)
        self.logger.info(f"[TIME] Stop time: {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("[FINAL] Final system statistics:")
        health_info = self.get_system_health()
        self.logger.info(f"   Total tasks processed: {self.task_counter}")
        self.logger.info(f"   Active clusters: {health_info['active_clusters']}")
        self.logger.info(f"   Human agents: {health_info['total_human_agents']}")
        self.logger.info("=" * 60)
        
    def register_cluster(self, cluster_id: str, cluster_info: Dict[str, Any]):
        """注册集群组件"""
        self.clusters[cluster_id] = {
            'info': cluster_info,
            'status': 'active',
            'last_heartbeat': datetime.now()
        }
        self.logger.info(f"[REGISTER] CLUSTER REGISTERED: {cluster_id}")
        self.logger.info(f"   Type: {cluster_info.get('type', 'unknown')}")
        self.logger.info(f"   Capacity: {cluster_info.get('capacity', 'unknown')}")
        self.logger.info(f"   Location: {cluster_info.get('location', 'unknown')}")
        
    def add_human_agent(self, agent_id: str, capabilities: List[str]):
        """添加人机协同代理"""
        human_agent = {
            'id': agent_id,
            'capabilities': capabilities,
            'status': 'available',
            'last_active': datetime.now()
        }
        self.human_agents.append(human_agent)
        self.logger.info(f"[REGISTER] HUMAN AGENT ADDED: {agent_id}")
        self.logger.info(f"   Capabilities: {', '.join(capabilities)}")
        self.logger.info(f"   Initial status: {human_agent['status']}")
        
    def dispatch_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分发任务到合适的集群或人机代理"""
        self.logger.info(f"[ROUTE] DISPATCHING TASK: {task.get('task_id', 'unknown')}")
        self.logger.info(f"   Task type: {task.get('type', 'unknown')}")
        
        # 基于任务类型和复杂度选择处理方式
        if task.get('requires_human_judgment', False):
            self.logger.info("   [DECISION] Task requires human judgment -> routing to human agent")
            return self._assign_to_human_agent(task)
        else:
            self.logger.info("   [DECISION] Task can be automated -> routing to cluster")
            return self._assign_to_cluster(task)
            
    def _assign_to_human_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分配任务给人机代理"""
        self.logger.info("[SEARCH] SEARCHING FOR AVAILABLE HUMAN AGENTS...")
        available_agents = [agent for agent in self.human_agents 
                           if agent['status'] == 'available']
        
        self.logger.info(f"   Available agents found: {len(available_agents)}")
        
        if available_agents:
            selected_agent = available_agents[0]
            old_status = selected_agent['status']
            selected_agent['status'] = 'busy'
            selected_agent['current_task'] = task
            selected_agent['last_active'] = datetime.now()
            
            self.logger.info(f"   [ASSIGN] AGENT ASSIGNED: {selected_agent['id']}")
            self.logger.info(f"   Previous status: {old_status} -> New status: {selected_agent['status']}")
            self.logger.info(f"   Assigned task: {task.get('task_id', 'unknown')}")
            
            return {
                'assigned_to': selected_agent['id'],
                'assignment_type': 'human',
                'status': 'assigned',
                'timestamp': datetime.now().isoformat(),
                'agent_capabilities': selected_agent['capabilities']
            }
        else:
            self.logger.warning("   [WARNING] No available human agents found!")
            self.logger.info("   Setting task to pending status")
            return {'error': 'No available human agents', 'status': 'pending'}
            
    def _assign_to_cluster(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分配任务给集群"""
        self.logger.info("[SEARCH] SEARCHING FOR AVAILABLE CLUSTERS...")
        
        # 简单的负载均衡策略 - 选择最近最少使用的集群
        if self.clusters:
            # 找到最久没有收到心跳的集群（模拟负载均衡）
            oldest_cluster = min(self.clusters.items(), 
                               key=lambda x: x[1]['last_heartbeat'])
            cluster_id, cluster_info = oldest_cluster
            
            self.clusters[cluster_id]['last_heartbeat'] = datetime.now()
            
            self.logger.info(f"   [ASSIGN] CLUSTER ASSIGNED: {cluster_id}")
            self.logger.info(f"   Cluster type: {cluster_info['info'].get('type', 'unknown')}")
            self.logger.info(f"   Cluster capacity: {cluster_info['info'].get('capacity', 'unknown')}")
            
            return {
                'assigned_to': cluster_id,
                'assignment_type': 'cluster',
                'status': 'assigned',
                'timestamp': datetime.now().isoformat(),
                'cluster_info': cluster_info['info']
            }
        else:
            self.logger.warning("   [WARNING] No available clusters found!")
            return {'error': 'No available clusters', 'status': 'pending'}
            
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        active_clusters = len([c for c in self.clusters.values() 
                              if c['status'] == 'active'])
        available_humans = len([h for h in self.human_agents 
                               if h['status'] == 'available'])
        busy_humans = len([h for h in self.human_agents 
                          if h['status'] == 'busy'])
                               
        return {
            'system_status': self.system_status,
            'active_clusters': active_clusters,
            'total_clusters': len(self.clusters),
            'available_human_agents': available_humans,
            'busy_human_agents': busy_humans,
            'total_human_agents': len(self.human_agents),
            'last_update': self.last_update.isoformat(),
            'running': self.running,
            'tasks_processed': self.task_counter
        }