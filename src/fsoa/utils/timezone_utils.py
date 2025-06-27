"""
时区工具模块

统一处理中国时区（UTC+8）的时间，确保所有时间都是中国本地时间
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 中国时区 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


def now_china() -> datetime:
    """
    获取当前中国时间
    
    Returns:
        中国时区的当前时间（带时区信息）
    """
    return datetime.now(CHINA_TZ)


def now_china_naive() -> datetime:
    """
    获取当前中国时间（不带时区信息）
    
    Returns:
        中国时区的当前时间（naive datetime）
    """
    return datetime.now(CHINA_TZ).replace(tzinfo=None)


def utc_to_china(utc_dt: datetime) -> datetime:
    """
    将UTC时间转换为中国时间
    
    Args:
        utc_dt: UTC时间
        
    Returns:
        中国时区的时间
    """
    if utc_dt.tzinfo is None:
        # 如果是naive datetime，假设它是UTC时间
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    return utc_dt.astimezone(CHINA_TZ)


def china_to_utc(china_dt: datetime) -> datetime:
    """
    将中国时间转换为UTC时间
    
    Args:
        china_dt: 中国时间
        
    Returns:
        UTC时间
    """
    if china_dt.tzinfo is None:
        # 如果是naive datetime，假设它是中国时间
        china_dt = china_dt.replace(tzinfo=CHINA_TZ)
    
    return china_dt.astimezone(timezone.utc)


def ensure_china_timezone(dt: datetime) -> datetime:
    """
    确保datetime对象是中国时区
    
    Args:
        dt: 时间对象
        
    Returns:
        中国时区的时间
    """
    if dt.tzinfo is None:
        # 如果是naive datetime，假设它已经是中国时间
        return dt.replace(tzinfo=CHINA_TZ)
    else:
        # 如果有时区信息，转换为中国时区
        return dt.astimezone(CHINA_TZ)


def format_china_time(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化中国时间为字符串
    
    Args:
        dt: 时间对象
        format_str: 格式字符串
        
    Returns:
        格式化的时间字符串
    """
    china_dt = ensure_china_timezone(dt)
    return china_dt.strftime(format_str)


def parse_china_time(time_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析时间字符串为中国时间
    
    Args:
        time_str: 时间字符串
        format_str: 格式字符串
        
    Returns:
        中国时区的时间
    """
    dt = datetime.strptime(time_str, format_str)
    return dt.replace(tzinfo=CHINA_TZ)


def get_china_date_range(date_offset: int = 0) -> tuple[datetime, datetime]:
    """
    获取中国时区的日期范围（当天00:00到23:59:59）
    
    Args:
        date_offset: 日期偏移量，0=今天，-1=昨天，1=明天
        
    Returns:
        (开始时间, 结束时间) 的元组
    """
    today = now_china_naive().date()
    target_date = today + timedelta(days=date_offset)
    
    start_time = datetime.combine(target_date, datetime.min.time())
    end_time = datetime.combine(target_date, datetime.max.time())
    
    return start_time, end_time


def is_same_china_day(dt1: datetime, dt2: datetime) -> bool:
    """
    判断两个时间是否是中国时区的同一天
    
    Args:
        dt1: 第一个时间
        dt2: 第二个时间
        
    Returns:
        是否是同一天
    """
    china_dt1 = ensure_china_timezone(dt1)
    china_dt2 = ensure_china_timezone(dt2)
    
    return china_dt1.date() == china_dt2.date()


def get_china_business_hours() -> tuple[int, int]:
    """
    获取中国时区的工作时间范围

    Returns:
        (开始小时, 结束小时) 的元组
    """
    try:
        from ..data.database import get_database_manager
        db_manager = get_database_manager()

        work_start_hour = int(db_manager.get_system_config("work_start_hour") or "9")
        work_end_hour = int(db_manager.get_system_config("work_end_hour") or "19")

        return work_start_hour, work_end_hour
    except Exception:
        # 如果数据库不可用，使用默认配置
        return 9, 19  # 早9点到晚7点


def is_china_business_hours(dt: Optional[datetime] = None) -> bool:
    """
    判断是否在中国时区的工作时间内

    Args:
        dt: 时间点，默认为当前时间

    Returns:
        是否在工作时间内
    """
    if dt is None:
        dt = now_china_naive()
    else:
        dt = ensure_china_timezone(dt).replace(tzinfo=None)

    try:
        from ..data.database import get_database_manager
        db_manager = get_database_manager()

        # 获取工作日配置
        work_days_str = db_manager.get_system_config("work_days") or "1,2,3,4,5"
        work_days = [int(d.strip()) for d in work_days_str.split(",") if d.strip().isdigit()]

        # 检查是否为工作日（1=周一，7=周日）
        weekday = dt.weekday() + 1  # Python的weekday()返回0-6，转换为1-7
        if weekday not in work_days:
            return False

        # 检查是否在工作时间内
        start_hour, end_hour = get_china_business_hours()
        return start_hour <= dt.hour < end_hour
    except Exception:
        # 如果数据库不可用，使用默认逻辑
        # 检查是否为工作日（周一到周五）
        if dt.weekday() >= 5:  # 周六=5, 周日=6
            return False

        # 检查是否在工作时间内
        start_hour, end_hour = get_china_business_hours()
        return start_hour <= dt.hour < end_hour


def china_time_delta_hours(start_dt: datetime, end_dt: Optional[datetime] = None) -> float:
    """
    计算中国时区两个时间点之间的小时差
    
    Args:
        start_dt: 开始时间
        end_dt: 结束时间，默认为当前时间
        
    Returns:
        时间差（小时）
    """
    if end_dt is None:
        end_dt = now_china_naive()
    
    # 确保都是中国时区的naive datetime
    start_china = ensure_china_timezone(start_dt).replace(tzinfo=None)
    end_china = ensure_china_timezone(end_dt).replace(tzinfo=None)
    
    delta = end_china - start_china
    return delta.total_seconds() / 3600


def get_china_timezone_info() -> dict:
    """
    获取中国时区信息
    
    Returns:
        时区信息字典
    """
    now = now_china()
    return {
        "timezone_name": "Asia/Shanghai",
        "timezone_offset": "+08:00",
        "current_time": now.isoformat(),
        "current_time_formatted": format_china_time(now),
        "is_business_hours": is_china_business_hours(now),
        "business_hours": f"{get_china_business_hours()[0]}:00-{get_china_business_hours()[1]}:00"
    }


# 为了向后兼容，提供一些别名
china_now = now_china_naive
china_format = format_china_time


def log_timezone_info():
    """记录时区信息到日志"""
    info = get_china_timezone_info()
    logger.info(f"Timezone Info: {info}")


# 在模块加载时记录时区信息
if __name__ != "__main__":
    log_timezone_info()
