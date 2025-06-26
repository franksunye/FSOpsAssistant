"""
Agent编排器模块

基于LangGraph实现Agent工作流编排
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from ..data.models import (
    # 推荐的模型
    AgentExecution, AgentStatus, DecisionResult, OpportunityInfo, NotificationTask, Priority,
    # 废弃的模型（仅用于兼容性）
    TaskInfo
)
from ..data.database import get_db_manager
from ..utils.logger import get_logger, log_agent_step
from ..utils.config import get_config
from .tools import (
    # 推荐的工具函数
    fetch_overdue_opportunities, get_all_opportunities,
    create_notification_tasks, execute_notification_tasks,
    start_agent_execution, complete_agent_execution,
    get_data_statistics, refresh_business_data,
    # 管理器
    get_data_strategy, get_notification_manager, get_execution_tracker,
    # 废弃的兼容性函数（存在任务-商机概念混淆）
    fetch_overdue_tasks, send_notification, send_business_notifications, update_task_status
)
from .decision import create_decision_engine
from .llm import get_deepseek_client

logger = get_logger(__name__)


class AgentState(TypedDict):
    """Agent状态定义 - 重构后使用新的数据模型"""
    execution_id: str
    run_id: int  # Agent运行ID
    start_time: datetime
    opportunities: List[OpportunityInfo]  # 使用商机而不是任务
    processed_opportunities: List[OpportunityInfo]
    notification_tasks: List[NotificationTask]  # 通知任务
    notifications_sent: int
    errors: List[str]
    current_opportunity: Optional[OpportunityInfo]
    decision_result: Optional[DecisionResult]
    context: Dict[str, Any]

    # 兼容性字段
    tasks: Optional[List[TaskInfo]]  # 保持向后兼容
    processed_tasks: Optional[List[TaskInfo]]
    current_task: Optional[TaskInfo]


class AgentOrchestrator:
    """Agent编排器 - 重构后使用新的管理器架构"""

    def __init__(self):
        self.config = get_config()
        self.db_manager = get_db_manager()
        self.decision_engine = create_decision_engine()

        # 新的管理器
        self.data_strategy = get_data_strategy()
        self.notification_manager = get_notification_manager()
        self.execution_tracker = get_execution_tracker()

        self.graph = self._build_graph()
        
    def _build_graph(self):
        """构建Agent执行图 - 符合架构设计的6步流程"""
        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加节点 - 按照架构设计的6个核心流程
        workflow.add_node("fetch_data", self._fetch_data_node)           # 2. 获取任务数据
        workflow.add_node("analyze_status", self._analyze_status_node)   # 3. 分析超时状态
        workflow.add_node("make_decision", self._make_decision_node)     # 4. 智能决策
        workflow.add_node("send_notifications", self._send_notification_node)  # 5. 发送通知
        workflow.add_node("record_results", self._record_results_node)   # 6. 记录结果

        # 设置入口点
        workflow.set_entry_point("fetch_data")

        # 添加边 - 线性流程，符合架构设计
        workflow.add_edge("fetch_data", "analyze_status")
        workflow.add_conditional_edges(
            "analyze_status",
            self._should_continue_processing,
            {
                "continue": "make_decision",
                "skip": "record_results"
            }
        )
        workflow.add_edge("make_decision", "send_notifications")
        workflow.add_edge("send_notifications", "record_results")
        workflow.add_edge("record_results", END)

        return workflow.compile()
    
    def execute(self, dry_run: bool = False, force_refresh: bool = False) -> AgentExecution:
        """
        执行Agent工作流 - 重构版本使用新管理器

        Args:
            dry_run: 是否为试运行
            force_refresh: 是否强制刷新数据

        Returns:
            执行结果
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()

        logger.info(f"Starting Agent execution: {execution_id} (dry_run={dry_run})")

        # 使用新的执行追踪器
        context = {
            "dry_run": dry_run,
            "force_refresh": force_refresh,
            "execution_id": execution_id,
            "orchestrator_version": "v2.0"
        }

        try:
            # 开始Agent执行
            run_id = self.execution_tracker.start_run(context)

            # 初始化状态
            initial_state = AgentState(
                execution_id=execution_id,
                run_id=run_id,
                start_time=start_time,
                opportunities=[],
                processed_opportunities=[],
                notification_tasks=[],
                notifications_sent=0,
                errors=[],
                current_opportunity=None,
                decision_result=None,
                context=context,
                # 兼容性字段
                tasks=[],
                processed_tasks=[],
                current_task=None
            )

            # 创建执行记录（兼容性）
            execution = AgentExecution(
                id=execution_id,
                start_time=start_time,
                status=AgentStatus.RUNNING
            )

            # 执行记录现在通过 AgentExecutionTracker 管理，不再使用废弃的 save_agent_execution

            # 执行工作流
            final_state = self.graph.invoke(initial_state)

            # 完成执行
            final_stats = {
                "opportunities_processed": len(final_state.get("processed_opportunities", [])),
                "notifications_sent": final_state.get("notifications_sent", 0),
                "notification_tasks_created": len(final_state.get("notification_tasks", [])),
                "errors_count": len(final_state.get("errors", [])),
                "context": final_state.get("context", {})
            }

            success = self.execution_tracker.complete_run(run_id, final_stats)

            # 更新执行结果（兼容性）
            execution.end_time = datetime.now()
            execution.status = AgentStatus.IDLE if success else AgentStatus.ERROR
            execution.tasks_processed = len(final_state.get("processed_opportunities", []))
            execution.notifications_sent = final_state["notifications_sent"]
            execution.errors = final_state["errors"]
            execution.context = final_state["context"]
            
            logger.info(f"Agent execution completed: {execution_id}")
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            execution.end_time = datetime.now()
            execution.status = AgentStatus.ERROR
            execution.errors = [str(e)]
            
        finally:
            # 执行结果现在通过 AgentExecutionTracker 管理，不再使用废弃的 save_agent_execution
            pass
        
        return execution
    
    def _fetch_data_node(self, state: AgentState) -> AgentState:
        """2. 获取任务数据 - 从Metabase获取商机数据"""
        run_id = state["run_id"]

        # 使用执行追踪器记录步骤
        with self.execution_tracker.track_step("fetch_data", {"run_id": run_id}) as output:
            try:
                # 使用新的数据策略获取商机
                force_refresh = state["context"].get("force_refresh", False)
                opportunities = self.data_strategy.get_overdue_opportunities(force_refresh)

                # 更新状态
                state["opportunities"] = opportunities
                state["context"]["total_opportunities"] = len(opportunities)
                state["context"]["use_business_flow"] = True

                # 输出数据
                output["opportunity_count"] = len(opportunities)
                output["overdue_count"] = len([opp for opp in opportunities if opp.is_overdue])
                output["escalation_count"] = len([opp for opp in opportunities if opp.escalation_level > 0])
                output["organizations"] = len(set(opp.org_name for opp in opportunities))

                logger.info(f"Fetched {len(opportunities)} overdue opportunities from {output['organizations']} organizations")

                # 向后兼容：尝试获取传统任务
                try:
                    # tasks = fetch_overdue_tasks()  # 已禁用旧系统
                    # state["tasks"] = []  # 已禁用旧系统
                    state["context"]["total_tasks"] = len(tasks)
                    output["legacy_task_count"] = len(tasks)
                    logger.info(f"Also fetched {len(tasks)} legacy tasks for compatibility")
                except Exception as e:
                    logger.warning(f"Failed to fetch legacy tasks (this is expected): {e}")
                    state["tasks"] = []
                    state["context"]["total_tasks"] = 0
                    output["legacy_task_count"] = 0

            except Exception as e:
                error_msg = f"Failed to fetch opportunities: {e}"
                state["errors"].append(error_msg)
                output["error"] = error_msg
                logger.error(error_msg)

                # 降级策略：尝试从缓存获取
                try:
                    cached_opportunities = self.data_strategy.get_cached_opportunities()
                    if cached_opportunities:
                        state["opportunities"] = cached_opportunities
                        state["context"]["total_opportunities"] = len(cached_opportunities)
                        state["context"]["use_cached_data"] = True
                        output["fallback_to_cache"] = True
                        output["cached_opportunity_count"] = len(cached_opportunities)
                        logger.warning(f"Using {len(cached_opportunities)} cached opportunities as fallback")
                    else:
                        state["opportunities"] = []
                        state["context"]["total_opportunities"] = 0
                        output["fallback_failed"] = True
                except Exception as cache_error:
                    logger.error(f"Cache fallback also failed: {cache_error}")
                    state["opportunities"] = []
                    state["context"]["total_opportunities"] = 0

        return state

    def _analyze_status_node(self, state: AgentState) -> AgentState:
        """3. 分析超时状态 - 分析商机的超时状态和优先级"""
        run_id = state["run_id"]

        with self.execution_tracker.track_step("analyze_status", {"run_id": run_id}) as output:
            try:
                opportunities = state.get("opportunities", [])

                if not opportunities:
                    output["message"] = "No opportunities to analyze"
                    logger.info("No opportunities to analyze")
                    return state

                # 分析超时状态
                overdue_opportunities = [opp for opp in opportunities if opp.is_overdue]
                escalation_opportunities = [opp for opp in opportunities if opp.escalation_level > 0]

                # 按组织分组
                org_stats = {}
                for opp in opportunities:
                    if opp.org_name not in org_stats:
                        org_stats[opp.org_name] = {"total": 0, "overdue": 0, "escalation": 0}
                    org_stats[opp.org_name]["total"] += 1
                    if opp.is_overdue:
                        org_stats[opp.org_name]["overdue"] += 1
                    if opp.escalation_level > 0:
                        org_stats[opp.org_name]["escalation"] += 1

                # 更新状态
                state["context"]["analysis_result"] = {
                    "total_opportunities": len(opportunities),
                    "overdue_count": len(overdue_opportunities),
                    "escalation_count": len(escalation_opportunities),
                    "organization_stats": org_stats
                }

                # 输出统计
                output.update(state["context"]["analysis_result"])

                logger.info(f"Analyzed {len(opportunities)} opportunities: {len(overdue_opportunities)} overdue, {len(escalation_opportunities)} need escalation")

            except Exception as e:
                error_msg = f"Failed to analyze status: {e}"
                state["errors"].append(error_msg)
                output["error"] = error_msg
                logger.error(error_msg)

        return state

    def _make_decision_node(self, state: AgentState) -> AgentState:
        """4. 智能决策 - 基于规则+LLM的混合决策"""
        run_id = state["run_id"]

        with self.execution_tracker.track_step("make_decision", {"run_id": run_id}) as output:
            try:
                opportunities = state.get("opportunities", [])

                if not opportunities:
                    output["message"] = "No opportunities for decision making"
                    logger.info("No opportunities for decision making")
                    return state

                # 创建通知任务（包含决策逻辑）
                notification_tasks = self.notification_manager.create_notification_tasks(
                    opportunities, run_id
                )

                state["notification_tasks"] = notification_tasks
                state["processed_opportunities"] = opportunities.copy()

                # 输出决策结果
                output["notification_tasks_created"] = len(notification_tasks)
                output["standard_tasks"] = len([t for t in notification_tasks if t.notification_type.value == "standard"])
                output["escalation_tasks"] = len([t for t in notification_tasks if t.notification_type.value == "escalation"])

                logger.info(f"Decision made: created {len(notification_tasks)} notification tasks")

            except Exception as e:
                error_msg = f"Failed to make decision: {e}"
                state["errors"].append(error_msg)
                output["error"] = error_msg
                logger.error(error_msg)

        return state

    def _process_task_node(self, state: AgentState) -> AgentState:
        """处理任务节点 - 重构版本处理商机和通知任务"""
        run_id = state["run_id"]

        # 使用执行追踪器记录步骤
        with self.execution_tracker.track_step("process_opportunities", {"run_id": run_id}) as output:
            try:
                opportunities = state.get("opportunities", [])

                if not opportunities:
                    output["message"] = "No opportunities to process"
                    logger.info("No opportunities to process")
                    return state

                # 创建通知任务
                notification_tasks = self.notification_manager.create_notification_tasks(
                    opportunities, run_id
                )

                state["notification_tasks"] = notification_tasks
                state["processed_opportunities"] = opportunities.copy()

                # 输出统计
                output["opportunities_processed"] = len(opportunities)
                output["notification_tasks_created"] = len(notification_tasks)
                output["standard_tasks"] = len([t for t in notification_tasks if t.notification_type.value == "standard"])
                output["escalation_tasks"] = len([t for t in notification_tasks if t.notification_type.value == "escalation"])

                logger.info(f"Processed {len(opportunities)} opportunities, created {len(notification_tasks)} notification tasks")

                # 向后兼容：处理传统任务
                remaining_tasks = [
                    task for task in state.get("tasks", [])
                    if task not in state.get("processed_tasks", [])
                ]

                if remaining_tasks:
                    current_task = remaining_tasks[0]
                    state["current_task"] = current_task
                    output["legacy_task_id"] = current_task.id
                    output["legacy_task_title"] = current_task.title
                    logger.info(f"Also processing legacy task: {current_task.title}")
                else:
                    state["current_task"] = None
                    output["legacy_tasks_remaining"] = 0

            except Exception as e:
                error_msg = f"Failed to process opportunities: {e}"
                state["errors"].append(error_msg)
                output["error"] = error_msg
                logger.error(error_msg)

        return state
    
    def _record_results_node(self, state: AgentState) -> AgentState:
        """6. 记录结果 - 记录执行结果和统计信息"""
        run_id = state["run_id"]

        with self.execution_tracker.track_step("record_results", {"run_id": run_id}) as output:
            try:
                # 统计执行结果
                opportunities = state.get("opportunities", [])
                processed_opportunities = state.get("processed_opportunities", [])
                notification_tasks = state.get("notification_tasks", [])
                notifications_sent = state.get("notifications_sent", 0)
                errors = state.get("errors", [])

                # 记录最终统计
                final_stats = {
                    "total_opportunities": len(opportunities),
                    "processed_opportunities": len(processed_opportunities),
                    "notification_tasks_created": len(notification_tasks),
                    "notifications_sent": notifications_sent,
                    "errors_count": len(errors),
                    "success_rate": (notifications_sent / len(notification_tasks)) if notification_tasks else 1.0
                }

                state["context"]["final_stats"] = final_stats
                output.update(final_stats)

                # 记录到日志
                logger.info(f"Execution completed: {final_stats}")

                # 向后兼容：记录传统任务统计
                legacy_tasks = state.get("tasks", [])
                processed_tasks = state.get("processed_tasks", [])
                output["legacy_tasks_total"] = len(legacy_tasks)
                output["legacy_tasks_processed"] = len(processed_tasks)

            except Exception as e:
                error_msg = f"Failed to record results: {e}"
                state["errors"].append(error_msg)
                output["error"] = error_msg
                logger.error(error_msg)

        return state
    
    def _send_notification_node(self, state: AgentState) -> AgentState:
        """发送通知节点 - 重构版本使用新的通知管理器"""
        run_id = state["run_id"]

        # 使用执行追踪器记录步骤
        with self.execution_tracker.track_step("send_notifications", {"run_id": run_id}) as output:
            try:
                # 检查是否为试运行
                if state["context"].get("dry_run", False):
                    logger.info("DRY RUN: Would execute notification tasks")
                    # 模拟执行结果
                    notification_tasks = state.get("notification_tasks", [])
                    result = {
                        "total_tasks": len(notification_tasks),
                        "sent_count": len(notification_tasks),
                        "failed_count": 0,
                        "escalated_count": len([t for t in notification_tasks if t.notification_type.value == "escalation"]),
                        "errors": []
                    }
                    output.update(result)
                    state["notifications_sent"] = result["sent_count"]
                    logger.info(f"DRY RUN: Simulated sending {result['sent_count']} notifications")
                else:
                    # 执行实际的通知任务
                    result = self.notification_manager.execute_pending_tasks(run_id)

                    # 转换结果格式
                    result_dict = {
                        "total_tasks": result.total_tasks,
                        "sent_count": result.sent_count,
                        "failed_count": result.failed_count,
                        "escalated_count": result.escalated_count,
                        "errors": result.errors
                    }

                    output.update(result_dict)
                    state["notifications_sent"] = result.sent_count

                    if result.errors:
                        state["errors"].extend(result.errors)

                    logger.info(f"Executed notifications: {result.sent_count} sent, {result.failed_count} failed")

                # 向后兼容：处理传统任务通知
                current_task = state.get("current_task")
                decision = state.get("decision_result")

                if current_task and decision and decision.action in ["notify", "escalate"]:
                    try:
                        if state["context"].get("dry_run", False):
                            logger.info(f"DRY RUN: Would send legacy notification for task {current_task.id}")
                            legacy_success = True
                        else:
                            # 发送传统通知
                            message = decision.message or f"任务 {current_task.id} 需要关注"
                            legacy_success = send_notification(current_task, message, decision.priority)

                        if legacy_success:
                            state["notifications_sent"] += 1
                            output["legacy_notification_sent"] = True
                            logger.info(f"Sent legacy notification for task {current_task.id}")

                    except Exception as e:
                        error_msg = f"Failed to send legacy notification: {e}"
                        state["errors"].append(error_msg)
                        output["legacy_notification_error"] = error_msg
                        logger.error(error_msg)

            except Exception as e:
                error_msg = f"Failed to execute notifications: {e}"
                state["errors"].append(error_msg)
                output["error"] = error_msg
                logger.error(error_msg)


    
    # 移除 _update_status_node - 状态更新已集成到通知管理器中
    
    # _finalize_node 已被 _record_results_node 替代
    
    def _should_continue_processing(self, state: AgentState) -> str:
        """判断是否继续处理 - 基于分析结果决定"""
        opportunities = state.get("opportunities", [])
        analysis_result = state.get("context", {}).get("analysis_result", {})

        # 如果有商机需要处理，继续执行决策
        if opportunities and analysis_result.get("overdue_count", 0) > 0:
            return "continue"
        elif opportunities:
            # 有商机但没有超时的，也继续处理（可能有其他需要通知的情况）
            return "continue"
        else:
            # 没有商机，跳过后续处理
            return "skip"
    
    def get_execution_history(self, limit: int = 10) -> List[AgentExecution]:
        """获取执行历史"""
        # 这里需要实现从数据库获取执行历史的逻辑
        # 暂时返回空列表
        return []
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "status": "idle",
            "last_execution": None,
            "next_execution": None,
            "total_executions": 0
        }

    def _send_business_notifications(self, state: AgentState) -> AgentState:
        """发送业务通知（新流程）"""
        opportunities = state["context"].get("opportunities", [])

        if not opportunities:
            log_agent_step(
                "send_business_notifications",
                output_data={"message": "No opportunities to notify"}
            )
            return state

        log_agent_step(
            "send_business_notifications",
            input_data={"opportunity_count": len(opportunities)}
        )

        try:
            # 检查是否为试运行
            if state["context"].get("dry_run", False):
                logger.info(f"DRY RUN: Would send business notifications for {len(opportunities)} opportunities")
                result = {
                    "total": len(opportunities),
                    "sent": len(opportunities),
                    "failed": 0,
                    "escalated": sum(1 for opp in opportunities if opp.escalation_level > 0)
                }
            else:
                # 发送业务通知
                result = send_business_notifications(opportunities)

            # 更新状态
            state["notifications_sent"] += result["sent"]
            state["context"]["notification_result"] = result

            log_agent_step(
                "send_business_notifications",
                output_data={
                    "success": True,
                    "total": result["total"],
                    "sent": result["sent"],
                    "failed": result["failed"],
                    "escalated": result["escalated"]
                }
            )

            if result["failed"] > 0:
                error_msg = f"Failed to send {result['failed']} notifications"
                state["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Business notification sending failed: {e}"
            state["errors"].append(error_msg)
            log_agent_step("send_business_notifications", error=error_msg)

        return state
