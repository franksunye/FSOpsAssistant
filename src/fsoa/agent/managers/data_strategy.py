"""
业务数据处理策略

负责管理业务数据的获取、缓存和更新策略
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from ...data.models import OpportunityInfo, OpportunityStatus
from ...data.database import get_db_manager
from ...data.metabase import get_metabase_client
from ...utils.logger import get_logger, log_function_call
from ...utils.config import get_config

logger = get_logger(__name__)


class BusinessDataStrategy:
    """业务数据处理策略"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.metabase_client = get_metabase_client()
        self.config = get_config()
        
        # 配置参数
        self.enable_cache = os.getenv("ENABLE_OPPORTUNITY_CACHE", "true").lower() == "true"
        self.cache_ttl_hours = int(os.getenv("CACHE_TTL_HOURS", "1"))
        self.force_refresh = False  # 强制刷新标志
    
    @log_function_call
    def get_opportunities(self, force_refresh: bool = False) -> List[OpportunityInfo]:
        """
        获取商机数据 - 重构版本：每次都获取全新数据并清空重建缓存

        Args:
            force_refresh: 保留参数以兼容现有调用，但实际上每次都是全新获取

        Returns:
            最新的商机数据列表
        """
        try:
            logger.info("Fetching fresh opportunities from Metabase (full refresh mode)")

            # 每次都从Metabase获取最新数据
            fresh_opportunities = self._get_direct_from_metabase()

            # 清空重建本地缓存（如果启用缓存）
            if self.enable_cache:
                self._full_refresh_cache(fresh_opportunities)

            return fresh_opportunities

        except Exception as e:
            logger.error(f"Failed to get opportunities: {e}")
            # 降级策略：尝试从缓存获取（仅在启用缓存时）
            if self.enable_cache:
                logger.warning("Falling back to cached data due to Metabase failure")
                return self._get_from_cache_only()
            raise
    
    def _full_refresh_cache(self, opportunities: List[OpportunityInfo]) -> None:
        """
        完全刷新缓存 - 清空重建模式

        这个方法实现了真正的"清空重建"：
        1. 清空所有现有缓存数据
        2. 重新插入新的数据
        3. 确保每次都是全新的数据状态

        Args:
            opportunities: 要缓存的商机列表
        """
        try:
            logger.info(f"Starting full cache refresh with {len(opportunities)} opportunities")

            # 使用数据库管理器的新方法进行完全刷新
            success_count = self.db_manager.full_refresh_opportunity_cache(opportunities)

            logger.info(f"Cache fully refreshed: {success_count}/{len(opportunities)} opportunities cached")

        except Exception as e:
            logger.error(f"Failed to perform full cache refresh: {e}")
            # 缓存失败不应该影响主流程，只记录错误
    
    def _get_direct_from_metabase(self) -> List[OpportunityInfo]:
        """直接从Metabase获取数据"""
        try:
            logger.info("Fetching opportunities directly from Metabase")
            # 获取所有需要监控的商机（包括逾期和即将逾期）
            opportunities = self.metabase_client.get_all_monitored_opportunities()

            # 更新逾期信息（已在get_all_monitored_opportunities中处理）
            logger.info(f"Retrieved {len(opportunities)} opportunities from Metabase")
            return opportunities

        except Exception as e:
            logger.error(f"Failed to fetch from Metabase: {e}")
            raise
    
    def _get_from_cache_only(self) -> List[OpportunityInfo]:
        """
        仅从缓存获取数据（降级策略）

        当Metabase不可用时的应急方案，获取最近的缓存数据
        """
        try:
            # 获取所有缓存数据，忽略TTL（应急情况下使用任何可用数据）
            cached_opportunities = self.db_manager.get_cached_opportunities(24 * 7)  # 7天内的缓存
            logger.warning(f"Using fallback cache data: {len(cached_opportunities)} opportunities")
            return cached_opportunities

        except Exception as e:
            logger.error(f"Failed to get fallback cache data: {e}")
            return []
    
    # 移除复杂的缓存更新逻辑，简化为清空重建模式
    # 以下方法已废弃，保留用于向后兼容

    def _update_cache(self, opportunities: List[OpportunityInfo]) -> None:
        """
        更新缓存 - 已废弃

        ⚠️ 此方法已废弃，请使用 _full_refresh_cache()
        保留此方法仅为向后兼容，实际调用 _full_refresh_cache()
        """
        logger.warning("_update_cache() is deprecated, using _full_refresh_cache() instead")
        self._full_refresh_cache(opportunities)

    def _should_partial_refresh(self, cached_opportunities: List[OpportunityInfo]) -> bool:
        """
        判断是否需要部分刷新 - 已废弃

        ⚠️ 此方法已废弃，新的清空重建模式不需要部分刷新判断
        保留此方法仅为向后兼容，始终返回 True
        """
        logger.warning("_should_partial_refresh() is deprecated in full refresh mode")
        return True  # 在清空重建模式下，始终需要刷新
    
    @log_function_call
    def get_overdue_opportunities(self, force_refresh: bool = False) -> List[OpportunityInfo]:
        """获取逾期商机"""
        try:
            all_opportunities = self.get_opportunities(force_refresh)
            overdue_opportunities = [opp for opp in all_opportunities if opp.is_overdue]

            logger.info(f"Found {len(overdue_opportunities)}/{len(all_opportunities)} overdue opportunities")
            return overdue_opportunities

        except Exception as e:
            logger.error(f"Failed to get overdue opportunities: {e}")
            raise

    @log_function_call
    def get_approaching_overdue_opportunities(self, force_refresh: bool = False) -> List[OpportunityInfo]:
        """获取即将逾期的商机"""
        try:
            all_opportunities = self.get_opportunities(force_refresh)
            approaching_opportunities = [opp for opp in all_opportunities if opp.is_approaching_overdue]

            logger.info(f"Found {len(approaching_opportunities)}/{len(all_opportunities)} approaching overdue opportunities")
            return approaching_opportunities

        except Exception as e:
            logger.error(f"Failed to get approaching overdue opportunities: {e}")
            raise

    @log_function_call
    def get_normal_opportunities(self, force_refresh: bool = False) -> List[OpportunityInfo]:
        """获取正常跟进的商机（未逾期且未即将逾期）"""
        try:
            all_opportunities = self.get_opportunities(force_refresh)
            normal_opportunities = [opp for opp in all_opportunities
                                  if not opp.is_overdue and not opp.is_approaching_overdue]

            logger.info(f"Found {len(normal_opportunities)}/{len(all_opportunities)} normal opportunities")
            return normal_opportunities

        except Exception as e:
            logger.error(f"Failed to get normal opportunities: {e}")
            raise
    
    @log_function_call
    def get_opportunities_by_org(self, org_name: str, force_refresh: bool = False) -> List[OpportunityInfo]:
        """按组织获取商机"""
        try:
            all_opportunities = self.get_opportunities(force_refresh)
            org_opportunities = [opp for opp in all_opportunities if opp.org_name == org_name]
            
            logger.info(f"Found {len(org_opportunities)} opportunities for {org_name}")
            return org_opportunities
            
        except Exception as e:
            logger.error(f"Failed to get opportunities for {org_name}: {e}")
            raise
    
    @log_function_call
    def get_escalation_opportunities(self, force_refresh: bool = False) -> List[OpportunityInfo]:
        """获取需要升级的商机"""
        try:
            overdue_opportunities = self.get_overdue_opportunities(force_refresh)
            escalation_opportunities = [opp for opp in overdue_opportunities if opp.escalation_level > 0]

            logger.info(f"Found {len(escalation_opportunities)} opportunities requiring escalation")
            return escalation_opportunities

        except Exception as e:
            logger.error(f"Failed to get escalation opportunities: {e}")
            raise

    @log_function_call
    def get_opportunity_statistics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """获取商机统计信息"""
        try:
            all_opportunities = self.get_opportunities(force_refresh)

            # 分类统计
            overdue_count = sum(1 for opp in all_opportunities if opp.is_overdue)
            approaching_count = sum(1 for opp in all_opportunities if opp.is_approaching_overdue)
            normal_count = len(all_opportunities) - overdue_count - approaching_count
            escalation_count = sum(1 for opp in all_opportunities if opp.escalation_level > 0)

            # 按状态统计
            status_stats = {}
            for opp in all_opportunities:
                status = str(opp.order_status)
                if status not in status_stats:
                    status_stats[status] = {"total": 0, "overdue": 0, "approaching": 0, "normal": 0}

                status_stats[status]["total"] += 1
                if opp.is_overdue:
                    status_stats[status]["overdue"] += 1
                elif opp.is_approaching_overdue:
                    status_stats[status]["approaching"] += 1
                else:
                    status_stats[status]["normal"] += 1

            # 按组织统计
            org_stats = {}
            for opp in all_opportunities:
                org = opp.org_name
                if org not in org_stats:
                    org_stats[org] = {"total": 0, "overdue": 0, "approaching": 0, "normal": 0}

                org_stats[org]["total"] += 1
                if opp.is_overdue:
                    org_stats[org]["overdue"] += 1
                elif opp.is_approaching_overdue:
                    org_stats[org]["approaching"] += 1
                else:
                    org_stats[org]["normal"] += 1

            statistics = {
                "total_opportunities": len(all_opportunities),
                "overdue_count": overdue_count,
                "approaching_overdue_count": approaching_count,
                "normal_count": normal_count,
                "escalation_count": escalation_count,
                "overdue_rate": round(overdue_count / len(all_opportunities) * 100, 2) if all_opportunities else 0,
                "approaching_rate": round(approaching_count / len(all_opportunities) * 100, 2) if all_opportunities else 0,
                "status_breakdown": status_stats,
                "organization_breakdown": org_stats,
                "last_updated": datetime.now()
            }

            logger.info(f"Generated opportunity statistics: {statistics['total_opportunities']} total, "
                       f"{statistics['overdue_count']} overdue, {statistics['approaching_overdue_count']} approaching")
            return statistics

        except Exception as e:
            logger.error(f"Failed to get opportunity statistics: {e}")
            raise
    
    @log_function_call
    def refresh_cache(self) -> Tuple[int, int]:
        """
        手动刷新缓存 - 重构版本：完全清空重建

        Returns:
            (old_count, new_count): 刷新前后的缓存条目数量
        """
        try:
            logger.info("Manual cache refresh initiated (full refresh mode)")

            # 获取刷新前的缓存数量
            old_count = len(self.db_manager.get_cached_opportunities(24 * 7))  # 获取所有缓存

            # 获取最新数据
            fresh_opportunities = self._get_direct_from_metabase()

            # 完全刷新缓存
            if self.enable_cache:
                self._full_refresh_cache(fresh_opportunities)
                new_count = len([opp for opp in fresh_opportunities if opp.should_cache()])
            else:
                new_count = 0

            logger.info(f"Cache refresh completed: {old_count} -> {new_count} entries")
            return old_count, new_count

        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            raise
    
    @log_function_call
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息 - 重构版本：简化统计指标

        在清空重建模式下，不再需要复杂的缓存命中率等指标
        """
        try:
            cached_opportunities = self.db_manager.get_cached_opportunities(24 * 7)  # 7天内

            stats = {
                "total_cached": len(cached_opportunities),
                "cache_enabled": self.enable_cache,
                "cache_mode": "full_refresh",  # 标识为清空重建模式
                "overdue_cached": len([opp for opp in cached_opportunities if opp.is_overdue]),
                "organizations": len(set(opp.org_name for opp in cached_opportunities)),
                "last_refresh": max([opp.last_updated for opp in cached_opportunities], default=None)
            }

            logger.info(f"Cache statistics (full refresh mode): {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {"cache_enabled": self.enable_cache, "cache_mode": "full_refresh"}
    
    def clear_cache(self) -> int:
        """清理缓存"""
        try:
            # 获取当前缓存数量
            cached_opportunities = self.db_manager.get_cached_opportunities(24 * 7)  # 7天内
            count = len(cached_opportunities)

            # 删除缓存记录
            from ...data.database import OpportunityCacheTable
            with self.db_manager.get_session() as session:
                deleted = session.query(OpportunityCacheTable).delete()
                session.commit()

            logger.info(f"Cache cleared: {deleted} records deleted")
            return deleted

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """验证数据一致性"""
        try:
            # 比较缓存数据和Metabase数据
            cached_data = self.db_manager.get_cached_opportunities(self.cache_ttl_hours)
            fresh_data = self._get_direct_from_metabase()
            
            # 简化的一致性检查
            consistency_report = {
                "cached_count": len(cached_data),
                "fresh_count": len(fresh_data),
                "data_consistent": len(cached_data) == len(fresh_data),
                "check_time": datetime.now(),
                "discrepancies": []
            }
            
            logger.info(f"Data consistency check: {consistency_report}")
            return consistency_report
            
        except Exception as e:
            logger.error(f"Failed to validate data consistency: {e}")
            return {"error": str(e)}
    
    @property
    def cache_enabled(self) -> bool:
        """缓存是否启用"""
        return self.enable_cache
    
    @property
    def cache_ttl(self) -> int:
        """缓存TTL（小时）"""
        return self.cache_ttl_hours
