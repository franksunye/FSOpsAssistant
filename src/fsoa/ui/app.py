"""
FSOA Streamlit应用主入口

提供Web界面管理功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 导入时区工具
from src.fsoa.utils.timezone_utils import now_china_naive, format_china_time

# 设置页面配置
st.set_page_config(
    page_title="FSOA - 现场服务运营助手",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 添加项目根目录到Python路径
import sys
import os
from pathlib import Path

# 获取项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入模块
try:
    from src.fsoa.agent.tools import (
        fetch_overdue_opportunities, test_metabase_connection,
        test_wechat_webhook, test_deepseek_connection, get_system_health, send_business_notifications
    )
    from src.fsoa.agent.orchestrator import AgentOrchestrator
    from src.fsoa.utils.scheduler import get_scheduler, setup_agent_scheduler, start_scheduler, stop_scheduler
    from src.fsoa.data.database import get_db_manager
    from src.fsoa.data.models import TaskStatus, Priority, OpportunityInfo, OpportunityStatus
    from src.fsoa.data.metabase import get_metabase_client
    from src.fsoa.notification.wechat import get_wechat_client
    from src.fsoa.analytics.business_metrics import BusinessMetricsCalculator
    from src.fsoa.utils.config import get_config
    from src.fsoa.utils.logger import get_logger

    # 强制重新加载配置
    from dotenv import load_dotenv
    load_dotenv(override=True)

except ImportError as e:
    st.error(f"模块导入失败: {e}")
    st.error("请检查项目结构和Python路径配置")
    st.stop()

logger = get_logger(__name__)


def main():
    """主应用函数"""
    
    # 侧边栏导航 - 重新设计为业务导向的清晰结构
    with st.sidebar:
        st.title("FSOA 运营助手")
        st.markdown("---")

        # 核心业务功能
        st.subheader("核心监控")
        if st.button("运营仪表板", use_container_width=True):
            st.session_state.page = "dashboard"
        if st.button("商机监控", use_container_width=True):
            st.session_state.page = "opportunities"
        if st.button("业务分析", use_container_width=True):
            st.session_state.page = "analytics"

        st.markdown("---")

        # Agent管理功能
        st.subheader("Agent管理")
        if st.button("Agent控制台", use_container_width=True):
            st.session_state.page = "agent_control"
        if st.button("执行历史", use_container_width=True):
            st.session_state.page = "execution_history"
        if st.button("通知管理", use_container_width=True):
            st.session_state.page = "notification_management"
        if st.button("🤖 LLM监控", use_container_width=True):
            st.session_state.page = "llm_monitor"

        st.markdown("---")

        # 系统管理功能
        st.subheader("系统管理")
        if st.button("缓存管理", use_container_width=True):
            st.session_state.page = "cache_management"
        if st.button("企微群配置", use_container_width=True):
            st.session_state.page = "wechat_config"
        if st.button("系统设置", use_container_width=True):
            st.session_state.page = "system_settings"
        if st.button("系统测试", use_container_width=True):
            st.session_state.page = "system_test"
        if st.button("关于", use_container_width=True):
            st.session_state.page = "about"

        # 获取当前页面
        page = st.session_state.get("page", "dashboard")
    
    # 根据选择显示不同页面
    if page == "dashboard":
        show_dashboard()
    elif page == "opportunities":
        show_opportunity_list()
    elif page == "analytics":
        show_business_analytics()
    elif page == "agent_control":
        show_agent_control()
    elif page == "execution_history":
        show_execution_history()
    elif page == "notification_management":
        show_notification_management()
    elif page == "llm_monitor":
        show_llm_monitor()
    elif page == "cache_management":
        show_cache_management()
    elif page == "wechat_config":
        show_wechat_config()
    elif page == "system_test":
        show_system_test()
    elif page == "system_settings":
        show_system_settings()
    elif page == "about":
        show_about()
    else:
        show_dashboard()  # 默认页面


def show_dashboard():
    """显示运营仪表板 - 重新设计为业务价值导向"""

    # 获取实时数据
    try:
        # 使用新的商机统计API
        from src.fsoa.agent.tools import get_opportunity_statistics, get_data_strategy

        # 获取商机统计信息
        opportunity_stats = get_opportunity_statistics()

        # 获取系统健康状态
        health = get_system_health()

        # 获取Agent执行状态 - 使用智能跨进程检测
        from src.fsoa.agent.tools import get_agent_execution_status, detect_fsoa_processes
        agent_exec_status = get_agent_execution_status()
        process_info = detect_fsoa_processes()

        # 获取Agent状态 - 区分Web模式和完整模式
        scheduler_running = agent_exec_status.get("scheduler_running", False)
        has_full_app_process = process_info.get("has_full_app_process", False)
        last_execution = agent_exec_status.get("last_execution")

        if scheduler_running or has_full_app_process:
            agent_status = "完整模式"
            agent_delta = "Agent + Web界面"
        elif last_execution and last_execution != "从未执行":
            # 如果有执行记录但调度器未运行，可能是其他进程在运行
            agent_status = "完整模式"
            agent_delta = "Agent + Web界面"
        else:
            agent_status = "Web模式"
            agent_delta = "仅Web界面"

        # 从统计信息中提取数据
        total_opportunities = opportunity_stats.get("total_opportunities", 0)
        overdue_opportunities = opportunity_stats.get("overdue_count", 0)
        approaching_opportunities = opportunity_stats.get("approaching_overdue_count", 0)
        normal_opportunities = opportunity_stats.get("normal_count", 0)
        escalation_count = opportunity_stats.get("escalation_count", 0)

        # 组织统计
        org_breakdown = opportunity_stats.get("organization_breakdown", {})
        org_count = len(org_breakdown)

        # 状态统计
        status_breakdown = opportunity_stats.get("status_breakdown", {})

    except Exception as e:
        st.error(f"获取系统数据失败: {e}")
        health = {}
        agent_exec_status = {"scheduler_running": False}
        # 设置默认的商机统计数据
        opportunity_stats = {
            "total_opportunities": 0,
            "overdue_count": 0,
            "normal_count": 0,
            "approaching_overdue_count": 0,
            "escalation_count": 0,
            "overdue_rate": 0,
            "approaching_rate": 0,
            "organization_breakdown": {},
            "status_breakdown": {},
            "organization_count": 0
        }
        # 设置默认的其他变量
        total_opportunities = 0
        overdue_opportunities = 0
        approaching_opportunities = 0
        normal_opportunities = 0
        escalation_count = 0
        org_count = 0
        org_breakdown = {}
        status_breakdown = {}
        agent_status = "Web模式"
        agent_delta = "仅Web界面"
        escalation_count = 0
        total_opportunities = 0
        overdue_opportunities = 0
        approaching_opportunities = 0
        normal_opportunities = 0
        org_count = 0
        org_breakdown = {}
        status_breakdown = {}

    # 核心业务指标
    st.subheader("核心业务指标")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Agent状态",
            value=agent_status,
            delta=agent_delta,
            delta_color="normal" if agent_delta == "正常" else "inverse"
        )
        if agent_status == "完整模式":
            st.success("智能监控运行中")
            # 显示最后执行时间
            last_exec = agent_exec_status.get("last_execution")
            if last_exec:
                st.caption(f"最后执行: {last_exec}")
        elif agent_status == "Web模式":
            st.info("Web界面模式")
            st.caption("使用 `python scripts/start_full_app.py` 启动完整Agent")
        else:
            st.error("需要启动Agent")

    with col2:
        st.metric(
            label="逾期商机",
            value=str(overdue_opportunities),
            delta=f"监控{total_opportunities}个" if total_opportunities > 0 else "0"
        )
        if overdue_opportunities > 0:
            st.warning(f"{overdue_opportunities}个商机需要关注")
        else:
            st.success("暂无逾期商机")
        st.caption("仅监控'待预约'和'暂不上门'状态")

    with col3:
        st.metric(
            label="升级处理",
            value=str(escalation_count),
            delta="紧急" if escalation_count > 0 else "正常",
            delta_color="inverse" if escalation_count > 0 else "normal"
        )
        if escalation_count > 0:
            st.error(f"{escalation_count}个商机需要升级处理")
        else:
            st.success("无需升级处理")

    with col4:
        st.metric(
            label="涉及组织",
            value=str(org_count),
            delta=f"监控{total_opportunities}个商机" if total_opportunities > 0 else "无数据"
        )
        if org_count > 0:
            st.info(f"{org_count}个组织")
        else:
            st.warning("无组织数据")
    
    # 第二行：详细分类统计
    st.markdown("### 商机分类统计")
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            label="已逾期",
            value=str(overdue_opportunities),
            delta=f"{overdue_opportunities/total_opportunities*100:.1f}%" if total_opportunities > 0 else "0%"
        )

    with col6:
        st.metric(
            label="即将逾期",
            value=str(approaching_opportunities),
            delta=f"{approaching_opportunities/total_opportunities*100:.1f}%" if total_opportunities > 0 else "0%"
        )

    with col7:
        st.metric(
            label="正常跟进",
            value=str(normal_opportunities),
            delta=f"{normal_opportunities/total_opportunities*100:.1f}%" if total_opportunities > 0 else "0%"
        )

    with col8:
        overdue_rate = opportunity_stats.get("overdue_rate", 0)
        approaching_rate = opportunity_stats.get("approaching_rate", 0)
        st.metric(
            label="风险比例",
            value=f"{overdue_rate + approaching_rate:.1f}%",
            delta="需关注" if (overdue_rate + approaching_rate) > 20 else "良好"
        )

    st.markdown("---")

    # 快速操作区域
    st.subheader("快速操作")

    col_action1, col_action2, col_action3, col_action4 = st.columns(4)

    with col_action1:
        if st.button("立即执行Agent", type="primary", use_container_width=True):
            st.session_state.page = "agent_control"
            st.rerun()

    with col_action2:
        if st.button("查看商机列表", use_container_width=True):
            st.session_state.page = "opportunities"
            st.rerun()

    with col_action3:
        if st.button("管理通知任务", use_container_width=True):
            st.session_state.page = "notification_management"
            st.rerun()

    with col_action4:
        if st.button("刷新数据", use_container_width=True):
            st.rerun()

    # Agent执行信息和系统状态
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Agent执行状态")

        # 获取真实的Agent执行状态
        try:
            from src.fsoa.agent.tools import get_agent_execution_status
            agent_status = get_agent_execution_status()

            # 显示上次执行
            last_exec = agent_status.get("last_execution", "未知")
            last_status = agent_status.get("last_execution_status", "未知")
            if last_status == "completed":
                st.success(f"上次执行: {last_exec} (成功)")
            elif last_status == "failed":
                st.error(f"上次执行: {last_exec} (失败)")
            elif last_status == "running":
                st.warning(f"上次执行: {last_exec} (运行中)")
            else:
                st.info(f"上次执行: {last_exec} ({last_status})")

            # 显示下次执行
            next_exec = agent_status.get("next_execution", "未知")
            st.info(f"下次执行: {next_exec}")

            # 显示执行间隔
            interval = agent_status.get("execution_interval", "60分钟")
            st.info(f"执行间隔: {interval}")

            # 显示调度器状态 - 使用智能跨进程检测
            from src.fsoa.agent.tools import detect_fsoa_processes
            process_info = detect_fsoa_processes()
            scheduler_running = agent_status.get("scheduler_running", False)
            has_full_app_process = process_info.get("has_full_app_process", False)

            if scheduler_running or has_full_app_process:
                st.success("调度器: 运行中")
            else:
                st.error("调度器: 已停止")

        except Exception as e:
            st.error(f"获取Agent状态失败: {e}")
            # 降级显示
            st.info("上次执行: 获取失败")
            st.info("下次执行: 获取失败")
            st.info("执行间隔: 60分钟")

        if st.button("手动执行Agent", type="primary"):
            with st.spinner("正在执行Agent..."):
                try:
                    agent = AgentOrchestrator()
                    result = agent.execute(dry_run=False)
                    st.success(f"Agent执行完成！处理任务: {result.tasks_processed}, 发送通知: {result.notifications_sent}")
                    if result.errors:
                        st.warning(f"执行中出现 {len(result.errors)} 个错误")
                except Exception as e:
                    st.error(f"Agent执行失败: {e}")

    with col2:
        st.subheader("系统健康状态")

        # 获取系统健康状态
        try:
            health = get_system_health()

            # 显示各组件状态
            if health.get("metabase_connection"):
                st.success("Metabase连接正常")
            else:
                st.error("Metabase连接异常")

            if health.get("wechat_webhook"):
                st.success("企微Webhook正常")
            else:
                st.error("企微Webhook异常")

            if health.get("deepseek_connection"):
                st.success("DeepSeek连接正常")
            else:
                st.error("DeepSeek连接异常")

            if health.get("database_connection"):
                st.success("数据库连接正常")
            else:
                st.error("数据库连接异常")

        except Exception as e:
            st.error(f"获取系统状态失败: {e}")

    # PoC阶段暂时移除性能趋势图表
    # 未来可以添加真实的系统性能监控


def show_agent_control():
    """显示Agent控制台页面 - 重新设计为Agent管理导向"""
    # Agent状态信息
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Agent状态")

        try:
            # 使用智能跨进程检测
            from src.fsoa.agent.tools import get_agent_execution_status, detect_fsoa_processes
            agent_exec_status = get_agent_execution_status()
            process_info = detect_fsoa_processes()

            # 获取调度器状态
            scheduler_running = agent_exec_status.get("scheduler_running", False)
            has_full_app_process = process_info.get("has_full_app_process", False)

            # 显示调度器状态
            if scheduler_running or has_full_app_process:
                st.success("🟢 调度器运行中")
                if has_full_app_process and not scheduler_running:
                    st.info("💡 检测到完整应用进程运行中")
            else:
                st.error("🔴 调度器已停止")

            # 显示详细状态信息
            last_execution = agent_exec_status.get("last_execution", "从未执行")
            last_status = agent_exec_status.get("last_execution_status", "未知")
            next_execution = agent_exec_status.get("next_execution", "未知")
            execution_interval = agent_exec_status.get("execution_interval", "60分钟")
            total_runs = agent_exec_status.get("total_runs", 0)

            st.info(f"📋 总执行次数: {total_runs}")
            st.info(f"⏰ 执行间隔: {execution_interval}")
            st.info(f"📅 最后执行: {last_execution}")
            st.info(f"🔮 下次执行: {next_execution}")

            # 显示进程信息
            if process_info.get("total_fsoa_processes", 0) > 0:
                st.write("**检测到的FSOA进程:**")
                for proc in process_info.get("fsoa_processes", []):
                    status_icon = "🟢" if proc.get("is_full_app") else "🔵"
                    proc_type = "完整应用" if proc.get("is_full_app") else "其他进程"
                    st.write(f"{status_icon} PID {proc['pid']}: {proc_type}")

            # 获取当前进程的调度器信息
            try:
                scheduler = get_scheduler()
                jobs_info = scheduler.get_jobs()

                if jobs_info["jobs"]:
                    st.write("**当前进程的定时任务:**")
                    for job in jobs_info["jobs"]:
                        with st.expander(f"📅 {job['id']}"):
                            st.write(f"**函数**: {job['func']}")
                            st.write(f"**触发器**: {job['trigger']}")
                            st.write(f"**下次执行**: {job['next_run_time'] or '未知'}")
                else:
                    st.info("当前进程无活跃任务")
            except Exception as e:
                st.warning(f"获取当前进程调度器信息失败: {e}")

        except Exception as e:
            st.error(f"获取Agent状态失败: {e}")

    with col2:
        st.subheader("🎛️ 控制操作")

        # 手动执行 - 使用新的执行追踪
        if st.button("🚀 立即执行Agent", type="primary"):
            with st.spinner("正在执行Agent..."):
                try:
                    from src.fsoa.agent.tools import (
                        start_agent_execution, get_all_opportunities,
                        create_notification_tasks, execute_notification_tasks,
                        complete_agent_execution
                    )

                    # 使用新的执行流程
                    context = {"manual_execution": True, "ui_triggered": True}
                    run_id = start_agent_execution(context)

                    # 获取商机数据
                    opportunities = get_all_opportunities(force_refresh=True)
                    overdue_opportunities = [opp for opp in opportunities if opp.is_overdue]

                    # 创建和执行通知任务
                    notification_result = {"sent_count": 0, "failed_count": 0}
                    if overdue_opportunities:
                        tasks = create_notification_tasks(overdue_opportunities, run_id)
                        notification_result = execute_notification_tasks(run_id)

                    # 完成执行
                    final_stats = {
                        "opportunities_processed": len(opportunities),
                        "notifications_sent": notification_result.get("sent_count", 0),
                        "context": {"ui_execution_completed": True}
                    }
                    complete_agent_execution(run_id, final_stats)

                    st.success("✅ Agent执行完成！")

                    # 显示执行结果
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("执行ID", run_id)
                    with col_b:
                        st.metric("处理商机", final_stats["opportunities_processed"])
                    with col_c:
                        st.metric("发送通知", final_stats["notifications_sent"])
                    with col_d:
                        st.metric("失败通知", notification_result.get("failed_count", 0))

                    if notification_result.get("errors"):
                        st.error("执行错误:")
                        for error in notification_result["errors"]:
                            st.write(f"• {error}")

                except Exception as e:
                    st.error(f"Agent执行失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        # 试运行 - 使用新的执行追踪
        if st.button("🧪 试运行 (Dry Run)"):
            with st.spinner("正在试运行..."):
                try:
                    from src.fsoa.agent.tools import get_data_statistics, get_data_strategy

                    # 获取数据统计进行模拟
                    stats = get_data_statistics()
                    data_strategy = get_data_strategy()

                    st.info("🧪 试运行完成！")

                    # 显示模拟结果
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("模拟处理商机", stats.get("total_opportunities", 0))
                    with col_b:
                        st.metric("模拟发送通知", stats.get("overdue_opportunities", 0))
                    with col_c:
                        st.metric("缓存状态", "启用" if data_strategy.cache_enabled else "禁用")

                    # 显示缓存统计（重构后的清空重建模式）
                    cache_stats = stats.get("cache_statistics", {})
                    if cache_stats:
                        st.write("**缓存统计 (清空重建模式):**")
                        st.write(f"• 缓存条目: {cache_stats.get('total_cached', 0)}")
                        st.write(f"• 缓存状态: {'启用' if cache_stats.get('cache_enabled', False) else '禁用'}")
                        st.write(f"• 数据模式: 每次完全刷新")

                except Exception as e:
                    st.error(f"试运行失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    st.markdown("---")

    # 调度器控制
    st.subheader("⏰ 调度器管理")

    # 检查是否有完整应用进程运行
    try:
        from src.fsoa.agent.tools import detect_fsoa_processes
        process_info = detect_fsoa_processes()
        has_full_app_process = process_info.get("has_full_app_process", False)

        if has_full_app_process:
            st.info("💡 检测到完整应用进程运行中。Web界面的调度器控制仅影响当前进程，不会影响完整应用的调度器。")
    except Exception:
        pass

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ 启动调度器"):
            try:
                start_scheduler()
                setup_agent_scheduler()
                st.success("调度器已启动")
                st.rerun()
            except Exception as e:
                st.error(f"启动失败: {e}")

    with col2:
        if st.button("⏸️ 停止调度器"):
            try:
                stop_scheduler()
                st.success("调度器已停止")
                st.rerun()
            except Exception as e:
                st.error(f"停止失败: {e}")

    with col3:
        if st.button("🔄 重启调度器"):
            try:
                stop_scheduler()
                start_scheduler()
                setup_agent_scheduler()
                st.success("调度器已重启")
                st.rerun()
            except Exception as e:
                st.error(f"重启失败: {e}")

    with col4:
        if st.button("📊 刷新状态"):
            st.rerun()


def show_task_list():
    """显示任务列表"""
    st.header("📋 任务列表")
    
    # 筛选器
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "进行中", "已完成", "已超时", "已取消"]
        )
    
    with col2:
        group_filter = st.selectbox(
            "群组筛选", 
            ["全部", "group_001", "group_002", "group_003"]
        )
    
    with col3:
        time_filter = st.selectbox(
            "时间筛选",
            ["今天", "最近3天", "最近7天", "最近30天"]
        )
    
    # 搜索框
    search_term = st.text_input("🔍 搜索任务ID或标题")
    
    st.markdown("---")
    
    # 任务列表
    try:
        # 获取任务数据（示例数据）
        sample_tasks = [
            {
                "ID": 1001,
                "标题": "设备维护任务",
                "状态": "进行中",
                "SLA(小时)": 8,
                "已用时间": 10.5,
                "超时时间": 2.5,
                "负责人": "张三",
                "客户": "ABC公司",
                "群组": "group_001"
            },
            {
                "ID": 1002,
                "标题": "故障排查",
                "状态": "已完成",
                "SLA(小时)": 4,
                "已用时间": 3.8,
                "超时时间": 0,
                "负责人": "李四",
                "客户": "XYZ公司",
                "群组": "group_002"
            }
        ]
        
        df = pd.DataFrame(sample_tasks)
        
        # 应用筛选
        if status_filter != "全部":
            status_map = {
                "进行中": "进行中",
                "已完成": "已完成", 
                "已超时": "已超时",
                "已取消": "已取消"
            }
            df = df[df["状态"] == status_map.get(status_filter)]
        
        if search_term:
            df = df[
                df["ID"].astype(str).str.contains(search_term, case=False) |
                df["标题"].str.contains(search_term, case=False)
            ]
        
        # 显示任务表格
        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # 操作按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📤 导出数据"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="下载CSV文件",
                        data=csv,
                        file_name=f"tasks_{now_china_naive().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("🔄 刷新数据"):
                    st.rerun()
            
            with col3:
                if st.button("📊 生成报表"):
                    st.info("报表功能开发中...")
        else:
            st.info("没有找到符合条件的任务")
            
    except Exception as e:
        st.error(f"获取任务列表失败: {e}")


def show_notification_history():
    """显示通知历史"""
    st.header("🔔 通知历史")
    
    # 时间范围选择
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("开始日期", now_china_naive() - timedelta(days=7))

    with col2:
        end_date = st.date_input("结束日期", now_china_naive())
    
    # 通知历史表格（示例数据）
    sample_notifications = [
        {
            "时间": "2025-06-25 10:30:00",
            "任务ID": 1001,
            "类型": "超时提醒",
            "群组": "group_001",
            "状态": "已发送",
            "内容": "任务已超时2.5小时，请及时处理"
        },
        {
            "时间": "2025-06-25 09:15:00", 
            "任务ID": 1003,
            "类型": "升级提醒",
            "群组": "group_002",
            "状态": "已发送",
            "内容": "任务严重超时，需要立即关注"
        }
    ]
    
    df = pd.DataFrame(sample_notifications)
    
    if not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        # 统计信息
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总通知数", len(df))
        
        with col2:
            sent_count = len(df[df["状态"] == "已发送"])
            st.metric("成功发送", sent_count)
        
        with col3:
            failed_count = len(df[df["状态"] == "发送失败"])
            st.metric("发送失败", failed_count)
    else:
        st.info("暂无通知记录")


def show_system_settings():
    """显示系统设置"""

    # 设置选项卡 - 添加工作时间配置
    tab1, tab2, tab3 = st.tabs(["Agent设置", "通知设置", "工作时间设置"])
    
    with tab1:
        st.subheader("🤖 Agent配置")

        # 从数据库加载现有Agent配置
        try:
            from src.fsoa.data.database import get_database_manager
            db_manager = get_database_manager()
            configs = db_manager.get_all_system_configs()

            default_execution_interval = int(configs.get("agent_execution_interval", "60"))
            default_use_llm = configs.get("use_llm_optimization", "true").lower() == "true"
            default_llm_temperature = float(configs.get("llm_temperature", "0.1"))
            default_max_retries = int(configs.get("agent_max_retries", "3"))
            default_use_llm_formatting = configs.get("use_llm_message_formatting", "false").lower() == "true"
        except Exception as e:
            st.warning(f"无法加载Agent配置，使用默认值: {e}")
            default_execution_interval = 60
            default_use_llm = True
            default_llm_temperature = 0.1
            default_max_retries = 3
            default_use_llm_formatting = False

        execution_interval = st.number_input(
            "执行频率（分钟）",
            min_value=1,
            max_value=1440,
            value=default_execution_interval
        )

        use_llm = st.checkbox("启用LLM优化", value=default_use_llm)

        llm_temperature = default_llm_temperature
        if use_llm:
            llm_temperature = st.slider(
                "LLM温度参数",
                min_value=0.0,
                max_value=1.0,
                value=default_llm_temperature,
                step=0.1
            )

        max_retries = st.number_input(
            "最大重试次数",
            min_value=1,
            max_value=10,
            value=default_max_retries
        )

        use_llm_formatting = st.checkbox(
            "启用LLM消息格式化（实验性功能）",
            value=default_use_llm_formatting,
            help="使用LLM智能格式化通知消息内容，提升消息质量"
        )

        if st.button("💾 保存Agent设置"):
            try:
                from src.fsoa.data.database import get_database_manager
                from src.fsoa.utils.scheduler import get_scheduler, stop_scheduler, start_scheduler, setup_agent_scheduler

                db_manager = get_database_manager()

                # 获取当前执行间隔以检查是否有变化
                current_interval_config = db_manager.get_system_config("agent_execution_interval")
                current_interval = int(current_interval_config) if current_interval_config else 60
                interval_changed = (execution_interval != current_interval)

                # 保存Agent配置到数据库
                agent_configs = [
                    ("agent_execution_interval", str(execution_interval), "Agent执行间隔（分钟）"),
                    ("use_llm_optimization", str(use_llm).lower(), "是否启用LLM优化"),
                    ("llm_temperature", str(llm_temperature), "LLM温度参数"),
                    ("agent_max_retries", str(max_retries), "Agent最大重试次数"),
                    ("use_llm_message_formatting", str(use_llm_formatting).lower(), "是否使用LLM格式化通知消息"),
                ]

                for key, value, description in agent_configs:
                    db_manager.set_system_config(key, value, description)

                # 如果执行间隔发生变化，自动重启/启动调度器使配置立即生效
                if interval_changed:
                    try:
                        scheduler = get_scheduler()
                        is_running = hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running

                        if is_running:
                            st.info("🔄 检测到执行间隔变化，正在重启调度器...")
                            # 重启调度器
                            stop_scheduler()
                            start_scheduler()
                            setup_agent_scheduler()
                            st.success(f"✅ Agent设置已保存，调度器已自动重启（新间隔：{execution_interval}分钟）")
                        else:
                            st.info("🔄 检测到执行间隔变化，正在启动调度器...")
                            # 启动调度器
                            start_scheduler()
                            setup_agent_scheduler()
                            st.success(f"✅ Agent设置已保存，调度器已自动启动（执行间隔：{execution_interval}分钟）")

                    except Exception as restart_error:
                        st.warning(f"⚠️ 配置已保存，但调度器启动/重启失败: {restart_error}")
                        st.info("💡 请手动点击'🔄 重启调度器'按钮使新配置生效")
                else:
                    st.success("✅ Agent设置已保存")

            except Exception as e:
                st.error(f"❌ 保存失败: {e}")
    
    with tab2:
        st.subheader("🔔 通知配置")

        # 从数据库加载现有配置
        try:
            from src.fsoa.data.database import get_database_manager
            db_manager = get_database_manager()
            configs = db_manager.get_all_system_configs()

            default_cooldown_minutes = int(configs.get("notification_cooldown", "120"))
            default_max_retry = int(configs.get("max_retry_count", "5"))
            default_api_interval = int(configs.get("webhook_api_interval", "3"))
            default_enable_dedup = configs.get("enable_dedup", "true").lower() == "true"
        except Exception as e:
            st.warning(f"无法加载配置，使用默认值: {e}")
            default_cooldown_minutes = 120
            default_max_retry = 5
            default_api_interval = 3
            default_enable_dedup = True
        
        cooldown_hours = st.number_input(
            "通知冷静时间（小时）",
            min_value=0.5,
            max_value=24.0,
            value=default_cooldown_minutes / 60.0,
            step=0.5,
            help="发送通知后的冷静时间，避免频繁打扰"
        )

        max_retry_count = st.number_input(
            "最大重试次数",
            min_value=1,
            max_value=10,
            value=default_max_retry,
            help="每个通知任务的最大重试次数"
        )

        api_interval_seconds = st.number_input(
            "Webhook API发送间隔（秒）",
            min_value=1,
            max_value=30,
            value=default_api_interval,
            help="每次调用企微Webhook API之间的间隔时间，避免触发速率限制"
        )

        st.markdown("**通知开关配置**")
        st.info("💡 控制是否发送不同类型的SLA通知")

        col_switch1, col_switch2 = st.columns(2)

        with col_switch1:
            default_reminder_enabled = configs.get("notification_reminder_enabled", "true").lower() == "true"
            reminder_enabled = st.checkbox(
                "启用提醒通知（4/8小时）→ 服务商群",
                value=default_reminder_enabled,
                help="是否发送SLA提醒通知到服务商群"
            )

        with col_switch2:
            default_escalation_enabled = configs.get("notification_escalation_enabled", "false").lower() == "true"
            escalation_enabled = st.checkbox(
                "启用升级通知（8/16小时）→ 运营群",
                value=default_escalation_enabled,
                help="是否发送SLA升级通知到运营群"
            )

        st.markdown("**SLA阈值设置（工作时间）**")
        st.info("💡 两级SLA体系：提醒→服务商群，升级→运营群")

        col_sla1, col_sla2 = st.columns(2)

        with col_sla1:
            st.markdown("**待预约商机**")
            pending_reminder = st.number_input(
                "提醒阈值（小时）",
                min_value=1,
                max_value=24,
                value=int(configs.get("sla_pending_reminder", "4")),
                help="待预约商机提醒阈值，发送到服务商群",
                key="pending_reminder"
            )

            pending_escalation = st.number_input(
                "升级阈值（小时）",
                min_value=1,
                max_value=48,
                value=int(configs.get("sla_pending_escalation", "8")),
                help="待预约商机升级阈值，发送到运营群",
                key="pending_escalation"
            )

        with col_sla2:
            st.markdown("**暂不上门商机**")
            not_visiting_reminder = st.number_input(
                "提醒阈值（小时）",
                min_value=1,
                max_value=48,
                value=int(configs.get("sla_not_visiting_reminder", "8")),
                help="暂不上门商机提醒阈值，发送到服务商群",
                key="not_visiting_reminder"
            )

            not_visiting_escalation = st.number_input(
                "升级阈值（小时）",
                min_value=1,
                max_value=72,
                value=int(configs.get("sla_not_visiting_escalation", "16")),
                help="暂不上门商机升级阈值，发送到运营群",
                key="not_visiting_escalation"
            )

        enable_dedup = st.checkbox("启用智能去重", value=default_enable_dedup)

        st.markdown("**消息显示配置**")
        st.info("💡 控制通知消息中显示的工单数量，避免消息过长")

        col_display1, col_display2 = st.columns(2)

        with col_display1:
            reminder_max_display = st.number_input(
                "提醒类通知最多显示工单数",
                min_value=1,
                max_value=50,
                value=int(configs.get("reminder_max_display_orders", "10")),
                help="提醒类通知（一般提醒、标准逾期）中最多显示的工单详情数量",
                key="reminder_max_display"
            )

        with col_display2:
            escalation_max_display = st.number_input(
                "升级类通知最多显示工单数",
                min_value=1,
                max_value=20,
                value=int(configs.get("escalation_max_display_orders", "5")),
                help="升级类通知（升级通知、紧急通知）中最多显示的工单详情数量",
                key="escalation_max_display"
            )

        if st.button("💾 保存通知设置"):
            try:
                from src.fsoa.data.database import get_database_manager
                db_manager = get_database_manager()

                # 保存通知配置
                configs = [
                    ("notification_cooldown", str(int(cooldown_hours * 60)), "通知冷却时间（分钟）"),
                    ("max_retry_count", str(max_retry_count), "最大重试次数"),
                    ("webhook_api_interval", str(api_interval_seconds), "Webhook API发送间隔（秒）"),
                    ("enable_dedup", str(enable_dedup).lower(), "启用智能去重"),
                    # 通知开关配置
                    ("notification_reminder_enabled", str(reminder_enabled).lower(), "是否启用提醒通知（4/8小时）→服务商群"),
                    ("notification_escalation_enabled", str(escalation_enabled).lower(), "是否启用升级通知（8/16小时）→运营群"),
                    # SLA配置
                    ("sla_pending_reminder", str(pending_reminder), "待预约提醒阈值（工作小时）→服务商群"),
                    ("sla_pending_escalation", str(pending_escalation), "待预约升级阈值（工作小时）→运营群"),
                    ("sla_not_visiting_reminder", str(not_visiting_reminder), "暂不上门提醒阈值（工作小时）→服务商群"),
                    ("sla_not_visiting_escalation", str(not_visiting_escalation), "暂不上门升级阈值（工作小时）→运营群"),
                    # 消息显示配置
                    ("reminder_max_display_orders", str(reminder_max_display), "提醒类通知最多显示工单数"),
                    ("escalation_max_display_orders", str(escalation_max_display), "升级类通知最多显示工单数"),
                ]

                for key, value, description in configs:
                    db_manager.set_system_config(key, value, description)

                st.success("✅ 通知设置已保存")
            except Exception as e:
                st.error(f"❌ 保存失败: {e}")

    with tab3:
        st.subheader("🕒 工作时间配置")
        st.info("💡 所有SLA时间计算均基于工作时间，非工作时间不计入SLA")

        # 读取当前配置
        try:
            current_start_hour = int(db_manager.get_system_config("work_start_hour") or "9")
            current_end_hour = int(db_manager.get_system_config("work_end_hour") or "19")
            current_work_days_str = db_manager.get_system_config("work_days") or "1,2,3,4,5"
            current_work_days_nums = [int(d.strip()) for d in current_work_days_str.split(",") if d.strip().isdigit()]

            # 转换为中文工作日名称
            day_names = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
            current_work_days_names = [day_names[d] for d in current_work_days_nums if d in day_names]
        except Exception as e:
            st.error(f"读取工作时间配置失败: {e}")
            current_start_hour = 9
            current_end_hour = 19
            current_work_days_names = ["周一", "周二", "周三", "周四", "周五"]

        col_time1, col_time2 = st.columns(2)

        with col_time1:
            work_start_hour = st.number_input(
                "工作开始时间（小时）",
                min_value=0,
                max_value=23,
                value=current_start_hour,
                help="工作日开始时间，24小时制"
            )

            work_end_hour = st.number_input(
                "工作结束时间（小时）",
                min_value=1,
                max_value=24,
                value=current_end_hour,
                help="工作日结束时间，24小时制"
            )

        with col_time2:
            st.markdown("**工作日设置**")
            work_days = st.multiselect(
                "选择工作日",
                ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                default=current_work_days_names,
                help="选择哪些天算作工作日"
            )

            st.markdown("**当前工作时间**")
            st.info(f"⏰ {work_start_hour}:00 - {work_end_hour}:00")
            st.info(f"📅 {', '.join(work_days)}")

        # 工作时间计算示例
        st.markdown("---")
        st.subheader("📊 工作时间计算示例")

        now = now_china_naive()

        # 示例计算
        example_scenarios = [
            ("周五下午5点创建", now.replace(hour=17, minute=0, second=0, microsecond=0)),
            ("周一上午9点创建", now.replace(hour=9, minute=0, second=0, microsecond=0)),
            ("周三中午12点创建", now.replace(hour=12, minute=0, second=0, microsecond=0))
        ]

        for desc, create_time in example_scenarios:
            try:
                from src.fsoa.utils.business_time import BusinessTimeCalculator
                elapsed_hours = BusinessTimeCalculator.calculate_elapsed_business_hours(create_time, now)

                col_ex1, col_ex2, col_ex3 = st.columns(3)
                with col_ex1:
                    st.write(f"**{desc}**")
                with col_ex2:
                    st.write(f"工作时长: {elapsed_hours:.1f}小时")
                with col_ex3:
                    if elapsed_hours > 12:
                        st.error("🚨 已违规")
                    elif elapsed_hours > 8:
                        st.warning("⚠️ 接近违规")
                    else:
                        st.success("✅ 正常")
            except Exception as e:
                st.error(f"计算示例失败: {e}")

        if st.button("💾 保存工作时间设置"):
            try:
                # 验证输入
                if work_start_hour >= work_end_hour:
                    st.error("❌ 工作开始时间必须小于结束时间")
                elif not work_days:
                    st.error("❌ 至少需要选择一个工作日")
                else:
                    # 转换工作日为数字
                    day_mapping = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7}
                    work_days_nums = [day_mapping[day] for day in work_days if day in day_mapping]
                    work_days_str = ",".join(map(str, sorted(work_days_nums)))

                    # 保存配置
                    configs = [
                        ("work_start_hour", str(work_start_hour), "工作开始时间（小时）"),
                        ("work_end_hour", str(work_end_hour), "工作结束时间（小时）"),
                        ("work_days", work_days_str, "工作日（1=周一，7=周日，逗号分隔）"),
                    ]

                    for key, value, description in configs:
                        db_manager.set_system_config(key, value, description)

                    st.success("✅ 工作时间设置已保存")
                    st.info("💡 新的工作时间配置将在下次Agent执行时生效")
            except Exception as e:
                st.error(f"❌ 保存失败: {e}")

    # 添加企微配置快速跳转
    st.markdown("---")
    st.subheader("🔧 相关配置")

    col_config1, col_config2 = st.columns(2)

    with col_config1:
        if st.button("🔧 企微群配置", type="primary", use_container_width=True):
            st.session_state.page = "wechat_config"
            st.rerun()

    with col_config2:
        if st.button("💾 缓存管理", use_container_width=True):
            st.session_state.page = "cache_management"
            st.rerun()


def show_system_test():
    """显示系统测试"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔗 连接测试")
        
        if st.button("测试Metabase连接"):
            with st.spinner("测试中..."):
                try:
                    result = test_metabase_connection()
                    if result:
                        st.success("✅ Metabase连接正常")
                    else:
                        st.error("❌ Metabase连接失败")
                except Exception as e:
                    st.error(f"❌ 测试失败: {e}")
        
        if st.button("测试企微Webhook"):
            with st.spinner("测试中..."):
                try:
                    result = test_wechat_webhook()
                    if result:
                        st.success("✅ 企微Webhook正常")
                    else:
                        st.error("❌ 企微Webhook失败")
                except Exception as e:
                    st.error(f"❌ 测试失败: {e}")

        if st.button("测试DeepSeek连接"):
            with st.spinner("测试中..."):
                try:
                    result = test_deepseek_connection()
                    if result:
                        st.success("✅ DeepSeek连接正常")
                    else:
                        st.error("❌ DeepSeek连接失败")
                except Exception as e:
                    st.error(f"❌ 测试失败: {e}")
    
    with col2:
        st.subheader("📊 系统信息")
        
        try:
            config = get_config()
            
            st.info(f"数据库: {config.database_url}")
            st.info(f"日志级别: {config.log_level}")
            st.info(f"调试模式: {config.debug}")
            
            # 显示配置的Webhook数量
            webhook_count = len(config.wechat_webhook_list)
            st.info(f"配置的Webhook数量: {webhook_count}")
            
        except Exception as e:
            st.error(f"获取系统信息失败: {e}")


