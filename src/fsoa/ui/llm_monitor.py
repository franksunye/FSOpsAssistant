"""
LLM监控界面

提供LLM调用的实时监控和历史查看功能
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..agent.llm_observer import get_llm_observer
from ..utils.logger import get_logger

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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 实时监控", "📋 调用历史", "🔍 详细查看", "⚙️ 配置管理"])
    
    with tab1:
        render_real_time_monitor(observer)
    
    with tab2:
        render_call_history(observer)
    
    with tab3:
        render_detailed_view(observer)
    
    with tab4:
        render_config_management()


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
    
    # 历史记录数量选择
    limit = st.selectbox("显示记录数", [10, 20, 50, 100], index=1)
    
    calls = observer.get_call_history(limit=limit)
    
    if not calls:
        st.info("暂无调用历史")
        return
    
    # 过滤选项
    col1, col2 = st.columns(2)
    
    with col1:
        status_filter = st.selectbox(
            "状态过滤",
            ["全部", "成功", "失败"],
            index=0
        )
    
    with col2:
        time_filter = st.selectbox(
            "时间过滤",
            ["全部", "最近1小时", "最近24小时", "最近7天"],
            index=0
        )
    
    # 应用过滤
    filtered_calls = calls
    
    if status_filter != "全部":
        status_map = {"成功": "success", "失败": "failed"}
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
        from ..data.database import get_database_manager
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
            
            if st.button("保存配置"):
                try:
                    db_manager.set_system_config("use_llm_optimization", new_llm_enabled)
                    db_manager.set_system_config("llm_temperature", str(new_temperature))
                    db_manager.set_system_config("llm_max_tokens", str(new_max_tokens))
                    st.success("配置保存成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"配置保存失败: {e}")
        
        # 连接测试
        st.markdown("### 连接测试")
        if st.button("测试DeepSeek连接"):
            try:
                from ..agent.llm import get_deepseek_client
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


if __name__ == "__main__":
    render_llm_monitor()
