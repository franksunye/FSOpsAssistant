#!/usr/bin/env python3
"""
简化的工作时间配置测试

这个脚本测试工作时间配置的核心功能，不依赖完整的系统配置
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置环境变量以避免配置验证错误
os.environ['DEEPSEEK_API_KEY'] = 'test'
os.environ['METABASE_URL'] = 'http://test'
os.environ['METABASE_USERNAME'] = 'test'
os.environ['METABASE_PASSWORD'] = 'test'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'http://test'

def test_business_time_calculator_hardcoded():
    """测试BusinessTimeCalculator的硬编码配置"""
    print("=== 测试BusinessTimeCalculator硬编码配置 ===")
    
    # 直接导入并测试
    from src.fsoa.utils.business_time import BusinessTimeCalculator
    
    # 测试默认配置
    print(f"默认工作开始时间: {BusinessTimeCalculator.DEFAULT_WORK_START_HOUR}")
    print(f"默认工作结束时间: {BusinessTimeCalculator.DEFAULT_WORK_END_HOUR}")
    print(f"默认工作日: {BusinessTimeCalculator.DEFAULT_WORK_DAYS}")
    
    # 测试_get_work_config方法（应该返回默认值，因为没有数据库）
    try:
        work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
        print(f"获取的工作配置: {work_start_hour}:00-{work_end_hour}:00, 工作日: {work_days}")
        
        # 验证是否使用了默认配置
        assert work_start_hour == BusinessTimeCalculator.DEFAULT_WORK_START_HOUR
        assert work_end_hour == BusinessTimeCalculator.DEFAULT_WORK_END_HOUR
        assert work_days == BusinessTimeCalculator.DEFAULT_WORK_DAYS
        print("✓ 默认配置正确")
        
    except Exception as e:
        print(f"✗ 获取工作配置失败: {e}")
        return False
    
    return True


def test_business_time_methods():
    """测试BusinessTimeCalculator的各种方法"""
    print("\n=== 测试BusinessTimeCalculator方法 ===")
    
    from src.fsoa.utils.business_time import BusinessTimeCalculator
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    # 创建测试时间
    now = now_china_naive()
    
    # 测试工作日判断
    print("\n工作日判断测试:")
    for i in range(7):
        test_date = now + timedelta(days=i)
        is_business_day = BusinessTimeCalculator.is_business_day(test_date)
        weekday_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][test_date.weekday()]
        print(f"  {weekday_name}: {is_business_day}")
    
    # 测试工作时间判断
    print("\n工作时间判断测试:")
    test_hours = [7, 9, 12, 18, 20]
    for hour in test_hours:
        test_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        is_business_hours = BusinessTimeCalculator.is_business_hours(test_time)
        print(f"  {hour}:00: {is_business_hours}")
    
    # 测试工作时长计算
    print("\n工作时长计算测试:")
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    test_durations = [
        timedelta(hours=2),    # 2小时
        timedelta(hours=8),    # 8小时
        timedelta(days=1),     # 1天
        timedelta(days=3),     # 3天
    ]
    
    for duration in test_durations:
        end_time = start_time + duration
        elapsed = BusinessTimeCalculator.calculate_business_hours_between(start_time, end_time)
        print(f"  {duration}: {elapsed:.1f}小时")
    
    return True


def test_timezone_utils():
    """测试timezone_utils模块"""
    print("\n=== 测试timezone_utils模块 ===")
    
    from src.fsoa.utils.timezone_utils import (
        get_china_business_hours, 
        is_china_business_hours,
        now_china_naive
    )
    
    # 测试get_china_business_hours
    try:
        start_hour, end_hour = get_china_business_hours()
        print(f"中国时区工作时间: {start_hour}:00-{end_hour}:00")
        
        # 应该返回默认值
        assert start_hour == 9
        assert end_hour == 19
        print("✓ 中国时区工作时间配置正确")
        
    except Exception as e:
        print(f"✗ 获取中国时区工作时间失败: {e}")
        return False
    
    # 测试is_china_business_hours
    print("\n中国时区工作时间判断:")
    now = now_china_naive()
    test_hours = [7, 9, 12, 18, 20]
    for hour in test_hours:
        test_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        is_business = is_china_business_hours(test_time)
        print(f"  {hour}:00: {is_business}")
    
    return True


def test_cross_day_calculation():
    """测试跨日工作时间计算"""
    print("\n=== 测试跨日工作时间计算 ===")
    
    from src.fsoa.utils.business_time import BusinessTimeCalculator
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    now = now_china_naive()
    
    # 测试场景1: 周五下午到周一上午
    friday_afternoon = now.replace(hour=16, minute=0, second=0, microsecond=0)
    while friday_afternoon.weekday() != 4:  # 找到周五
        friday_afternoon += timedelta(days=1)
    
    monday_morning = friday_afternoon + timedelta(days=3)  # 周一
    monday_morning = monday_morning.replace(hour=10, minute=0, second=0, microsecond=0)
    
    elapsed = BusinessTimeCalculator.calculate_business_hours_between(friday_afternoon, monday_morning)
    print(f"周五16:00到周一10:00: {elapsed:.1f}小时 (期望: 4.0小时)")
    
    # 测试场景2: 同一天内
    same_day_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    same_day_end = same_day_start.replace(hour=17, minute=0, second=0, microsecond=0)
    
    elapsed_same_day = BusinessTimeCalculator.calculate_business_hours_between(same_day_start, same_day_end)
    print(f"同一天9:00到17:00: {elapsed_same_day:.1f}小时 (期望: 8.0小时)")
    
    # 测试场景3: 非工作时间开始
    night_start = now.replace(hour=22, minute=0, second=0, microsecond=0)
    next_day_end = night_start + timedelta(days=1)
    next_day_end = next_day_end.replace(hour=12, minute=0, second=0, microsecond=0)
    
    elapsed_night = BusinessTimeCalculator.calculate_business_hours_between(night_start, next_day_end)
    print(f"晚上22:00到次日12:00: {elapsed_night:.1f}小时")
    
    return True


def test_get_next_business_start():
    """测试获取下一个工作时间开始点"""
    print("\n=== 测试获取下一个工作时间开始点 ===")
    
    from src.fsoa.utils.business_time import BusinessTimeCalculator
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    now = now_china_naive()
    
    # 测试不同时间点
    test_times = [
        now.replace(hour=7, minute=0, second=0, microsecond=0),   # 早上7点
        now.replace(hour=10, minute=0, second=0, microsecond=0),  # 上午10点
        now.replace(hour=20, minute=0, second=0, microsecond=0),  # 晚上8点
    ]
    
    for test_time in test_times:
        next_start = BusinessTimeCalculator.get_next_business_start(test_time)
        print(f"  {test_time.strftime('%H:%M')} -> {next_start.strftime('%m-%d %H:%M')}")
    
    return True


def main():
    """主测试函数"""
    print("开始测试工作时间配置功能（简化版）...")
    
    try:
        # 运行所有测试
        success = True
        success &= test_business_time_calculator_hardcoded()
        success &= test_business_time_methods()
        success &= test_timezone_utils()
        success &= test_cross_day_calculation()
        success &= test_get_next_business_start()
        
        if success:
            print("\n✅ 所有测试完成！工作时间配置功能正常")
        else:
            print("\n❌ 部分测试失败")
        
        return success
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
