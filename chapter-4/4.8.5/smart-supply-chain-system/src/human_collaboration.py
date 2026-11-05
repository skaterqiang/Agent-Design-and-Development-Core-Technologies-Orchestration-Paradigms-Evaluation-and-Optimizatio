"""
智能供应链系统 - 人机协同模块
负责管理人类专家与AI系统的协作流程
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class CollaborationType(Enum):
    """协作类型"""
    REVIEW = "review"           # 审核评判
    DECISION = "decision"       # 决策支持
    EMERGENCY = "emergency"     # 紧急干预
    OPTIMIZATION = "optimization"  # 优化建议

class HumanRole(Enum):
    """人类角色"""
    SUPPLIER_MANAGER = "supplier_manager"
    LOGISTICS_MANAGER = "logistics_manager"
    INVENTORY_MANAGER = "inventory_manager"
    RISK_ANALYST = "risk_analyst"
    EXECUTIVE = "executive"

@dataclass
class CollaborationRequest:
    """协作请求"""
    request_id: str
    collaboration_type: CollaborationType
    human_roles: List[HumanRole]
    context: Dict[str, Any]  # 协作上下文信息
    priority: int
    created_at: datetime
    deadline: datetime
    status: str  # pending, in_progress, completed, cancelled
    ai_recommendation: Optional[str] = None
    human_response: Optional[Dict[str, Any]] = None

@dataclass
class HumanExpert:
    """人类专家信息"""
    expert_id: str
    name: str
    roles: List[HumanRole]
    availability: bool
    response_time_avg: float  # 平均响应时间（分钟）
    expertise_score: float    # 专业评分（0-1）

class HumanCollaborationManager:
    """人机协同管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collaboration_requests: Dict[str, CollaborationRequest] = {}
        self.human_experts: Dict[str, HumanExpert] = {}
        self.logger = logging.getLogger(__name__)
        
    async def register_human_expert(self, expert_info: Dict[str, Any]) -> bool:
        """注册人类专家"""
        try:
            expert_id = expert_info.get('expert_id')
            if not expert_id:
                return False
                
            roles = [HumanRole(role) for role in expert_info.get('roles', [])]
            
            expert = HumanExpert(
                expert_id=expert_id,
                name=expert_info.get('name', f'expert-{expert_id}'),
                roles=roles,
                availability=expert_info.get('availability', True),
                response_time_avg=expert_info.get('response_time_avg', 30.0),
                expertise_score=expert_info.get('expertise_score', 0.5)
            )
            
            self.human_experts[expert_id] = expert
            self.logger.info(f"Human expert {expert_id} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register human expert: {e}")
            return False
    
    async def create_collaboration_request(
        self, 
        collaboration_type: CollaborationType,
        human_roles: List[HumanRole],
        context: Dict[str, Any],
        ai_recommendation: Optional[str] = None,
        priority: int = 1,
        deadline_minutes: int = 60
    ) -> str:
        """创建协作请求"""
        request_id = f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        request = CollaborationRequest(
            request_id=request_id,
            collaboration_type=collaboration_type,
            human_roles=human_roles,
            context=context,
            priority=priority,
            created_at=datetime.now(),
            deadline=datetime.now() + timedelta(minutes=deadline_minutes),
            status='pending',
            ai_recommendation=ai_recommendation
        )
        
        self.collaboration_requests[request_id] = request
        self.logger.info(f"Collaboration request {request_id} created")
        
        # 通知相关专家
        await self._notify_relevant_experts(request)
        
        return request_id
    
    async def _notify_relevant_experts(self, request: CollaborationRequest):
        """通知相关专家"""
        relevant_experts = []
        
        for expert in self.human_experts.values():
            if (expert.availability and 
                any(role in expert.roles for role in request.human_roles)):
                relevant_experts.append(expert)
        
        # 按专业评分排序，优先通知高分专家
        relevant_experts.sort(key=lambda x: x.expertise_score, reverse=True)
        
        # 通知前N个专家（根据配置）
        notify_count = min(len(relevant_experts), 
                          self.config.get('max_notify_experts', 3))
        
        for i, expert in enumerate(relevant_experts[:notify_count]):
            await self._send_notification(expert, request, priority=i+1)
    
    async def _send_notification(self, expert: HumanExpert, 
                                request: CollaborationRequest, 
                                priority: int):
        """发送通知给专家"""
        notification = {
            'expert_id': expert.expert_id,
            'request_id': request.request_id,
            'type': request.collaboration_type.value,
            'priority': priority,
            'context_summary': self._summarize_context(request.context),
            'deadline': request.deadline.isoformat(),
            'ai_recommendation': request.ai_recommendation
        }
        
        self.logger.info(f"Notification sent to expert {expert.expert_id} "
                        f"for request {request.request_id}")
        # 这里可以集成实际的通知系统（邮件、消息等）
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """生成上下文摘要"""
        if 'risk_level' in context:
            return f"Risk alert: {context.get('risk_description', 'High risk detected')}"
        elif 'cost_optimization' in context:
            return f"Cost optimization opportunity: {context.get('savings_potential', 'Significant')}"
        elif 'supply_chain_disruption' in context:
            return f"Supply chain disruption: {context.get('disruption_type', 'Unknown')}"
        else:
            return "Collaboration required for supply chain decision"
    
    async def submit_human_response(self, request_id: str, 
                                  expert_id: str, 
                                  response: Dict[str, Any]) -> bool:
        """提交人类专家响应"""
        if request_id not in self.collaboration_requests:
            return False
            
        request = self.collaboration_requests[request_id]
        if request.status != 'pending':
            return False
            
        request.human_response = response
        request.status = 'completed'
        
        self.logger.info(f"Human response submitted for request {request_id} "
                        f"by expert {expert_id}")
        return True
    
    async def get_pending_requests(self, expert_id: str) -> List[CollaborationRequest]:
        """获取专家的待处理请求"""
        if expert_id not in self.human_experts:
            return []
            
        expert = self.human_experts[expert_id]
        current_time = datetime.now()
        
        pending_requests = []
        for request in self.collaboration_requests.values():
            if (request.status == 'pending' and 
                request.deadline > current_time and
                any(role in expert.roles for role in request.human_roles)):
                pending_requests.append(request)
        
        # 按优先级和截止时间排序
        pending_requests.sort(key=lambda x: (x.priority, x.deadline))
        return pending_requests
    
    async def get_collaboration_statistics(self) -> Dict[str, Any]:
        """获取协作统计信息"""
        total_requests = len(self.collaboration_requests)
        completed_requests = sum(1 for r in self.collaboration_requests.values() 
                               if r.status == 'completed')
        pending_requests = sum(1 for r in self.collaboration_requests.values() 
                             if r.status == 'pending')
        
        avg_response_time = 0
        if completed_requests > 0:
            response_times = []
            for request in self.collaboration_requests.values():
                if request.status == 'completed' and request.human_response:
                    response_time = (
                        datetime.fromisoformat(request.human_response.get('submitted_at', ''))
                        - request.created_at
                    ).total_seconds() / 60
                    response_times.append(response_time)
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'completion_rate': completed_requests / total_requests if total_requests > 0 else 0,
            'average_response_time_minutes': avg_response_time,
            'active_experts': sum(1 for e in self.human_experts.values() if e.availability)
        }