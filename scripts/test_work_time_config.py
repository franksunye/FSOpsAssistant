#!/usr/bin/env python3
"""
测试工作时间配置功能

这个脚本测试：
1. 工作时间配置的保存和读取
2. BusinessTimeCalculator使用动态配置
3. 前端界面的配置功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fsoa.data.database import get_database_manager
from src.fsoa.utils.business_time import BusinessTimeCalculator
from src.fsoa.utils.timezone_utils import now_china_naive, get_china_business_hours, is_china_business_hours


def test_config_save_and_load():
    """测试配置的保存和读取"""
    print("=== 测试配置保存和读取 ===")
    
    db_manager = get_database_manager()
    
    # 保存测试配置
    test_configs = [
        ("work_start_hour", "8", "工作开始时间（小时）"),
        ("work_end_hour", "18", "工作结束时间（小时）"),
        ("work_days", "1,2,3,4,5,6", "工作日（1=周一，7=周日，逗号分隔）"),
    ]
    
    print("保存测试配置...")
    for key, value, description in test_configs:
        success = db_manager.set_system_config(key, value, description)
        print(f"  {key}: {value} -> {'成功' if success else '失败'}")
    
    # 读取配置
    print("\n读取配置...")
    for key, expected_value, _ in test_configs:
        actual_value = db_manager.get_system_config(key)
        print(f"  {key}: {actual_value} (期望: {expected_value}) -> {'✓' if actual_value == expected_value else '✗'}")
    
    return True


def test_business_time_calculator():
    """测试BusinessTimeCalculator使用动态配置"""
    print("\n=== 测试BusinessTimeCalculator动态配置 ===")
    
    # 获取配置
    work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
    print(f"当前工作时间配置: {work_start_hour}:00 - {work_end_hour}:00")
    print(f"工作日: {work_days}")
    
    # 测试工作时间判断
    now = now_china_naive()
    test_times = [
        now.replace(hour=7, minute=0, second=0, microsecond=0),   # 早上7点
        now.replace(hour=9, minute=0, second=0, microsecond=0),   # 早上9点
        now.replace(hour=12, minute=0, second=0, microsecond=0),  # 中午12点
        now.replace(hour=18, minute=0, second=0, microsecond=0),  # 下午6点
        now.replace(hour=20, minute=0, second=0, microsecond=0),  # 晚上8点
    ]
    
    print("\n工作时间判断测试:")
    for test_time in test_times:
        is_business = BusinessTimeCalculator.is_business_hours(test_time)
        is_business_day = BusinessTimeCalculator.is_business_day(test_time)
        weekday = test_time.weekday() + 1
        print(f"  {test_time.strftime('%H:%M')} (周{weekday}): 工作时间={is_business}, 工作日={is_business_day}")
    
    # 测试工作时长计算
    print("\n工作时长计算测试:")
    start_time = now.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
    end_times = [
        start_time + timedelta(hours=2),   # 2小时后
        start_time + timedelta(hours=5),   # 5小时后
        start_time + timedelta(days=1),    # 1天后
        start_time + timedelta(days=2),    # 2天后
    ]
    
    for end_time in end_times:
        elapsed = BusinessTimeCalculator.calculate_business_hours_between(start_time, end_time)
        print(f"  从 {start_time.strftime('%m-%d %H:%M')} 到 {end_time.strftime('%m-%d %H:%M')}: {elapsed:.1f}小时")
    
    return True


def test_timezone_utils():
    """测试timezone_utils模块的动态配置"""
    print("\n=== 测试timezone_utils动态配置 ===")
    
    # 测试get_china_business_hours
    start_hour, end_hour = get_china_business_hours()
    print(f"中国时区工作时间: {start_hour}:00 - {end_hour}:00")
    
    # 测试is_china_business_hours
    now = now_china_naive()
    test_times = [
        now.replace(hour=7, minute=0, second=0, microsecond=0),
        now.replace(hour=9, minute=0, second=0, microsecond=0),
        now.replace(hour=12, minute=0, second=0, microsecond=0),
        now.replace(hour=18, minute=0, second=0, microsecond=0),
        now.replace(hour=20, minute=0, second=0, microsecond=0),
    ]
    
    print("\n中国时区工作时间判断:")
    for test_time in test_times:
        is_business = is_china_business_hours(test_time)
        weekday = test_time.weekday() + 1
        print(f"  {test_time.strftime('%H:%M')} (周{weekday}): {is_business}")
    
    return True


def test_config_scenarios():
    """测试不同配置场景"""
    print("\n=== 测试不同配置场景 ===")
    
    db_manager = get_database_manager()
    
    # 场景1: 996工作制
    print("\n场景1: 996工作制 (9:00-21:00, 周一到周六)")
    configs_996 = [
        ("work_start_hour", "9", "工作开始时间（小时）"),
        ("work_end_hour", "21", "工作结束时间（小时）"),
        ("work_days", "1,2,3,4,5,6", "工作日（1=周一，7=周日，逗号分隔）"),
    ]
    
    for key, value, description in configs_996:
        db_manager.set_system_config(key, value, description)
    
    work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
    print(f"  配置: {work_start_hour}:00-{work_end_hour}:00, 工作日: {work_days}")
    
    # 测试周六是否为工作日
    saturday = now_china_naive().replace(hour=10, minute=0, second=0, microsecond=0)
    while saturday.weekday() != 5:  # 找到周六
        saturday += timedelta(days=1)
    
    is_saturday_business = BusinessTimeCalculator.is_business_day(saturday)
    print(f"  周六是否为工作日: {is_saturday_business}")
    
    # 场景2: 朝九晚五
    print("\n场景2: 朝九晚五 (9:00-17:00, 周一到周五)")
    configs_955 = [
        ("work_start_hour", "9", "工作开始时间（小时）"),
        ("work_end_hour", "17", "工作结束时间（小时）"),
        ("work_days", "1,2,3,4,5", "工作日（1=周一，7=周日，逗号分隔）"),
    ]
    
    for key, value, description in configs_955:
        db_manager.set_system_config(key, value, description)
    
    work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
    print(f"  配置: {work_start_hour}:00-{work_end_hour}:00, 工作日: {work_days}")
    
    # 测试工作时长
    start_time = now_china_naive().replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = start_time.replace(hour=17, minute=0, second=0, microsecond=0)
    daily_hours = BusinessTimeCalculator.calculate_business_hours_between(start_time, end_time)
    print(f"  每日工作时长: {daily_hours}小时")
    
    return True


def restore_default_config():
    """恢复默认配置"""
    print("\n=== 恢复默认配置 ===")
    
    db_manager = get_database_manager()
    
    default_configs = [
        ("work_start_hour", "9", "工作开始时间（小时）"),
        ("work_end_hour", "19", "工作结束时间（小时）"),
        ("work_days", "1,2,3,4,5", "工作日（1=周一，7=周日，逗号分隔）"),
    ]
    
    for key, value, description in default_configs:
        success = db_manager.set_system_config(key, value, description)
        print(f"  恢复 {key}: {value} -> {'成功' if success else '失败'}")
    
    return True


def main():
    """主测试函数"""
    print("开始测试工作时间配置功能...")
    
    try:
        # 运行所有测试
        test_config_save_and_load()
        test_business_time_calculator()
        test_timezone_utils()
        test_config_scenarios()
        restore_default_config()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
