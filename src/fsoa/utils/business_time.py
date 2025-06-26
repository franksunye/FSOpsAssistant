"""
工作时间计算模块

实现工作时间的计算逻辑，支持：
- 工作时间定义：早9点到晚7点（12小时）
- 工作日定义：周一到周五
- 工作时间内的时长计算
- SLA时间的工作时间换算
"""

from datetime import datetime, timedelta, time
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class BusinessTimeCalculator:
    """工作时间计算器"""
    
    # 工作时间配置
    WORK_START_HOUR = 9   # 早上9点
    WORK_END_HOUR = 19    # 晚上7点（不包含）
    WORK_HOURS_PER_DAY = 10  # 每天工作10小时 (9-19点)
    
    @classmethod
    def is_business_hours(cls, dt: datetime) -> bool:
        """
        判断是否为工作时间
        
        Args:
            dt: 时间点
            
        Returns:
            是否为工作时间
        """
        # 检查是否为工作日（周一到周五）
        if dt.weekday() >= 5:  # 周六=5, 周日=6
            return False
        
        # 检查是否在工作时间内
        hour = dt.hour
        return cls.WORK_START_HOUR <= hour < cls.WORK_END_HOUR
    
    @classmethod
    def is_business_day(cls, dt: datetime) -> bool:
        """
        判断是否为工作日
        
        Args:
            dt: 时间点
            
        Returns:
            是否为工作日
        """
        return dt.weekday() < 5  # 周一到周五
    
    @classmethod
    def get_next_business_start(cls, dt: datetime) -> datetime:
        """
        获取下一个工作时间开始点
        
        Args:
            dt: 当前时间
            
        Returns:
            下一个工作时间开始点
        """
        # 如果是工作日且在工作时间内，返回当前时间
        if cls.is_business_day(dt) and cls.is_business_hours(dt):
            return dt
        
        # 如果是工作日但不在工作时间内
        if cls.is_business_day(dt):
            if dt.hour < cls.WORK_START_HOUR:
                # 当天还没开始工作，返回当天工作开始时间
                return dt.replace(hour=cls.WORK_START_HOUR, minute=0, second=0, microsecond=0)
            else:
                # 当天工作已结束，返回下一个工作日开始时间
                next_day = dt + timedelta(days=1)
                while not cls.is_business_day(next_day):
                    next_day += timedelta(days=1)
                return next_day.replace(hour=cls.WORK_START_HOUR, minute=0, second=0, microsecond=0)
        
        # 如果是非工作日，找到下一个工作日
        next_day = dt + timedelta(days=1)
        while not cls.is_business_day(next_day):
            next_day += timedelta(days=1)
        return next_day.replace(hour=cls.WORK_START_HOUR, minute=0, second=0, microsecond=0)
    
    @classmethod
    def calculate_business_hours_between(cls, start_dt: datetime, end_dt: datetime) -> float:
        """
        计算两个时间点之间的工作时长（小时）
        
        Args:
            start_dt: 开始时间
            end_dt: 结束时间
            
        Returns:
            工作时长（小时）
        """
        if start_dt >= end_dt:
            return 0.0
        
        total_hours = 0.0
        current_dt = start_dt
        
        while current_dt < end_dt:
            # 如果当前时间不是工作时间，跳到下一个工作时间开始点
            if not cls.is_business_hours(current_dt):
                current_dt = cls.get_next_business_start(current_dt)
                if current_dt >= end_dt:
                    break
            
            # 计算当天的工作结束时间
            work_end_today = current_dt.replace(hour=cls.WORK_END_HOUR, minute=0, second=0, microsecond=0)
            
            # 确定当天的计算结束时间
            day_end = min(end_dt, work_end_today)
            
            # 计算当天的工作时长
            if day_end > current_dt:
                day_hours = (day_end - current_dt).total_seconds() / 3600
                total_hours += day_hours
            
            # 移动到下一个工作日开始
            current_dt = cls.get_next_business_start(work_end_today + timedelta(minutes=1))
        
        return total_hours
    
    @classmethod
    def calculate_elapsed_business_hours(cls, create_time: datetime, 
                                       current_time: datetime = None) -> float:
        """
        计算从创建时间到当前时间的工作时长
        
        Args:
            create_time: 创建时间
            current_time: 当前时间，默认为现在
            
        Returns:
            工作时长（小时）
        """
        if current_time is None:
            current_time = datetime.now()
        
        return cls.calculate_business_hours_between(create_time, current_time)
    
    @classmethod
    def add_business_hours(cls, start_dt: datetime, hours: float) -> datetime:
        """
        在指定时间基础上增加工作时长
        
        Args:
            start_dt: 开始时间
            hours: 要增加的工作时长（小时）
            
        Returns:
            增加工作时长后的时间
        """
        if hours <= 0:
            return start_dt
        
        current_dt = start_dt
        remaining_hours = hours
        
        while remaining_hours > 0:
            # 如果当前时间不是工作时间，跳到下一个工作时间开始点
            if not cls.is_business_hours(current_dt):
                current_dt = cls.get_next_business_start(current_dt)
            
            # 计算当天剩余的工作时间
            work_end_today = current_dt.replace(hour=cls.WORK_END_HOUR, minute=0, second=0, microsecond=0)
            remaining_today = (work_end_today - current_dt).total_seconds() / 3600
            
            if remaining_hours <= remaining_today:
                # 在当天就能完成
                return current_dt + timedelta(hours=remaining_hours)
            else:
                # 需要跨天
                remaining_hours -= remaining_today
                current_dt = cls.get_next_business_start(work_end_today + timedelta(minutes=1))
        
        return current_dt


def calculate_business_elapsed_hours(create_time: datetime, 
                                   current_time: datetime = None) -> float:
    """
    便捷函数：计算工作时长
    
    Args:
        create_time: 创建时间
        current_time: 当前时间
        
    Returns:
        工作时长（小时）
    """
    return BusinessTimeCalculator.calculate_elapsed_business_hours(create_time, current_time)


def is_within_business_hours(dt: datetime = None) -> bool:
    """
    便捷函数：判断是否在工作时间内
    
    Args:
        dt: 时间点，默认为当前时间
        
    Returns:
        是否在工作时间内
    """
    if dt is None:
        dt = datetime.now()
    return BusinessTimeCalculator.is_business_hours(dt)
