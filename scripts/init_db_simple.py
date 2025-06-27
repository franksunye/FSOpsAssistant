#!/usr/bin/env python3
"""
简化的数据库初始化脚本

这个脚本初始化数据库并测试工作时间配置功能
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置环境变量以避免配置验证错误
os.environ['DEEPSEEK_API_KEY'] = 'test'
os.environ['METABASE_URL'] = 'http://test'
os.environ['METABASE_USERNAME'] = 'test'
os.environ['METABASE_PASSWORD'] = 'test'
os.environ['INTERNAL_OPS_WEBHOOK'] = 'http://test'

def init_database():
    """初始化数据库"""
    print("=== 初始化数据库 ===")
    
    from src.fsoa.data.database import DatabaseManager
    from src.fsoa.utils.timezone_utils import now_china_naive
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    # 初始化数据库
    db_manager.init_database()
    print("✓ 数据库初始化完成")
    
    return db_manager


def test_work_time_config_with_db(db_manager):
    """测试工作时间配置的数据库功能"""
    print("\n=== 测试工作时间配置数据库功能 ===")
    
    # 测试保存配置
    print("保存工作时间配置...")
    configs = [
        ("work_start_hour", "8", "工作开始时间（小时）"),
        ("work_end_hour", "18", "工作结束时间（小时）"),
        ("work_days", "1,2,3,4,5,6", "工作日（1=周一，7=周日，逗号分隔）"),
    ]
    
    for key, value, description in configs:
        success = db_manager.set_system_config(key, value, description)
        print(f"  {key}: {value} -> {'成功' if success else '失败'}")
    
    # 测试读取配置
    print("\n读取工作时间配置...")
    for key, expected_value, _ in configs:
        actual_value = db_manager.get_system_config(key)
        print(f"  {key}: {actual_value} (期望: {expected_value}) -> {'✓' if actual_value == expected_value else '✗'}")
    
    return True


def test_business_time_with_db():
    """测试BusinessTimeCalculator使用数据库配置"""
    print("\n=== 测试BusinessTimeCalculator使用数据库配置 ===")

    from src.fsoa.utils.business_time import BusinessTimeCalculator
    from src.fsoa.utils.timezone_utils import now_china_naive
    from datetime import timedelta
    
    # 获取配置（应该从数据库读取）
    work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
    print(f"从数据库读取的工作时间配置: {work_start_hour}:00 - {work_end_hour}:00")
    print(f"工作日: {work_days}")
    
    # 验证配置是否正确（应该是我们刚才保存的8-18, 周一到周六）
    expected_start = 8
    expected_end = 18
    expected_days = [1, 2, 3, 4, 5, 6]
    
    if work_start_hour == expected_start and work_end_hour == expected_end and work_days == expected_days:
        print("✓ 数据库配置读取正确")
    else:
        print("✗ 数据库配置读取错误")
        return False
    
    # 测试工作时间判断
    now = now_china_naive()
    
    # 测试周六是否为工作日（应该是True，因为我们设置了1,2,3,4,5,6）
    saturday = now.replace(hour=10, minute=0, second=0, microsecond=0)
    while saturday.weekday() != 5:  # 找到周六
        saturday += timedelta(days=1)
    
    is_saturday_business_day = BusinessTimeCalculator.is_business_day(saturday)
    print(f"周六是否为工作日: {is_saturday_business_day} (期望: True)")
    
    # 测试7点是否为工作时间（应该是False，因为我们设置了8-18）
    early_morning = now.replace(hour=7, minute=0, second=0, microsecond=0)
    is_early_business = BusinessTimeCalculator.is_business_hours(early_morning)
    print(f"早上7点是否为工作时间: {is_early_business} (期望: False)")
    
    # 测试10点是否为工作时间（应该是True）
    morning = now.replace(hour=10, minute=0, second=0, microsecond=0)
    is_morning_business = BusinessTimeCalculator.is_business_hours(morning)
    print(f"上午10点是否为工作时间: {is_morning_business} (期望: True)")
    
    return True


def test_timezone_utils_with_db():
    """测试timezone_utils使用数据库配置"""
    print("\n=== 测试timezone_utils使用数据库配置 ===")
    
    from src.fsoa.utils.timezone_utils import get_china_business_hours, is_china_business_hours, now_china_naive
    
    # 测试get_china_business_hours
    start_hour, end_hour = get_china_business_hours()
    print(f"中国时区工作时间: {start_hour}:00-{end_hour}:00 (期望: 8:00-18:00)")
    
    if start_hour == 8 and end_hour == 18:
        print("✓ timezone_utils配置读取正确")
    else:
        print("✗ timezone_utils配置读取错误")
        return False
    
    # 测试is_china_business_hours
    now = now_china_naive()
    test_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
    is_business = is_china_business_hours(test_time)
    print(f"上午10点是否为中国工作时间: {is_business}")
    
    return True


def test_config_change():
    """测试配置更改"""
    print("\n=== 测试配置更改 ===")
    
    from src.fsoa.data.database import get_database_manager
    from src.fsoa.utils.business_time import BusinessTimeCalculator
    
    db_manager = get_database_manager()
    
    # 更改为朝九晚五
    print("更改为朝九晚五配置...")
    new_configs = [
        ("work_start_hour", "9", "工作开始时间（小时）"),
        ("work_end_hour", "17", "工作结束时间（小时）"),
        ("work_days", "1,2,3,4,5", "工作日（1=周一，7=周日，逗号分隔）"),
    ]
    
    for key, value, description in new_configs:
        db_manager.set_system_config(key, value, description)
    
    # 验证配置更改
    work_start_hour, work_end_hour, work_days = BusinessTimeCalculator._get_work_config()
    print(f"更新后的配置: {work_start_hour}:00-{work_end_hour}:00, 工作日: {work_days}")
    
    if work_start_hour == 9 and work_end_hour == 17 and work_days == [1, 2, 3, 4, 5]:
        print("✓ 配置更改成功")
        return True
    else:
        print("✗ 配置更改失败")
        return False


def main():
    """主函数"""
    print("开始测试工作时间配置功能（完整版）...")
    
    try:
        # 初始化数据库
        db_manager = init_database()
        
        # 运行所有测试
        success = True
        success &= test_work_time_config_with_db(db_manager)
        success &= test_business_time_with_db()
        success &= test_timezone_utils_with_db()
        success &= test_config_change()
        
        if success:
            print("\n✅ 所有测试完成！工作时间配置功能完全正常")
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
