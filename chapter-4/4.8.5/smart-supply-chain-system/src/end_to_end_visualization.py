"""
智能供应链系统 - 端到端可视化模块
提供供应链全流程的可视化展示和监控
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class VisualizationData:
    """可视化数据结构"""
    timestamp: datetime
    supply_chain_id: str
    nodes: List[Dict[str, Any]]  # 节点信息
    edges: List[Dict[str, Any]]  # 连接关系
    metrics: Dict[str, Any]      # 关键指标
    alerts: List[Dict[str, Any]] # 预警信息
    metadata: Dict[str, Any]

class EndToEndVisualization:
    """端到端可视化管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.visualization_cache: Dict[str, VisualizationData] = {}
        
    async def generate_supply_chain_map(self, supply_chain_id: str) -> Dict[str, Any]:
        """生成供应链地图数据"""
        try:
            # 获取供应链全链条数据
            from .supply_chain_full_coverage import SupplyChainFullCoverage
            full_coverage = SupplyChainFullCoverage(self.config)
            chain_data = await full_coverage.get_supply_chain_data(supply_chain_id)
            
            if not chain_data:
                return {}
            
            # 构建节点和边
            nodes = []
            edges = []
            node_positions = {}
            
            # 添加供应商节点
            for i, supplier in enumerate(chain_data.get('suppliers', [])):
                node_id = f"supplier_{supplier['id']}"
                nodes.append({
                    'id': node_id,
                    'type': 'supplier',
                    'name': supplier['name'],
                    'status': supplier.get('status', 'active'),
                    'metrics': supplier.get('metrics', {}),
                    'position': {'x': i * 200, 'y': 100}
                })
                node_positions[node_id] = {'x': i * 200, 'y': 100}
            
            # 添加制造节点
            for i, manufacturer in enumerate(chain_data.get('manufacturers', [])):
                node_id = f"manufacturer_{manufacturer['id']}"
                nodes.append({
                    'id': node_id,
                    'type': 'manufacturer',
                    'name': manufacturer['name'],
                    'status': manufacturer.get('status', 'active'),
                    'metrics': manufacturer.get('metrics', {}),
                    'position': {'x': i * 200, 'y': 300}
                })
                node_positions[node_id] = {'x': i * 200, 'y': 300}
            
            # 添加仓库节点
            for i, warehouse in enumerate(chain_data.get('warehouses', [])):
                node_id = f"warehouse_{warehouse['id']}"
                nodes.append({
                    'id': node_id,
                    'type': 'warehouse',
                    'name': warehouse['name'],
                    'status': warehouse.get('status', 'active'),
                    'metrics': warehouse.get('metrics', {}),
                    'position': {'x': i * 200, 'y': 500}
                })
                node_positions[node_id] = {'x': i * 200, 'y': 500}
            
            # 添加分销商节点
            for i, distributor in enumerate(chain_data.get('distributors', [])):
                node_id = f"distributor_{distributor['id']}"
                nodes.append({
                    'id': node_id,
                    'type': 'distributor',
                    'name': distributor['name'],
                    'status': distributor.get('status', 'active'),
                    'metrics': distributor.get('metrics', {}),
                    'position': {'x': i * 200, 'y': 700}
                })
                node_positions[node_id] = {'x': i * 200, 'y': 700}
            
            # 添加零售商节点
            for i, retailer in enumerate(chain_data.get('retailers', [])):
                node_id = f"retailer_{retailer['id']}"
                nodes.append({
                    'id': node_id,
                    'type': 'retailer',
                    'name': retailer['name'],
                    'status': retailer.get('status', 'active'),
                    'metrics': retailer.get('metrics', {}),
                    'position': {'x': i * 200, 'y': 900}
                })
                node_positions[node_id] = {'x': i * 200, 'y': 900}
            
            # 构建连接关系（简化示例）
            all_nodes = chain_data.get('suppliers', []) + \
                       chain_data.get('manufacturers', []) + \
                       chain_data.get('warehouses', []) + \
                       chain_data.get('distributors', []) + \
                       chain_data.get('retailers', [])
            
            for i in range(len(all_nodes) - 1):
                if i < len(chain_data.get('suppliers', [])):
                    source_type = 'supplier'
                    source_idx = i
                elif i < len(chain_data.get('suppliers', [])) + len(chain_data.get('manufacturers', [])):
                    source_type = 'manufacturer'
                    source_idx = i - len(chain_data.get('suppliers', []))
                elif i < len(chain_data.get('suppliers', [])) + len(chain_data.get('manufacturers', [])) + len(chain_data.get('warehouses', [])):
                    source_type = 'warehouse'
                    source_idx = i - len(chain_data.get('suppliers', [])) - len(chain_data.get('manufacturers', []))
                elif i < len(chain_data.get('suppliers', [])) + len(chain_data.get('manufacturers', [])) + len(chain_data.get('warehouses', [])) + len(chain_data.get('distributors', [])):
                    source_type = 'distributor'
                    source_idx = i - len(chain_data.get('suppliers', [])) - len(chain_data.get('manufacturers', [])) - len(chain_data.get('warehouses', []))
                else:
                    continue
                
                next_i = i + 1
                if next_i < len(chain_data.get('suppliers', [])):
                    target_type = 'supplier'
                    target_idx = next_i
                elif next_i < len(chain_data.get('suppliers', [])) + len(chain_data.get('manufacturers', [])):
                    target_type = 'manufacturer'
                    target_idx = next_i - len(chain_data.get('suppliers', []))
                elif next_i < len(chain_data.get('suppliers', [])) + len(chain_data.get('manufacturers', [])) + len(chain_data.get('warehouses', [])):
                    target_type = 'warehouse'
                    target_idx = next_i - len(chain_data.get('suppliers', [])) - len(chain_data.get('manufacturers', []))
                elif next_i < len(chain_data.get('suppliers', [])) + len(chain_data.get('manufacturers', [])) + len(chain_data.get('warehouses', [])) + len(chain_data.get('distributors', [])):
                    target_type = 'distributor'
                    target_idx = next_i - len(chain_data.get('suppliers', [])) - len(chain_data.get('manufacturers', [])) - len(chain_data.get('warehouses', []))
                else:
                    target_type = 'retailer'
                    target_idx = next_i - len(chain_data.get('suppliers', [])) - len(chain_data.get('manufacturers', [])) - len(chain_data.get('warehouses', [])) - len(chain_data.get('distributors', []))
                
                source_id = f"{source_type}_{all_nodes[i]['id']}"
                target_id = f"{target_type}_{all_nodes[next_i]['id']}"
                
                edges.append({
                    'source': source_id,
                    'target': target_id,
                    'type': 'flow',
                    'status': 'active',
                    'metrics': {
                        'flow_rate': 100,
                        'lead_time': 24,
                        'cost': 50.0
                    }
                })
            
            # 计算关键指标
            metrics = await self._calculate_key_metrics(chain_data)
            
            # 获取实时预警
            alerts = await self._get_real_time_alerts(supply_chain_id)
            
            visualization_data = VisualizationData(
                timestamp=datetime.now(),
                supply_chain_id=supply_chain_id,
                nodes=nodes,
                edges=edges,
                metrics=metrics,
                alerts=alerts,
                metadata={
                    'generated_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
            )
            
            # 缓存数据
            self.visualization_cache[supply_chain_id] = visualization_data
            
            return {
                'nodes': nodes,
                'edges': edges,
                'metrics': metrics,
                'alerts': alerts,
                'metadata': visualization_data.metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate supply chain map for {supply_chain_id}: {e}")
            return {}
    
    async def _calculate_key_metrics(self, chain_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算关键指标"""
        try:
            total_cost = 0
            total_lead_time = 0
            service_level = 100.0
            inventory_turnover = 0
            
            # 计算总成本
            for node_type in ['suppliers', 'manufacturers', 'warehouses', 'distributors', 'retailers']:
                for node in chain_data.get(node_type, []):
                    total_cost += node.get('metrics', {}).get('cost', 0)
                    total_lead_time += node.get('metrics', {}).get('lead_time', 0)
            
            # 计算服务水平
            on_time_deliveries = sum(node.get('metrics', {}).get('on_time_deliveries', 0) 
                                   for node in chain_data.get('retailers', []))
            total_deliveries = sum(node.get('metrics', {}).get('total_deliveries', 1) 
                                 for node in chain_data.get('retailers', []))
            if total_deliveries > 0:
                service_level = (on_time_deliveries / total_deliveries) * 100
            
            # 计算库存周转率
            total_inventory = sum(node.get('metrics', {}).get('inventory_level', 0) 
                                for node in chain_data.get('warehouses', []))
            total_sales = sum(node.get('metrics', {}).get('sales_volume', 1) 
                            for node in chain_data.get('retailers', []))
            if total_inventory > 0:
                inventory_turnover = total_sales / total_inventory
            
            return {
                'total_cost': total_cost,
                'average_lead_time': total_lead_time / max(len(chain_data.get('suppliers', [])) + 
                                                         len(chain_data.get('manufacturers', [])) + 
                                                         len(chain_data.get('warehouses', [])) + 
                                                         len(chain_data.get('distributors', [])) + 
                                                         len(chain_data.get('retailers', [])), 1),
                'service_level': service_level,
                'inventory_turnover': inventory_turnover,
                'carbon_footprint': total_cost * 0.1,  # 简化计算
                'risk_score': await self._calculate_risk_score(chain_data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate key metrics: {e}")
            return {}
    
    async def _calculate_risk_score(self, chain_data: Dict[str, Any]) -> float:
        """计算风险评分"""
        risk_factors = []
        
        # 供应商集中度风险
        suppliers = chain_data.get('suppliers', [])
        if len(suppliers) > 0:
            top_supplier_share = max(s.get('metrics', {}).get('supply_share', 0) for s in suppliers)
            risk_factors.append(top_supplier_share * 0.3)
        
        # 库存水平风险
        warehouses = chain_data.get('warehouses', [])
        if warehouses:
            avg_inventory = sum(w.get('metrics', {}).get('inventory_level', 0) for w in warehouses) / len(warehouses)
            safety_stock = sum(w.get('metrics', {}).get('safety_stock', 0) for w in warehouses) / len(warehouses)
            if safety_stock > 0:
                inventory_risk = abs(avg_inventory - safety_stock) / safety_stock
                risk_factors.append(min(inventory_risk, 1.0) * 0.2)
        
        # 交付延迟风险
        retailers = chain_data.get('retailers', [])
        if retailers:
            avg_delay = sum(r.get('metrics', {}).get('average_delay', 0) for r in retailers) / len(retailers)
            delay_risk = min(avg_delay / 24.0, 1.0)  # 假设24小时为高风险阈值
            risk_factors.append(delay_risk * 0.3)
        
        # 地理风险（简化）
        risk_factors.append(0.1)  # 默认地理风险
        
        return min(sum(risk_factors), 1.0) * 100
    
    async def _get_real_time_alerts(self, supply_chain_id: str) -> List[Dict[str, Any]]:
        """获取实时预警信息"""
        alerts = []
        
        # 模拟一些预警条件
        # 这里应该连接到实时风险预警模块
        try:
            from .real_time_risk_alert import RealTimeRiskAlert
            risk_alert = RealTimeRiskAlert(self.config)
            alerts = await risk_alert.get_active_alerts(supply_chain_id)
        except ImportError:
            # 如果模块不存在，使用模拟数据
            alerts = [
                {
                    'id': 'alert_001',
                    'type': 'inventory_low',
                    'severity': 'high',
                    'message': 'Warehouse WH-001 inventory below safety stock',
                    'timestamp': datetime.now().isoformat(),
                    'affected_nodes': ['warehouse_WH-001']
                },
                {
                    'id': 'alert_002',
                    'type': 'delay_risk',
                    'severity': 'medium',
                    'message': 'Supplier SUP-002 showing delivery delay risk',
                    'timestamp': datetime.now().isoformat(),
                    'affected_nodes': ['supplier_SUP-002']
                }
            ]
        
        return alerts
    
    async def get_visualization_data(self, supply_chain_id: str, 
                                   time_range: Optional[timedelta] = None) -> Optional[VisualizationData]:
        """获取可视化数据"""
        if supply_chain_id in self.visualization_cache:
            cached_data = self.visualization_cache[supply_chain_id]
            if time_range is None or (datetime.now() - cached_data.timestamp) <= time_range:
                return cached_data
        
        # 重新生成数据
        new_data = await self.generate_supply_chain_map(supply_chain_id)
        if new_data:
            return self.visualization_cache.get(supply_chain_id)
        return None
    
    async def export_visualization(self, supply_chain_id: str, format_type: str = 'json') -> bytes:
        """导出可视化数据"""
        data = await self.get_visualization_data(supply_chain_id)
        if not data:
            return b''
        
        if format_type == 'json':
            export_data = {
                'timestamp': data.timestamp.isoformat(),
                'supply_chain_id': data.supply_chain_id,
                'nodes': data.nodes,
                'edges': data.edges,
                'metrics': data.metrics,
                'alerts': data.alerts,
                'metadata': data.metadata
            }
            return json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')
        elif format_type == 'csv':
            # CSV格式导出（简化）
            csv_lines = ['Node ID,Type,Name,Status,X,Y']
            for node in data.nodes:
                csv_lines.append(f"{node['id']},{node['type']},{node['name']},{node['status']},{node['position']['x']},{node['position']['y']}")
            return '\n'.join(csv_lines).encode('utf-8')
        
        return b''