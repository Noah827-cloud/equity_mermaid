#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构手动编辑工具

本模块提供手动添加公司、股东、子公司及关系的界面，生成与图片识别相同格式的JSON数据，
并使用相同的mermaid_function来生成图表。
"""

import os
import json
import streamlit as st
from streamlit_mermaid import st_mermaid

# 导入Mermaid生成功能
from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram

# 配置检查与环境变量支持
def check_environment():
    """检查运行环境并准备必要的配置"""
    # 检查是否存在alicloud_translator模块，如果存在则进行初始化
    try:
        # 尝试导入alicloud_translator模块
        import src.utils.alicloud_translator as alicloud_translator
        # 如果在Streamlit Cloud环境中，提供友好的错误处理
        if os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud':
            # 记录日志而不抛出异常
            st.log('Streamlit Cloud环境检测到，将使用环境变量配置')
    except ImportError:
        st.log('未找到alicloud_translator模块，继续运行')

# 运行环境检查
check_environment()

# 设置页面配置
st.set_page_config(
    page_title="股权结构手动编辑器",
    page_icon="📝",
    layout="wide"
)

# 初始化会话状态
def initialize_session_state():
    if "equity_data" not in st.session_state:
        st.session_state.equity_data = {
            "companyName": "核心公司",
            "shareholders": [],
            "subsidiaries": []
        }

# 初始化会话状态
initialize_session_state()

# 自定义 CSS
st.markdown("""
<style>
    /* 全局样式 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #f5f7fa;
    }
    
    .main-container {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* 卡片容器样式 - 更现代的设计 */
    .section-container {
        background-color: white;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border: 1px solid #e9ecef;
        transition: box-shadow 0.3s ease;
    }
    
    .section-container:hover {
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
    }
    
    /* 按钮样式 - 商务蓝色系 */
    .stButton>button {
        background-color: #165DFF;
        color: white;
        border: none;
        padding: 0.625rem 1.25rem;
        font-size: 0.9375rem;
        font-weight: 500;
        cursor: pointer;
        border-radius: 6px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(22, 93, 255, 0.2);
    }
    
    .stButton>button:hover {
        background-color: #0E4FD7;
        box-shadow: 0 4px 8px rgba(22, 93, 255, 0.3);
        transform: translateY(-1px);
    }
    
    .stButton>button:focus {
        outline: 2px solid rgba(22, 93, 255, 0.5);
        outline-offset: 2px;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.title("📝 股权结构手动编辑器")
st.write("手动创建和编辑股权结构图，设置公司关系和持股比例。")

# 主要编辑区域
col1, col2 = st.columns(2)

with col1:
    with st.container():
        st.subheader("公司基本信息")
        company_name = st.text_input("核心公司名称", value=st.session_state.equity_data["companyName"])
        if st.button("更新公司名称"):
            st.session_state.equity_data["companyName"] = company_name
            st.success("公司名称已更新")
    
    # 股东编辑
    with st.container():
        st.subheader("股东管理")
        
        # 添加股东
        with st.form("add_shareholder_form"):
            st.write("添加新股东")
            shareholder_name = st.text_input("股东名称")
            shareholder_percentage = st.slider("持股比例 (%)", 0.1, 100.0, 10.0)
            submitted = st.form_submit_button("添加股东")
            
            if submitted and shareholder_name:
                new_shareholder = {
                    "name": shareholder_name,
                    "percentage": round(shareholder_percentage, 2)
                }
                st.session_state.equity_data["shareholders"].append(new_shareholder)
                st.success(f"已添加股东: {shareholder_name}")
        
        # 显示和编辑现有股东
        if st.session_state.equity_data["shareholders"]:
            st.write("现有股东列表")
            for i, shareholder in enumerate(st.session_state.equity_data["shareholders"]):
                col1_sh, col2_sh, col3_sh = st.columns([2, 2, 1])
                with col1_sh:
                    new_name = st.text_input(f"股东 {i+1} 名称", value=shareholder["name"], key=f"shareholder_name_{i}")
                with col2_sh:
                    new_percentage = st.slider(f"持股比例", 0.1, 100.0, shareholder["percentage"], key=f"shareholder_percentage_{i}")
                with col3_sh:
                    if st.button("删除", key=f"delete_shareholder_{i}"):
                        st.session_state.equity_data["shareholders"].pop(i)
                        st.experimental_rerun()
                
                # 更新股东信息
                if new_name != shareholder["name"]:
                    st.session_state.equity_data["shareholders"][i]["name"] = new_name
                if new_percentage != shareholder["percentage"]:
                    st.session_state.equity_data["shareholders"][i]["percentage"] = round(new_percentage, 2)

# 子公司编辑
with col2:
    with st.container():
        st.subheader("子公司管理")
        
        # 添加子公司
        with st.form("add_subsidiary_form"):
            st.write("添加新子公司")
            subsidiary_name = st.text_input("子公司名称")
            subsidiary_percentage = st.slider("持股比例 (%)", 0.1, 100.0, 60.0)
            submitted = st.form_submit_button("添加子公司")
            
            if submitted and subsidiary_name:
                new_subsidiary = {
                    "companyName": subsidiary_name,
                    "shareholders": [{
                        "name": st.session_state.equity_data["companyName"],
                        "percentage": round(subsidiary_percentage, 2)
                    }],
                    "subsidiaries": []
                }
                st.session_state.equity_data["subsidiaries"].append(new_subsidiary)
                st.success(f"已添加子公司: {subsidiary_name}")
        
        # 显示和编辑现有子公司
        if st.session_state.equity_data["subsidiaries"]:
            st.write("现有子公司列表")
            for i, subsidiary in enumerate(st.session_state.equity_data["subsidiaries"]):
                st.write(f"#### {subsidiary['companyName']}")
                col1_sub, col2_sub, col3_sub = st.columns([2, 2, 1])
                
                with col1_sub:
                    new_name = st.text_input(f"子公司 {i+1} 名称", value=subsidiary["companyName"], key=f"subsidiary_name_{i}")
                
                # 默认持股比例
                parent_percentage = 0
                for shareholder in subsidiary["shareholders"]:
                    if shareholder["name"] == st.session_state.equity_data["companyName"]:
                        parent_percentage = shareholder["percentage"]
                        break
                
                with col2_sub:
                    new_percentage = st.slider(f"持股比例", 0.1, 100.0, parent_percentage, key=f"subsidiary_percentage_{i}")
                
                with col3_sub:
                    if st.button("删除", key=f"delete_subsidiary_{i}"):
                        st.session_state.equity_data["subsidiaries"].pop(i)
                        st.experimental_rerun()
                
                # 更新子公司信息
                if new_name != subsidiary["companyName"]:
                    st.session_state.equity_data["subsidiaries"][i]["companyName"] = new_name
                
                # 更新持股比例
                if new_percentage != parent_percentage:
                    # 查找父公司的持股记录
                    parent_found = False
                    for j, shareholder in enumerate(subsidiary["shareholders"]):
                        if shareholder["name"] == st.session_state.equity_data["companyName"]:
                            st.session_state.equity_data["subsidiaries"][i]["shareholders"][j]["percentage"] = round(new_percentage, 2)
                            parent_found = True
                            break
                    # 如果没有找到，添加一个新的持股记录
                    if not parent_found:
                        st.session_state.equity_data["subsidiaries"][i]["shareholders"].append({
                            "name": st.session_state.equity_data["companyName"],
                            "percentage": round(new_percentage, 2)
                        })

# 分隔线
st.markdown("---")

# 生成和显示图表
st.subheader("📊 生成的股权结构图")

# 生成Mermaid代码
mermaid_code = generate_mermaid_diagram(st.session_state.equity_data)

# 显示Mermaid代码
st.code(mermaid_code, language="mermaid")

# 渲染图表
st_mermaid(mermaid_code)

# 下载区域
st.subheader("📥 下载")
col1_dl, col2_dl = st.columns(2)

with col1_dl:
    # JSON下载
    st.download_button(
        label="下载股权结构JSON",
        data=json.dumps(st.session_state.equity_data, ensure_ascii=False, indent=2),
        file_name="equity_structure.json",
        mime="application/json"
    )

with col2_dl:
    # Mermaid代码下载
    st.download_button(
        label="下载Mermaid代码",
        data=mermaid_code,
        file_name="equity_structure.mermaid",
        mime="text/plain"
    )

# 底部信息
st.markdown("---")
st.markdown("© 2023 股权结构图生成工具 - 手动编辑模式")