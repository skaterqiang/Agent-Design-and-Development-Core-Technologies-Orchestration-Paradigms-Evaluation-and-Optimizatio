"""
API密钥配置文件 - 生产环境请使用环境变量或密钥管理服务
"""
import os
from typing import Dict, Any

# API密钥配置 TODO 例子的解释信息都在《智能体设计开发实战：核心技术、编排模式、评估与调优》一书中


API_KEYS = {
    "tongyi": os.getenv("TONGYI_API_KEY", "")
}

def get_api_key(provider: str = "tongyi") -> str:
    """
    获取指定提供商的API密钥
    
    Args:
        provider: 提供商名称 ("tongyi")
    
    Returns:
        API密钥字符串
    """
    key = API_KEYS.get(provider.lower(), "")
    if not key:
        raise ValueError(f"未找到提供商 '{provider}' 的API密钥，请检查配置")
    return key

def get_all_configs() -> Dict[str, Any]:
    """获取所有配置"""
    return {
        "api_keys": {k: "***" + v[-4:] if v else "" for k, v in API_KEYS.items()},
        "env_vars_set": {
            "TONGYI_API_KEY": bool(os.getenv("TONGYI_API_KEY"))
        }
    }