def show_business_analytics():
    """显示业务分析页面"""
    st.markdown("深入分析商机处理效率和组织绩效表现")

    # 添加说明
    with st.expander("📋 数据说明", expanded=False):
        st.markdown("""
        **数据统计逻辑说明：**

        - **全局统计**：基于所有商机数据，与首页仪表板保持一致
        - **逾期分析**：专注于需要关注的逾期商机，提供问题导向的深度分析
        - **组织对比**：展示各组织的整体表现和逾期情况

        **指标含义：**
        - 涉及组织数：有商机的所有组织数量
        - 逾期涉及组织：有逾期商机的组织数量
        - SLA达成率：按时处理的商机比例
        """)

    try:
        # 获取全量商机数据用于全局统计
        from src.fsoa.agent.tools import get_opportunity_statistics

        # 获取全局统计信息
        global_stats = get_opportunity_statistics()

        # 获取逾期商机数据用于详细分析
        overdue_opportunities = fetch_overdue_opportunities()

        if not overdue_opportunities:
            st.info("暂无逾期商机数据进行详细分析")
            # 但仍显示全局统计

        calculator = BusinessMetricsCalculator()

        # 基础统计 - 使用全局数据保持与首页一致
        st.subheader("📊 基础统计")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("总商机数", global_stats["total_opportunities"])
        with col2:
            st.metric("逾期商机数", global_stats["overdue_count"])
        with col3:
            st.metric("升级商机数", global_stats["escalation_count"])
        with col4:
            st.metric("涉及组织数", global_stats["organization_count"])
            st.caption("全部组织")
        with col5:
            overdue_org_count = len(set(opp.org_name for opp in overdue_opportunities)) if overdue_opportunities else 0
            st.metric("逾期涉及组织", overdue_org_count)
            st.caption("有逾期商机的组织")

        st.markdown("---")

        # 全局组织概览
        st.subheader("🌐 全局组织概览")
        if global_stats["organization_breakdown"]:
            org_overview_data = []
            for org_name, org_data in global_stats["organization_breakdown"].items():
                org_overview_data.append({
                    "组织名称": org_name,
                    "总商机数": org_data["total"],
                    "逾期商机数": org_data["overdue"],
                    "正常商机数": org_data["normal"],
                    "逾期率": f"{(org_data['overdue'] / org_data['total'] * 100):.1f}%" if org_data["total"] > 0 else "0%"
                })

            df_overview = pd.DataFrame(org_overview_data)
            st.dataframe(df_overview, use_container_width=True)

        # 逾期商机详细分析（仅当有逾期数据时显示）
        if overdue_opportunities:
            st.markdown("---")
            st.subheader("🚨 逾期商机详细分析")

            # 生成逾期商机报告
            report = calculator.generate_summary_report(overdue_opportunities)

            # 组织绩效对比（基于逾期商机）
            st.subheader("🏢 逾期商机组织分布")
            org_performance = report["组织绩效"]
            if org_performance:
                df_org = pd.DataFrame.from_dict(org_performance, orient='index')
                st.dataframe(df_org, use_container_width=True)

                # 绩效排名图表
                if "SLA达成率" in df_org.columns:
                    st.subheader("SLA达成率排名")
                    df_sorted = df_org.sort_values("SLA达成率", ascending=False)
                    st.bar_chart(df_sorted["SLA达成率"])

            # 时长分布
            st.subheader("⏱️ 逾期时长分布")
            time_distribution = report["时长分布"]
            if time_distribution:
                df_time = pd.DataFrame(list(time_distribution.items()), columns=["时长区间", "数量"])
                st.bar_chart(df_time.set_index("时长区间"))
        else:
            st.success("🎉 当前没有逾期商机，系统运行良好！")

    except Exception as e:
        st.error(f"获取业务分析数据失败: {e}")


