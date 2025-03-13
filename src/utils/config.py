"""
Configuration handling utilities for the USB File Transfer Tracker
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Union

@dataclass
class GeneralConfig:
    """General configuration settings"""
    log_directory: str = "logs"
    run_at_startup: bool = True
    minimize_to_tray: bool = True

@dataclass
class MonitoringConfig:
    """File monitoring configuration settings"""
    check_interval_seconds: int = 1
    include_file_extensions: List[str] = field(default_factory=lambda: ["*"])
    exclude_file_extensions: List[str] = field(default_factory=lambda: [".tmp", ".temp", ".lock"])
    min_file_size_bytes: int = 0
    max_file_size_bytes: Optional[int] = None

@dataclass
class TimeBasedAlertConfig:
    """Time-based alert configuration"""
    enabled: bool = True
    restricted_hours: Dict[str, str] = field(default_factory=lambda: {"start": "18:00", "end": "07:00"})
    weekend_alerts: bool = True

@dataclass
class AlertConfig:
    """Alert configuration settings"""
    enable_alerts: bool = True
    alert_threshold_mb: int = 100
    suspicious_extensions: List[str] = field(default_factory=lambda: 
        [".zip", ".rar", ".7z", ".tar", ".gz", ".db", ".sql", ".xlsx", ".docx", ".pdf"])
    large_transfer_alert: bool = True
    large_transfer_threshold_mb: int = 500
    time_based_alerts: TimeBasedAlertConfig = field(default_factory=TimeBasedAlertConfig)

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    hash_algorithm: str = "sha256"
    encrypt_logs: bool = False
    log_retention_days: int = 90

@dataclass
class Config:
    """Main configuration class"""
    CONFIG_PATH: str = "config.json"
    
    general: GeneralConfig = field(default_factory=GeneralConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

def config_to_dict(config: Config) -> Dict[str, Any]:
    """Convert config object to dictionary for JSON serialization"""
    return {
        "general": asdict(config.general),
        "monitoring": asdict(config.monitoring),
        "alerts": {
            **{k: v for k, v in asdict(config.alerts).items() if k != "time_based_alerts"},
            "time_based_alerts": asdict(config.alerts.time_based_alerts)
        },
        "security": asdict(config.security)
    }

def dict_to_config(config_dict: Dict[str, Any]) -> Config:
    """Convert dictionary to config object"""
    config = Config()
    
    # General settings
    if "general" in config_dict:
        for key, value in config_dict["general"].items():
            if hasattr(config.general, key):
                setattr(config.general, key, value)
    
    # Monitoring settings
    if "monitoring" in config_dict:
        for key, value in config_dict["monitoring"].items():
            if hasattr(config.monitoring, key):
                setattr(config.monitoring, key, value)
    
    # Alert settings
    if "alerts" in config_dict:
        alert_dict = config_dict["alerts"]
        for key, value in alert_dict.items():
            if key == "time_based_alerts" and isinstance(value, dict):
                for tba_key, tba_value in value.items():
                    if hasattr(config.alerts.time_based_alerts, tba_key):
                        setattr(config.alerts.time_based_alerts, tba_key, tba_value)
            elif hasattr(config.alerts, key):
                setattr(config.alerts, key, value)
    
    # Security settings
    if "security" in config_dict:
        for key, value in config_dict["security"].items():
            if hasattr(config.security, key):
                setattr(config.security, key, value)
    
    return config

def load_config() -> Config:
    """Load configuration from file"""
    config_path = Path(Config.CONFIG_PATH)
    
    # If config file doesn't exist, create default config
    if not config_path.exists():
        config = Config()
        save_config(config)
        return config
    
    try:
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return dict_to_config(config_dict)
    except Exception as e:
        print(f"Error loading config: {str(e)}. Using default configuration.")
        return Config()

def save_config(config: Config) -> bool:
    """Save configuration to file"""
    config_path = Path(Config.CONFIG_PATH)
    
    try:
        config_dict = config_to_dict(config)
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {str(e)}")
        return False