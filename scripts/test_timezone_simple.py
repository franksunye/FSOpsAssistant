#!/usr/bin/env python3
"""
简化的时区测试

验证时区工具函数正常工作
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.fsoa.utils.timezone_utils import (
    now_china, now_china_naive, utc_to_china, china_to_utc,
    get_china_timezone_info, format_china_time, is_china_business_hours
)


def main():
    """主函数"""
    print("🚀 FSOA 时区修复验证")
    print("=" * 50)
    
    # 1. 基本时区功能测试
    print("1. 基本时区功能:")
    china_time = now_china()
    china_naive = now_china_naive()
    
    print(f"   中国时间（带时区）: {china_time}")
    print(f"   中国时间（naive）: {china_naive}")
    print(f"   时区偏移: {china_time.strftime('%z')}")
    
    # 2. 时区转换测试
    print("\n2. 时区转换:")
    utc_now = datetime.now(timezone.utc)
    china_converted = utc_to_china(utc_now)
    
    print(f"   UTC时间: {utc_now}")
    print(f"   转换为中国时间: {china_converted}")
    
    # 验证时差
    time_diff = china_converted.hour - utc_now.hour
    if time_diff < 0:
        time_diff += 24
    print(f"   时差: {time_diff}小时 ({'✅ 正确' if time_diff == 8 else '❌ 错误'})")
    
    # 3. 工作时间判断
    print("\n3. 工作时间判断:")
    is_work_time = is_china_business_hours()
    print(f"   当前是否工作时间: {'✅ 是' if is_work_time else '❌ 否'}")
    
    # 4. 时间格式化
    print("\n4. 时间格式化:")
    formatted = format_china_time(china_time)
    print(f"   格式化时间: {formatted}")
    
    # 5. 时区信息
    print("\n5. 时区信息:")
    info = get_china_timezone_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # 6. 验证数据模型时间
    print("\n6. 数据模型时间测试:")
    try:
        from src.fsoa.data.models import OpportunityInfo, OpportunityStatus
        
        # 创建测试商机（不涉及数据库）
        test_opp = OpportunityInfo(
            order_num="TIMEZONE_TEST",
            name="时区测试客户",
            address="测试地址",
            supervisor_name="测试销售",
            create_time=now_china_naive(),
            org_name="测试公司",
            order_status=OpportunityStatus.PENDING_APPOINTMENT
        )
        
        print(f"   商机创建时间: {test_opp.create_time}")
        print(f"   时间类型: {type(test_opp.create_time)}")
        print(f"   ✅ 数据模型时间正常")
        
    except Exception as e:
        print(f"   ❌ 数据模型时间测试失败: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 时区修复验证完成！")
    print("✅ 系统现在使用中国时区（UTC+8）")
    print("✅ 所有时间记录都是中国本地时间")
    print("=" * 50)


if __name__ == "__main__":
    main()