def show_opportunity_list():
    """显示商机监控页面 - 重新设计为业务监控导向"""

    try:
        # 获取逾期商机数据
        opportunities = fetch_overdue_opportunities()

        if not opportunities:
            st.info("暂无逾期商机数据")
            return

        # 筛选器
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox(
                "状态筛选",
                ["全部"] + list(set(opp.order_status for opp in opportunities))
            )

        with col2:
            org_filter = st.selectbox(
                "组织筛选",
                ["全部"] + list(set(opp.org_name for opp in opportunities))
            )

        with col3:
            escalation_filter = st.selectbox(
                "升级筛选",
                ["全部", "需要升级", "标准处理"]
            )

        # 应用筛选
        filtered_opportunities = opportunities

        if status_filter != "全部":
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.order_status == status_filter]

        if org_filter != "全部":
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.org_name == org_filter]

        if escalation_filter == "需要升级":
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.escalation_level > 0]
        elif escalation_filter == "标准处理":
            filtered_opportunities = [opp for opp in filtered_opportunities if opp.escalation_level == 0]

        # 显示商机表格
        if filtered_opportunities:
            # 转换为DataFrame
            data = []
            for opp in filtered_opportunities:
                # 确保计算字段已更新
                opp.update_overdue_info(use_business_time=True)

                data.append({
                    "工单号": opp.order_num,
                    "客户": opp.name,
                    "地址": opp.address,
                    "负责人": opp.supervisor_name,
                    "组织": opp.org_name,
                    "状态": opp.order_status,
                    "创建时间": format_china_time(opp.create_time, "%Y-%m-%d %H:%M"),
                    "工作时长(小时)": f"{opp.elapsed_hours:.1f}",
                    "是否提醒": "💡 是" if getattr(opp, 'is_violation', False) else "否",
                    "是否升级": "🚨 是" if opp.is_overdue else "否",
                    "升级级别": opp.escalation_level,
                    "SLA进度": f"{(getattr(opp, 'sla_progress_ratio', 0) * 100):.1f}%"
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 操作按钮
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📤 导出数据"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="下载CSV文件",
                        data=csv,
                        file_name=f"opportunities_{now_china_naive().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

            with col2:
                if st.button("🔔 发送通知"):
                    with st.spinner("发送通知中..."):
                        try:
                            result = send_business_notifications(filtered_opportunities)
                            st.success(f"通知发送完成: 成功{result['sent']}个，失败{result['failed']}个")
                        except Exception as e:
                            st.error(f"发送通知失败: {e}")

            with col3:
                if st.button("🔄 刷新数据"):
                    st.rerun()
        else:
            st.info("没有找到符合条件的商机")

    except Exception as e:
        st.error(f"获取商机列表失败: {e}")


def show_execution_history():
    """显示Agent执行历史页面 - 重新设计版本"""

    try:
        from src.fsoa.agent.tools import get_execution_tracker
        tracker = get_execution_tracker()

        # 时间范围选择
        col_time1, col_time2 = st.columns(2)
        with col_time1:
            hours_back = st.selectbox(
                "查看时间范围",
                options=[24, 72, 168, 720],  # 1天, 3天, 1周, 1月
                format_func=lambda x: f"最近{x//24}天" if x >= 24 else f"最近{x}小时",
                index=2  # 默认1周
            )

        with col_time2:
            if st.button("🔄 刷新数据"):
                st.rerun()

        # 获取执行统计
        stats = tracker.get_run_statistics(hours_back)

        # 显示核心统计信息
        st.subheader("📈 执行统计概览")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "总运行次数",
                stats.get("total_runs", 0),
                help="指定时间范围内的总执行次数"
            )
        with col2:
            st.metric(
                "成功运行",
                stats.get("successful_runs", 0),
                delta=f"{stats.get('success_rate', 0):.1f}%"
            )
        with col3:
            st.metric(
                "失败运行",
                stats.get("failed_runs", 0),
                delta=f"-{100-stats.get('success_rate', 0):.1f}%" if stats.get('success_rate', 0) < 100 else None
            )
        with col4:
            st.metric(
                "平均耗时",
                f"{stats.get('average_duration_seconds', 0):.1f}秒",
                help="成功执行的平均耗时"
            )
        with col5:
            st.metric(
                "处理商机",
                stats.get("total_opportunities_processed", 0),
                help="总共处理的商机数量"
            )

        # 业务指标
        col_biz1, col_biz2 = st.columns(2)
        with col_biz1:
            st.metric(
                "发送通知",
                stats.get("total_notifications_sent", 0),
                help="总共发送的通知数量"
            )
        with col_biz2:
            if stats.get("total_runs", 0) > 0:
                avg_notifications = stats.get("total_notifications_sent", 0) / stats.get("total_runs", 1)
                st.metric(
                    "平均通知/次",
                    f"{avg_notifications:.1f}",
                    help="每次执行平均发送的通知数"
                )

        st.markdown("---")

        # 执行历史列表
        st.subheader("📋 最近执行记录")

        recent_runs = tracker.get_recent_runs(limit=20, hours_back=hours_back)

        if recent_runs:
            # 创建执行记录表格数据
            table_data = []
            for run in recent_runs:
                status_icon = {
                    "completed": "✅",
                    "failed": "❌",
                    "running": "🔄"
                }.get(run.status.value, "❓")

                duration = ""
                if run.duration_seconds:
                    if run.duration_seconds < 60:
                        duration = f"{run.duration_seconds:.1f}秒"
                    else:
                        duration = f"{run.duration_seconds/60:.1f}分钟"

                table_data.append({
                    "运行ID": run.id,
                    "状态": f"{status_icon} {run.status.value}",
                    "开始时间": run.trigger_time.strftime("%m-%d %H:%M:%S"),
                    "耗时": duration,
                    "处理商机": run.opportunities_processed,
                    "发送通知": run.notifications_sent,
                    "错误": len(run.errors) if run.errors else 0
                })

            # 显示表格
            import pandas as pd
            df = pd.DataFrame(table_data)

            # 选择要查看详情的运行
            selected_run_id = st.selectbox(
                "选择运行查看详情",
                options=[0] + [run.id for run in recent_runs],
                format_func=lambda x: "请选择..." if x == 0 else f"运行 #{x}",
                key="selected_run"
            )

            st.dataframe(df, use_container_width=True, hide_index=True)

            # 显示选中运行的详情
            if selected_run_id and selected_run_id != 0:
                show_run_details(tracker, selected_run_id)

        else:
            st.info("📝 暂无执行记录")
            st.markdown("**可能的原因:**")
            st.markdown("- Agent尚未运行过")
            st.markdown("- 选择的时间范围内没有执行记录")
            st.markdown("- 数据库连接问题")

        st.markdown("---")

        # 步骤性能分析
        st.subheader("🔧 步骤性能分析")

        # 获取所有步骤的性能数据
        common_steps = [
            ("fetch_opportunities", "获取商机数据"),
            ("process_opportunities", "处理商机逻辑"),
            ("send_notifications", "发送通知"),
            ("create_notification_tasks", "创建通知任务"),
            ("execute_notification_tasks", "执行通知任务")
        ]

        step_tabs = st.tabs([desc for _, desc in common_steps] + ["全部步骤"])

        for i, (step_name, step_desc) in enumerate(common_steps):
            with step_tabs[i]:
                show_step_performance(tracker, step_name, step_desc, hours_back)

        # 全部步骤标签页
        with step_tabs[-1]:
            show_step_performance(tracker, None, "所有步骤", hours_back)

    except Exception as e:
        st.error(f"❌ 获取执行历史失败: {e}")
        st.info("💡 **故障排除提示:**")
        st.markdown("- 检查数据库连接是否正常")
        st.markdown("- 确认Agent执行追踪器配置正确")
        st.markdown("- 查看系统日志获取详细错误信息")

        if st.button("🔧 重试加载"):
            st.rerun()


def show_run_details(tracker, run_id: int):
    """显示运行详情"""
    st.markdown("---")
    st.subheader(f"🔍 运行详情 #{run_id}")

    try:
        run_details = tracker.get_run_details(run_id)

        if not run_details:
            st.warning(f"未找到运行 #{run_id} 的详情")
            return

        run, history = run_details

        # 运行基本信息
        col_info1, col_info2, col_info3 = st.columns(3)

        with col_info1:
            st.metric("运行状态", run.status.value)
            st.metric("开始时间", run.trigger_time.strftime("%Y-%m-%d %H:%M:%S"))

        with col_info2:
            if run.end_time:
                st.metric("结束时间", run.end_time.strftime("%Y-%m-%d %H:%M:%S"))
                st.metric("总耗时", f"{run.duration_seconds:.2f}秒" if run.duration_seconds else "未知")
            else:
                st.metric("结束时间", "运行中...")

        with col_info3:
            st.metric("处理商机", run.opportunities_processed)
            st.metric("发送通知", run.notifications_sent)

        # 错误信息
        if run.errors:
            st.error("❌ 执行错误:")
            for error in run.errors:
                st.code(error)

        # 执行上下文
        if run.context:
            with st.expander("📋 执行上下文"):
                st.json(run.context)

        # 步骤执行历史
        if history:
            st.subheader("📝 执行步骤")

            for i, step in enumerate(history, 1):
                status_icon = "❌" if step.error_message else "✅"
                duration_text = f" ({step.duration_seconds:.2f}s)" if step.duration_seconds else ""

                with st.expander(f"{status_icon} {i}. {step.step_name}{duration_text}"):
                    col_step1, col_step2 = st.columns(2)

                    with col_step1:
                        st.write("**执行时间:**", step.timestamp.strftime("%H:%M:%S"))
                        if step.duration_seconds:
                            st.write("**耗时:**", f"{step.duration_seconds:.2f}秒")

                    with col_step2:
                        if step.error_message:
                            st.error(f"错误: {step.error_message}")

                    # 输入数据
                    if step.input_data:
                        st.write("**输入数据:**")
                        st.json(step.input_data)

                    # 输出数据
                    if step.output_data:
                        st.write("**输出数据:**")
                        st.json(step.output_data)
        else:
            st.info("该运行没有详细的步骤记录")

    except Exception as e:
        st.error(f"获取运行详情失败: {e}")


def show_step_performance(tracker, step_name: str, step_desc: str, hours_back: int):
    """显示步骤性能信息"""
    try:
        perf = tracker.get_step_performance(step_name, hours_back)

        if perf.get("total_executions", 0) == 0:
            st.info(f"📝 {step_desc}: 暂无执行记录")
            return

        # 性能指标
        col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)

        with col_perf1:
            st.metric("执行次数", perf.get("total_executions", 0))

        with col_perf2:
            st.metric(
                "成功次数",
                perf.get("successful_executions", 0),
                delta=f"{perf.get('success_rate', 0):.1f}%"
            )

        with col_perf3:
            st.metric("失败次数", perf.get("failed_executions", 0))

        with col_perf4:
            st.metric("平均耗时", f"{perf.get('average_duration_seconds', 0):.2f}秒")

        # 性能详情
        if perf.get("min_duration_seconds", 0) > 0 or perf.get("max_duration_seconds", 0) > 0:
            col_detail1, col_detail2 = st.columns(2)

            with col_detail1:
                st.metric("最快执行", f"{perf.get('min_duration_seconds', 0):.2f}秒")

            with col_detail2:
                st.metric("最慢执行", f"{perf.get('max_duration_seconds', 0):.2f}秒")

        # 成功率进度条
        success_rate = perf.get("success_rate", 0)
        st.progress(success_rate / 100, text=f"成功率: {success_rate:.1f}%")

    except Exception as e:
        st.error(f"获取{step_desc}性能数据失败: {e}")


