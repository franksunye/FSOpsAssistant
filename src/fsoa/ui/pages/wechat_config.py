"""
企微群配置管理页面

提供企微群配置的Web界面管理功能
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.fsoa.config.wechat_config import get_wechat_config_manager
    from src.fsoa.notification.wechat import get_wechat_client
    from src.fsoa.utils.logger import get_logger
except ImportError as e:
    st.error(f"模块导入失败: {e}")
    st.stop()

logger = get_logger(__name__)


def show_wechat_config_page():
    """显示企微群配置管理页面"""
    st.header("🔧 企微群配置管理")
    
    config_manager = get_wechat_config_manager()
    
    # 创建选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["组织群配置", "内部运营群", "@用户配置", "通知设置"])
    
    with tab1:
        show_org_webhook_config(config_manager)
    
    with tab2:
        show_internal_ops_config(config_manager)
    
    with tab3:
        show_mention_users_config(config_manager)
    
    with tab4:
        show_notification_settings(config_manager)


def show_org_webhook_config(config_manager):
    """显示组织群配置"""
    st.subheader("📋 组织群Webhook配置")
    
    # 获取当前配置
    org_mapping = config_manager.get_org_webhook_mapping()
    
    # 显示当前配置表格
    if org_mapping:
        st.write("**当前配置：**")
        
        # 转换为DataFrame显示
        config_data = []
        for org_name, webhook_url in org_mapping.items():
            status = "✅ 已配置" if webhook_url else "❌ 未配置"
            config_data.append({
                "组织名称": org_name,
                "Webhook状态": status,
                "Webhook URL": webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url
            })
        
        df = pd.DataFrame(config_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无组织群配置")
    
    st.markdown("---")
    
    # 添加新配置
    st.subheader("➕ 添加/更新组织群配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        org_name = st.text_input("组织名称", placeholder="请输入组织名称")
    
    with col2:
        webhook_url = st.text_input("Webhook URL", placeholder="https://qyapi.weixin.qq.com/...")
    
    col_add, col_test, col_delete = st.columns(3)
    
    with col_add:
        if st.button("💾 保存配置"):
            if org_name and webhook_url:
                if config_manager.set_org_webhook(org_name, webhook_url):
                    st.success(f"已保存 {org_name} 的配置")
                    st.rerun()
                else:
                    st.error("保存配置失败")
            else:
                st.warning("请填写完整信息")
    
    with col_test:
        if st.button("🧪 测试Webhook"):
            if webhook_url:
                # 测试webhook连接
                try:
                    wechat_client = get_wechat_client()
                    # 这里可以添加测试逻辑
                    st.info("测试功能开发中...")
                except Exception as e:
                    st.error(f"测试失败: {e}")
            else:
                st.warning("请输入Webhook URL")
    
    with col_delete:
        if st.button("🗑️ 删除配置"):
            if org_name:
                if config_manager.remove_org_webhook(org_name):
                    st.success(f"已删除 {org_name} 的配置")
                    st.rerun()
                else:
                    st.warning("删除失败或配置不存在")
            else:
                st.warning("请输入组织名称")


def show_internal_ops_config(config_manager):
    """显示内部运营群配置"""
    st.subheader("🏢 内部运营群配置")
    
    # 获取当前配置
    current_webhook = config_manager.get_internal_ops_webhook()
    
    if current_webhook:
        st.success(f"当前配置: {current_webhook[:50]}...")
    else:
        st.warning("未配置内部运营群Webhook")
    
    st.markdown("---")
    
    # 配置内部运营群
    new_webhook = st.text_input(
        "内部运营群Webhook URL",
        value=current_webhook,
        placeholder="https://qyapi.weixin.qq.com/..."
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 保存内部运营群配置"):
            if new_webhook:
                if config_manager.set_internal_ops_webhook(new_webhook):
                    st.success("内部运营群配置已保存")
                    st.rerun()
                else:
                    st.error("保存失败")
            else:
                st.warning("请输入Webhook URL")
    
    with col2:
        if st.button("🧪 测试内部运营群"):
            if new_webhook:
                try:
                    # 这里可以添加测试逻辑
                    st.info("测试功能开发中...")
                except Exception as e:
                    st.error(f"测试失败: {e}")
            else:
                st.warning("请输入Webhook URL")


def show_mention_users_config(config_manager):
    """显示@用户配置"""
    st.subheader("👥 @用户配置")
    
    # 获取当前配置
    escalation_users = config_manager.get_mention_users("escalation")
    emergency_users = config_manager.get_mention_users("emergency")
    
    # 升级通知@用户
    st.write("**升级通知@用户：**")
    escalation_text = st.text_area(
        "升级通知时需要@的用户（每行一个）",
        value="\n".join(escalation_users),
        height=100
    )
    
    if st.button("💾 保存升级通知@用户"):
        users = [user.strip() for user in escalation_text.split("\n") if user.strip()]
        if config_manager.set_mention_users("escalation", users):
            st.success("升级通知@用户配置已保存")
            st.rerun()
        else:
            st.error("保存失败")
    
    st.markdown("---")
    
    # 紧急通知@用户
    st.write("**紧急通知@用户：**")
    emergency_text = st.text_area(
        "紧急通知时需要@的用户（每行一个）",
        value="\n".join(emergency_users),
        height=100
    )
    
    if st.button("💾 保存紧急通知@用户"):
        users = [user.strip() for user in emergency_text.split("\n") if user.strip()]
        if config_manager.set_mention_users("emergency", users):
            st.success("紧急通知@用户配置已保存")
            st.rerun()
        else:
            st.error("保存失败")


def show_notification_settings(config_manager):
    """显示通知设置"""
    st.subheader("⚙️ 通知设置")
    
    # 获取当前设置
    settings = config_manager.get_notification_settings()
    
    # 通知开关
    st.write("**通知开关：**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        enable_standard = st.checkbox(
            "启用标准通知",
            value=settings.get("enable_standard_notifications", True)
        )
    
    with col2:
        enable_escalation = st.checkbox(
            "启用升级通知",
            value=settings.get("enable_escalation_notifications", True)
        )
    
    with col3:
        enable_summary = st.checkbox(
            "启用汇总通知",
            value=settings.get("enable_summary_notifications", False)
        )
    
    st.markdown("---")
    
    # 通知参数
    st.write("**通知参数：**")
    col1, col2 = st.columns(2)
    
    with col1:
        max_items = st.number_input(
            "每次通知最大条目数",
            min_value=1,
            max_value=50,
            value=settings.get("max_items_per_notification", 10)
        )
    
    with col2:
        cooldown_minutes = st.number_input(
            "通知冷却时间（分钟）",
            min_value=1,
            max_value=1440,
            value=settings.get("cooldown_minutes", 30)
        )
    
    # 保存设置
    if st.button("💾 保存通知设置"):
        new_settings = {
            "enable_standard_notifications": enable_standard,
            "enable_escalation_notifications": enable_escalation,
            "enable_summary_notifications": enable_summary,
            "max_items_per_notification": max_items,
            "cooldown_minutes": cooldown_minutes
        }
        
        if config_manager.update_notification_settings(new_settings):
            st.success("通知设置已保存")
            st.rerun()
        else:
            st.error("保存失败")
    
    st.markdown("---")
    
    # 配置验证
    st.subheader("🔍 配置验证")
    
    if st.button("🔍 验证配置"):
        issues = config_manager.validate_config()
        
        if any(issues.values()):
            st.error("发现配置问题：")
            for category, problems in issues.items():
                if problems:
                    st.write(f"**{category}:**")
                    for problem in problems:
                        st.write(f"- {problem}")
        else:
            st.success("✅ 配置验证通过，所有配置都正确！")
    
    # 配置导入导出
    st.markdown("---")
    st.subheader("📤 配置导入导出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 导出配置"):
            config_json = config_manager.export_config()
            st.download_button(
                label="下载配置文件",
                data=config_json,
                file_name="wechat_config.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_file = st.file_uploader("📥 导入配置", type=['json'])
        if uploaded_file is not None:
            try:
                config_content = uploaded_file.read().decode('utf-8')
                if config_manager.import_config(config_content):
                    st.success("配置导入成功")
                    st.rerun()
                else:
                    st.error("配置导入失败")
            except Exception as e:
                st.error(f"导入失败: {e}")


if __name__ == "__main__":
    show_wechat_config_page()
