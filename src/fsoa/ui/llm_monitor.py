"""
LLM监控界面

提供LLM调用的实时监控和历史查看功能
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.fsoa.agent.llm_observer import get_llm_observer
from src.fsoa.utils.logger import get_logger

logger = get_logger(__name__)


def render_llm_monitor():
    """渲染LLM监控界面"""
    st.title("🤖 LLM监控中心")
    st.markdown("实时监控LLM调用状态、性能指标和调用详情")
    
    observer = get_llm_observer()
    
    # 获取统计信息
    stats = observer.get_statistics()
    
    # 顶部指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="总调用次数",
            value=stats.get("total_calls", 0),
            delta=None
        )
    
    with col2:
        success_rate = stats.get("success_rate", 0)
        st.metric(
            label="成功率",
            value=f"{success_rate:.1%}",
            delta=None,
            delta_color="normal" if success_rate > 0.9 else "inverse"
        )
    
    with col3:
        avg_duration = stats.get("avg_duration_ms", 0)
        st.metric(
            label="平均响应时间",
            value=f"{avg_duration:.0f}ms",
            delta=None,
            delta_color="normal" if avg_duration < 5000 else "inverse"
        )
    
    with col4:
        total_tokens = stats.get("total_tokens_used", 0)
        st.metric(
            label="总Token使用",
            value=f"{total_tokens:,}",
            delta=None
        )
    
    st.divider()
    
    # 选项卡
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 实时监控", "📋 调用历史", "🔍 详细查看", "⚙️ 配置管理", "💾 数据管理"])
    
    with tab1:
        render_real_time_monitor(observer)
    
    with tab2:
        render_call_history(observer)
    
    with tab3:
        render_detailed_view(observer)
    
    with tab4:
        render_config_management()

    with tab5:
        render_data_management()


def render_real_time_monitor(observer):
    """渲染实时监控"""
    st.subheader("📊 实时监控")
    
    # 自动刷新控制
    auto_refresh = st.checkbox("自动刷新 (30秒)", value=False)
    if auto_refresh:
        st.rerun()
    
    # 获取最近的调用记录
    recent_calls = observer.get_call_history(limit=5)
    
    if not recent_calls:
        st.info("暂无LLM调用记录")
        return
    
    st.markdown("### 最近5次调用")
    
    # 创建表格数据
    table_data = []
    for call in recent_calls:
        table_data.append({
            "时间": call["timestamp"][:19].replace("T", " "),
            "商机ID": call["opportunity_id"],
            "状态": "✅ 成功" if call["status"] == "success" else "❌ 失败",
            "响应时间": f"{call.get('duration_ms', 0):.0f}ms",
            "Token使用": call.get("tokens_used", "N/A"),
            "决策": call.get("parsed_result", {}).get("action", "N/A")
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
    
    # 状态分布图
    if len(recent_calls) > 1:
        st.markdown("### 调用状态分布")
        status_counts = {}
        for call in recent_calls:
            status = call["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        st.bar_chart(status_counts)


def render_call_history(observer):
    """渲染调用历史"""
    st.subheader("📋 调用历史")

    # 控制选项
    col1, col2, col3 = st.columns(3)

    with col1:
        limit = st.selectbox("显示记录数", [10, 20, 50, 100], index=1)

    with col2:
        data_source = st.selectbox("数据源", ["数据库", "内存"], index=0)

    with col3:
        auto_refresh = st.checkbox("自动刷新", value=False)

    # 获取调用历史
    use_database = (data_source == "数据库")
    calls = observer.get_call_history(limit=limit, use_database=use_database)
    
    if not calls:
        st.info("暂无调用历史")
        return
    
    # 过滤选项
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "状态过滤",
            ["全部", "成功", "失败", "超时"],
            index=0
        )

    with col2:
        time_filter = st.selectbox(
            "时间过滤",
            ["全部", "最近1小时", "最近24小时", "最近7天"],
            index=0
        )

    with col3:
        opportunity_filter = st.text_input("商机ID过滤", placeholder="输入商机ID")
    
    # 应用过滤
    filtered_calls = calls

    if status_filter != "全部":
        status_map = {"成功": "success", "失败": "failed", "超时": "timeout"}
        filtered_calls = [c for c in filtered_calls if c["status"] == status_map[status_filter]]

    if time_filter != "全部":
        now = datetime.now()
        time_deltas = {
            "最近1小时": timedelta(hours=1),
            "最近24小时": timedelta(days=1),
            "最近7天": timedelta(days=7)
        }
        cutoff = now - time_deltas[time_filter]
        filtered_calls = [
            c for c in filtered_calls
            if datetime.fromisoformat(c["timestamp"]) > cutoff
        ]

    if opportunity_filter:
        filtered_calls = [
            c for c in filtered_calls
            if opportunity_filter.lower() in c["opportunity_id"].lower()
        ]
    
    # 显示过滤后的结果
    st.markdown(f"### 调用记录 ({len(filtered_calls)} 条)")
    
    for call in filtered_calls:
        with st.expander(
            f"🕐 {call['timestamp'][:19]} - {call['opportunity_id']} - "
            f"{'✅' if call['status'] == 'success' else '❌'}"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**基本信息**")
                st.write(f"商机ID: {call['opportunity_id']}")
                st.write(f"状态: {call['status']}")
                st.write(f"模型: {call['model_name']}")
                st.write(f"温度: {call['temperature']}")
                st.write(f"响应时间: {call.get('duration_ms', 0):.0f}ms")
                
                if call.get('tokens_used'):
                    st.write(f"Token使用: {call['tokens_used']}")
                    st.write(f"  - 提示词: {call.get('tokens_prompt', 'N/A')}")
                    st.write(f"  - 完成: {call.get('tokens_completion', 'N/A')}")
            
            with col2:
                if call['status'] == 'success':
                    st.markdown("**决策结果**")
                    result = call.get('parsed_result', {})
                    st.write(f"动作: {result.get('action', 'N/A')}")
                    st.write(f"优先级: {result.get('priority', 'N/A')}")
                    st.write(f"置信度: {result.get('confidence', 'N/A')}")
                else:
                    st.markdown("**错误信息**")
                    st.write(f"错误类型: {call.get('error_type', 'N/A')}")
                    st.error(call.get('error_message', '未知错误'))


def render_detailed_view(observer):
    """渲染详细查看"""
    st.subheader("🔍 详细查看")
    
    calls = observer.get_call_history(limit=20)
    
    if not calls:
        st.info("暂无调用记录")
        return
    
    # 选择要查看的调用
    call_options = [
        f"{call['timestamp'][:19]} - {call['opportunity_id']}"
        for call in calls
    ]
    
    selected_index = st.selectbox("选择调用记录", range(len(call_options)), format_func=lambda x: call_options[x])
    
    if selected_index is not None:
        call = calls[selected_index]
        
        # 显示详细信息
        st.markdown("### 📋 Context数据")
        with st.expander("查看完整Context", expanded=False):
            st.json(call.get('context_data', {}))
        
        st.markdown("### 📝 提示词")
        with st.expander("查看完整提示词", expanded=False):
            st.text_area(
                "提示词内容",
                value=call.get('prompt_text', ''),
                height=300,
                disabled=True
            )
        
        if call['status'] == 'success':
            st.markdown("### 📤 LLM响应")
            with st.expander("查看原始响应", expanded=False):
                st.text_area(
                    "原始响应",
                    value=call.get('response_text', ''),
                    height=200,
                    disabled=True
                )
            
            st.markdown("### 🎯 解析结果")
            with st.expander("查看解析后的结果", expanded=True):
                st.json(call.get('parsed_result', {}))
            
            # 决策对比
            if call.get('rule_suggestion') and call.get('final_decision'):
                st.markdown("### ⚖️ 决策对比")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**规则引擎建议**")
                    st.json(call['rule_suggestion'])
                
                with col2:
                    st.markdown("**最终决策**")
                    st.json(call['final_decision'])


def render_config_management():
    """渲染配置管理"""
    st.subheader("⚙️ LLM配置管理")
    
    try:
        from src.fsoa.data.database import get_database_manager
        db_manager = get_database_manager()
        
        # 当前配置
        st.markdown("### 当前配置")
        
        configs = {
            "use_llm_optimization": db_manager.get_system_config("use_llm_optimization") or "false",
            "llm_temperature": db_manager.get_system_config("llm_temperature") or "0.1",
            "llm_max_tokens": db_manager.get_system_config("llm_max_tokens") or "1000"
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**LLM优化启用**: {configs['use_llm_optimization']}")
            st.write(f"**温度参数**: {configs['llm_temperature']}")
            st.write(f"**最大Token**: {configs['llm_max_tokens']}")
        
        with col2:
            # 配置修改
            st.markdown("### 修改配置")
            
            new_llm_enabled = st.selectbox(
                "LLM优化",
                ["true", "false"],
                index=0 if configs['use_llm_optimization'] == "true" else 1
            )
            
            new_temperature = st.slider(
                "温度参数",
                min_value=0.0,
                max_value=1.0,
                value=float(configs['llm_temperature']),
                step=0.1
            )
            
            new_max_tokens = st.number_input(
                "最大Token",
                min_value=100,
                max_value=4000,
                value=int(configs['llm_max_tokens']),
                step=100
            )

            new_message_formatting = st.selectbox(
                "LLM消息格式化",
                ["false", "true"],
                index=0 if configs.get('use_llm_message_formatting', 'false') == "false" else 1,
                help="是否使用LLM格式化通知消息（实验性功能）"
            )

            if st.button("保存配置"):
                try:
                    db_manager.set_system_config("use_llm_optimization", new_llm_enabled)
                    db_manager.set_system_config("llm_temperature", str(new_temperature))
                    db_manager.set_system_config("llm_max_tokens", str(new_max_tokens))
                    db_manager.set_system_config("use_llm_message_formatting", new_message_formatting)
                    st.success("配置保存成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"配置保存失败: {e}")
        
        # 连接测试
        st.markdown("### 连接测试")
        if st.button("测试DeepSeek连接"):
            try:
                from src.fsoa.agent.llm import get_deepseek_client
                client = get_deepseek_client()
                
                with st.spinner("正在测试连接..."):
                    result = client.test_connection()
                
                if result:
                    st.success("✅ DeepSeek连接正常")
                else:
                    st.error("❌ DeepSeek连接失败")
            except Exception as e:
                st.error(f"连接测试失败: {e}")
    
    except Exception as e:
        st.error(f"无法加载配置: {e}")


def render_data_management():
    """渲染数据管理"""
    st.subheader("💾 LLM数据管理")

    try:
        from src.fsoa.data.database import get_database_manager
        db_manager = get_database_manager()

        # 数据统计
        st.markdown("### 数据统计")

        col1, col2 = st.columns(2)

        with col1:
            # 总体统计
            total_stats = db_manager.get_llm_call_statistics()
            st.metric("数据库总记录数", total_stats.get("total_calls", 0))
            st.metric("总成功调用", total_stats.get("success_calls", 0))
            st.metric("总失败调用", total_stats.get("failed_calls", 0))

        with col2:
            # 最近24小时统计
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            recent_stats = db_manager.get_llm_call_statistics(start_time=yesterday)
            st.metric("24小时内调用", recent_stats.get("total_calls", 0))
            st.metric("24小时成功率", f"{recent_stats.get('success_rate', 0):.1%}")
            st.metric("24小时平均响应时间", f"{recent_stats.get('avg_duration_ms', 0):.0f}ms")

        st.divider()

        # 数据清理
        st.markdown("### 数据清理")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**清理旧数据**")
            days_to_keep = st.number_input(
                "保留天数",
                min_value=1,
                max_value=365,
                value=30,
                help="删除指定天数之前的LLM调用记录"
            )

            if st.button("清理旧数据", type="secondary"):
                with st.spinner("正在清理数据..."):
                    deleted_count = db_manager.delete_old_llm_records(days_to_keep)
                    if deleted_count > 0:
                        st.success(f"成功删除 {deleted_count} 条旧记录")
                    else:
                        st.info("没有需要清理的旧记录")

        with col2:
            st.markdown("**数据导出**")
            export_days = st.number_input(
                "导出天数",
                min_value=1,
                max_value=90,
                value=7,
                help="导出最近指定天数的LLM调用记录"
            )

            if st.button("导出数据", type="secondary"):
                try:
                    import json
                    from datetime import datetime, timedelta

                    start_time = datetime.now() - timedelta(days=export_days)
                    records = db_manager.get_llm_call_records(
                        limit=1000,
                        start_time=start_time
                    )

                    if records:
                        # 转换为JSON格式
                        export_data = {
                            "export_time": datetime.now().isoformat(),
                            "export_days": export_days,
                            "total_records": len(records),
                            "records": records
                        }

                        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

                        st.download_button(
                            label="下载JSON文件",
                            data=json_str,
                            file_name=f"llm_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )

                        st.success(f"准备导出 {len(records)} 条记录")
                    else:
                        st.info("没有找到符合条件的记录")

                except Exception as e:
                    st.error(f"导出失败: {e}")

        st.divider()

        # 数据库维护
        st.markdown("### 数据库维护")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**数据库信息**")
            try:
                # 获取数据库文件大小等信息
                import os
                db_path = "fsoa.db"  # 默认数据库路径
                if os.path.exists(db_path):
                    db_size = os.path.getsize(db_path)
                    st.write(f"数据库文件大小: {db_size / 1024 / 1024:.2f} MB")
                else:
                    st.write("数据库文件: 未找到")

                # 显示表信息
                st.write("LLM记录表: llm_call_records")

            except Exception as e:
                st.write(f"无法获取数据库信息: {e}")

        with col2:
            st.markdown("**性能优化**")

            if st.button("优化数据库", type="secondary"):
                try:
                    # 这里可以添加数据库优化逻辑，比如VACUUM等
                    st.info("数据库优化功能开发中...")
                except Exception as e:
                    st.error(f"优化失败: {e}")

        # 高级查询
        st.divider()
        st.markdown("### 高级查询")

        with st.expander("自定义查询", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                query_start_date = st.date_input("开始日期")
                query_status = st.selectbox("状态", ["全部", "success", "failed", "timeout"])

            with col2:
                query_end_date = st.date_input("结束日期")
                query_limit = st.number_input("记录数量", min_value=1, max_value=500, value=50)

            if st.button("执行查询"):
                try:
                    from datetime import datetime

                    start_time = datetime.combine(query_start_date, datetime.min.time())
                    end_time = datetime.combine(query_end_date, datetime.max.time())

                    status_filter = None if query_status == "全部" else query_status

                    records = db_manager.get_llm_call_records(
                        limit=query_limit,
                        status_filter=status_filter,
                        start_time=start_time,
                        end_time=end_time
                    )

                    if records:
                        st.success(f"查询到 {len(records)} 条记录")

                        # 显示查询结果摘要
                        df_data = []
                        for record in records:
                            df_data.append({
                                "时间": record["timestamp"][:19].replace("T", " "),
                                "商机ID": record["opportunity_id"],
                                "状态": record["status"],
                                "响应时间": f"{record.get('duration_ms', 0):.0f}ms",
                                "Token": record.get("tokens_used", "N/A")
                            })

                        import pandas as pd
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("没有找到符合条件的记录")

                except Exception as e:
                    st.error(f"查询失败: {e}")

    except Exception as e:
        st.error(f"无法加载数据管理功能: {e}")


if __name__ == "__main__":
    render_llm_monitor()