def show_notification_management():
    """显示通知任务管理页面"""
    st.header("🔔 通知管理")

    try:
        from src.fsoa.agent.tools import get_notification_manager

        manager = get_notification_manager()

        # 时间范围选择
        col_time1, col_time2 = st.columns(2)
        with col_time1:
            hours_back = st.selectbox("统计时间范围", [1, 6, 12, 24, 48, 168], index=3, format_func=lambda x: f"最近{x}小时")
        with col_time2:
            if st.button("🔄 刷新数据"):
                st.rerun()

        # 获取通知统计
        stats = manager.get_notification_statistics(hours_back=hours_back)

        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total = stats.get("total_tasks", 0)
            st.metric("总任务数", total)
        with col2:
            sent = stats.get("sent_count", 0)
            success_rate = (sent / total * 100) if total > 0 else 0
            st.metric("已发送", sent, delta=f"{success_rate:.1f}%")
        with col3:
            failed = stats.get("failed_count", 0)
            failure_rate = (failed / total * 100) if total > 0 else 0
            st.metric("发送失败", failed, delta=f"{failure_rate:.1f}%", delta_color="inverse")
        with col4:
            pending = stats.get("pending_count", 0)
            st.metric("待处理", pending)

        # 显示错误信息（如果有）
        if "error" in stats:
            st.error(f"获取统计数据时出错: {stats['error']}")

        # 显示时间范围信息
        if "start_time" in stats and "end_time" in stats:
            st.caption(f"📅 统计时间范围: {stats['start_time']} ~ {stats['end_time']}")

        st.markdown("---")

        # 创建选项卡
        tab1, tab2, tab3 = st.tabs(["📋 待处理任务", "📊 任务历史", "🔧 管理操作"])

        with tab1:
            # 待处理任务列表
            st.subheader("待处理任务")
            pending_tasks = manager.db_manager.get_pending_notification_tasks()

            if pending_tasks:
                for task in pending_tasks:
                    # 根据通知类型设置图标
                    type_icons = {
                        "reminder": "💡",
                        "escalation": "🚨",
                        "violation": "🚨",  # 向后兼容
                        "standard": "📬"   # 向后兼容
                    }
                    icon = type_icons.get(task.notification_type.value, "📬")

                    # 根据类型设置标题颜色
                    type_names = {
                        "reminder": "提醒通知",
                        "escalation": "升级通知",
                        "violation": "违规通知",  # 向后兼容
                        "standard": "标准通知"   # 向后兼容
                    }
                    type_name = type_names.get(task.notification_type.value, task.notification_type.value)

                    with st.expander(f"{icon} 任务 {task.id} - {task.order_num} ({type_name})"):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.write(f"**工单号**: {task.order_num}")
                            st.write(f"**组织**: {task.org_name}")
                            st.write(f"**类型**: {type_name}")
                        with col_b:
                            st.write(f"**状态**: {task.status.value}")
                            st.write(f"**应发送时间**: {task.due_time}")
                            st.write(f"**重试次数**: {task.retry_count}/{getattr(task, 'max_retry_count', 5)}")
                        with col_c:
                            st.write(f"**冷静时间**: {getattr(task, 'cooldown_hours', 2.0)}小时")
                            if hasattr(task, 'last_sent_at') and task.last_sent_at:
                                st.write(f"**最后发送**: {format_china_time(task.last_sent_at, '%m-%d %H:%M')}")
                            else:
                                st.write(f"**最后发送**: 未发送")

                            # 显示是否在冷静期
                            if hasattr(task, 'is_in_cooldown') and task.is_in_cooldown:
                                st.warning("⏰ 冷静期内")
                            elif hasattr(task, 'can_retry') and not task.can_retry:
                                st.error("❌ 无法重试")
                            else:
                                st.success("✅ 可发送")

                        if task.message:
                            st.write(f"**消息内容**: {task.message}")
            else:
                st.info("📭 当前没有待处理的通知任务")

        with tab2:
            # 任务历史
            st.subheader("任务历史")

            # 获取最近的任务历史
            try:
                from src.fsoa.data.database import NotificationTaskTable
                with manager.db_manager.get_session() as session:
                    recent_tasks = session.query(NotificationTaskTable).order_by(
                        NotificationTaskTable.created_at.desc()
                    ).limit(20).all()

                    if recent_tasks:
                        history_data = []
                        for task in recent_tasks:
                            history_data.append({
                                "任务ID": task.id,
                                "工单号": task.order_num,
                                "组织": task.org_name,
                                "类型": task.notification_type,
                                "状态": task.status,
                                "创建时间": task.created_at.strftime("%m-%d %H:%M"),
                                "发送时间": task.sent_at.strftime("%m-%d %H:%M") if task.sent_at else "-",
                                "重试次数": task.retry_count
                            })

                        import pandas as pd
                        df_history = pd.DataFrame(history_data)
                        st.dataframe(df_history, use_container_width=True, hide_index=True)
                    else:
                        st.info("📭 暂无任务历史")
            except Exception as e:
                st.error(f"获取任务历史失败: {e}")

        with tab3:
            # 管理操作
            st.subheader("管理操作")

            col_op1, col_op2 = st.columns(2)

            with col_op1:
                st.markdown("**任务管理**")
                if st.button("🔄 刷新任务列表", use_container_width=True):
                    st.rerun()

                if st.button("🧹 清理旧任务", use_container_width=True):
                    try:
                        cleaned = manager.cleanup_old_tasks()
                        st.success(f"✅ 已清理 {cleaned} 个旧任务")
                    except Exception as e:
                        st.error(f"清理失败: {e}")

            with col_op2:
                st.markdown("**配置管理**")
                if st.button("🔧 企微配置", use_container_width=True):
                    st.session_state.page = "wechat_config"
                    st.rerun()

                if st.button("⚙️ 系统设置", use_container_width=True):
                    st.session_state.page = "system_settings"
                    st.rerun()

            # 企微配置状态检查
            st.markdown("---")
            st.markdown("**🔧 企微配置状态**")

            try:
                from src.fsoa.data.database import get_database_manager
                from src.fsoa.utils.config import get_config

                db_manager = get_database_manager()
                config = get_config()

                # 检查配置状态
                group_configs = db_manager.get_enabled_group_configs()
                internal_webhook = config.internal_ops_webhook_url

                total_webhooks = len([gc for gc in group_configs if gc.webhook_url])
                has_internal = bool(internal_webhook)

                if total_webhooks > 0 and has_internal:
                    st.success("✅ 企微配置正常，通知可以正常发送")
                    st.info(f"📊 已配置 {total_webhooks} 个组织群 + 1 个运营群")
                else:
                    missing = []
                    if not has_internal:
                        missing.append("内部运营群")
                    if total_webhooks == 0:
                        missing.append("组织群")
                    st.warning(f"⚠️ 企微配置缺少: {'/'.join(missing)}")
            except Exception as e:
                st.error(f"无法检查企微配置: {e}")



    except Exception as e:
        st.error(f"获取通知管理数据失败: {e}")


