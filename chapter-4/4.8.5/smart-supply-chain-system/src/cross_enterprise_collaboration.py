"""
智能供应链系统 - 跨企业协作模块
实现多企业间的供应链协同、数据共享和业务流程集成
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets

from .blockchain_ledger import BlockchainLedger
from .data_encryption import DataEncryptionManager

logger = logging.getLogger(__name__)

class CollaborationType(Enum):
    """协作类型"""
    INVENTORY_SHARING = "inventory_sharing"
    JOINT_PROCUREMENT = "joint_procurement"
    LOGISTICS_POOLING = "logistics_pooling"
    DEMAND_FORECASTING = "demand_forecasting"
    RISK_MANAGEMENT = "risk_management"

class EnterpriseRole(Enum):
    """企业角色"""
    SUPPLIER = "supplier"
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    RETAILER = "retailer"
    LOGISTICS_PROVIDER = "logistics_provider"

@dataclass
class EnterpriseProfile:
    """企业档案"""
    enterprise_id: str
    name: str
    role: EnterpriseRole
    capabilities: List[str]
    contact_info: Dict[str, str]
    security_level: int  # 1-5, 5为最高安全级别
    collaboration_preferences: Dict[str, Any]
    created_at: datetime
    last_updated: datetime

@dataclass
class CollaborationAgreement:
    """协作协议"""
    agreement_id: str
    collaboration_type: CollaborationType
    participating_enterprises: List[str]  # enterprise_id列表
    data_sharing_rules: Dict[str, Any]
    service_level_agreements: Dict[str, Any]
    encryption_keys: Dict[str, str]  # 每个企业的加密密钥
    status: str  # active, suspended, terminated
    created_at: datetime
    expires_at: datetime

@dataclass
class SharedDataRequest:
    """共享数据请求"""
    request_id: str
    requester_id: str
    target_enterprise_id: str
    data_type: str
    purpose: str
    requested_fields: List[str]
    time_range: Dict[str, str]
    urgency: str  # low, medium, high
    status: str  # pending, approved, rejected, completed
    created_at: datetime
    processed_at: Optional[datetime] = None

@dataclass
class CollaborationEvent:
    """协作事件"""
    event_id: str
    event_type: str
    source_enterprise: str
    target_enterprises: List[str]
    payload: Dict[str, Any]
    timestamp: datetime
    priority: str  # low, medium, high, critical
    requires_acknowledgment: bool = False
    acknowledged_by: Set[str] = None

class CrossEnterpriseCollaboration:
    """跨企业协作管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enterprises: Dict[str, EnterpriseProfile] = {}
        self.agreements: Dict[str, CollaborationAgreement] = {}
        self.data_requests: Dict[str, SharedDataRequest] = {}
        self.collaboration_events: List[CollaborationEvent] = []
        self.blockchain_ledger = BlockchainLedger()
        self.encryption_manager = DataEncryptionManager()
        self.logger = logging.getLogger(__name__)
        
    async def register_enterprise(self, enterprise_data: Dict[str, Any]) -> str:
        """注册企业"""
        try:
            enterprise_id = enterprise_data.get('enterprise_id')
            if not enterprise_id:
                enterprise_id = self._generate_enterprise_id(enterprise_data['name'])
            
            if enterprise_id in self.enterprises:
                raise ValueError(f"Enterprise {enterprise_id} already exists")
            
            profile = EnterpriseProfile(
                enterprise_id=enterprise_id,
                name=enterprise_data['name'],
                role=EnterpriseRole(enterprise_data['role']),
                capabilities=enterprise_data.get('capabilities', []),
                contact_info=enterprise_data.get('contact_info', {}),
                security_level=enterprise_data.get('security_level', 3),
                collaboration_preferences=enterprise_data.get('collaboration_preferences', {}),
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            self.enterprises[enterprise_id] = profile
            self.logger.info(f"Enterprise {enterprise_id} registered successfully")
            
            # 在区块链上记录企业注册
            await self.blockchain_ledger.record_transaction(
                transaction_type="enterprise_registration",
                data=asdict(profile),
                participants=[enterprise_id]
            )
            
            return enterprise_id
            
        except Exception as e:
            self.logger.error(f"Failed to register enterprise: {e}")
            raise
    
    def _generate_enterprise_id(self, name: str) -> str:
        """生成企业ID"""
        timestamp = str(datetime.now().timestamp())
        hash_input = f"{name}_{timestamp}_{secrets.token_hex(8)}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def create_collaboration_agreement(self, 
                                           collaboration_type: CollaborationType,
                                           participating_enterprises: List[str],
                                           data_sharing_rules: Dict[str, Any],
                                           service_level_agreements: Dict[str, Any]) -> str:
        """创建协作协议"""
        try:
            # 验证参与企业是否存在
            for enterprise_id in participating_enterprises:
                if enterprise_id not in self.enterprises:
                    raise ValueError(f"Enterprise {enterprise_id} not found")
            
            agreement_id = self._generate_agreement_id(collaboration_type, participating_enterprises)
            
            # 为每个参与企业生成加密密钥
            encryption_keys = {}
            for enterprise_id in participating_enterprises:
                encryption_keys[enterprise_id] = self.encryption_manager.generate_key()
            
            agreement = CollaborationAgreement(
                agreement_id=agreement_id,
                collaboration_type=collaboration_type,
                participating_enterprises=participating_enterprises,
                data_sharing_rules=data_sharing_rules,
                service_level_agreements=service_level_agreements,
                encryption_keys=encryption_keys,
                status='active',
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=365)  # 默认1年有效期
            )
            
            self.agreements[agreement_id] = agreement
            self.logger.info(f"Collaboration agreement {agreement_id} created successfully")
            
            # 在区块链上记录协议创建
            await self.blockchain_ledger.record_transaction(
                transaction_type="agreement_creation",
                data=asdict(agreement),
                participants=participating_enterprises
            )
            
            return agreement_id
            
        except Exception as e:
            self.logger.error(f"Failed to create collaboration agreement: {e}")
            raise
    
    def _generate_agreement_id(self, collaboration_type: CollaborationType, 
                              enterprises: List[str]) -> str:
        """生成协议ID"""
        enterprises_str = "_".join(sorted(enterprises))
        hash_input = f"{collaboration_type.value}_{enterprises_str}_{datetime.now().timestamp()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:20]
    
    async def request_shared_data(self, 
                                requester_id: str,
                                target_enterprise_id: str,
                                data_type: str,
                                requested_fields: List[str],
                                purpose: str,
                                time_range: Dict[str, str],
                                urgency: str = "medium") -> str:
        """请求共享数据"""
        try:
            if requester_id not in self.enterprises:
                raise ValueError(f"Requester {requester_id} not found")
            if target_enterprise_id not in self.enterprises:
                raise ValueError(f"Target enterprise {target_enterprise_id} not found")
            
            # 检查是否存在有效的协作协议
            valid_agreement = None
            for agreement in self.agreements.values():
                if (agreement.status == 'active' and
                    requester_id in agreement.participating_enterprises and
                    target_enterprise_id in agreement.participating_enterprises):
                    valid_agreement = agreement
                    break
            
            if not valid_agreement:
                raise ValueError("No valid collaboration agreement found between enterprises")
            
            # 验证请求的数据字段是否在协议允许范围内
            allowed_fields = valid_agreement.data_sharing_rules.get(data_type, [])
            if not all(field in allowed_fields for field in requested_fields):
                raise ValueError("Requested fields not allowed by collaboration agreement")
            
            request_id = f"req_{datetime.now().timestamp()}_{secrets.token_hex(6)}"
            request = SharedDataRequest(
                request_id=request_id,
                requester_id=requester_id,
                target_enterprise_id=target_enterprise_id,
                data_type=data_type,
                purpose=purpose,
                requested_fields=requested_fields,
                time_range=time_range,
                urgency=urgency,
                status='pending',
                created_at=datetime.now()
            )
            
            self.data_requests[request_id] = request
            self.logger.info(f"Data sharing request {request_id} created")
            
            # 发送协作事件通知目标企业
            await self.send_collaboration_event(
                event_type="data_request_notification",
                source_enterprise=requester_id,
                target_enterprises=[target_enterprise_id],
                payload={
                    "request_id": request_id,
                    "data_type": data_type,
                    "requested_fields": requested_fields,
                    "purpose": purpose,
                    "urgency": urgency
                },
                priority=urgency
            )
            
            return request_id
            
        except Exception as e:
            self.logger.error(f"Failed to create data sharing request: {e}")
            raise
    
    async def approve_data_request(self, request_id: str, approver_id: str) -> bool:
        """批准数据请求"""
        try:
            if request_id not in self.data_requests:
                raise ValueError(f"Request {request_id} not found")
            
            request = self.data_requests[request_id]
            if request.target_enterprise_id != approver_id:
                raise ValueError("Only the target enterprise can approve the request")
            
            if request.status != 'pending':
                raise ValueError(f"Request is already {request.status}")
            
            request.status = 'approved'
            request.processed_at = datetime.now()
            
            # 获取数据（这里简化处理，实际应从数据源获取）
            shared_data = await self._retrieve_shared_data(request)
            
            # 加密数据并发送给请求方
            encrypted_data = self.encryption_manager.encrypt_data(
                shared_data, 
                self.agreements[request_id.split('_')[0]].encryption_keys[request.requester_id]
            )
            
            # 发送协作事件通知请求方数据已准备就绪
            await self.send_collaboration_event(
                event_type="data_ready_notification",
                source_enterprise=approver_id,
                target_enterprises=[request.requester_id],
                payload={
                    "request_id": request_id,
                    "encrypted_data": encrypted_data,
                    "data_type": request.data_type
                },
                priority="high"
            )
            
            self.logger.info(f"Data request {request_id} approved by {approver_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to approve data request {request_id}: {e}")
            return False
    
    async def _retrieve_shared_data(self, request: SharedDataRequest) -> Dict[str, Any]:
        """检索要共享的数据（简化实现）"""
        # 实际实现中，这里会从数据库或API获取真实数据
        return {
            "metadata": {
                "request_id": request.request_id,
                "data_type": request.data_type,
                "time_range": request.time_range,
                "generated_at": datetime.now().isoformat()
            },
            "data": {
                "sample_field": "sample_value",
                "requested_fields": request.requested_fields
            }
        }
    
    async def send_collaboration_event(self,
                                     event_type: str,
                                     source_enterprise: str,
                                     target_enterprises: List[str],
                                     payload: Dict[str, Any],
                                     priority: str = "medium",
                                     requires_acknowledgment: bool = False) -> str:
        """发送协作事件"""
        try:
            event_id = f"event_{datetime.now().timestamp()}_{secrets.token_hex(6)}"
            event = CollaborationEvent(
                event_id=event_id,
                event_type=event_type,
                source_enterprise=source_enterprise,
                target_enterprises=target_enterprises,
                payload=payload,
                timestamp=datetime.now(),
                priority=priority,
                requires_acknowledgment=requires_acknowledgment,
                acknowledged_by=set() if requires_acknowledgment else None
            )
            
            self.collaboration_events.append(event)
            
            # 在区块链上记录事件（如果需要审计）
            if priority in ["high", "critical"] or requires_acknowledgment:
                await self.blockchain_ledger.record_transaction(
                    transaction_type="collaboration_event",
                    data=asdict(event),
                    participants=[source_enterprise] + target_enterprises
                )
            
            self.logger.info(f"Collaboration event {event_id} sent to {len(target_enterprises)} enterprises")
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to send collaboration event: {e}")
            raise
    
    async def acknowledge_event(self, event_id: str, enterprise_id: str) -> bool:
        """确认接收事件"""
        try:
            for event in self.collaboration_events:
                if event.event_id == event_id:
                    if enterprise_id not in event.target_enterprises:
                        raise ValueError("Enterprise not a target of this event")
                    
                    if event.acknowledged_by is not None:
                        event.acknowledged_by.add(enterprise_id)
                        self.logger.info(f"Event {event_id} acknowledged by {enterprise_id}")
                        return True
                    else:
                        raise ValueError("Event does not require acknowledgment")
            
            raise ValueError(f"Event {event_id} not found")
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge event {event_id}: {e}")
            return False
    
    async def get_enterprise_collaborations(self, enterprise_id: str) -> Dict[str, Any]:
        """获取企业的协作信息"""
        if enterprise_id not in self.enterprises:
            raise ValueError(f"Enterprise {enterprise_id} not found")
        
        active_agreements = []
        pending_requests = []
        recent_events = []
        
        # 获取活跃的协作协议
        for agreement in self.agreements.values():
            if (agreement.status == 'active' and 
                enterprise_id in agreement.participating_enterprises):
                active_agreements.append({
                    'agreement_id': agreement.agreement_id,
                    'collaboration_type': agreement.collaboration_type.value,
                    'participants': [eid for eid in agreement.participating_enterprises 
                                   if eid != enterprise_id],
                    'created_at': agreement.created_at.isoformat(),
                    'expires_at': agreement.expires_at.isoformat()
                })
        
        # 获取待处理的数据请求
        for request in self.data_requests.values():
            if ((request.requester_id == enterprise_id or request.target_enterprise_id == enterprise_id) and
                request.status == 'pending'):
                pending_requests.append({
                    'request_id': request.request_id,
                    'direction': 'outgoing' if request.requester_id == enterprise_id else 'incoming',
                    'target_enterprise': (request.target_enterprise_id if request.requester_id == enterprise_id 
                                        else request.requester_id),
                    'data_type': request.data_type,
                    'urgency': request.urgency,
                    'created_at': request.created_at.isoformat()
                })
        
        # 获取最近的协作事件（过去7天）
        week_ago = datetime.now() - timedelta(days=7)
        for event in reversed(self.collaboration_events):
            if event.timestamp >= week_ago and (
                enterprise_id == event.source_enterprise or 
                enterprise_id in event.target_enterprises
            ):
                recent_events.append({
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'direction': 'outgoing' if enterprise_id == event.source_enterprise else 'incoming',
                    'timestamp': event.timestamp.isoformat(),
                    'priority': event.priority
                })
                if len(recent_events) >= 10:  # 限制返回最近10个事件
                    break
        
        return {
            'enterprise_id': enterprise_id,
            'active_agreements': active_agreements,
            'pending_requests': pending_requests,
            'recent_events': recent_events
        }
    
    async def terminate_collaboration_agreement(self, agreement_id: str, 
                                              reason: str = "normal_expiration") -> bool:
        """终止协作协议"""
        try:
            if agreement_id not in self.agreements:
                raise ValueError(f"Agreement {agreement_id} not found")
            
            agreement = self.agreements[agreement_id]
            agreement.status = 'terminated'
            
            # 在区块链上记录协议终止
            await self.blockchain_ledger.record_transaction(
                transaction_type="agreement_termination",
                data={
                    'agreement_id': agreement_id,
                    'reason': reason,
                    'terminated_at': datetime.now().isoformat()
                },
                participants=agreement.participating_enterprises
            )
            
            self.logger.info(f"Collaboration agreement {agreement_id} terminated: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to terminate agreement {agreement_id}: {e}")
            return False