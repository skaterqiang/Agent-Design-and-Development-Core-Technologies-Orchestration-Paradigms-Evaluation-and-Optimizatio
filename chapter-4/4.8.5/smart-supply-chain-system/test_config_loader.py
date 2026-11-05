"""
Test script to verify config_loader functionality
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_loader import (
    load_config, 
    get_system_config, 
    get_coordinator_config,
    get_cluster_config,
    get_visualization_config
)

def test_config_loading():
    """Test configuration loading functionality"""
    print("Testing configuration loading...")
    
    # Test basic config loading
    config_loader = load_config()
    print("✓ Basic config loading successful")
    
    # Test system config
    system_config = get_system_config()
    print(f"✓ System config loaded: {system_config.name} v{system_config.version}")
    
    # Test coordinator config
    coord_config = get_coordinator_config()
    print(f"✓ Coordinator config loaded: heartbeat={coord_config.heartbeat_interval}s")
    
    # Test cluster config
    cluster_config = get_cluster_config()
    print(f"✓ Cluster config loaded: min_nodes={cluster_config.min_nodes}, max_nodes={cluster_config.max_nodes}")
    
    # Test visualization config
    viz_config = get_visualization_config()
    print(f"✓ Visualization config loaded: refresh_interval={viz_config.refresh_interval}s")
    
    print("\nAll configuration tests passed!")

if __name__ == "__main__":
    test_config_loading()