def show_cache_management():
    """显示缓存管理页面"""
    try:
        from src.fsoa.agent.tools import get_data_strategy

        data_strategy = get_data_strategy()

        # 获取缓存统计
        cache_stats = data_strategy.get_cache_statistics()

        # 显示缓存状态（重构后的清空重建模式）
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("缓存状态", "启用" if cache_stats.get("cache_enabled", False) else "禁用")
        with col2:
            st.metric("缓存条目", cache_stats.get("total_cached", 0))
        with col3:
            st.metric("数据模式", "清空重建")
        with col4:
            st.metric("命中率", f"{cache_stats.get('cache_hit_ratio', 0):.1%}")

        st.markdown("---")

        # 缓存详情
        st.subheader("📊 缓存详情")

        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**TTL设置**: {cache_stats.get('cache_ttl_hours', 0)} 小时")
            st.write(f"**逾期缓存**: {cache_stats.get('overdue_cached', 0)} 个")
        with col_b:
            st.write(f"**涉及组织**: {cache_stats.get('organizations', 0)} 个")
            st.write(f"**缓存启用**: {'是' if data_strategy.cache_enabled else '否'}")

        st.markdown("---")

        # 缓存操作
        st.subheader("🔧 缓存操作")

        col_x, col_y, col_z = st.columns(3)

        with col_x:
            if st.button("🔄 完全刷新缓存"):
                try:
                    with st.spinner("正在从Metabase获取最新数据并完全刷新缓存..."):
                        old_count, new_count = data_strategy.refresh_cache()
                        st.success(f"✅ 缓存已完全刷新: {old_count} → {new_count}")
                        st.info("💡 采用清空重建模式，确保数据完全同步")
                except Exception as e:
                    st.error(f"刷新缓存失败: {e}")

        with col_y:
            if st.button("🧹 清空缓存"):
                try:
                    with st.spinner("正在清空所有缓存数据..."):
                        cleared = data_strategy.clear_cache()
                        st.success(f"✅ 已清空 {cleared} 个缓存条目")
                        st.info("💡 下次获取数据时将直接从Metabase同步")
                except Exception as e:
                    st.error(f"清空缓存失败: {e}")

        with col_z:
            if st.button("🔍 验证一致性"):
                try:
                    with st.spinner("正在验证数据一致性..."):
                        consistency = data_strategy.validate_data_consistency()
                        if consistency.get("data_consistent", False):
                            st.success("✅ 数据一致性验证通过")
                        else:
                            st.warning("⚠️ 发现数据不一致")

                        st.write(f"缓存数据: {consistency.get('cached_count', 0)}")
                        st.write(f"源数据: {consistency.get('fresh_count', 0)}")
                except Exception as e:
                    st.error(f"一致性验证失败: {e}")

    except Exception as e:
        st.error(f"获取缓存管理数据失败: {e}")


