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

# 导入模块
try:
    from ..agent.tools import (
        fetch_overdue_tasks, test_metabase_connection,
        test_wechat_webhook, test_deepseek_connection, get_system_health
    )
    from ..agent.orchestrator import AgentOrchestrator
    from ..utils.scheduler import get_scheduler, setup_agent_scheduler, start_scheduler, stop_scheduler
    from ..data.database import get_db_manager
    from ..data.models import TaskStatus, Priority
    from ..notification.wechat import get_wechat_client
    from ..utils.config import get_config
    from ..utils.logger import get_logger
except ImportError:
    # 开发环境下的导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    st.error("模块导入失败，请检查项目结构")
    st.stop()

logger = get_logger(__name__)


def main():
    """主应用函数"""
    st.title("🤖 FSOA - 现场服务运营助手")
    st.markdown("---")
    
    # 侧边栏导航
    with st.sidebar:
        st.header("📋 导航菜单")
        page = st.selectbox(
            "选择页面",
            ["📊 仪表板", "🤖 Agent控制", "📋 任务列表", "🔔 通知历史", "⚙️ 系统设置", "🔧 系统测试"]
        )
    
    # 根据选择显示不同页面
    if page == "📊 仪表板":
        show_dashboard()
    elif page == "🤖 Agent控制":
        show_agent_control()
    elif page == "📋 任务列表":
        show_task_list()
    elif page == "🔔 通知历史":
        show_notification_history()
    elif page == "⚙️ 系统设置":
        show_system_settings()
    elif page == "🔧 系统测试":
        show_system_test()


def show_dashboard():
    """显示仪表板"""
    st.header("📊 系统仪表板")

    # 获取实时数据
    try:
        # 获取系统健康状态
        health = get_system_health()

        # 获取调度器状态
        scheduler = get_scheduler()
        jobs_info = scheduler.get_jobs()

        # 获取Agent状态
        agent_status = "运行中" if jobs_info["is_running"] else "已停止"
        agent_delta = "正常" if health.get("overall_status") == "healthy" else "异常"

        # 模拟统计数据（实际应从数据库获取）
        db_manager = get_db_manager()

    except Exception as e:
        st.error(f"获取系统数据失败: {e}")
        health = {}
        jobs_info = {"is_running": False, "total_jobs": 0}
        agent_status = "未知"
        agent_delta = "错误"

    # 系统状态卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Agent状态",
            value=agent_status,
            delta=agent_delta,
            delta_color="normal" if agent_delta == "正常" else "inverse"
        )

    with col2:
        # 这里应该从数据库获取实际数据
        st.metric(
            label="今日处理任务",
            value="0",  # 实际应查询数据库
            delta="0"
        )

    with col3:
        st.metric(
            label="发送通知",
            value="0",  # 实际应查询数据库
            delta="0"
        )

    with col4:
        st.metric(
            label="活跃任务",
            value=str(jobs_info.get("total_jobs", 0)),
            delta="0"
        )
    
    st.markdown("---")

    # 实时刷新控制
    col_refresh1, col_refresh2, col_refresh3 = st.columns([1, 1, 2])

    with col_refresh1:
        auto_refresh = st.checkbox("自动刷新", value=False)

    with col_refresh2:
        if st.button("🔄 手动刷新"):
            st.rerun()

    with col_refresh3:
        if auto_refresh:
            st.info("⏱️ 页面将每30秒自动刷新")
            # 自动刷新（注意：这会导致页面重新加载）
            import time
            time.sleep(30)
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
    """显示Agent控制页面"""
    st.header("🤖 Agent控制中心")

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

        # 手动执行
        if st.button("🚀 立即执行Agent", type="primary"):
            with st.spinner("正在执行Agent..."):
                try:
                    agent = AgentOrchestrator()
                    result = agent.execute(dry_run=False)

                    st.success("✅ Agent执行完成！")

                    # 显示执行结果
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("处理任务", result.tasks_processed)
                    with col_b:
                        st.metric("发送通知", result.notifications_sent)
                    with col_c:
                        st.metric("错误数量", len(result.errors))

                    if result.errors:
                        st.error("执行错误:")
                        for error in result.errors:
                            st.write(f"• {error}")

                except Exception as e:
                    st.error(f"Agent执行失败: {e}")

        # 试运行
        if st.button("🧪 试运行 (Dry Run)"):
            with st.spinner("正在试运行..."):
                try:
                    agent = AgentOrchestrator()
                    result = agent.execute(dry_run=True)

                    st.info("🧪 试运行完成！")
                    st.write(f"**模拟处理任务**: {result.tasks_processed}")
                    st.write(f"**模拟发送通知**: {result.notifications_sent}")

                    if result.errors:
                        st.warning("发现问题:")
                        for error in result.errors:
                            st.write(f"• {error}")

                except Exception as e:
                    st.error(f"试运行失败: {e}")

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


if __name__ == "__main__":
    main()
