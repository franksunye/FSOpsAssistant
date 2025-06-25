"""
日志管理模块

提供结构化日志记录功能
"""

import os
import sys
import logging
import structlog
from datetime import datetime
from typing import Any, Dict
from pathlib import Path

from .config import get_config


def setup_logging():
    """设置日志配置"""
    config = get_config()
    
    # 确保日志目录存在
    log_file_path = Path(config.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置标准库logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.log_file, encoding='utf-8')
        ]
    )
    
    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not config.is_development 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """获取日志记录器"""
    if not structlog.is_configured():
        setup_logging()
    
    return structlog.get_logger(name)


class LoggerMixin:
    """日志记录器混入类"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """获取当前类的日志记录器"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """函数调用日志装饰器"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                "Function completed",
                function=func.__name__,
                execution_time=execution_time
            )
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(
                "Function failed",
                function=func.__name__,
                execution_time=execution_time,
                error=str(e)
            )
            raise
    
    return wrapper


def log_agent_step(step_name: str, input_data: Dict[str, Any] = None, 
                   output_data: Dict[str, Any] = None, error: str = None):
    """记录Agent步骤日志"""
    logger = get_logger("agent")
    
    log_data = {
        "step": step_name,
        "timestamp": datetime.now().isoformat()
    }
    
    if input_data:
        log_data["input"] = input_data
    if output_data:
        log_data["output"] = output_data
    if error:
        log_data["error"] = error
        logger.error("Agent step failed", **log_data)
    else:
        logger.info("Agent step completed", **log_data)


# 初始化日志配置
setup_logging()
