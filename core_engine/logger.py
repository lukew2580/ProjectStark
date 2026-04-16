"""
Hardwareless AI — Logging System
Centralized logging with security events and debug mode
"""
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    GENERAL = "general"
    SECURITY = "security"
    VIRUS = "virus"
    SCAM = "scam"
    API = "api"
    SYSTEM = "system"


class HardwarelessLogger:
    """
    Centralized logging for Hardwareless AI.
    Supports security events, debug mode, and log rotation.
    """
    
    def __init__(
        self,
        log_dir: str = "logs",
        max_bytes: int = 10_000_000,  # 10MB
        backup_count: int = 5,
        debug_mode: bool = False
    ):
        self.log_dir = log_dir
        self.debug_mode = debug_mode
        self._setup_directories(max_bytes, backup_count)
        self._loggers: Dict[str, logging.Logger] = {}
        self._init_loggers()
    
    def _setup_directories(self, max_bytes: int, backup_count: int):
        """Create log directories."""
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(f"{self.log_dir}/security", exist_ok=True)
        os.makedirs(f"{self.log_dir}/virus", exist_ok=True)
        os.makedirs(f"{self.log_dir}/scam", exist_ok=True)
        os.makedirs(f"{self.log_dir}/api", exist_ok=True)
        
        self.max_bytes = max_bytes
        self.backup_count = backup_count
    
    def _init_loggers(self):
        """Initialize loggers for each category."""
        categories = [
            LogCategory.GENERAL,
            LogCategory.SECURITY,
            LogCategory.VIRUS,
            LogCategory.SCAM,
            LogCategory.API,
            LogCategory.SYSTEM
        ]
        
        for category in categories:
            logger = logging.getLogger(category.value)
            logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
            
            if not logger.handlers:
                log_file = f"{self.log_dir}/{category.value}.log"
                handler = RotatingFileHandler(
                    log_file,
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count
                )
                
                formatter = logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            
            self._loggers[category.value] = logger
    
    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode."""
        self.debug_mode = enabled
        level = logging.DEBUG if enabled else logging.INFO
        for logger in self._loggers.values():
            logger.setLevel(level)
    
    def log(
        self,
        message: str,
        category: LogCategory = LogCategory.GENERAL,
        level: LogLevel = LogLevel.INFO,
        **kwargs
    ):
        """Log a message."""
        logger = self._loggers.get(category.value)
        if not logger:
            return
        
        log_level = getattr(logging, level.value)
        logger.log(log_level, message, extra=kwargs)
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "MEDIUM",
        **metadata
    ):
        """Log a security event."""
        logger = self._loggers.get(LogCategory.SECURITY.value)
        
        event_data = {
            "event_type": event_type,
            "description": description,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            **metadata
        }
        
        if severity == "CRITICAL":
            logger.critical(event_data)
        elif severity == "HIGH":
            logger.error(event_data)
        elif severity == "MEDIUM":
            logger.warning(event_data)
        else:
            logger.info(event_data)
    
    def log_virus_detection(
        self,
        file_path: str,
        virus_name: str,
        action: str,
        quarantined: bool = False
    ):
        """Log virus detection event."""
        logger = self._loggers.get(LogCategory.VIRUS.value)
        
        event = {
            "file": file_path,
            "virus": virus_name,
            "action": action,
            "quarantined": quarantined,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.warning(event)
    
    def log_scam_detection(
        self,
        scam_type: str,
        source: str,
        confidence: float,
        indicators: list = None
    ):
        """Log scam detection event."""
        logger = self._loggers.get(LogCategory.SCAM.value)
        
        event = {
            "scam_type": scam_type,
            "source": source,
            "confidence": confidence,
            "indicators": indicators or [],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.warning(event)
    
    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_agent: str = None
    ):
        """Log API request."""
        logger = self._loggers.get(LogCategory.API.value)
        
        event = {
            "endpoint": endpoint,
            "method": method,
            "status": status_code,
            "duration_ms": duration_ms,
            "user_agent": user_agent,
            "timestamp": datetime.now().isoformat()
        }
        
        if status_code >= 500:
            logger.error(event)
        elif status_code >= 400:
            logger.warning(event)
        else:
            logger.info(event)
    
    def get_logs(
        self,
        category: LogCategory = LogCategory.GENERAL,
        limit: int = 100
    ) -> list:
        """Get recent logs."""
        logger = self._loggers.get(category.value)
        if not logger:
            return []
        
        return []  # Would need to read from file
    
    def get_security_events(
        self,
        severity: str = None,
        limit: int = 100
    ) -> list:
        """Get security events."""
        logger = self._loggers.get(LogCategory.SECURITY.value)
        
        return []  # Would need to read from file
    
    def clear_old_logs(self, days: int = 30):
        """Clear logs older than N days."""
        pass  # Implementation would remove old files


_global_logger: Optional[HardwarelessLogger] = None


def get_logger(
    log_dir: str = "logs",
    debug_mode: bool = None
) -> HardwarelessLogger:
    global _global_logger
    
    if _global_logger is None:
        debug = debug_mode or os.getenv("DEBUG_MODE", "false").lower() == "true"
        _global_logger = HardwarelessLogger(log_dir=log_dir, debug_mode=debug)
    
    return _global_logger