def show_wechat_config():
    """显示企微群配置页面 - 数据库+.env混合配置管理"""

    # 配置状态概览
    st.subheader("📊 配置状态概览")

    try:
        from src.fsoa.data.database import get_database_manager
        from src.fsoa.utils.config import get_config

        db_manager = get_database_manager()
        config = get_config()

        # 获取配置状态
        group_configs = db_manager.get_enabled_group_configs()
        internal_webhook = config.internal_ops_webhook_url

        # 状态指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            enabled_orgs = len(group_configs)
            total_orgs = len(db_manager.get_group_configs())
            st.metric(
                "组织群配置",
                f"{enabled_orgs}/{total_orgs}",
                delta="完整" if enabled_orgs == total_orgs else f"{total_orgs - enabled_orgs}个禁用",
                delta_color="normal" if enabled_orgs == total_orgs else "inverse"
            )

        with col2:
            st.metric(
                "内部运营群",
                "已配置" if internal_webhook else "未配置",
                delta="正常" if internal_webhook else "需要配置",
                delta_color="normal" if internal_webhook else "inverse"
            )

        with col3:
            total_webhooks = len([gc for gc in group_configs if gc.webhook_url])
            st.metric(
                "有效Webhook",
                f"{total_webhooks}个",
                delta="已配置" if total_webhooks > 0 else "未配置",
                delta_color="normal" if total_webhooks > 0 else "inverse"
            )

        with col4:
            avg_cooldown = sum(gc.notification_cooldown_minutes for gc in group_configs) / len(group_configs) if group_configs else 0
            st.metric(
                "平均冷却时间",
                f"{avg_cooldown:.0f}分钟",
                delta="正常" if 15 <= avg_cooldown <= 60 else "需调整",
                delta_color="normal" if 15 <= avg_cooldown <= 60 else "inverse"
            )

        # 配置完整性检查
        st.markdown("---")
        st.subheader("🔍 配置完整性检查")

        # 检查配置问题
        issues = []
        if not internal_webhook:
            issues.append("内部运营群Webhook未配置")
        if total_webhooks == 0:
            issues.append("没有配置任何组织群Webhook")

        # 检查webhook格式
        for gc in group_configs:
            if gc.webhook_url and not gc.webhook_url.startswith("https://qyapi.weixin.qq.com/"):
                issues.append(f"组织群 {gc.name} 的Webhook格式无效")

        if len(issues) == 0:
            st.success("✅ 所有配置都正确！Agent可以正常发送通知")
        else:
            st.error(f"❌ 发现 {len(issues)} 个配置问题，可能影响通知发送")
            for issue in issues:
                st.write(f"• {issue}")

        # 快速操作
        st.markdown("---")
        st.subheader("⚡ 快速操作")

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            if st.button("🔧 详细配置", type="primary", use_container_width=True):
                st.session_state.show_detailed_config = True
                st.rerun()

        # 新增组织群配置
        st.markdown("---")
        st.subheader("➕ 新增组织群配置")

        with st.form("add_org_config"):
            col_form1, col_form2 = st.columns(2)

            with col_form1:
                new_org_name = st.text_input(
                    "组织名称 (orgName)",
                    placeholder="例如: 北京分公司",
                    help="必须与Metabase数据中的orgName完全一致"
                )

            with col_form2:
                new_webhook_url = st.text_input(
                    "企微群Webhook地址",
                    placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...",
                    help="从企微群机器人获取的Webhook URL"
                )

            col_submit1, col_submit2, col_submit3 = st.columns([1, 1, 2])

            with col_submit1:
                submitted = st.form_submit_button("✅ 添加配置", type="primary")

            with col_submit2:
                if st.form_submit_button("🧪 测试URL"):
                    if new_webhook_url:
                        if new_webhook_url.startswith("https://qyapi.weixin.qq.com/"):
                            st.success("✅ Webhook URL格式正确")
                        else:
                            st.error("❌ Webhook URL格式无效")
                    else:
                        st.warning("请输入Webhook URL")

            if submitted:
                if new_org_name and new_webhook_url:
                    try:
                        # 检查是否已存在
                        existing_configs = db_manager.get_group_configs()
                        if any(gc.group_id == new_org_name for gc in existing_configs):
                            st.error(f"❌ 组织 '{new_org_name}' 已存在，请使用不同的名称")
                        elif not new_webhook_url.startswith("https://qyapi.weixin.qq.com/"):
                            st.error("❌ Webhook URL格式无效，必须以 https://qyapi.weixin.qq.com/ 开头")
                        else:
                            # 创建新配置
                            new_config = db_manager.create_or_update_group_config(
                                group_id=new_org_name,
                                name=new_org_name,
                                webhook_url=new_webhook_url,
                                enabled=True
                            )
                            if new_config:
                                st.success(f"✅ 成功添加组织群配置: {new_org_name}")
                                st.rerun()
                            else:
                                st.error("❌ 添加配置失败，请检查数据库连接")
                    except Exception as e:
                        st.error(f"❌ 添加配置时发生错误: {e}")
                else:
                    st.warning("⚠️ 请填写完整的组织名称和Webhook地址")

        with col_b:
            if st.button("🧪 测试通知", use_container_width=True):
                st.session_state.test_notification = True
                st.rerun()

        with col_c:
            if st.button("📤 导出配置", use_container_width=True):
                # 导出当前配置
                import json
                export_data = {
                    "internal_ops_webhook": internal_webhook,
                    "group_configs": [
                        {
                            "group_id": gc.group_id,
                            "name": gc.name,
                            "webhook_url": gc.webhook_url,
                            "enabled": gc.enabled
                        } for gc in db_manager.get_group_configs()
                    ]
                }
                config_json = json.dumps(export_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载配置文件",
                    data=config_json,
                    file_name="wechat_config.json",
                    mime="application/json"
                )

        with col_d:
            if st.button("🔄 刷新状态", use_container_width=True):
                st.rerun()

        # 显示详细配置界面
        if st.session_state.get("show_detailed_config", False):
            st.markdown("---")
            show_detailed_config(db_manager, config)

        # 显示测试通知界面
        if st.session_state.get("test_notification", False):
            st.markdown("---")
            show_notification_test(db_manager, config)

    except Exception as e:
        st.error(f"获取企微配置失败: {e}")
        st.info("💡 提示: 企微配置是Agent通知功能的基础，请确保正确配置")


