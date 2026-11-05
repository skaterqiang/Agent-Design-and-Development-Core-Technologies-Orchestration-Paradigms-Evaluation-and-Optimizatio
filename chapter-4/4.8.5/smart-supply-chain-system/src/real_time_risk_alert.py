"""
智能供应链系统 - 实时风险预警模块
提供供应链各环节的风险监控、预警和应对建议
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics

class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskType(Enum):
    """风险类型"""
    SUPPLIER = "supplier"
    LOGISTICS = "logistics"
    INVENTORY = "inventory"
    DEMAND = "demand"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    GEOGRAPHICAL = "geographical"

@dataclass
class RiskEvent:
    """风险事件"""
    event_id: str
    risk_type: RiskType
    risk_level: RiskLevel
    description: str
    affected_entities: List[str]  # 供应商ID、仓库ID、产品ID等
    timestamp: datetime
    confidence: float  # 0.0 - 1.0
    source: str  # 数据来源
    metadata: Dict[str, Any]

@dataclass
class RiskAlert:
    """风险预警"""
    alert_id: str
    event_id: str
    risk_level: RiskLevel
    title: str
    description: str
    recommended_actions: List[str]
    created_at: datetime
    acknowledged: bool = False
    resolved: bool = False
    resolution_notes: str = ""

class RiskMonitoringEngine:
    """风险监控引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_events: List[RiskEvent] = []
        self.alerts: List[RiskAlert] = []
        self.logger = logging.getLogger(__name__)
        
        # 风险阈值配置
        self.thresholds = config.get('thresholds', {
            'supplier_delay_days': 3,
            'inventory_stockout_days': 2,
            'logistics_delay_hours': 24,
            'demand_volatility_threshold': 0.3,
            'quality_defect_rate': 0.05,
            'financial_risk_score': 0.7
        })
        
    async def detect_supplier_risks(self, supplier_data: Dict[str, Any]) -> List[RiskEvent]:
        """检测供应商风险"""
        events = []
        supplier_id = supplier_data.get('supplier_id')
        
        # 检测交货延迟风险
        if 'delivery_history' in supplier_data:
            delivery_history = supplier_data['delivery_history']
            if len(delivery_history) > 5:
                avg_delay = statistics.mean([item.get('delay_days', 0) 
                                           for item in delivery_history[-10:]])
                if avg_delay > self.thresholds['supplier_delay_days']:
                    event = RiskEvent(
                        event_id=f"supplier_delay_{supplier_id}_{int(datetime.now().timestamp())}",
                        risk_type=RiskType.SUPPLIER,
                        risk_level=self._calculate_risk_level(avg_delay, 
                                                            self.thresholds['supplier_delay_days']),
                        description=f"供应商 {supplier_id} 平均交货延迟 {avg_delay:.1f} 天",
                        affected_entities=[supplier_id],
                        timestamp=datetime.now(),
                        confidence=0.8,
                        source="delivery_performance_analysis",
                        metadata={'avg_delay_days': avg_delay, 'historical_data_points': len(delivery_history)}
                    )
                    events.append(event)
        
        # 检测财务风险
        if 'financial_health_score' in supplier_data:
            financial_score = supplier_data['financial_health_score']
            if financial_score < (1 - self.thresholds['financial_risk_score']):
                event = RiskEvent(
                    event_id=f"supplier_financial_{supplier_id}_{int(datetime.now().timestamp())}",
                    risk_type=RiskType.FINANCIAL,
                    risk_level=RiskLevel.HIGH if financial_score < 0.3 else RiskLevel.MEDIUM,
                    description=f"供应商 {supplier_id} 财务健康评分过低: {financial_score:.2f}",
                    affected_entities=[supplier_id],
                    timestamp=datetime.now(),
                    confidence=0.7,
                    source="financial_analysis",
                    metadata={'financial_score': financial_score}
                )
                events.append(event)
                
        return events
    
    async def detect_logistics_risks(self, logistics_data: Dict[str, Any]) -> List[RiskEvent]:
        """检测物流风险"""
        events = []
        
        # 检测运输延迟
        if 'shipment_delays' in logistics_data:
            delays = logistics_data['shipment_delays']
            if delays:
                avg_delay_hours = statistics.mean(delays)
                if avg_delay_hours > self.thresholds['logistics_delay_hours']:
                    event = RiskEvent(
                        event_id=f"logistics_delay_{int(datetime.now().timestamp())}",
                        risk_type=RiskType.LOGISTICS,
                        risk_level=self._calculate_risk_level(avg_delay_hours / 24, 
                                                            self.thresholds['logistics_delay_hours'] / 24),
                        description=f"物流平均延迟 {avg_delay_hours:.1f} 小时",
                        affected_entities=logistics_data.get('routes', []),
                        timestamp=datetime.now(),
                        confidence=0.85,
                        source="logistics_performance_monitoring",
                        metadata={'avg_delay_hours': avg_delay_hours, 'affected_routes': len(logistics_data.get('routes', []))}
                    )
                    events.append(event)
        
        # 检测地理政治风险
        if 'geographical_risks' in logistics_data:
            geo_risks = logistics_data['geographical_risks']
            for risk in geo_risks:
                if risk.get('risk_score', 0) > 0.6:
                    event = RiskEvent(
                        event_id=f"geo_risk_{risk.get('region', 'unknown')}_{int(datetime.now().timestamp())}",
                        risk_type=RiskType.GEOGRAPHICAL,
                        risk_level=RiskLevel.CRITICAL if risk.get('risk_score', 0) > 0.8 else RiskLevel.HIGH,
                        description=f"地区 {risk.get('region')} 存在高风险: {risk.get('description', '')}",
                        affected_entities=risk.get('affected_routes', []),
                        timestamp=datetime.now(),
                        confidence=risk.get('confidence', 0.7),
                        source="geopolitical_risk_monitoring",
                        metadata=risk
                    )
                    events.append(event)
                    
        return events
    
    async def detect_inventory_risks(self, inventory_data: Dict[str, Any]) -> List[RiskEvent]:
        """检测库存风险"""
        events = []
        
        # 检测缺货风险
        if 'stockout_predictions' in inventory_data:
            stockout_items = [item for item in inventory_data['stockout_predictions'] 
                            if item.get('days_until_stockout', 999) <= self.thresholds['inventory_stockout_days']]
            
            if stockout_items:
                event = RiskEvent(
                    event_id=f"inventory_stockout_{int(datetime.now().timestamp())}",
                    risk_type=RiskType.INVENTORY,
                    risk_level=RiskLevel.HIGH if len(stockout_items) > 5 else RiskLevel.MEDIUM,
                    description=f"预测 {len(stockout_items)} 个商品将在 {self.thresholds['inventory_stockout_days']} 天内缺货",
                    affected_entities=[item['product_id'] for item in stockout_items],
                    timestamp=datetime.now(),
                    confidence=0.8,
                    source="inventory_forecasting",
                    metadata={'at_risk_products': len(stockout_items), 'stockout_items': stockout_items}
                )
                events.append(event)
        
        # 检测库存过剩风险
        if 'excess_inventory' in inventory_data:
            excess_items = inventory_data['excess_inventory']
            if excess_items:
                total_excess_value = sum(item.get('excess_value', 0) for item in excess_items)
                if total_excess_value > 100000:  # 假设超过10万为高风险
                    event = RiskEvent(
                        event_id=f"inventory_excess_{int(datetime.now().timestamp())}",
                        risk_type=RiskType.INVENTORY,
                        risk_level=RiskLevel.MEDIUM,
                        description=f"库存过剩，总价值约 {total_excess_value:,.0f} 元",
                        affected_entities=[item['product_id'] for item in excess_items],
                        timestamp=datetime.now(),
                        confidence=0.75,
                        source="inventory_optimization_analysis",
                        metadata={'total_excess_value': total_excess_value, 'excess_items': len(excess_items)}
                    )
                    events.append(event)
                    
        return events
    
    async def detect_demand_risks(self, demand_data: Dict[str, Any]) -> List[RiskEvent]:
        """检测需求风险"""
        events = []
        
        # 检测需求波动风险
        if 'demand_volatility' in demand_data:
            volatility = demand_data['demand_volatility']
            if volatility > self.thresholds['demand_volatility_threshold']:
                event = RiskEvent(
                    event_id=f"demand_volatility_{int(datetime.now().timestamp())}",
                    risk_type=RiskType.DEMAND,
                    risk_level=self._calculate_risk_level(volatility, 
                                                        self.thresholds['demand_volatility_threshold']),
                    description=f"需求波动性过高: {volatility:.2f}",
                    affected_entities=demand_data.get('products', []),
                    timestamp=datetime.now(),
                    confidence=0.8,
                    source="demand_forecasting",
                    metadata={'volatility_coefficient': volatility, 'affected_products': len(demand_data.get('products', []))}
                )
                events.append(event)
                
        return events
    
    async def detect_quality_risks(self, quality_data: Dict[str, Any]) -> List[RiskEvent]:
        """检测质量风险"""
        events = []
        
        # 检测缺陷率过高
        if 'defect_rates' in quality_data:
            high_defect_items = [item for item in quality_data['defect_rates'] 
                               if item.get('defect_rate', 0) > self.thresholds['quality_defect_rate']]
            
            if high_defect_items:
                event = RiskEvent(
                    event_id=f"quality_defects_{int(datetime.now().timestamp())}",
                    risk_type=RiskType.QUALITY,
                    risk_level=RiskLevel.HIGH if len(high_defect_items) > 3 else RiskLevel.MEDIUM,
                    description=f"{len(high_defect_items)} 个产品的缺陷率超过 {self.thresholds['quality_defect_rate']*100:.1f}%",
                    affected_entities=[item['product_id'] for item in high_defect_items],
                    timestamp=datetime.now(),
                    confidence=0.9,
                    source="quality_control_monitoring",
                    metadata={'high_defect_products': len(high_defect_items), 'defect_details': high_defect_items}
                )
                events.append(event)
                
        return events
    
    def _calculate_risk_level(self, value: float, threshold: float) -> RiskLevel:
        """根据数值和阈值计算风险等级"""
        ratio = value / threshold
        if ratio >= 2.0:
            return RiskLevel.CRITICAL
        elif ratio >= 1.5:
            return RiskLevel.HIGH
        elif ratio >= 1.0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def process_risk_events(self, new_events: List[RiskEvent]) -> List[RiskAlert]:
        """处理风险事件并生成预警"""
        alerts = []
        
        for event in new_events:
            # 检查是否已存在相同类型的风险
            existing_alert = None
            for alert in self.alerts:
                if (not alert.resolved and 
                    alert.event_id.startswith(event.event_id.split('_')[0])):
                    existing_alert = alert
                    break
            
            if existing_alert:
                # 更新现有预警的严重程度
                if event.risk_level.value > existing_alert.risk_level.value:
                    existing_alert.risk_level = event.risk_level
                    existing_alert.description = event.description
                    existing_alert.recommended_actions = self._generate_recommendations(event)
            else:
                # 创建新预警
                alert = RiskAlert(
                    alert_id=f"alert_{event.event_id}",
                    event_id=event.event_id,
                    risk_level=event.risk_level,
                    title=self._generate_alert_title(event),
                    description=event.description,
                    recommended_actions=self._generate_recommendations(event),
                    created_at=datetime.now()
                )
                alerts.append(alert)
                self.alerts.append(alert)
            
            self.risk_events.append(event)
            
        return alerts
    
    def _generate_alert_title(self, event: RiskEvent) -> str:
        """生成预警标题"""
        type_titles = {
            RiskType.SUPPLIER: "供应商风险",
            RiskType.LOGISTICS: "物流风险", 
            RiskType.INVENTORY: "库存风险",
            RiskType.DEMAND: "需求风险",
            RiskType.QUALITY: "质量风险",
            RiskType.COMPLIANCE: "合规风险",
            RiskType.FINANCIAL: "财务风险",
            RiskType.GEOGRAPHICAL: "地缘政治风险"
        }
        
        level_titles = {
            RiskLevel.LOW: "低",
            RiskLevel.MEDIUM: "中",
            RiskLevel.HIGH: "高", 
            RiskLevel.CRITICAL: "严重"
        }
        
        return f"{level_titles[event.risk_level]}级别{type_titles[event.risk_type]}"
    
    def _generate_recommendations(self, event: RiskEvent) -> List[str]:
        """生成推荐行动方案"""
        recommendations = []
        
        if event.risk_type == RiskType.SUPPLIER:
            recommendations = [
                "联系供应商了解延迟原因",
                "评估备用供应商选项",
                "调整生产计划以适应可能的延迟",
                "与供应商重新协商交货条款"
            ]
        elif event.risk_type == RiskType.LOGISTICS:
            recommendations = [
                "寻找替代运输路线",
                "增加安全库存水平",
                "与物流合作伙伴协调应急方案",
                "考虑多式联运降低风险"
            ]
        elif event.risk_type == RiskType.INVENTORY:
            recommendations = [
                "紧急补货关键商品",
                "优化库存分配策略",
                "清理过剩库存减少资金占用",
                "重新评估安全库存水平"
            ]
        elif event.risk_type == RiskType.DEMAND:
            recommendations = [
                "加强需求预测模型",
                "建立灵活的生产调度机制",
                "与销售团队协调促销策略",
                "增加原材料安全库存"
            ]
        elif event.risk_type == RiskType.QUALITY:
            recommendations = [
                "立即停止相关批次产品发货",
                "启动质量调查程序",
                "加强供应商质量审核",
                "增加进料检验频次"
            ]
        else:
            recommendations = [
                "立即评估风险影响范围",
                "启动应急预案",
                "通知相关利益相关方",
                "制定缓解措施"
            ]
            
        return recommendations[:3]  # 返回前3个最重要的建议
    
    async def get_active_alerts(self, risk_level: Optional[RiskLevel] = None) -> List[RiskAlert]:
        """获取活跃的预警"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        if risk_level:
            active_alerts = [alert for alert in active_alerts if alert.risk_level == risk_level]
        return active_alerts
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """确认预警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """解决预警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolution_notes = resolution_notes
                return True
        return False
    
    async def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        risk_level_counts = {level: 0 for level in RiskLevel}
        
        for alert in active_alerts:
            risk_level_counts[alert.risk_level] += 1
            
        return {
            'total_active_alerts': len(active_alerts),
            'risk_level_distribution': {level.value: count for level, count in risk_level_counts.items()},
            'recent_events_count': len([event for event in self.risk_events 
                                      if (datetime.now() - event.timestamp).total_seconds() < 3600]),
            'most_affected_areas': self._get_most_affected_areas()
        }
    
    def _get_most_affected_areas(self) -> List[str]:
        """获取最受影响的领域"""
        risk_type_counts = {}
        for event in self.risk_events[-50:]:  # 最近50个事件
            risk_type_counts[event.risk_type] = risk_type_counts.get(event.risk_type, 0) + 1
        
        sorted_types = sorted(risk_type_counts.items(), key=lambda x: x[1], reverse=True)
        return [f"{type.value}: {count}" for type, count in sorted_types[:3]]