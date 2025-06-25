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
        """获取商机数据 - 统一入口"""
        try:
            self.force_refresh = force_refresh
            
            if self.enable_cache and not force_refresh:
                return self._get_with_cache()
            else:
                return self._get_direct_from_metabase()
                
        except Exception as e:
            logger.error(f"Failed to get opportunities: {e}")
            # 降级策略：尝试从缓存获取
            if self.enable_cache:
                logger.info("Falling back to cached data")
                return self._get_from_cache_only()
            raise
    
    def _get_with_cache(self) -> List[OpportunityInfo]:
        """使用缓存策略获取数据"""
        try:
            # 1. 先尝试从缓存获取有效数据
            cached_opportunities = self.db_manager.get_cached_opportunities(self.cache_ttl_hours)
            
            if cached_opportunities:
                logger.info(f"Retrieved {len(cached_opportunities)} opportunities from cache")
                
                # 检查是否需要部分刷新
                if self._should_partial_refresh(cached_opportunities):
                    fresh_opportunities = self._get_direct_from_metabase()
                    self._update_cache(fresh_opportunities)
                    return fresh_opportunities
                
                return cached_opportunities
            
            # 2. 缓存为空或过期，从Metabase获取
            logger.info("Cache miss or expired, fetching from Metabase")
            fresh_opportunities = self._get_direct_from_metabase()
            
            # 3. 更新缓存
            self._update_cache(fresh_opportunities)
            
            return fresh_opportunities
            
        except Exception as e:
            logger.error(f"Failed to get opportunities with cache: {e}")
            raise
    
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
        """仅从缓存获取数据（降级策略）"""
        try:
            # 获取所有缓存数据，忽略TTL
            cached_opportunities = self.db_manager.get_cached_opportunities(24 * 7)  # 7天内的缓存
            logger.warning(f"Using fallback cache data: {len(cached_opportunities)} opportunities")
            return cached_opportunities
            
        except Exception as e:
            logger.error(f"Failed to get fallback cache data: {e}")
            return []
    
    def _update_cache(self, opportunities: List[OpportunityInfo]) -> None:
        """更新缓存"""
        try:
            cached_count = 0
            
            for opp in opportunities:
                # 只缓存需要缓存的商机
                if opp.should_cache():
                    success = self.db_manager.save_opportunity_cache(opp)
                    if success:
                        cached_count += 1
            
            logger.info(f"Updated cache with {cached_count}/{len(opportunities)} opportunities")
            
        except Exception as e:
            logger.error(f"Failed to update cache: {e}")
    
    def _should_partial_refresh(self, cached_opportunities: List[OpportunityInfo]) -> bool:
        """判断是否需要部分刷新"""
        try:
            # 检查缓存数据的新鲜度
            now = datetime.now()
            old_data_count = 0
            
            for opp in cached_opportunities:
                if opp.last_updated:
                    age_hours = (now - opp.last_updated).total_seconds() / 3600
                    if age_hours > self.cache_ttl_hours * 0.8:  # 超过80%的TTL
                        old_data_count += 1
            
            # 如果超过50%的数据较旧，则刷新
            refresh_threshold = len(cached_opportunities) * 0.5
            should_refresh = old_data_count > refresh_threshold
            
            if should_refresh:
                logger.info(f"Partial refresh needed: {old_data_count}/{len(cached_opportunities)} old entries")
            
            return should_refresh
            
        except Exception as e:
            logger.error(f"Failed to check partial refresh: {e}")
            return False
    
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
        """手动刷新缓存"""
        try:
            logger.info("Manual cache refresh initiated")
            
            # 获取最新数据
            fresh_opportunities = self._get_direct_from_metabase()
            
            # 更新缓存
            old_count = len(self.db_manager.get_cached_opportunities(24 * 7))  # 获取所有缓存
            self._update_cache(fresh_opportunities)
            new_count = len([opp for opp in fresh_opportunities if opp.should_cache()])
            
            logger.info(f"Cache refresh completed: {old_count} -> {new_count} entries")
            return old_count, new_count
            
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            raise
    
    @log_function_call
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            cached_opportunities = self.db_manager.get_cached_opportunities(24 * 7)  # 7天内
            valid_cache = self.db_manager.get_cached_opportunities(self.cache_ttl_hours)
            
            stats = {
                "total_cached": len(cached_opportunities),
                "valid_cached": len(valid_cache),
                "cache_ttl_hours": self.cache_ttl_hours,
                "cache_enabled": self.enable_cache,
                "cache_hit_ratio": len(valid_cache) / max(len(cached_opportunities), 1),
                "overdue_cached": len([opp for opp in cached_opportunities if opp.is_overdue]),
                "organizations": len(set(opp.org_name for opp in cached_opportunities))
            }
            
            logger.info(f"Cache statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {}
    
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
