"""
业务指标计算模块

计算和分析业务相关的关键指标
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import statistics
from ..data.models import OpportunityInfo, OpportunityStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BusinessMetricsCalculator:
    """业务指标计算器"""
    
    @staticmethod
    def calculate_overdue_rate(opportunities: List[OpportunityInfo]) -> Dict[str, float]:
        """
        计算逾期率
        
        Args:
            opportunities: 商机列表
            
        Returns:
            各状态的逾期率
        """
        if not opportunities:
            return {}
        
        # 按状态分组
        status_groups = defaultdict(list)
        for opp in opportunities:
            status_groups[opp.order_status].append(opp)
        
        overdue_rates = {}
        
        for status, opps in status_groups.items():
            total_count = len(opps)
            overdue_count = sum(1 for opp in opps if opp.is_overdue)
            
            overdue_rate = (overdue_count / total_count * 100) if total_count > 0 else 0
            overdue_rates[status] = round(overdue_rate, 2)
        
        # 计算总体逾期率
        total_opportunities = len(opportunities)
        total_overdue = sum(1 for opp in opportunities if opp.is_overdue)
        overdue_rates["总体"] = round((total_overdue / total_opportunities * 100), 2)
        
        return overdue_rates
    
    @staticmethod
    def calculate_average_processing_time(opportunities: List[OpportunityInfo]) -> Dict[str, float]:
        """
        计算平均处理时长
        
        Args:
            opportunities: 商机列表
            
        Returns:
            各状态的平均处理时长（小时）
        """
        if not opportunities:
            return {}
        
        # 按状态分组
        status_groups = defaultdict(list)
        for opp in opportunities:
            status_groups[opp.order_status].append(opp.elapsed_hours)
        
        avg_times = {}
        
        for status, times in status_groups.items():
            if times:
                avg_time = statistics.mean(times)
                avg_times[status] = round(avg_time, 2)
        
        # 计算总体平均时长
        all_times = [opp.elapsed_hours for opp in opportunities]
        if all_times:
            avg_times["总体"] = round(statistics.mean(all_times), 2)
        
        return avg_times
    
    @staticmethod
    def calculate_org_performance(opportunities: List[OpportunityInfo]) -> Dict[str, Dict[str, Any]]:
        """
        计算组织绩效排名
        
        Args:
            opportunities: 商机列表
            
        Returns:
            各组织的绩效数据
        """
        if not opportunities:
            return {}
        
        # 按组织分组
        org_groups = defaultdict(list)
        for opp in opportunities:
            org_groups[opp.org_name].append(opp)
        
        org_performance = {}
        
        for org_name, org_opps in org_groups.items():
            total_count = len(org_opps)
            overdue_count = sum(1 for opp in org_opps if opp.is_overdue)
            escalation_count = sum(1 for opp in org_opps if opp.escalation_level > 0)
            
            # SLA达成率
            sla_achievement_rate = ((total_count - overdue_count) / total_count * 100) if total_count > 0 else 0
            
            # 平均响应时间
            avg_response_time = statistics.mean([opp.elapsed_hours for opp in org_opps]) if org_opps else 0
            
            # 逾期率
            overdue_rate = (overdue_count / total_count * 100) if total_count > 0 else 0
            
            # 升级率
            escalation_rate = (escalation_count / total_count * 100) if total_count > 0 else 0
            
            org_performance[org_name] = {
                "总任务数": total_count,
                "逾期任务数": overdue_count,
                "升级任务数": escalation_count,
                "SLA达成率": round(sla_achievement_rate, 2),
                "平均响应时间": round(avg_response_time, 2),
                "逾期率": round(overdue_rate, 2),
                "升级率": round(escalation_rate, 2)
            }
        
        return org_performance
    
    @staticmethod
    def calculate_supervisor_workload(opportunities: List[OpportunityInfo]) -> Dict[str, Dict[str, Any]]:
        """
        计算负责人工作量统计
        
        Args:
            opportunities: 商机列表
            
        Returns:
            各负责人的工作量数据
        """
        if not opportunities:
            return {}
        
        # 按负责人分组
        supervisor_groups = defaultdict(list)
        for opp in opportunities:
            supervisor_groups[opp.supervisor_name].append(opp)
        
        supervisor_workload = {}
        
        for supervisor, supervisor_opps in supervisor_groups.items():
            total_count = len(supervisor_opps)
            overdue_count = sum(1 for opp in supervisor_opps if opp.is_overdue)
            
            # 按状态统计
            status_counts = defaultdict(int)
            for opp in supervisor_opps:
                status_counts[opp.order_status] += 1
            
            # 平均处理时间
            avg_processing_time = statistics.mean([opp.elapsed_hours for opp in supervisor_opps]) if supervisor_opps else 0
            
            supervisor_workload[supervisor] = {
                "总任务数": total_count,
                "逾期任务数": overdue_count,
                "逾期率": round((overdue_count / total_count * 100), 2) if total_count > 0 else 0,
                "平均处理时间": round(avg_processing_time, 2),
                "状态分布": dict(status_counts)
            }
        
        return supervisor_workload
    
    @staticmethod
    def calculate_time_distribution(opportunities: List[OpportunityInfo]) -> Dict[str, int]:
        """
        计算逾期时长分布
        
        Args:
            opportunities: 商机列表
            
        Returns:
            时长分布统计
        """
        if not opportunities:
            return {}
        
        # 定义时长区间（小时）
        time_ranges = {
            "0-24小时": (0, 24),
            "1-3天": (24, 72),
            "3-7天": (72, 168),
            "1-2周": (168, 336),
            "2-4周": (336, 672),
            "1个月以上": (672, float('inf'))
        }
        
        distribution = {range_name: 0 for range_name in time_ranges.keys()}
        
        for opp in opportunities:
            elapsed_hours = opp.elapsed_hours
            
            for range_name, (min_hours, max_hours) in time_ranges.items():
                if min_hours <= elapsed_hours < max_hours:
                    distribution[range_name] += 1
                    break
        
        return distribution
    
    @staticmethod
    def calculate_trend_data(opportunities: List[OpportunityInfo], days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """
        计算趋势数据（模拟，实际需要历史数据）
        
        Args:
            opportunities: 当前商机列表
            days: 计算天数
            
        Returns:
            趋势数据
        """
        # 这里是模拟数据，实际应该从历史数据计算
        trend_data = {
            "逾期任务趋势": [],
            "SLA达成率趋势": [],
            "组织绩效趋势": []
        }
        
        # 生成最近几天的模拟趋势数据
        for i in range(days):
            date = datetime.now() - timedelta(days=days-1-i)
            
            # 模拟逾期任务数量趋势
            overdue_count = len([opp for opp in opportunities if opp.is_overdue])
            # 添加一些随机变化
            simulated_overdue = max(0, overdue_count + (i - days//2) * 2)
            
            trend_data["逾期任务趋势"].append({
                "日期": date.strftime("%m-%d"),
                "逾期任务数": simulated_overdue
            })
            
            # 模拟SLA达成率趋势
            total_count = len(opportunities)
            sla_rate = ((total_count - overdue_count) / total_count * 100) if total_count > 0 else 100
            simulated_sla_rate = max(0, min(100, sla_rate + (i - days//2) * 1.5))
            
            trend_data["SLA达成率趋势"].append({
                "日期": date.strftime("%m-%d"),
                "SLA达成率": round(simulated_sla_rate, 2)
            })
        
        return trend_data
    
    @staticmethod
    def generate_summary_report(opportunities: List[OpportunityInfo]) -> Dict[str, Any]:
        """
        生成综合分析报告
        
        Args:
            opportunities: 商机列表
            
        Returns:
            综合报告数据
        """
        calculator = BusinessMetricsCalculator()
        
        report = {
            "基础统计": {
                "总商机数": len(opportunities),
                "逾期商机数": sum(1 for opp in opportunities if opp.is_overdue),
                "升级商机数": sum(1 for opp in opportunities if opp.escalation_level > 0),
                "涉及组织数": len(set(opp.org_name for opp in opportunities)),
                "涉及负责人数": len(set(opp.supervisor_name for opp in opportunities))
            },
            "逾期率分析": calculator.calculate_overdue_rate(opportunities),
            "平均处理时长": calculator.calculate_average_processing_time(opportunities),
            "组织绩效": calculator.calculate_org_performance(opportunities),
            "负责人工作量": calculator.calculate_supervisor_workload(opportunities),
            "时长分布": calculator.calculate_time_distribution(opportunities),
            "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return report
