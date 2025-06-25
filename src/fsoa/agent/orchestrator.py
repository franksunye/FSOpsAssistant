"""
Agent编排器模块

基于LangGraph实现Agent工作流编排
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from ..data.models import (
    TaskInfo, AgentExecution, AgentStatus, AgentHistory, 
    DecisionResult, NotificationInfo, Priority
)
from ..data.database import get_db_manager
from ..utils.logger import get_logger, log_agent_step
from ..utils.config import get_config
from .tools import fetch_overdue_tasks, fetch_overdue_opportunities, send_notification, send_business_notifications, update_task_status
from .decision import create_decision_engine
from .llm import get_deepseek_client

logger = get_logger(__name__)


class AgentState(TypedDict):
    """Agent状态定义"""
    execution_id: str
    start_time: datetime
    tasks: List[TaskInfo]
    processed_tasks: List[TaskInfo]
    notifications_sent: int
    errors: List[str]
    current_task: Optional[TaskInfo]
    decision_result: Optional[DecisionResult]
    context: Dict[str, Any]


class AgentOrchestrator:
    """Agent编排器"""
    
    def __init__(self):
        self.config = get_config()
        self.db_manager = get_db_manager()
        self.decision_engine = create_decision_engine()
        self.graph = self._build_graph()
        
    def _build_graph(self):
        """构建Agent执行图"""
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("fetch_tasks", self._fetch_tasks_node)
        workflow.add_node("process_task", self._process_task_node)
        workflow.add_node("make_decision", self._make_decision_node)
        workflow.add_node("send_notification", self._send_notification_node)
        workflow.add_node("update_status", self._update_status_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # 设置入口点
        workflow.set_entry_point("fetch_tasks")
        
        # 添加边
        workflow.add_edge("fetch_tasks", "process_task")
        workflow.add_conditional_edges(
            "process_task",
            self._should_continue_processing,
            {
                "continue": "make_decision",
                "finish": "finalize"
            }
        )
        workflow.add_edge("make_decision", "send_notification")
        workflow.add_edge("send_notification", "update_status")
        workflow.add_edge("update_status", "process_task")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def execute(self, dry_run: bool = False) -> AgentExecution:
        """
        执行Agent工作流
        
        Args:
            dry_run: 是否为试运行
            
        Returns:
            执行结果
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()
        
        logger.info(f"Starting Agent execution: {execution_id}")
        
        # 初始化状态
        initial_state = AgentState(
            execution_id=execution_id,
            start_time=start_time,
            tasks=[],
            processed_tasks=[],
            notifications_sent=0,
            errors=[],
            current_task=None,
            decision_result=None,
            context={"dry_run": dry_run}
        )
        
        # 创建执行记录
        execution = AgentExecution(
            id=execution_id,
            start_time=start_time,
            status=AgentStatus.RUNNING
        )
        
        try:
            # 保存执行记录
            self.db_manager.save_agent_execution(execution)
            
            # 执行工作流
            final_state = self.graph.invoke(initial_state)
            
            # 更新执行结果
            execution.end_time = datetime.now()
            execution.status = AgentStatus.IDLE
            execution.tasks_processed = len(final_state["processed_tasks"])
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
            # 保存最终执行结果
            self.db_manager.save_agent_execution(execution)
        
        return execution
    
    def _fetch_tasks_node(self, state: AgentState) -> AgentState:
        """获取任务节点"""
        log_agent_step("fetch_tasks", {"execution_id": state["execution_id"]})

        try:
            # 获取传统任务（向后兼容）
            tasks = fetch_overdue_tasks()
            state["tasks"] = tasks
            state["context"]["total_tasks"] = len(tasks)

            # 获取逾期商机（新业务流程）
            try:
                opportunities = fetch_overdue_opportunities()
                state["context"]["opportunities"] = opportunities
                state["context"]["total_opportunities"] = len(opportunities)

                # 如果有商机数据，优先使用新的业务流程
                if opportunities:
                    state["context"]["use_business_flow"] = True
                    logger.info(f"Using business flow with {len(opportunities)} opportunities")
                else:
                    state["context"]["use_business_flow"] = False
                    logger.info("Using legacy task flow")

            except Exception as e:
                logger.warning(f"Failed to fetch opportunities, falling back to legacy flow: {e}")
                state["context"]["use_business_flow"] = False
                state["context"]["opportunities"] = []

            log_agent_step(
                "fetch_tasks",
                output_data={
                    "task_count": len(tasks),
                    "opportunity_count": len(state["context"].get("opportunities", [])),
                    "use_business_flow": state["context"].get("use_business_flow", False)
                }
            )

        except Exception as e:
            error_msg = f"Failed to fetch tasks: {e}"
            state["errors"].append(error_msg)
            log_agent_step("fetch_tasks", error=error_msg)

        return state
    
    def _process_task_node(self, state: AgentState) -> AgentState:
        """处理任务节点"""
        # 获取下一个待处理的任务
        remaining_tasks = [
            task for task in state["tasks"] 
            if task not in state["processed_tasks"]
        ]
        
        if remaining_tasks:
            current_task = remaining_tasks[0]
            state["current_task"] = current_task
            
            log_agent_step(
                "process_task",
                input_data={"task_id": current_task.id, "task_title": current_task.title}
            )
        else:
            state["current_task"] = None
            log_agent_step("process_task", output_data={"message": "No more tasks to process"})
        
        return state
    
    def _make_decision_node(self, state: AgentState) -> AgentState:
        """决策节点"""
        current_task = state["current_task"]
        if not current_task:
            return state
        
        log_agent_step(
            "make_decision",
            input_data={"task_id": current_task.id}
        )
        
        try:
            # 构建决策上下文
            from ..data.models import DecisionContext
            context = DecisionContext(
                task=current_task,
                history=[],  # 可以从数据库获取历史记录
                system_config={}
            )
            
            # 执行决策
            decision = self.decision_engine.make_decision(current_task, context)
            state["decision_result"] = decision
            
            log_agent_step(
                "make_decision",
                output_data={
                    "action": decision.action,
                    "priority": decision.priority.value,
                    "llm_used": decision.llm_used,
                    "confidence": decision.confidence
                }
            )
            
        except Exception as e:
            error_msg = f"Decision making failed for task {current_task.id}: {e}"
            state["errors"].append(error_msg)
            log_agent_step("make_decision", error=error_msg)
            
            # 设置默认决策
            state["decision_result"] = DecisionResult(
                action="skip",
                priority=Priority.LOW,
                reasoning="决策失败，跳过处理"
            )
        
        return state
    
    def _send_notification_node(self, state: AgentState) -> AgentState:
        """发送通知节点"""
        # 检查是否使用新的业务流程
        if state["context"].get("use_business_flow", False):
            return self._send_business_notifications(state)

        # 传统任务通知流程
        current_task = state["current_task"]
        decision = state["decision_result"]

        if not current_task or not decision:
            return state

        # 只有决策为notify或escalate时才发送通知
        if decision.action not in ["notify", "escalate"]:
            log_agent_step(
                "send_notification",
                output_data={"message": f"Skipping notification for action: {decision.action}"}
            )
            return state
        
        log_agent_step(
            "send_notification",
            input_data={
                "task_id": current_task.id,
                "action": decision.action,
                "priority": decision.priority.value
            }
        )
        
        try:
            # 检查是否为试运行
            if state["context"].get("dry_run", False):
                logger.info(f"DRY RUN: Would send notification for task {current_task.id}")
                success = True
            else:
                # 生成消息内容
                message = decision.message
                if not message and decision.llm_used:
                    # 使用LLM生成消息
                    try:
                        deepseek_client = get_deepseek_client()
                        message_type = "escalation_alert" if decision.action == "escalate" else "overdue_alert"
                        message = deepseek_client.generate_notification_message(current_task, message_type)
                    except Exception as e:
                        logger.warning(f"LLM message generation failed: {e}")
                        message = decision.message or f"任务 {current_task.id} 需要关注"
                
                # 发送通知
                success = send_notification(current_task, message, decision.priority)
            
            if success:
                state["notifications_sent"] += 1
                log_agent_step(
                    "send_notification",
                    output_data={"success": True, "message_sent": True}
                )
            else:
                error_msg = f"Failed to send notification for task {current_task.id}"
                state["errors"].append(error_msg)
                log_agent_step("send_notification", error=error_msg)
                
        except Exception as e:
            error_msg = f"Notification sending failed for task {current_task.id}: {e}"
            state["errors"].append(error_msg)
            log_agent_step("send_notification", error=error_msg)
        
        return state
    
    def _update_status_node(self, state: AgentState) -> AgentState:
        """更新状态节点"""
        current_task = state["current_task"]
        if not current_task:
            return state
        
        log_agent_step(
            "update_status",
            input_data={"task_id": current_task.id}
        )
        
        try:
            # 将任务标记为已处理
            state["processed_tasks"].append(current_task)
            
            # 更新任务的最后通知时间（如果发送了通知）
            decision = state["decision_result"]
            if decision and decision.action in ["notify", "escalate"]:
                current_task.last_notification = datetime.now()
                
                # 保存到数据库
                if not state["context"].get("dry_run", False):
                    self.db_manager.save_task(current_task)
            
            log_agent_step(
                "update_status",
                output_data={"task_processed": True}
            )
            
        except Exception as e:
            error_msg = f"Status update failed for task {current_task.id}: {e}"
            state["errors"].append(error_msg)
            log_agent_step("update_status", error=error_msg)
        
        return state
    
    def _finalize_node(self, state: AgentState) -> AgentState:
        """完成节点"""
        log_agent_step(
            "finalize",
            output_data={
                "total_tasks": len(state["tasks"]),
                "processed_tasks": len(state["processed_tasks"]),
                "notifications_sent": state["notifications_sent"],
                "errors_count": len(state["errors"])
            }
        )
        
        return state
    
    def _should_continue_processing(self, state: AgentState) -> str:
        """判断是否继续处理任务"""
        remaining_tasks = [
            task for task in state["tasks"] 
            if task not in state["processed_tasks"]
        ]
        
        return "continue" if remaining_tasks else "finish"
    
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
