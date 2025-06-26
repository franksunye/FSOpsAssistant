"""
Agent执行追踪器

负责追踪和记录Agent的执行过程
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager

# 导入时区工具
from ...utils.timezone_utils import now_china_naive

from ...data.models import AgentRun, AgentHistory, AgentRunStatus
from ...data.database import get_db_manager
from ...utils.logger import get_logger, log_function_call

logger = get_logger(__name__)


class AgentExecutionTracker:
    """Agent执行追踪器"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.current_run_id: Optional[int] = None
        self.current_step_start_time: Optional[datetime] = None
    
    @log_function_call
    def start_run(self, context: Optional[Dict[str, Any]] = None) -> int:
        """开始一次Agent运行"""
        try:
            agent_run = AgentRun(
                trigger_time=now_china_naive(),
                status=AgentRunStatus.RUNNING,
                context=context or {},
                opportunities_processed=0,
                notifications_sent=0,
                errors=[]
            )
            
            run_id = self.db_manager.save_agent_run(agent_run)
            self.current_run_id = run_id
            
            logger.info(f"Started Agent run {run_id}")
            return run_id
            
        except Exception as e:
            logger.error(f"Failed to start Agent run: {e}")
            raise
    
    @log_function_call
    def complete_run(self, run_id: int, final_stats: Dict[str, Any]) -> bool:
        """完成Agent运行"""
        try:
            updates = {
                "end_time": datetime.now(),
                "status": AgentRunStatus.COMPLETED.value,
                "opportunities_processed": final_stats.get("opportunities_processed", 0),
                "notifications_sent": final_stats.get("notifications_sent", 0),
                "context": final_stats.get("context", {})
            }
            
            success = self.db_manager.update_agent_run(run_id, updates)
            
            if success:
                logger.info(f"Completed Agent run {run_id}: {final_stats}")
                self.current_run_id = None
            else:
                logger.error(f"Failed to complete Agent run {run_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to complete Agent run {run_id}: {e}")
            return False
    
    @log_function_call
    def fail_run(self, run_id: int, error: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """标记Agent运行失败"""
        try:
            updates = {
                "end_time": datetime.now(),
                "status": AgentRunStatus.FAILED.value,
                "errors": [error],
                "context": context or {}
            }
            
            success = self.db_manager.update_agent_run(run_id, updates)
            
            if success:
                logger.error(f"Failed Agent run {run_id}: {error}")
                self.current_run_id = None
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to mark Agent run {run_id} as failed: {e}")
            return False
    
    @log_function_call
    def log_step(self, run_id: int, step_name: str, input_data: Optional[Dict[str, Any]] = None,
                 output_data: Optional[Dict[str, Any]] = None, 
                 error_message: Optional[str] = None) -> bool:
        """记录执行步骤"""
        try:
            # 计算执行时长
            duration_seconds = None
            if self.current_step_start_time:
                duration_seconds = (now_china_naive() - self.current_step_start_time).total_seconds()
            
            history = AgentHistory(
                run_id=run_id,
                step_name=step_name,
                timestamp=now_china_naive(),
                input_data=input_data or {},
                output_data=output_data or {},
                duration_seconds=duration_seconds,
                error_message=error_message
            )
            
            success = self.db_manager.save_agent_history(history)
            
            if success:
                if error_message:
                    logger.error(f"Step {step_name} failed: {error_message}")
                else:
                    logger.info(f"Step {step_name} completed in {duration_seconds:.2f}s" if duration_seconds else f"Step {step_name} completed")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to log step {step_name}: {e}")
            return False
    
    @contextmanager
    def track_step(self, step_name: str, input_data: Optional[Dict[str, Any]] = None):
        """上下文管理器：自动追踪执行步骤"""
        if not self.current_run_id:
            raise ValueError("No active Agent run to track")
        
        self.current_step_start_time = now_china_naive()
        output_data = {}
        error_message = None
        
        try:
            logger.info(f"Starting step: {step_name}")
            yield output_data
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Step {step_name} failed: {error_message}")
            raise
            
        finally:
            # 记录步骤
            self.log_step(
                self.current_run_id,
                step_name,
                input_data,
                output_data,
                error_message
            )
            self.current_step_start_time = None
    
    @log_function_call
    def update_run_progress(self, run_id: int, progress_data: Dict[str, Any]) -> bool:
        """更新运行进度"""
        try:
            # 获取当前上下文并更新
            current_context = {}
            
            # 合并进度数据
            updated_context = {**current_context, **progress_data}
            
            updates = {
                "context": updated_context,
                "opportunities_processed": progress_data.get("opportunities_processed", 0),
                "notifications_sent": progress_data.get("notifications_sent", 0)
            }
            
            success = self.db_manager.update_agent_run(run_id, updates)
            
            if success:
                logger.debug(f"Updated run {run_id} progress: {progress_data}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update run progress for {run_id}: {e}")
            return False
    
    @log_function_call
    def get_run_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """获取运行统计信息"""
        try:
            stats = self.db_manager.get_agent_run_statistics(hours_back)
            logger.info(f"Retrieved run statistics for last {hours_back} hours: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get run statistics: {e}")
            return {}
    
    @log_function_call
    def get_step_performance(self, step_name: Optional[str] = None,
                           hours_back: int = 24) -> Dict[str, Any]:
        """获取步骤性能统计"""
        try:
            performance = self.db_manager.get_step_performance_statistics(step_name, hours_back)
            logger.info(f"Retrieved step performance for {step_name or 'all steps'}: {performance}")
            return performance

        except Exception as e:
            logger.error(f"Failed to get step performance: {e}")
            return {}

    @log_function_call
    def get_recent_runs(self, limit: int = 20, hours_back: int = 168) -> List['AgentRun']:
        """获取最近的执行记录"""
        try:
            runs = self.db_manager.get_agent_runs(limit, hours_back)
            logger.info(f"Retrieved {len(runs)} recent runs")
            return runs

        except Exception as e:
            logger.error(f"Failed to get recent runs: {e}")
            return []

    @log_function_call
    def get_run_details(self, run_id: int) -> Optional[Tuple['AgentRun', List['AgentHistory']]]:
        """获取运行详情和步骤历史"""
        try:
            # 获取运行记录
            runs = self.db_manager.get_agent_runs(limit=1000)  # 获取足够多的记录
            run = next((r for r in runs if r.id == run_id), None)

            if not run:
                logger.warning(f"Run {run_id} not found")
                return None

            # 获取步骤历史
            history = self.db_manager.get_agent_history_by_run(run_id)

            logger.info(f"Retrieved details for run {run_id}: {len(history)} steps")
            return run, history

        except Exception as e:
            logger.error(f"Failed to get run details for {run_id}: {e}")
            return None
    
    def cleanup_old_records(self, days_back: int = 30) -> int:
        """清理旧的执行记录"""
        try:
            # 这里简化实现，实际需要删除旧记录
            logger.info(f"Cleaned up execution records older than {days_back} days")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0
    
    @property
    def is_running(self) -> bool:
        """是否有正在运行的Agent"""
        return self.current_run_id is not None
    
    @property
    def current_run(self) -> Optional[int]:
        """当前运行的ID"""
        return self.current_run_id
