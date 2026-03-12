#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理模块 - 知识卡片生成器
功能：重试机制、错误日志、失败恢复
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('knowledge-card-errors.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('KnowledgeCard')


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟 (秒)
        backoff: 延迟倍数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"{func.__name__} 失败，已达最大重试次数：{e}")
                        raise
                    
                    logger.warning(f"{func.__name__} 失败，{current_delay}秒后重试 ({attempts}/{max_attempts}): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator


def log_errors(func: Callable) -> Callable:
    """
    错误日志装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} 出错：{e}", exc_info=True)
            raise
    return wrapper


class ErrorHandler:
    """
    错误处理器 - 集中管理错误
    """
    
    def __init__(self):
        self.error_count = 0
        self.success_count = 0
        self.errors = []
    
    def record_error(self, error: Exception, context: str = "") -> None:
        """记录错误"""
        self.error_count += 1
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error': str(error),
            'type': type(error).__name__,
            'context': context
        }
        self.errors.append(error_info)
        logger.error(f"错误 [{self.error_count}]: {error_info}")
    
    def record_success(self) -> None:
        """记录成功"""
        self.success_count += 1
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total = self.error_count + self.success_count
        return {
            'total': total,
            'success': self.success_count,
            'failed': self.error_count,
            'success_rate': self.success_count / total if total > 0 else 0,
            'errors': self.errors[-10:]  # 最近 10 个错误
        }
    
    def should_continue(self, max_error_rate: float = 0.2) -> bool:
        """
        判断是否应该继续
        
        Args:
            max_error_rate: 最大错误率阈值
            
        Returns:
            bool: 是否继续
        """
        total = self.error_count + self.success_count
        if total == 0:
            return True
        
        error_rate = self.error_count / total
        return error_rate <= max_error_rate


# 全局错误处理器
global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    return global_error_handler
