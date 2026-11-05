"""
Configuration loader for Smart Supply Chain System
Handles loading and parsing of YAML configuration files
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SystemConfig:
    """System configuration data class"""
    name: str
    version: str
    debug: bool
    log_level: str


@dataclass
class CoordinatorConfig:
    """Coordinator configuration data class"""
    heartbeat_interval: int
    task_timeout: int
    max_concurrent_tasks: int
    retry_attempts: int


@dataclass
class ClusterConfig:
    """Cluster configuration data class"""
    node_timeout: int
    load_threshold: float
    auto_scale: bool
    min_nodes: int
    max_nodes: int


@dataclass
class VisualizationConfig:
    """Visualization configuration data class"""
    refresh_interval: int
    retention_days: int
    enable_realtime_updates: bool
    chart_types: list


@dataclass
class DatabaseConfig:
    """Database configuration data class"""
    host: str
    port: int
    name: str
    user: str
    password: str
    pool_size: int


@dataclass
class CacheConfig:
    """Cache configuration data class"""
    type: str
    host: str
    port: int
    ttl: int


class ConfigLoader:
    """Configuration loader class"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
        """
        self.logger = logging.getLogger(__name__)
        
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = Path(__file__).parent.parent
            self.config_path = project_root / "config" / "config.yaml"
        else:
            self.config_path = Path(config_path)
            
        self._config_data: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)
                
            self.logger.info(f"Configuration loaded successfully from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration"""
        system_data = self._config_data.get('system', {})
        return SystemConfig(
            name=system_data.get('name', 'Smart Supply Chain System'),
            version=system_data.get('version', '1.0.0'),
            debug=system_data.get('debug', False),
            log_level=system_data.get('log_level', 'INFO')
        )
    
    def get_coordinator_config(self) -> CoordinatorConfig:
        """Get coordinator configuration"""
        coord_data = self._config_data.get('coordinator', {})
        return CoordinatorConfig(
            heartbeat_interval=coord_data.get('heartbeat_interval', 30),
            task_timeout=coord_data.get('task_timeout', 3600),
            max_concurrent_tasks=coord_data.get('max_concurrent_tasks', 100),
            retry_attempts=coord_data.get('retry_attempts', 3)
        )
    
    def get_cluster_config(self) -> ClusterConfig:
        """Get cluster configuration"""
        cluster_data = self._config_data.get('cluster', {})
        return ClusterConfig(
            node_timeout=cluster_data.get('node_timeout', 300),
            load_threshold=cluster_data.get('load_threshold', 0.8),
            auto_scale=cluster_data.get('auto_scale', True),
            min_nodes=cluster_data.get('min_nodes', 3),
            max_nodes=cluster_data.get('max_nodes', 20)
        )
    
    def get_visualization_config(self) -> VisualizationConfig:
        """Get visualization configuration"""
        viz_data = self._config_data.get('visualization', {})
        return VisualizationConfig(
            refresh_interval=viz_data.get('refresh_interval', 10),
            retention_days=viz_data.get('retention_days', 30),
            enable_realtime_updates=viz_data.get('enable_realtime_updates', True),
            chart_types=viz_data.get('chart_types', ['timeline', 'network', 'heatmap', 'gantt'])
        )
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_data = self._config_data.get('database', {})
        return DatabaseConfig(
            host=db_data.get('host', 'localhost'),
            port=db_data.get('port', 5432),
            name=db_data.get('name', 'supply_chain_db'),
            user=db_data.get('user', 'sc_user'),
            password=db_data.get('password', 'sc_password'),
            pool_size=db_data.get('pool_size', 20)
        )
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration"""
        cache_data = self._config_data.get('cache', {})
        return CacheConfig(
            type=cache_data.get('type', 'redis'),
            host=cache_data.get('host', 'localhost'),
            port=cache_data.get('port', 6379),
            ttl=cache_data.get('ttl', 3600)
        )
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration data"""
        return self._config_data.copy() if self._config_data else {}


def load_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Load configuration and return ConfigLoader instance
    
    Args:
        config_path: Path to configuration file. If None, uses default path.
        
    Returns:
        ConfigLoader instance
    """
    return ConfigLoader(config_path)


# Convenience functions for direct access to specific configurations
def get_system_config(config_path: Optional[str] = None) -> SystemConfig:
    """Get system configuration directly"""
    loader = load_config(config_path)
    return loader.get_system_config()


def get_coordinator_config(config_path: Optional[str] = None) -> CoordinatorConfig:
    """Get coordinator configuration directly"""
    loader = load_config(config_path)
    return loader.get_coordinator_config()


def get_cluster_config(config_path: Optional[str] = None) -> ClusterConfig:
    """Get cluster configuration directly"""
    loader = load_config(config_path)
    return loader.get_cluster_config()


def get_visualization_config(config_path: Optional[str] = None) -> VisualizationConfig:
    """Get visualization configuration directly"""
    loader = load_config(config_path)
    return loader.get_visualization_config()


def get_database_config(config_path: Optional[str] = None) -> DatabaseConfig:
    """Get database configuration directly"""
    loader = load_config(config_path)
    return loader.get_database_config()


def get_cache_config(config_path: Optional[str] = None) -> CacheConfig:
    """Get cache configuration directly"""
    loader = load_config(config_path)
    return loader.get_cache_config()