def show_notification_test(db_manager, config):
    """显示通知测试界面"""
    st.subheader("🧪 通知测试")

    test_type = st.selectbox(
        "选择测试类型",
        ["组织群通知", "内部运营群通知"]
    )

    if test_type == "组织群通知":
        group_configs = db_manager.get_enabled_group_configs()
        if group_configs:
            org_options = {gc.name: gc for gc in group_configs if gc.webhook_url}
            if org_options:
                org_name = st.selectbox("选择组织", list(org_options.keys()))

                if st.button("发送测试消息"):
                    selected_config = org_options[org_name]
                    st.info(f"正在向 {org_name} 发送测试消息...")

                    try:
                        # 导入企微客户端
                        from src.fsoa.notification.wechat import get_wechat_client
                        from datetime import datetime

                        # 获取企微客户端
                        wechat_client = get_wechat_client()

                        # 构造测试消息
                        test_message = f"""🧪 FSOA系统测试消息

组织: {org_name}
时间: {format_china_time(now_china_naive())}
状态: 测试通知功能正常

这是一条来自FSOA系统的测试消息，用于验证企微群通知功能是否正常工作。"""

                        # 发送测试消息
                        success = wechat_client.send_notification_to_org(
                            org_name=org_name,
                            content=test_message,
                            is_escalation=False
                        )

                        if success:
                            st.success(f"✅ 测试消息发送成功！请检查 {org_name} 的企微群。")
                        else:
                            st.error(f"❌ 测试消息发送失败！请检查webhook配置和网络连接。")

                    except Exception as e:
                        st.error(f"❌ 发送测试消息时发生错误: {e}")
                        st.exception(e)
            else:
                st.warning("没有配置有效的组织群Webhook")
        else:
            st.warning("没有启用的组织群配置")

    else:  # 内部运营群通知
        if st.button("发送内部运营群测试消息"):
            st.info("正在向内部运营群发送测试消息...")

            try:
                # 导入企微客户端
                from src.fsoa.notification.wechat import get_wechat_client
                from datetime import datetime

                # 获取企微客户端
                wechat_client = get_wechat_client()

                # 构造测试消息
                test_message = f"""🚨 FSOA内部运营群测试消息

时间: {format_china_time(now_china_naive())}
类型: 升级通知测试
状态: 系统功能正常

这是一条来自FSOA系统的内部运营群测试消息，用于验证升级通知功能是否正常工作。"""

                # 发送升级通知测试消息
                success = wechat_client.send_notification_to_org(
                    org_name="内部运营群",
                    content=test_message,
                    is_escalation=True
                )

                if success:
                    st.success("✅ 内部运营群测试消息发送成功！请检查内部运营群。")
                else:
                    st.error("❌ 内部运营群测试消息发送失败！请检查内部运营群webhook配置。")

            except Exception as e:
                st.error(f"❌ 发送内部运营群测试消息时发生错误: {e}")
                st.exception(e)



    if st.button("关闭测试"):
        st.session_state.test_notification = False
        st.rerun()

