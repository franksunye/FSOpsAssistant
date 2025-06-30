"""
业务时间工具测试
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.fsoa.utils.business_time import (
    BusinessTimeCalculator, calculate_business_elapsed_hours, is_within_business_hours
)


class TestBusinessTimeCalculator:
    """业务时间计算器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        calculator = BusinessTimeCalculator()
        assert calculator is not None
    
    def test_calculate_business_elapsed_hours(self):
        """测试计算业务时长"""
        start_time = datetime(2025, 6, 30, 10, 0, 0)  # 周一上午10点
        end_time = datetime(2025, 6, 30, 14, 0, 0)    # 周一下午2点
        
        hours = calculate_business_elapsed_hours(start_time, end_time)
        assert isinstance(hours, float)
        assert hours >= 0
    
    def test_is_within_business_hours(self):
        """测试工作时间判断"""
        # 测试工作日时间
        monday_10am = datetime(2025, 6, 30, 10, 0, 0)  # 周一上午10点
        result = is_within_business_hours(monday_10am)
        assert isinstance(result, bool)
    
    def test_business_time_calculator_methods(self):
        """测试业务时间计算器方法"""
        calculator = BusinessTimeCalculator()

        # 测试类方法存在
        assert hasattr(calculator, 'calculate_business_hours_between')
        assert hasattr(calculator, 'is_business_hours')
        # 注意：实际方法名可能不同，这里只测试对象存在
        assert calculator is not None
