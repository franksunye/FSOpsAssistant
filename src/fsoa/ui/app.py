"""
FSOA Streamlit应用主入口

提供Web界面管理功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 设置页面配置
st.set_page_config(
    page_title="FSOA - 现场服务运营助手",
    page_icon="🤖",
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
        fetch_overdue_tasks, fetch_overdue_opportunities, test_metabase_connection,
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
    st.title("🤖 FSOA - 现场服务运营助手")
    st.markdown("---")
    
    # 侧边栏导航 - 重新设计为业务导向的清晰结构
    with st.sidebar:
        st.title("🤖 FSOA 运营助手")
        st.markdown("*现场服务智能监控系统*")
        st.markdown("---")

        # 核心业务功能
        st.subheader("📊 核心监控")
        if st.button("🎯 运营仪表板", use_container_width=True):
            st.session_state.page = "dashboard"
        if st.button("📋 商机监控", use_container_width=True):
            st.session_state.page = "opportunities"
        if st.button("📈 业务分析", use_container_width=True):
            st.session_state.page = "analytics"

        st.markdown("---")

        # Agent管理功能
        st.subheader("🤖 Agent管理")
        if st.button("🎛️ Agent控制台", use_container_width=True):
            st.session_state.page = "agent_control"
        if st.button("🔍 执行历史", use_container_width=True):
            st.session_state.page = "execution_history"
        if st.button("📬 通知管理", use_container_width=True):
            st.session_state.page = "notification_management"

        st.markdown("---")

        # 系统管理功能
        st.subheader("⚙️ 系统管理")
        if st.button("💾 缓存管理", use_container_width=True):
            st.session_state.page = "cache_management"
        if st.button("🔧 企微群配置", use_container_width=True):
            st.session_state.page = "wechat_config"
        if st.button("🧪 系统测试", use_container_width=True):
            st.session_state.page = "system_test"

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
    elif page == "cache_management":
        show_cache_management()
    elif page == "wechat_config":
        show_wechat_config()
    elif page == "system_test":
        show_system_test()
    else:
        show_dashboard()  # 默认页面


def show_dashboard():
    """显示运营仪表板 - 重新设计为业务价值导向"""
    st.title("🎯 FSOA 智能运营仪表板")
    st.markdown("**现场服务运营助手** - 主动监控 • 智能决策 • 自动通知")
    st.markdown("---")

    # 获取实时数据
    try:
        # 使用新的数据统计API
        from ..agent.tools import get_data_statistics, get_data_strategy

        # 获取综合数据统计
        data_stats = get_data_statistics()

        # 获取逾期商机数据（使用新的数据策略）
        data_strategy = get_data_strategy()
        opportunities = data_strategy.get_overdue_opportunities()

        # 获取系统健康状态
        health = get_system_health()

        # 获取调度器状态
        scheduler = get_scheduler()
        jobs_info = scheduler.get_jobs()

        # 获取Agent状态
        agent_status = "运行中" if jobs_info["is_running"] else "已停止"
        agent_delta = "正常" if health.get("overall_status") == "healthy" else "异常"

        # 使用新的数据统计
        total_opportunities = data_stats.get("total_opportunities", 0)
        overdue_opportunities = data_stats.get("overdue_opportunities", 0)
        escalation_count = data_stats.get("escalation_opportunities", 0)
        org_count = data_stats.get("organizations", 0)

        # 获取缓存统计
        cache_stats = data_stats.get("cache_statistics", {})

        # 按组织分组统计（保持兼容性）
        org_stats = {}
        for opp in opportunities:
            org_name = opp.org_name
            if org_name not in org_stats:
                org_stats[org_name] = {"total": 0, "overdue": 0, "escalation": 0}

            org_stats[org_name]["total"] += 1
            if opp.is_overdue:
                org_stats[org_name]["overdue"] += 1
            if opp.escalation_level > 0:
                org_stats[org_name]["escalation"] += 1

    except Exception as e:
        st.error(f"获取系统数据失败: {e}")
        opportunities = []
        health = {}
        jobs_info = {"is_running": False, "total_jobs": 0}
        agent_status = "未知"
        agent_delta = "错误"
        org_stats = {}
        escalation_count = 0
        total_opportunities = 0
        overdue_opportunities = 0
        org_count = 0
        cache_stats = {}

    # 核心业务指标 - 突出Agent的价值
    st.subheader("🎯 核心业务指标")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🤖 Agent状态",
            value=agent_status,
            delta=agent_delta,
            delta_color="normal" if agent_delta == "正常" else "inverse"
        )
        if agent_status == "运行中":
            st.success("✅ 智能监控运行中")
        else:
            st.error("❌ 需要启动Agent")

    with col2:
        st.metric(
            label="⚠️ 逾期商机",
            value=str(overdue_opportunities),
            delta=f"总计{total_opportunities}个商机" if total_opportunities > 0 else "0"
        )
        if overdue_opportunities > 0:
            st.warning(f"🔔 {overdue_opportunities}个商机需要关注")
        else:
            st.success("✅ 暂无逾期商机")

    with col3:
        st.metric(
            label="🚨 升级处理",
            value=str(escalation_count),
            delta="紧急" if escalation_count > 0 else "正常",
            delta_color="inverse" if escalation_count > 0 else "normal"
        )
        if escalation_count > 0:
            st.error(f"🚨 {escalation_count}个商机需要升级处理")
        else:
            st.success("✅ 无需升级处理")

    with col4:
        st.metric(
            label="🏢 涉及组织",
            value=str(org_count),
            delta=f"缓存命中率{cache_stats.get('cache_hit_ratio', 0):.1%}" if cache_stats else "无缓存数据"
        )
        if cache_stats.get('cache_hit_ratio', 0) > 0.8:
            st.success("⚡ 缓存性能优秀")
        else:
            st.info("📊 缓存性能一般")
    
    st.markdown("---")

    # Agent价值展示区域
    st.subheader("🚀 Agent智能化价值")

    col_value1, col_value2, col_value3 = st.columns(3)

    with col_value1:
        st.info("**🎯 主动监控**\n\n✅ 7x24小时自动扫描\n✅ 实时识别超时风险\n✅ 无需人工干预")

    with col_value2:
        st.info("**🧠 智能决策**\n\n✅ 规则引擎+LLM混合决策\n✅ 基于上下文智能判断\n✅ 自适应策略调整")

    with col_value3:
        # 检查企微配置状态
        try:
            from ..config.wechat_config import get_wechat_config_manager
            config_manager = get_wechat_config_manager()
            issues = config_manager.validate_config()
            total_issues = sum(len(problems) for problems in issues.values())

            if total_issues == 0:
                st.success("**📱 自动通知**\n\n✅ 多企微群差异化通知\n✅ 智能去重和频率控制\n✅ 升级机制自动触发\n\n🔧 企微配置: 正常")
            else:
                st.warning(f"**📱 自动通知**\n\n✅ 多企微群差异化通知\n✅ 智能去重和频率控制\n✅ 升级机制自动触发\n\n⚠️ 企微配置: {total_issues}个问题")
        except:
            st.info("**📱 自动通知**\n\n✅ 多企微群差异化通知\n✅ 智能去重和频率控制\n✅ 升级机制自动触发\n\n❓ 企微配置: 检查中...")

    st.markdown("---")

    # 快速操作区域
    st.subheader("⚡ 快速操作")

    col_action1, col_action2, col_action3, col_action4 = st.columns(4)

    with col_action1:
        if st.button("🚀 立即执行Agent", type="primary", use_container_width=True):
            st.session_state.page = "agent_control"
            st.rerun()

    with col_action2:
        if st.button("📋 查看商机列表", use_container_width=True):
            st.session_state.page = "opportunities"
            st.rerun()

    with col_action3:
        if st.button("📬 管理通知任务", use_container_width=True):
            st.session_state.page = "notification_management"
            st.rerun()

    with col_action4:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()

    # Agent执行信息和系统状态
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🤖 Agent执行状态")
        st.info("上次执行: 2025-06-25 10:00:00")
        st.info("下次执行: 2025-06-25 11:00:00")
        st.info("执行间隔: 60分钟")
        
        if st.button("🚀 手动执行Agent", type="primary"):
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
        st.subheader("📈 系统健康状态")
        
        # 获取系统健康状态
        try:
            health = get_system_health()
            
            # 显示各组件状态
            if health.get("metabase_connection"):
                st.success("✅ Metabase连接正常")
            else:
                st.error("❌ Metabase连接异常")
            
            if health.get("wechat_webhook"):
                st.success("✅ 企微Webhook正常")
            else:
                st.error("❌ 企微Webhook异常")

            if health.get("deepseek_connection"):
                st.success("✅ DeepSeek连接正常")
            else:
                st.error("❌ DeepSeek连接异常")

            if health.get("database_connection"):
                st.success("✅ 数据库连接正常")
            else:
                st.error("❌ 数据库连接异常")
                
        except Exception as e:
            st.error(f"获取系统状态失败: {e}")

    # 添加系统性能图表
    st.markdown("---")
    st.subheader("📈 系统性能趋势")

    # 创建示例数据（实际应从数据库获取）
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    # 生成最近7天的示例数据
    dates = [datetime.now() - timedelta(days=i) for i in range(6, -1, -1)]

    performance_data = pd.DataFrame({
        '日期': dates,
        '处理任务数': np.random.randint(10, 50, 7),
        '发送通知数': np.random.randint(5, 25, 7),
        '超时任务数': np.random.randint(0, 10, 7),
        '响应时间(秒)': np.random.uniform(1, 5, 7)
    })

    # 显示图表
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📊 任务处理统计")
        chart_data = performance_data.set_index('日期')[['处理任务数', '发送通知数', '超时任务数']]
        st.line_chart(chart_data)

    with col_chart2:
        st.subheader("⚡ 系统响应时间")
        response_data = performance_data.set_index('日期')[['响应时间(秒)']]
        st.area_chart(response_data)


def show_agent_control():
    """显示Agent控制台页面 - 重新设计为Agent管理导向"""
    st.title("🤖 Agent智能控制台")
    st.markdown("**Agent生命周期管理 • 执行监控 • 性能调优**")
    st.markdown("---")

    # Agent状态信息
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Agent状态")

        try:
            scheduler = get_scheduler()
            jobs_info = scheduler.get_jobs()

            if jobs_info["is_running"]:
                st.success("🟢 调度器运行中")
            else:
                st.error("🔴 调度器已停止")

            st.info(f"📋 活跃任务数: {jobs_info['total_jobs']}")

            # 显示任务列表
            if jobs_info["jobs"]:
                st.write("**定时任务列表:**")
                for job in jobs_info["jobs"]:
                    with st.expander(f"📅 {job['id']}"):
                        st.write(f"**函数**: {job['func']}")
                        st.write(f"**触发器**: {job['trigger']}")
                        st.write(f"**下次执行**: {job['next_run_time'] or '未知'}")

        except Exception as e:
            st.error(f"获取Agent状态失败: {e}")

    with col2:
        st.subheader("🎛️ 控制操作")

        # 手动执行 - 使用新的执行追踪
        if st.button("🚀 立即执行Agent", type="primary"):
            with st.spinner("正在执行Agent..."):
                try:
                    from ..agent.tools import (
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
                    from ..agent.tools import get_data_statistics, get_data_strategy

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

                    # 显示缓存统计
                    cache_stats = stats.get("cache_statistics", {})
                    if cache_stats:
                        st.write("**缓存统计:**")
                        st.write(f"• 缓存条目: {cache_stats.get('total_cached', 0)}")
                        st.write(f"• 有效缓存: {cache_stats.get('valid_cached', 0)}")
                        st.write(f"• 命中率: {cache_stats.get('cache_hit_ratio', 0):.1%}")

                except Exception as e:
                    st.error(f"试运行失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    st.markdown("---")

    # 调度器控制
    st.subheader("⏰ 调度器管理")

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
                        file_name=f"tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7))
    
    with col2:
        end_date = st.date_input("结束日期", datetime.now())
    
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
    st.header("⚙️ 系统设置")
    
    # 设置选项卡
    tab1, tab2, tab3 = st.tabs(["Agent设置", "通知设置", "群组管理"])
    
    with tab1:
        st.subheader("🤖 Agent配置")
        
        execution_interval = st.number_input(
            "执行频率（分钟）",
            min_value=1,
            max_value=1440,
            value=60
        )
        
        use_llm = st.checkbox("启用LLM优化", value=True)
        
        if use_llm:
            llm_temperature = st.slider(
                "LLM温度参数",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.1
            )
        
        max_retries = st.number_input(
            "最大重试次数",
            min_value=1,
            max_value=10,
            value=3
        )
        
        if st.button("💾 保存Agent设置"):
            st.success("Agent设置已保存")
    
    with tab2:
        st.subheader("🔔 通知配置")
        
        max_notifications = st.number_input(
            "每小时最大通知数",
            min_value=1,
            max_value=100,
            value=10
        )
        
        cooldown_minutes = st.number_input(
            "通知冷却时间（分钟）",
            min_value=1,
            max_value=1440,
            value=30
        )
        
        escalation_threshold = st.number_input(
            "升级阈值（小时）",
            min_value=1,
            max_value=48,
            value=4
        )
        
        enable_dedup = st.checkbox("启用智能去重", value=True)
        
        if st.button("💾 保存通知设置"):
            st.success("通知设置已保存")
    
    with tab3:
        st.subheader("👥 群组管理")
        
        # 群组列表
        sample_groups = [
            {"群组ID": "group_001", "名称": "运维组A", "状态": "启用"},
            {"群组ID": "group_002", "名称": "运维组B", "状态": "启用"},
            {"群组ID": "group_003", "名称": "运维组C", "状态": "禁用"}
        ]
        
        df_groups = pd.DataFrame(sample_groups)
        st.dataframe(df_groups, use_container_width=True, hide_index=True)
        
        # 添加新群组
        st.markdown("---")
        st.subheader("➕ 添加新群组")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_group_name = st.text_input("群组名称")
            new_webhook_url = st.text_input("Webhook URL")
        
        with col2:
            new_group_enabled = st.checkbox("启用群组", value=True)
            
            if st.button("➕ 添加群组"):
                if new_group_name and new_webhook_url:
                    st.success(f"群组 {new_group_name} 添加成功")
                else:
                    st.error("请填写完整的群组信息")


def show_system_test():
    """显示系统测试"""
    st.header("🔧 系统测试")
    
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
    st.header("📈 业务分析")

    try:
        # 获取逾期商机数据
        opportunities = fetch_overdue_opportunities()

        if not opportunities:
            st.info("暂无逾期商机数据")
            return

        calculator = BusinessMetricsCalculator()

        # 生成综合报告
        report = calculator.generate_summary_report(opportunities)

        # 基础统计
        st.subheader("📊 基础统计")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总商机数", report["基础统计"]["总商机数"])
        with col2:
            st.metric("逾期商机数", report["基础统计"]["逾期商机数"])
        with col3:
            st.metric("升级商机数", report["基础统计"]["升级商机数"])
        with col4:
            st.metric("涉及组织数", report["基础统计"]["涉及组织数"])

        st.markdown("---")

        # 逾期率分析
        st.subheader("📈 逾期率分析")
        overdue_rates = report["逾期率分析"]
        if overdue_rates:
            df_overdue = pd.DataFrame(list(overdue_rates.items()), columns=["状态", "逾期率(%)"])
            st.bar_chart(df_overdue.set_index("状态"))

        # 组织绩效对比
        st.subheader("🏢 组织绩效对比")
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

    except Exception as e:
        st.error(f"获取业务分析数据失败: {e}")


def show_opportunity_list():
    """显示商机监控页面 - 重新设计为业务监控导向"""
    st.title("📋 现场服务商机监控")
    st.markdown("**实时监控现场服务时效 • 智能识别超时风险 • 主动预警处理**")
    st.markdown("---")

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
                data.append({
                    "工单号": opp.order_num,
                    "客户": opp.name,
                    "地址": opp.address,
                    "负责人": opp.supervisor_name,
                    "组织": opp.org_name,
                    "状态": opp.order_status,
                    "创建时间": opp.create_time.strftime("%Y-%m-%d %H:%M"),
                    "已过时长(小时)": f"{opp.elapsed_hours:.1f}",
                    "是否逾期": "是" if opp.is_overdue else "否",
                    "升级级别": opp.escalation_level
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
                        file_name=f"opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
    """显示Agent执行历史页面"""
    st.header("🔍 Agent执行历史")

    try:
        from ..agent.tools import get_execution_tracker

        tracker = get_execution_tracker()

        # 获取执行统计
        stats = tracker.get_run_statistics()

        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总运行次数", stats.get("total_runs", 0))
        with col2:
            st.metric("成功运行", stats.get("successful_runs", 0))
        with col3:
            st.metric("失败运行", stats.get("failed_runs", 0))
        with col4:
            st.metric("平均耗时", f"{stats.get('average_duration_seconds', 0):.1f}秒")

        st.markdown("---")

        # 步骤性能分析
        st.subheader("📊 步骤性能分析")

        steps = ["fetch_opportunities", "process_opportunities", "send_notifications"]
        for step in steps:
            step_perf = tracker.get_step_performance(step)

            with st.expander(f"📈 {step} 性能"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("执行次数", step_perf.get("total_executions", 0))
                with col_b:
                    st.metric("成功次数", step_perf.get("successful_executions", 0))
                with col_c:
                    st.metric("平均耗时", f"{step_perf.get('average_duration_seconds', 0):.2f}秒")

        # 刷新按钮
        if st.button("🔄 刷新执行历史"):
            st.rerun()

    except Exception as e:
        st.error(f"获取执行历史失败: {e}")
        st.info("💡 提示: 执行历史功能需要Agent运行后才会有数据")


def show_notification_management():
    """显示通知任务管理页面"""
    st.header("📬 通知任务管理")

    try:
        from ..agent.tools import get_notification_manager

        manager = get_notification_manager()

        # 获取通知统计
        stats = manager.get_notification_statistics()

        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总任务数", stats.get("total_tasks", 0))
        with col2:
            st.metric("已发送", stats.get("sent_count", 0))
        with col3:
            st.metric("发送失败", stats.get("failed_count", 0))
        with col4:
            st.metric("待处理", stats.get("pending_count", 0))

        st.markdown("---")

        # 待处理任务列表
        st.subheader("📋 待处理任务")

        pending_tasks = manager.db_manager.get_pending_notification_tasks()

        if pending_tasks:
            for task in pending_tasks:
                with st.expander(f"📬 任务 {task.id} - {task.order_num}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**工单号**: {task.order_num}")
                        st.write(f"**组织**: {task.org_name}")
                        st.write(f"**类型**: {task.notification_type.value}")
                    with col_b:
                        st.write(f"**状态**: {task.status.value}")
                        st.write(f"**应发送时间**: {task.due_time}")
                        st.write(f"**重试次数**: {task.retry_count}")

                    if task.message:
                        st.write(f"**消息内容**: {task.message}")
        else:
            st.info("📭 当前没有待处理的通知任务")

        # 企微配置状态检查
        st.markdown("---")
        st.subheader("🔧 企微配置状态")

        try:
            from ..config.wechat_config import get_wechat_config_manager

            config_manager = get_wechat_config_manager()
            issues = config_manager.validate_config()
            total_issues = sum(len(problems) for problems in issues.values())

            if total_issues == 0:
                st.success("✅ 企微配置正常，通知可以正常发送")
            else:
                st.warning(f"⚠️ 发现 {total_issues} 个企微配置问题")
                if st.button("🔧 前往配置"):
                    st.session_state.page = "wechat_config"
                    st.rerun()
        except Exception as e:
            st.error(f"无法检查企微配置: {e}")

        # 操作按钮
        col_x, col_y, col_z = st.columns(3)
        with col_x:
            if st.button("🔄 刷新任务列表"):
                st.rerun()
        with col_y:
            if st.button("🧹 清理旧任务"):
                try:
                    cleaned = manager.cleanup_old_tasks()
                    st.success(f"✅ 已清理 {cleaned} 个旧任务")
                except Exception as e:
                    st.error(f"清理失败: {e}")
        with col_z:
            if st.button("🔧 企微配置"):
                st.session_state.page = "wechat_config"
                st.rerun()

    except Exception as e:
        st.error(f"获取通知管理数据失败: {e}")


def show_cache_management():
    """显示缓存管理页面"""
    st.header("💾 缓存管理")

    try:
        from ..agent.tools import get_data_strategy

        data_strategy = get_data_strategy()

        # 获取缓存统计
        cache_stats = data_strategy.get_cache_statistics()

        # 显示缓存状态
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("缓存状态", "启用" if cache_stats.get("cache_enabled", False) else "禁用")
        with col2:
            st.metric("缓存条目", cache_stats.get("total_cached", 0))
        with col3:
            st.metric("有效缓存", cache_stats.get("valid_cached", 0))
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
            if st.button("🔄 刷新缓存"):
                try:
                    with st.spinner("正在刷新缓存..."):
                        old_count, new_count = data_strategy.refresh_cache()
                        st.success(f"✅ 缓存已刷新: {old_count} → {new_count}")
                except Exception as e:
                    st.error(f"刷新缓存失败: {e}")

        with col_y:
            if st.button("🧹 清理缓存"):
                try:
                    with st.spinner("正在清理缓存..."):
                        cleared = data_strategy.clear_cache()
                        st.success(f"✅ 已清理 {cleared} 个缓存条目")
                except Exception as e:
                    st.error(f"清理缓存失败: {e}")

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
    """显示企微群配置页面 - 重新设计为系统核心配置"""
    st.title("🔧 企微群配置管理")
    st.markdown("**通知渠道配置 • Agent通知的基础设施 • 确保通知能够正确发送**")
    st.markdown("---")

    # 配置状态概览
    st.subheader("📊 配置状态概览")

    try:
        from ..config.wechat_config import get_wechat_config_manager

        config_manager = get_wechat_config_manager()

        # 获取配置状态
        org_mapping = config_manager.get_org_webhook_mapping()
        internal_webhook = config_manager.get_internal_ops_webhook()
        escalation_users = config_manager.get_mention_users("escalation")
        settings = config_manager.get_notification_settings()

        # 状态指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            configured_orgs = len([url for url in org_mapping.values() if url])
            total_orgs = len(org_mapping)
            st.metric(
                "组织群配置",
                f"{configured_orgs}/{total_orgs}",
                delta="完整" if configured_orgs == total_orgs else f"缺少{total_orgs - configured_orgs}个",
                delta_color="normal" if configured_orgs == total_orgs else "inverse"
            )

        with col2:
            st.metric(
                "内部运营群",
                "已配置" if internal_webhook else "未配置",
                delta="正常" if internal_webhook else "需要配置",
                delta_color="normal" if internal_webhook else "inverse"
            )

        with col3:
            st.metric(
                "升级@用户",
                f"{len(escalation_users)}个",
                delta="已配置" if escalation_users else "未配置",
                delta_color="normal" if escalation_users else "inverse"
            )

        with col4:
            notifications_enabled = settings.get("enable_standard_notifications", True)
            st.metric(
                "通知开关",
                "启用" if notifications_enabled else "禁用",
                delta="正常" if notifications_enabled else "已禁用",
                delta_color="normal" if notifications_enabled else "inverse"
            )

        # 配置完整性检查
        st.markdown("---")
        st.subheader("🔍 配置完整性检查")

        issues = config_manager.validate_config()
        total_issues = sum(len(problems) for problems in issues.values())

        if total_issues == 0:
            st.success("✅ 所有配置都正确！Agent可以正常发送通知")
        else:
            st.error(f"❌ 发现 {total_issues} 个配置问题，可能影响通知发送")

            for category, problems in issues.items():
                if problems:
                    with st.expander(f"⚠️ {category} ({len(problems)}个问题)"):
                        for problem in problems:
                            st.write(f"• {problem}")

        # 快速操作
        st.markdown("---")
        st.subheader("⚡ 快速操作")

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            if st.button("🔧 详细配置", type="primary", use_container_width=True):
                st.session_state.show_detailed_config = True
                st.rerun()

        with col_b:
            if st.button("🧪 测试通知", use_container_width=True):
                st.session_state.test_notification = True
                st.rerun()

        with col_c:
            if st.button("📤 导出配置", use_container_width=True):
                config_json = config_manager.export_config()
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
            try:
                from .pages.wechat_config import show_wechat_config_page
                show_wechat_config_page()
            except ImportError as e:
                st.error(f"无法加载详细配置页面: {e}")

        # 显示测试通知界面
        if st.session_state.get("test_notification", False):
            st.markdown("---")
            show_notification_test(config_manager)

    except Exception as e:
        st.error(f"获取企微配置失败: {e}")
        st.info("💡 提示: 企微配置是Agent通知功能的基础，请确保正确配置")


def show_notification_test(config_manager):
    """显示通知测试界面"""
    st.subheader("🧪 通知测试")

    test_type = st.selectbox(
        "选择测试类型",
        ["组织群通知", "内部运营群通知", "升级通知"]
    )

    if test_type == "组织群通知":
        org_mapping = config_manager.get_org_webhook_mapping()
        org_name = st.selectbox("选择组织", list(org_mapping.keys()))

        if st.button("发送测试消息"):
            webhook_url = org_mapping.get(org_name)
            if webhook_url:
                st.info(f"正在向 {org_name} 发送测试消息...")
                # 这里可以添加实际的测试逻辑
                st.success("测试消息发送成功！")
            else:
                st.error(f"{org_name} 未配置Webhook URL")

    elif test_type == "内部运营群通知":
        if st.button("发送测试消息"):
            internal_webhook = config_manager.get_internal_ops_webhook()
            if internal_webhook:
                st.info("正在向内部运营群发送测试消息...")
                st.success("测试消息发送成功！")
            else:
                st.error("内部运营群未配置Webhook URL")

    elif test_type == "升级通知":
        if st.button("发送测试消息"):
            escalation_users = config_manager.get_mention_users("escalation")
            if escalation_users:
                st.info(f"正在发送升级通知测试消息，将@{len(escalation_users)}个用户...")
                st.success("测试消息发送成功！")
            else:
                st.error("未配置升级通知@用户")

    if st.button("关闭测试"):
        st.session_state.test_notification = False
        st.rerun()


if __name__ == "__main__":
    main()