def show_detailed_config(db_manager, config):
    """显示详细配置界面"""
    st.subheader("🔧 详细配置管理")

    # 组织群配置
    st.markdown("### 组织群配置")
    group_configs = db_manager.get_group_configs()

    if group_configs:
        for i, gc in enumerate(group_configs):
            with st.expander(f"{'✅' if gc.enabled else '❌'} {gc.name} ({gc.group_id})"):
                col_info, col_actions = st.columns([3, 1])

                with col_info:
                    st.write(f"**Webhook URL:** {gc.webhook_url or '未配置'}")
                    st.write(f"**状态:** {'启用' if gc.enabled else '禁用'}")
                    st.write(f"**冷却时间:** {gc.notification_cooldown_minutes} 分钟")
                    st.write(f"**最大通知数/小时:** {gc.max_notifications_per_hour}")

                with col_actions:
                    # 启用/禁用按钮
                    if gc.enabled:
                        if st.button(f"🔴 禁用", key=f"disable_{gc.group_id}"):
                            try:
                                db_manager.create_or_update_group_config(
                                    group_id=gc.group_id,
                                    name=gc.name,
                                    webhook_url=gc.webhook_url,
                                    enabled=False
                                )
                                st.success(f"已禁用 {gc.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"禁用失败: {e}")
                    else:
                        if st.button(f"🟢 启用", key=f"enable_{gc.group_id}"):
                            try:
                                db_manager.create_or_update_group_config(
                                    group_id=gc.group_id,
                                    name=gc.name,
                                    webhook_url=gc.webhook_url,
                                    enabled=True
                                )
                                st.success(f"已启用 {gc.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"启用失败: {e}")

                    # 删除按钮
                    if st.button(f"🗑️ 删除", key=f"delete_{gc.group_id}"):
                        try:
                            if db_manager.delete_group_config(gc.group_id):
                                st.success(f"已删除 {gc.name}")
                                st.rerun()
                            else:
                                st.error("删除失败")
                        except Exception as e:
                            st.error(f"删除失败: {e}")

                # 编辑Webhook URL
                with st.form(f"edit_webhook_{gc.group_id}"):
                    new_webhook = st.text_input(
                        "更新Webhook URL",
                        value=gc.webhook_url or "",
                        key=f"webhook_input_{gc.group_id}"
                    )
                    if st.form_submit_button("💾 更新"):
                        if new_webhook and new_webhook.startswith("https://qyapi.weixin.qq.com/"):
                            try:
                                db_manager.create_or_update_group_config(
                                    group_id=gc.group_id,
                                    name=gc.name,
                                    webhook_url=new_webhook,
                                    enabled=gc.enabled
                                )
                                st.success(f"已更新 {gc.name} 的Webhook")
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新失败: {e}")
                        else:
                            st.error("请输入有效的企微Webhook URL")
    else:
        st.info("暂无组织群配置，请使用上方的'新增组织群配置'功能添加")

    # 内部运营群配置
    st.markdown("### 内部运营群配置")
    internal_webhook = config.internal_ops_webhook_url
    if internal_webhook:
        st.success(f"✅ 已配置: {internal_webhook[:50]}...")
    else:
        st.error("❌ 未配置内部运营群Webhook")
        st.info("请在 .env 文件中设置 INTERNAL_OPS_WEBHOOK")

    if st.button("关闭详细配置"):
        st.session_state.show_detailed_config = False
        st.rerun()


def show_about():
    """显示关于页面 - Agent智能化价值介绍"""
    # Agent智能化价值展示
    st.subheader("Agent智能化价值")

    col_value1, col_value2, col_value3 = st.columns(3)

    with col_value1:
        st.info("**主动监控**\n\n• 7x24小时自动扫描\n• 实时识别超时风险\n• 无需人工干预")

    with col_value2:
        st.info("**智能决策**\n\n• 规则引擎+LLM混合决策\n• 基于上下文智能判断\n• 自适应策略调整")

    with col_value3:
        # 检查企微配置状态
        try:
            from src.fsoa.data.database import get_database_manager
            from src.fsoa.utils.config import get_config

            db_manager = get_database_manager()
            config = get_config()

            # 检查配置状态
            group_configs = db_manager.get_enabled_group_configs()
            internal_webhook = config.internal_ops_webhook_url

            total_webhooks = len([gc for gc in group_configs if gc.webhook_url])
            has_internal = bool(internal_webhook)

            if total_webhooks > 0 and has_internal:
                st.success("**自动通知**\n\n• 多企微群差异化通知\n• 智能去重和频率控制\n• 升级机制自动触发\n\n企微配置: 正常")
            else:
                missing = []
                if not has_internal:
                    missing.append("内部运营群")
                if total_webhooks == 0:
                    missing.append("组织群")
                st.warning(f"**自动通知**\n\n• 多企微群差异化通知\n• 智能去重和频率控制\n• 升级机制自动触发\n\n企微配置: 缺少{'/'.join(missing)}")
        except:
            st.info("**自动通知**\n\n• 多企微群差异化通知\n• 智能去重和频率控制\n• 升级机制自动触发\n\n企微配置: 检查中...")

    st.markdown("---")

    # 系统架构
    st.subheader("系统架构")
    st.markdown("""
    **FSOA** (Field Service Operations Assistant) 是一个基于 LangGraph 的智能Agent系统，专为现场服务运营管理设计：

    **核心组件：**
    - **Agent Orchestrator**: 基于LangGraph的智能编排引擎
    - **Decision Engine**: 规则+LLM的混合决策系统
    - **Tool Layer**: 标准化的工具函数集合
    - **Data Layer**: 统一的数据访问和存储层
    - **UI Layer**: 基于Streamlit的管理界面

    **业务价值：**
    - 自动监控现场服务SLA合规性
    - 智能识别超时风险并主动预警
    - 多渠道差异化通知机制
    - 完整的执行追踪和性能分析
    """)

    st.markdown("---")

    # 技术特性
    st.subheader("技术特性")

    col_tech1, col_tech2 = st.columns(2)

    with col_tech1:
        st.markdown("""
        **Agent能力:**
        - 定时执行：基于Cron的自动化调度
        - 状态管理：完整的执行状态追踪
        - 错误处理：异常捕获和自动恢复
        - 工具调用：标准化的Function Calling
        """)

    with col_tech2:
        st.markdown("""
        **业务功能:**
        - 分级通知：orgName智能路由，标准通知和升级通知
        - 业务分析：逾期率、处理时长、组织绩效实时分析
        - 商机管理：逾期商机列表、筛选、导出功能
        - 格式化通知：按业务需求格式化工单详情和滞留时长
        """)

    st.markdown("---")

    # 版本信息
    st.subheader("版本信息")

    col_ver1, col_ver2, col_ver3 = st.columns(3)

    with col_ver1:
        st.info("**当前版本**\n\nv1.0.0")

    with col_ver2:
        st.info("**更新日期**\n\n2025-06-26")

    with col_ver3:
        st.info("**开发状态**\n\n生产就绪")

    # 快速链接
    st.markdown("---")
    st.subheader("快速链接")

    col_link1, col_link2, col_link3, col_link4 = st.columns(4)

    with col_link1:
        if st.button("运营仪表板", use_container_width=True, key="about_dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

    with col_link2:
        if st.button("Agent控制台", use_container_width=True, key="about_agent"):
            st.session_state.page = "agent_control"
            st.rerun()

    with col_link3:
        if st.button("企微群配置", use_container_width=True, key="about_wechat"):
            st.session_state.page = "wechat_config"
            st.rerun()

    with col_link4:
        if st.button("系统设置", use_container_width=True, key="about_settings"):
            st.session_state.page = "system_settings"
            st.rerun()


def show_llm_monitor():
    """显示LLM监控页面"""
    try:
        from src.fsoa.ui.llm_monitor import render_llm_monitor
        render_llm_monitor()
    except ImportError as e:
        st.error(f"LLM监控模块导入失败: {e}")
        st.markdown("### 🤖 LLM监控功能")
        st.info("LLM监控功能正在开发中，请稍后再试。")
    except Exception as e:
        st.error(f"LLM监控页面加载失败: {e}")
        logger.error(f"LLM monitor error: {e}")


if __name__ == "__main__":
    main()
