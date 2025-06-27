"""
任务调度器模块

使用APScheduler实现定时任务调度
"""

import atexit
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.config = get_config()
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self._is_running = False
        
        # 注册退出时停止调度器
        atexit.register(self.shutdown)
    
    def start(self):
        """启动调度器"""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Task scheduler started")
    
    def shutdown(self):
        """停止调度器"""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Task scheduler stopped")
    
    def add_interval_job(self, func: Callable, interval_minutes: int, 
                        job_id: str = None, **kwargs) -> str:
        """
        添加间隔任务
        
        Args:
            func: 要执行的函数
            interval_minutes: 间隔分钟数
            job_id: 任务ID
            **kwargs: 其他参数
            
        Returns:
            任务ID
        """
        if not job_id:
            job_id = f"{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        trigger = IntervalTrigger(minutes=interval_minutes)
        
        job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        
        logger.info(f"Added interval job: {job_id}, interval: {interval_minutes} minutes")
        return job.id
    
    def add_cron_job(self, func: Callable, cron_expression: str, 
                     job_id: str = None, **kwargs) -> str:
        """
        添加Cron任务
        
        Args:
            func: 要执行的函数
            cron_expression: Cron表达式
            job_id: 任务ID
            **kwargs: 其他参数
            
        Returns:
            任务ID
        """
        if not job_id:
            job_id = f"{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 解析Cron表达式
        parts = cron_expression.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
        else:
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        
        logger.info(f"Added cron job: {job_id}, cron: {cron_expression}")
        return job.id
    
    def remove_job(self, job_id: str) -> bool:
        """
        移除任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def get_jobs(self) -> Dict[str, Any]:
        """获取所有任务信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "func": job.func.__name__,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })

        # 检测调度器的实际运行状态
        # APScheduler的状态：0=停止, 1=运行, 2=暂停
        actual_running = self.scheduler.state == 1

        return {
            "total_jobs": len(jobs),
            "is_running": actual_running,  # 使用实际状态而不是内部标志
            "jobs": jobs
        }
    
    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def _job_listener(self, event):
        """任务执行监听器"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} executed successfully")


# 全局调度器实例
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


def setup_agent_scheduler():
    """设置Agent定时任务"""
    from ..agent.orchestrator import AgentOrchestrator
    
    scheduler = get_scheduler()
    config = get_config()
    
    # 创建Agent实例
    agent = AgentOrchestrator()
    
    # 添加定时任务
    interval_minutes = config.agent_execution_interval
    job_id = scheduler.add_interval_job(
        func=agent.execute,
        interval_minutes=interval_minutes,
        job_id="agent_execution",
        max_instances=1  # 确保同时只有一个实例运行
    )
    
    logger.info(f"Agent scheduler setup completed, job_id: {job_id}")
    return job_id


def start_scheduler():
    """启动调度器"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """停止调度器"""
    scheduler = get_scheduler()
    scheduler.shutdown()
