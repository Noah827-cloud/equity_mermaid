#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构手动编辑工具

本模块提供手动添加公司、股东、子公司及关系的界面，生成与图片识别相同格式的JSON数据，
并使用相同的mermaid_function来生成图表。
"""

import os
import sys
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import streamlit as st
from streamlit_mermaid import st_mermaid

# 导入Mermaid生成功能
from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram

# 导入AI分析模块
from src.utils.ai_equity_analyzer import analyze_equity_with_ai

# 初始化会话状态变量
if "entity_relationships" not in st.session_state:
    st.session_state.entity_relationships = []
if "control_relationships" not in st.session_state:
    st.session_state.control_relationships = []
if "actual_controller" not in st.session_state:
    st.session_state.actual_controller = ""
if "core_company" not in st.session_state:
    st.session_state.core_company = "未命名公司"
if "dashscope_api_key" not in st.session_state:
    st.session_state.dashscope_api_key = ""
if "equity_data" not in st.session_state:
    st.session_state.equity_data = {
        "core_company": "未命名公司",
        "actual_controller": "",
        "entity_relationships": [],
        "control_relationships": [],
        "top_level_entities": [],  # 添加缺失的top_level_entities键
        "subsidiaries": []  # 也添加subsidiaries键以确保完整性
    }


def validate_equity_data(equity_data, show_logs=True):
    """
    验证股权数据的完整性和有效性
    
    Args:
        equity_data: 要验证的股权数据字典
        show_logs: 是否显示验证日志
        
    Returns:
        tuple: (是否有效, 验证日志列表)
    """
    validation_logs = []
    data_valid = True
    
    try:
        # 验证核心公司是否存在
        if not equity_data.get("core_company", "").strip():
            validation_logs.append("错误: 核心公司名称不能为空")
            data_valid = False
        else:
            validation_logs.append(f"✓ 核心公司验证通过: {equity_data['core_company']}")
        
        # 验证顶级实体列表
        top_level_entities = equity_data.get("top_level_entities", [])
        if not isinstance(top_level_entities, list):
            validation_logs.append("错误: 顶级实体数据格式无效")
            data_valid = False
        else:
            # 检查顶级实体中的每个元素
            valid_entities_count = 0
            for i, entity in enumerate(top_level_entities):
                if not isinstance(entity, dict):
                    validation_logs.append(f"错误: 顶级实体 #{i+1} 不是有效的字典格式")
                    data_valid = False
                elif not entity.get("name", "").strip():
                    validation_logs.append(f"错误: 顶级实体 #{i+1} 缺少名称")
                    data_valid = False
                elif "type" not in entity:
                    validation_logs.append(f"警告: 顶级实体 #{i+1} ({entity.get('name', '未命名')}) 缺少类型字段")
                else:
                    valid_entities_count += 1
            
            if valid_entities_count > 0:
                validation_logs.append(f"✓ 顶级实体列表验证，共 {len(top_level_entities)} 个实体，其中 {valid_entities_count} 个有效")
            else:
                validation_logs.append(f"警告: 顶级实体列表为空或全部无效")
        
        # 验证子公司列表
        subsidiaries = equity_data.get("subsidiaries", [])
        if not isinstance(subsidiaries, list):
            validation_logs.append("错误: 子公司数据格式无效")
            data_valid = False
        else:
            valid_subs_count = 0
            for i, sub in enumerate(subsidiaries):
                if not isinstance(sub, dict):
                    validation_logs.append(f"错误: 子公司 #{i+1} 不是有效的字典格式")
                    data_valid = False
                elif not sub.get("name", "").strip():
                    validation_logs.append(f"错误: 子公司 #{i+1} 缺少名称")
                    data_valid = False
                elif "percentage" not in sub:
                    validation_logs.append(f"警告: 子公司 #{i+1} ({sub.get('name', '未命名')}) 缺少持股比例")
                else:
                    valid_subs_count += 1
            
            if valid_subs_count > 0:
                validation_logs.append(f"✓ 子公司列表验证，共 {len(subsidiaries)} 个子公司，其中 {valid_subs_count} 个有效")
            else:
                validation_logs.append(f"警告: 子公司列表为空或全部无效")
        
        # 验证实体关系列表
        entity_relationships = equity_data.get("entity_relationships", [])
        if not isinstance(entity_relationships, list):
            validation_logs.append("错误: 实体关系数据格式无效")
            data_valid = False
        else:
            valid_rels_count = 0
            for i, rel in enumerate(entity_relationships):
                if not isinstance(rel, dict):
                    validation_logs.append(f"错误: 实体关系 #{i+1} 不是有效的字典格式")
                    data_valid = False
                else:
                    # 同时支持parent/child和from/to两种格式
                    parent_entity = rel.get("parent", rel.get("from", ""))
                    child_entity = rel.get("child", rel.get("to", ""))
                    if not parent_entity.strip() or not child_entity.strip():
                        validation_logs.append(f"错误: 实体关系 #{i+1} 缺少必要的实体信息")
                        data_valid = False
                    else:
                        valid_rels_count += 1
            
            if valid_rels_count > 0:
                validation_logs.append(f"✓ 实体关系列表验证，共 {len(entity_relationships)} 个关系，其中 {valid_rels_count} 个有效")
            else:
                validation_logs.append(f"警告: 实体关系列表为空或全部无效")
        
        # 验证all_entities列表
        all_entities = equity_data.get("all_entities", [])
        if not isinstance(all_entities, list):
            validation_logs.append("错误: 所有实体列表格式无效")
            data_valid = False
        else:
            valid_all_count = 0
            for i, entity in enumerate(all_entities):
                if not isinstance(entity, dict):
                    validation_logs.append(f"错误: 实体 #{i+1} 不是有效的字典格式")
                    data_valid = False
                elif not entity.get("name", "").strip():
                    validation_logs.append(f"错误: 实体 #{i+1} 缺少名称")
                    data_valid = False
                elif "type" not in entity:
                    validation_logs.append(f"警告: 实体 #{i+1} ({entity.get('name', '未命名')}) 缺少类型字段")
                else:
                    valid_all_count += 1
            
            if valid_all_count > 0:
                validation_logs.append(f"✓ 所有实体列表验证，共 {len(all_entities)} 个实体，其中 {valid_all_count} 个有效")
            else:
                validation_logs.append(f"警告: 所有实体列表为空或全部无效")
        
        # 验证shareholders字段（可选）
        shareholders = equity_data.get("shareholders", [])
        if shareholders and not isinstance(shareholders, list):
            validation_logs.append("警告: shareholders字段存在但不是列表格式")
        else:
            validation_logs.append(f"✓ Shareholders字段验证通过")
        
        # 显示验证日志
        if show_logs:
            with st.expander("数据验证日志", expanded=True):
                for log in validation_logs:
                    if "错误" in log:
                        st.error(log)
                    elif "警告" in log:
                        st.warning(log)
                    else:
                        st.info(log)
        
    except Exception as e:
        import traceback
        error_msg = f"验证过程中发生错误: {str(e)}"
        validation_logs.append(error_msg)
        if show_logs:
            st.error(error_msg)
            with st.expander("查看详细错误信息", expanded=False):
                st.text(traceback.format_exc())
        data_valid = False
    
    return data_valid, validation_logs

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
    page_title="股权结构手动编辑器 - V1",
    page_icon="📝",
    layout="wide"
)

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
    
    /* 信息框样式优化 */
    .info-box {
        background-color: #F0F5FF;
        border-left: 4px solid #165DFF;
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .success-box {
        background-color: #F6FFED;
        border-left: 4px solid #52C41A;
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .error-box {
        background-color: #FFF1F0;
        border-left: 4px solid #FF4D4F;
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* 实体卡片样式 - 更现代的设计 */
    .entity-card {
        background-color: white;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }
    
    .entity-card:hover {
        border-color: #165DFF;
        box-shadow: 0 4px 12px rgba(22, 93, 255, 0.1);
    }
    
    /* 关系项样式 */
    .relationship-item {
        background-color: white;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }
    
    .relationship-item:hover {
        border-color: #165DFF;
        box-shadow: 0 4px 12px rgba(22, 93, 255, 0.1);
    }
    
    .relationship-arrow {
        font-size: 1.25rem;
        color: #165DFF;
        font-weight: bold;
    }
    
    /* 输入框样式优化 */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>select {
        border-radius: 6px;
        border: 1px solid #D9D9D9;
        padding: 0.625rem 0.75rem;
        font-size: 0.9375rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus,
    .stNumberInput>div>div>input:focus,
    .stSelectbox>div>div>select:focus {
        border-color: #165DFF;
        box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.2);
        outline: none;
    }
    
    /* 标题样式优化 */
    h1, h2, h3, h4, h5, h6 {
        color: #1F2937;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    h1 {
        font-size: 1.875rem;
        color: #1F2937;
    }
    
    h2 {
        font-size: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E9ECEF;
    }
    
    h3 {
        font-size: 1.25rem;
        color: #374151;
    }
    
    /* 步骤指示器样式 */
    .step-indicator {
        display: flex;
        margin-bottom: 2rem;
        overflow-x: auto;
        padding-bottom: 0.5rem;
    }
    
    .step-item {
        display: flex;
        align-items: center;
        min-width: 120px;
    }
    
    .step-number {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #E9ECEF;
        color: #6B7280;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        margin-right: 0.75rem;
        transition: all 0.3s ease;
    }
    
    .step-number.active {
        background-color: #165DFF;
        color: white;
    }
    
    .step-number.completed {
        background-color: #52C41A;
        color: white;
    }
    
    .step-text {
        font-size: 0.875rem;
        color: #6B7280;
        white-space: nowrap;
    }
    
    .step-text.active {
        color: #165DFF;
        font-weight: 500;
    }
    
    .step-divider {
        width: 24px;
        height: 2px;
        background-color: #E9ECEF;
        margin: 0 0.5rem;
        flex-shrink: 0;
    }
    
    .step-divider.completed {
        background-color: #52C41A;
    }
    
    /* 数据表格样式 */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1.25rem 0;
        background-color: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .data-table th {
        background-color: #F8FAFC;
        padding: 0.875rem 1rem;
        text-align: left;
        font-weight: 600;
        color: #374151;
        border-bottom: 1px solid #E9ECEF;
    }
    
    .data-table td {
        padding: 0.875rem 1rem;
        border-bottom: 1px solid #F3F4F6;
        color: #6B7280;
    }
    
    .data-table tr:hover td {
        background-color: #F9FAFB;
        color: #1F2937;
    }
    
    /* 进度条样式 */
    .progress-bar {
        height: 6px;
        background-color: #E9ECEF;
        border-radius: 3px;
        overflow: hidden;
        margin: 1rem 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #165DFF 0%, #0E4FD7 100%);
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    /* 响应式优化 */
    @media (max-width: 768px) {
        .main-container {
            padding: 1rem;
        }
        
        .section-container {
            padding: 1.5rem;
        }
        
        .relationship-item {
            flex-direction: column;
            align-items: flex-start;
        }
        
        .step-indicator {
            justify-content: flex-start;
        }
    }
</style>
""", unsafe_allow_html=True)

# 辅助函数
# 定义用于获取顶级实体名称的辅助函数
def get_top_level_entity_names():
    return [entity["name"] for entity in st.session_state.equity_data["top_level_entities"]]

# 获取子公司名称列表
def get_subsidiary_names():
    return [s["name"] for s in st.session_state.equity_data["subsidiaries"]]

# 初始化会话状态
def initialize_session_state():
    if 'equity_data' not in st.session_state:
        st.session_state.equity_data = {
            "core_company": "",
            "shareholders": [],
            "subsidiaries": [],
            "actual_controller": "",
            "top_level_entities": [],
            "entity_relationships": [],
            "control_relationships": [],
            "all_entities": []
        }
    
    if 'mermaid_code' not in st.session_state:
        st.session_state.mermaid_code = ""
    
    if 'editing_entity' not in st.session_state:
        st.session_state.editing_entity = None
    
    if 'editing_relationship' not in st.session_state:
        st.session_state.editing_relationship = None
    
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "core_company"
    
    if 'fullscreen_mode' not in st.session_state:
        st.session_state.fullscreen_mode = False

initialize_session_state()

# 定义步骤列表
steps = ["core_company", "top_entities", "subsidiaries", "relationships", "generate"]
# 定义步骤显示名称
step_names = {
    "core_company": "1. 核心公司",
    "top_entities": "2. 顶层实体",
    "subsidiaries": "3. 子公司",
    "relationships": "4. 关系设置",
    "generate": "5. 生成图表"
}

# 标题
st.title("✏️ 股权结构手动编辑器 - V1")

# 简介
st.markdown("""
本工具允许您手动添加公司、股东、子公司及它们之间的关系，生成股权结构图。
按照步骤填写信息，最终可以生成与图片识别相同格式的交互式Mermaid图表。
""")

# 全局导航栏 - 固定在顶部方便访问
with st.container():
    st.markdown("<div class='nav-buttons'>", unsafe_allow_html=True)
    nav_cols = st.columns([1, 1, 1])
    
    # 上一步按钮
    if st.session_state.current_step != steps[0]:
        prev_index = steps.index(st.session_state.current_step) - 1
        if nav_cols[0].button("⬅️ 上一步", use_container_width=True):
            # 检查是否有未保存的数据
            data_changed = False
            # 根据当前步骤检查是否有未保存的数据
            if st.session_state.current_step == "core_company":
                data_changed = 'temp_core_company' in st.session_state and st.session_state.temp_core_company != st.session_state.equity_data["core_company"]
            elif st.session_state.current_step == "top_entities":
                data_changed = 'temp_top_entities' in st.session_state and st.session_state.temp_top_entities != st.session_state.equity_data["top_level_entities"]
            elif st.session_state.current_step == "subsidiaries":
                data_changed = 'temp_subsidiaries' in st.session_state and st.session_state.temp_subsidiaries != st.session_state.equity_data["subsidiaries"]
            elif st.session_state.current_step == "relationships":
                data_changed = 'temp_relationships' in st.session_state and st.session_state.temp_relationships != st.session_state.equity_data["entity_relationships"]
            
            if data_changed:
                st.warning("您有未保存的更改，确定要离开当前页面吗？")
                confirm_cols = st.columns([1, 1])
                if confirm_cols[0].button("确定离开"):
                    st.session_state.current_step = steps[prev_index]
                    st.session_state.editing_entity = None
                    st.session_state.editing_relationship = None
                    st.rerun()
                if confirm_cols[1].button("取消"):
                    st.rerun()
            else:
                st.session_state.current_step = steps[prev_index]
                st.session_state.editing_entity = None
                st.session_state.editing_relationship = None
                st.rerun()
    
    # 下一步按钮
    if st.session_state.current_step != steps[-1]:
        next_index = steps.index(st.session_state.current_step) + 1
        if nav_cols[1].button("下一步 ➡️", use_container_width=True, type="primary"):
            # 特殊检查：确保核心公司已设置
            if st.session_state.current_step == "core_company" and not st.session_state.equity_data["core_company"]:
                st.error("请先设置核心公司")
            else:
                st.session_state.current_step = steps[next_index]
                st.session_state.editing_entity = None
                st.session_state.editing_relationship = None
                st.rerun()
    
    # 重置按钮 - 简化确认流程
    if nav_cols[2].button("🔄 重置当前步骤", use_container_width=True, type="secondary"):
        # 根据当前步骤重置数据
        if st.session_state.current_step == "core_company":
            if st.checkbox("确认重置核心公司设置？"):
                st.session_state.equity_data["core_company"] = ""
                st.session_state.equity_data["actual_controller"] = ""
                # 移除core_company实体
                st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "core_company"]
                st.success("核心公司设置已重置")
        elif st.session_state.current_step == "top_entities":
            if st.checkbox("确认重置顶级实体/股东？"):
                st.session_state.equity_data["top_level_entities"] = []
                # 移除相关实体
                st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "top_entity"]
                st.success("顶级实体/股东已重置")
        elif st.session_state.current_step == "subsidiaries":
            if st.checkbox("确认重置子公司？"):
                st.session_state.equity_data["subsidiaries"] = []
                # 移除相关实体
                st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "subsidiary"]
                st.success("子公司已重置")
        elif st.session_state.current_step == "relationships":
            if st.checkbox("确认重置关系设置？"):
                st.session_state.equity_data["entity_relationships"] = []
                st.session_state.equity_data["control_relationships"] = []
                st.success("关系设置已重置")
        elif st.session_state.current_step == "generate":
            st.info("在图表生成步骤中无需重置")
    
    # 危险操作 - 完全重置所有数据
    if st.button("⚠️ 完全重置所有数据", type="secondary", help="此操作将清除所有已输入的数据"):
        if st.checkbox("确认完全重置所有数据？此操作不可撤销！"):
            if st.button("确认完全重置"):
                # 重置所有会话状态
                st.session_state.equity_data = {
                    "core_company": "",
                    "shareholders": [],
                    "subsidiaries": [],
                    "actual_controller": "",
                    "top_level_entities": [],
                    "entity_relationships": [],
                    "control_relationships": [],
                    "all_entities": []
                }
                st.session_state.mermaid_code = ""
                st.session_state.editing_entity = None
                st.session_state.editing_relationship = None
                st.session_state.current_step = "core_company"
                st.success("所有数据已重置")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# 进度条
progress = steps.index(st.session_state.current_step) / (len(steps) - 1)
st.progress(progress)

# 步骤按钮导航
cols = st.columns(len(steps))
for i, step in enumerate(steps):
    disabled = i > steps.index(st.session_state.current_step)
    if cols[i].button(step_names[step], disabled=disabled, use_container_width=True):
        if not disabled:
            # 检查是否有未保存的数据
            data_changed = False
            # 根据当前步骤检查是否有未保存的数据
            if st.session_state.current_step == "core_company":
                data_changed = 'temp_core_company' in st.session_state and st.session_state.temp_core_company != st.session_state.equity_data["core_company"]
            elif st.session_state.current_step == "top_entities":
                data_changed = 'temp_top_entities' in st.session_state and st.session_state.temp_top_entities != st.session_state.equity_data["top_level_entities"]
            elif st.session_state.current_step == "subsidiaries":
                data_changed = 'temp_subsidiaries' in st.session_state and st.session_state.temp_subsidiaries != st.session_state.equity_data["subsidiaries"]
            elif st.session_state.current_step == "relationships":
                data_changed = 'temp_relationships' in st.session_state and st.session_state.temp_relationships != st.session_state.equity_data["entity_relationships"]
            
            if data_changed:
                st.warning("您有未保存的更改，确定要切换步骤吗？")
                confirm_cols = st.columns([1, 1])
                if confirm_cols[0].button("确定切换"):
                    st.session_state.current_step = step
                    st.session_state.editing_entity = None
                    st.session_state.editing_relationship = None
                    st.rerun()
                if confirm_cols[1].button("取消"):
                    st.rerun()
            else:
                st.session_state.current_step = step
                st.session_state.editing_entity = None
                st.session_state.editing_relationship = None
                st.rerun()

st.divider()

# 步骤1: 设置核心公司
if st.session_state.current_step == "core_company":
    st.subheader("📌 设置核心公司")
    
    with st.form("core_company_form"):
        core_company = st.text_input(
            "核心公司名称", 
            value=st.session_state.equity_data["core_company"],
            placeholder="请输入核心公司名称（如：Vastec Medical Equipment (Shanghai) Co., Ltd）"
        )
        
        controller = st.text_input(
            "实际控制人（可选）", 
            value=st.session_state.equity_data["actual_controller"],
            placeholder="请输入实际控制人名称（如：Collective control 或 个人/公司名称）"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.form_submit_button("保存并继续", type="primary"):
                if core_company.strip():
                    st.session_state.equity_data["core_company"] = core_company
                    st.session_state.equity_data["actual_controller"] = controller
                    
                    # 更新all_entities列表
                    all_entities = [e for e in st.session_state.equity_data["all_entities"] if e["type"] != "core_company"]
                    all_entities.append({"name": core_company, "type": "company"})
                    st.session_state.equity_data["all_entities"] = all_entities
                    
                    st.success("核心公司信息已保存")
                    # 不再自动跳转到下一步，而是让用户使用顶部导航按钮控制导航
                    st.rerun()
                else:
                    st.error("请输入核心公司名称")
        
        with col2:
            if st.form_submit_button("加载示例数据"):
                # 加载示例数据
                st.session_state.equity_data = {
                    "core_company": "Vastec Medical Equipment (Shanghai) Co., Ltd",
                    "actual_controller": "Collective control",
                    "shareholders": [],
                    "subsidiaries": [
                        {"name": "Yunnan Vastec Medical Equipment Co., Ltd.", "percentage": 70.0},
                        {"name": "Guangzhou Vastec Medical Equipment Co., Ltd.", "percentage": 60.0}
                    ],
                    "top_level_entities": [
                        {"name": "测试公司1", "type": "company"},
                        {"name": "Mr.ABC", "type": "person"},
                        {"name": "Shinva Medical Instrument Co., Ltd.", "type": "company"}
                    ],
                    "entity_relationships": [],
                    "control_relationships": [],
                    "all_entities": [
                        {"name": "Vastec Medical Equipment (Shanghai) Co., Ltd", "type": "company"},
                        {"name": "Yunnan Vastec Medical Equipment Co., Ltd.", "type": "company"},
                        {"name": "Guangzhou Vastec Medical Equipment Co., Ltd.", "type": "company"},
                        {"name": "测试公司1", "type": "company"},
                        {"name": "Mr.ABC", "type": "person"},
                        {"name": "Shinva Medical Instrument Co., Ltd.", "type": "company"}
                    ]
                }
                # 验证示例数据
                data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
                
                if data_valid:
                    st.success("示例数据已加载！包含核心公司、两家子公司和三个顶级实体，可直接在第4步测试股权关系定义。")
                    # 设置为下一个步骤并跳转
                    st.session_state.current_step = "relationships"
                    # 使用较新的st.rerun()方法，这是Streamlit推荐的方式
                    st.rerun()
                else:
                    st.error("示例数据验证失败，请联系管理员。")
    
    # 新增：AI分析功能
    st.markdown("---")
    st.subheader("🤖 AI分析功能")
    st.markdown("通过上传文件或文本描述，使用AI自动分析股权结构信息")
    
    with st.container():
        # 使用+号按钮打开文件上传对话框
        if st.button("➕ 上传股权结构文件", type="secondary", use_container_width=False):
            st.session_state.show_file_uploader = True
        
        # 显示上传的文件列表
        if "uploaded_files" in st.session_state and st.session_state.uploaded_files:
            st.markdown("### 已上传的文件")
            files_container = st.container(border=True)
            for i, file in enumerate(st.session_state.uploaded_files):
                cols = files_container.columns([0.8, 0.1, 0.1])
                cols[0].text(f"{file.name} ({file.size // 1024}KB)")
                if cols[1].button("查看", key=f"view_file_{i}"):
                    # 这里可以添加文件预览功能
                    st.info(f"文件名: {file.name}\n文件大小: {file.size} 字节\n文件类型: {file.type}")
                if cols[2].button("删除", key=f"del_file_{i}", type="secondary"):
                    # 从会话状态中移除文件
                    st.session_state.uploaded_files.pop(i)
                    st.rerun()
        
        # 显示文件上传对话框
        if "show_file_uploader" in st.session_state and st.session_state.show_file_uploader:
            with st.expander("选择文件上传", expanded=True):
                # 多文件上传器
                new_files = st.file_uploader(
                    "上传股权结构文件（支持Excel格式，可多选）", 
                    type=["xlsx", "xls"],
                    accept_multiple_files=True,
                    key="multiple_file_uploader"
                )
                
                # 初始化上传文件列表
                if "uploaded_files" not in st.session_state:
                    st.session_state.uploaded_files = []
                
                # 添加新上传的文件
                if new_files:
                    for file in new_files:
                        # 检查文件是否已存在
                        if not any(f.name == file.name and f.size == file.size for f in st.session_state.uploaded_files):
                            st.session_state.uploaded_files.append(file)
                    
                    # 关闭对话框
                    st.session_state.show_file_uploader = False
                    st.success(f"已成功上传 {len(new_files)} 个文件")
                    st.rerun()
                
                # 关闭按钮
                if st.button("取消", key="close_uploader"):
                    st.session_state.show_file_uploader = False
                    st.rerun()
        
        # DashScope API密钥输入
        api_key = st.text_input(
            "DashScope API密钥（可选）",
            type="password",
            placeholder="输入您的DashScope API密钥以使用真实AI服务"
        )
        
        # 分析提示词
        prompt = st.text_area(
            "分析要求说明",
            value="请详细分析此文件中的股权结构信息，包括核心公司、实际控制人、所有股东及其持股比例、子公司关系等。",
            help="提供更具体的要求可以获得更准确的分析结果"
        )
        
        # 分析按钮
        if st.button("🔍 使用AI分析股权结构", type="primary"):
            if "uploaded_files" not in st.session_state or not st.session_state.uploaded_files and not prompt.strip():
                st.error("请上传文件或提供分析要求")
            else:
                with st.spinner("正在分析股权结构信息..."):
                    try:
                        # 初始化分析结果计数
                        processed_files = 0
                        total_files = len(st.session_state.uploaded_files)
                        error_logs = []  # 确保error_logs已初始化
                        
                        # 处理所有上传的文件
                        if total_files > 0:
                            st.info(f"开始分析 {total_files} 个文件，请稍候...")
                            
                            for idx, uploaded_file in enumerate(st.session_state.uploaded_files, 1):
                                # 准备文件内容
                                file_content = uploaded_file.getvalue()
                                file_name = uploaded_file.name
                                
                                st.info(f"正在分析文件 {idx}/{total_files}: {file_name}")
                                
                                # 调用AI分析函数
                                result_data, file_error_logs = analyze_equity_with_ai(
                                    prompt=prompt,
                                    file_content=file_content,
                                    file_name=file_name,
                                    api_key=api_key
                                )
                                
                                # 合并错误日志
                                if file_error_logs:
                                    error_logs.extend(file_error_logs)
                                
                                # 处理分析结果
                                if result_data:
                                    processed_files += 1
                                    # 更新会话状态中的股权数据
                                    if "core_company" in result_data and result_data["core_company"]:
                                        st.session_state.equity_data["core_company"] = result_data["core_company"]
                                    
                                    if "actual_controller" in result_data and result_data["actual_controller"]:
                                        st.session_state.equity_data["actual_controller"] = result_data["actual_controller"]
                                    
                                    # 更新顶级实体
                                    if "top_level_entities" in result_data:
                                        new_entities = 0
                                        for entity in result_data["top_level_entities"]:
                                            # 转换格式以匹配现有数据结构
                                            formatted_entity = {
                                                "name": entity.get("name", ""),
                                                "type": "company" if entity.get("entity_type", "").lower() == "法人" else "person",
                                                "percentage": entity.get("percentage", 0.0)
                                            }
                                            # 避免重复添加
                                            if not any(e["name"] == formatted_entity["name"] for e in st.session_state.equity_data["top_level_entities"]):
                                                st.session_state.equity_data["top_level_entities"].append(formatted_entity)
                                                new_entities += 1
                                        if new_entities > 0:
                                            st.success(f"从 {file_name} 中添加了 {new_entities} 个新的顶级实体")
                                    
                                    # 更新子公司
                                    if "subsidiaries" in result_data:
                                        new_subsidiaries = 0
                                        for subsidiary in result_data["subsidiaries"]:
                                            formatted_subsidiary = {
                                                "name": subsidiary.get("name", ""),
                                                "percentage": subsidiary.get("percentage", 0.0)
                                            }
                                            # 避免重复添加
                                            if not any(s["name"] == formatted_subsidiary["name"] for s in st.session_state.equity_data["subsidiaries"]):
                                                st.session_state.equity_data["subsidiaries"].append(formatted_subsidiary)
                                                new_subsidiaries += 1
                                        if new_subsidiaries > 0:
                                            st.success(f"从 {file_name} 中添加了 {new_subsidiaries} 个子公司")
                                    
                                    # 更新实体关系
                                    if "entity_relationships" in result_data:
                                        # 创建子公司名称集合用于重复检查
                                        subsidiary_names = set(s["name"] for s in st.session_state.equity_data["subsidiaries"])
                                        core_company = st.session_state.equity_data.get("core_company", "")
                                        
                                        for rel in result_data["entity_relationships"]:
                                            formatted_rel = {
                                                "from": rel.get("from", ""),
                                                "to": rel.get("to", ""),
                                                "relationship_type": rel.get("relationship_type", ""),
                                                "description": rel.get("description", "")
                                            }
                                            
                                            # 获取关系的来源和目标（兼容两种格式）
                                            rel_from = formatted_rel.get("from", "")
                                            rel_to = formatted_rel.get("to", "")
                                            
                                            # 检查是否是核心公司对子公司的控股关系（应跳过）
                                            if (rel_from == core_company and 
                                                rel_to in subsidiary_names and 
                                                ("控股" in str(formatted_rel.get("relationship_type", "")) or 
                                                 "持有" in str(formatted_rel.get("relationship_type", "")) or 
                                                 "100%" in str(formatted_rel.get("description", "")))):
                                                continue
                                            
                                            # 避免重复添加，同时检查两种格式
                                            exists = False
                                            if "entity_relationships" in st.session_state.equity_data and isinstance(st.session_state.equity_data["entity_relationships"], list):
                                                for r in st.session_state.equity_data["entity_relationships"]:
                                                    # 检查两种格式的关系是否已经存在
                                                    if ((r.get("from", "") == rel_from and r.get("to", "") == rel_to) or 
                                                        (r.get("parent", "") == rel_from and r.get("child", "") == rel_to)):
                                                        exists = True
                                                        break
                                                
                                                if not exists:
                                                    st.session_state.equity_data["entity_relationships"].append(formatted_rel)
                                    
                                    # 更新控制关系
                                    if "control_relationships" in result_data:
                                        if "control_relationships" not in st.session_state.equity_data:
                                            st.session_state.equity_data["control_relationships"] = []
                                        
                                        for rel in result_data["control_relationships"]:
                                            # 支持parent/child和from/to两种格式
                                            formatted_rel = {
                                                "parent": rel.get("parent", rel.get("from", "")),
                                                "child": rel.get("child", rel.get("to", "")),
                                                "relationship_type": rel.get("relationship_type", "控制"),
                                                "description": rel.get("description", "")
                                            }
                                            # 避免重复添加
                                            if not any(r.get("parent", "") == formatted_rel["parent"] and r.get("child", "") == formatted_rel["child"] for r in st.session_state.equity_data["control_relationships"]):
                                                st.session_state.equity_data["control_relationships"].append(formatted_rel)
                                                st.success(f"添加控制关系: {formatted_rel['parent']} -> {formatted_rel['child']}")
                                    
                                    # 更新all_entities列表
                                    all_entities = []
                                    # 添加核心公司
                                    if st.session_state.equity_data["core_company"]:
                                        all_entities.append({"name": st.session_state.equity_data["core_company"], "type": "company"})
                                    # 添加顶级实体
                                    for entity in st.session_state.equity_data["top_level_entities"]:
                                        all_entities.append({"name": entity["name"], "type": entity["type"]})
                                    # 添加子公司
                                    for subsidiary in st.session_state.equity_data["subsidiaries"]:
                                        all_entities.append({"name": subsidiary["name"], "type": "company"})
                                    # 去重
                                    unique_entities = []
                                    names_seen = set()
                                    for entity in all_entities:
                                        if entity["name"] not in names_seen:
                                            unique_entities.append(entity)
                                            names_seen.add(entity["name"])
                                    st.session_state.equity_data["all_entities"] = unique_entities
                                else:
                                    st.error(f"无法从 {file_name} 中提取有效的股权结构信息")
                            
                            if processed_files > 0:
                                st.success(f"成功处理了 {processed_files}/{total_files} 个文件")
                            else:
                                st.error("无法从任何上传的文件中提取有效的股权结构信息")
                        else:
                            # 仅使用文本提示进行分析
                            st.info("仅使用文本提示进行分析...")
                            
                            result_data, error_logs = analyze_equity_with_ai(
                                prompt=prompt,
                                file_content=None,
                                file_name=None,
                                api_key=api_key
                            )
                            
                            if result_data:
                                # 更新会话状态中的股权数据
                                if "core_company" in result_data and result_data["core_company"]:
                                    st.session_state.equity_data["core_company"] = result_data["core_company"]
                                
                                if "actual_controller" in result_data and result_data["actual_controller"]:
                                    st.session_state.equity_data["actual_controller"] = result_data["actual_controller"]
                                
                                # 更新顶级实体
                                if "top_level_entities" in result_data:
                                    for entity in result_data["top_level_entities"]:
                                        formatted_entity = {
                                            "name": entity.get("name", ""),
                                            "type": "company" if entity.get("entity_type", "").lower() == "法人" else "person",
                                            "percentage": entity.get("percentage", 0.0)
                                        }
                                        if not any(e["name"] == formatted_entity["name"] for e in st.session_state.equity_data["top_level_entities"]):
                                            st.session_state.equity_data["top_level_entities"].append(formatted_entity)
                                
                                # 更新子公司
                                if "subsidiaries" in result_data:
                                    for subsidiary in result_data["subsidiaries"]:
                                        formatted_subsidiary = {
                                            "name": subsidiary.get("name", ""),
                                            "percentage": subsidiary.get("percentage", 0.0)
                                        }
                                        if not any(s["name"] == formatted_subsidiary["name"] for s in st.session_state.equity_data["subsidiaries"]):
                                            st.session_state.equity_data["subsidiaries"].append(formatted_subsidiary)
                                
                                # 更新实体关系
                                if "entity_relationships" in result_data:
                                    # 创建子公司名称集合用于重复检查
                                    subsidiary_names = set(s["name"] for s in st.session_state.equity_data["subsidiaries"])
                                    core_company = st.session_state.equity_data.get("core_company", "")
                                    
                                    for rel in result_data["entity_relationships"]:
                                        formatted_rel = {
                                            "from": rel.get("from", ""),
                                            "to": rel.get("to", ""),
                                            "relationship_type": rel.get("relationship_type", ""),
                                            "description": rel.get("description", "")
                                        }
                                        
                                        # 获取关系的来源和目标
                                        rel_from = formatted_rel.get("from", "")
                                        rel_to = formatted_rel.get("to", "")
                                        
                                        # 检查是否是核心公司对子公司的控股关系（应跳过）
                                        if (rel_from == core_company and 
                                            rel_to in subsidiary_names and 
                                            ("控股" in str(formatted_rel.get("relationship_type", "")) or 
                                             "持有" in str(formatted_rel.get("relationship_type", "")) or 
                                             "100%" in str(formatted_rel.get("description", "")))):
                                            continue
                                        
                                        # 避免重复添加，同时检查两种格式
                                        exists = False
                                        for r in st.session_state.equity_data["entity_relationships"]:
                                            # 检查两种格式的关系是否已经存在
                                            if ((r.get("from", "") == rel_from and r.get("to", "") == rel_to) or 
                                                (r.get("parent", "") == rel_from and r.get("child", "") == rel_to)):
                                                exists = True
                                                break
                                        
                                        if not exists:
                                            st.session_state.equity_data["entity_relationships"].append(formatted_rel)
                                
                                # 更新all_entities列表
                                all_entities = []
                                # 添加核心公司
                                if st.session_state.equity_data["core_company"]:
                                    all_entities.append({"name": st.session_state.equity_data["core_company"], "type": "company"})
                                # 添加顶级实体
                                for entity in st.session_state.equity_data["top_level_entities"]:
                                    all_entities.append({"name": entity["name"], "type": entity["type"]})
                                # 添加子公司
                                for subsidiary in st.session_state.equity_data["subsidiaries"]:
                                    all_entities.append({"name": subsidiary["name"], "type": "company"})
                                # 去重
                                unique_entities = []
                                names_seen = set()
                                for entity in all_entities:
                                    if entity["name"] not in names_seen:
                                        unique_entities.append(entity)
                                        names_seen.add(entity["name"])
                                st.session_state.equity_data["all_entities"] = unique_entities
                                
                                st.success("成功根据文本提示分析股权结构")
                            else:
                                st.error("无法根据提供的文本提示提取有效的股权结构信息")
                            
                        # 分析完成后显示结果摘要
                        st.success("AI分析完成！已自动填充股权结构信息")
                        st.markdown("### 分析结果摘要")
                        st.markdown(f"**核心公司**: {st.session_state.equity_data['core_company']}")
                        st.markdown(f"**实际控制人**: {st.session_state.equity_data['actual_controller']}")
                        st.markdown(f"**识别到的股东/顶级实体**: {len(st.session_state.equity_data['top_level_entities'])}")
                        st.markdown(f"**识别到的子公司**: {len(st.session_state.equity_data['subsidiaries'])}")
                        
                        # 确保按钮在分析完成后始终显示并正常工作
                        st.markdown("### 操作选项")
                        
                        # 使用表单来处理按钮点击，这样可以更好地控制错误信息的显示
                        with st.form(key='relationship_form'):
                            # 添加基本调试信息显示（默认折叠）
                            with st.expander("调试信息", expanded=False):
                                if 'equity_data' in st.session_state:
                                    st.json(st.session_state.equity_data, expanded=False)
                            
                            # 提交按钮
                            submit_button = st.form_submit_button("🔗 前往关系设置", type="primary")
                            
                            # 当按钮被点击时执行的逻辑
                            if submit_button:
                                # 使用通用数据验证函数
                                data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
                                
                                # 只有在数据有效的情况下才进行跳转
                                if data_valid:
                                    st.success("数据验证通过，正在跳转至关系设置...")
                                    # 设置下一步并跳转
                                    st.session_state.current_step = "relationships"
                                    # 清除任何编辑状态
                                    if 'editing_entity' in st.session_state:
                                        del st.session_state.editing_entity
                                    if 'editing_relationship' in st.session_state:
                                        del st.session_state.editing_relationship
                                    # 强制刷新页面
                                    st.rerun()
                                else:
                                    # 显示错误信息
                                    st.error("数据验证失败，无法跳转至关系设置。")
                                    
                                    # 显示关键错误
                                    error_messages = [log for log in validation_logs if "错误" in log]
                                    if error_messages:
                                        st.info("检测到以下问题：")
                                        for error in error_messages[:5]:  # 只显示前5个错误
                                            st.error(f"• {error}")
                                        if len(error_messages) > 5:
                                            st.info(f"...以及 {len(error_messages) - 5} 个其他问题")
                                    
                                    # 提供简单的修复建议
                                    st.info("建议检查：\n"
                                            "- 核心公司名称是否已设置\n"
                                            "- 所有实体列表(all_entities)是否包含数据\n"
                                            "- 所有必要字段的格式是否正确")
                                    
                                    # 简单的数据完整性检查
                                    st.markdown("#### 数据完整性检查")
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f"核心公司: {'✅' if st.session_state.equity_data.get('core_company', '').strip() else '❌'}")
                                        st.markdown(f"顶级实体: {len(st.session_state.equity_data.get('top_level_entities', []))}")
                                    with col2:
                                        st.markdown(f"子公司: {len(st.session_state.equity_data.get('subsidiaries', []))}")
                                        st.markdown(f"所有实体: {'✅' if len(st.session_state.equity_data.get('all_entities', [])) > 0 else '❌'}")
                        
                        # 显示错误日志（如果有）
                        if error_logs:
                            with st.expander("查看分析日志", expanded=False):
                                for log in error_logs:
                                    st.info(log)
                    except Exception as e:
                        import traceback
                        st.error(f"分析过程中发生错误: {str(e)}")
                        with st.expander("查看详细错误信息", expanded=False):
                            st.text(traceback.format_exc())
    
    # 提示信息
    st.markdown("""\n*提示：\n- 点击 ➕ 按钮可以上传多个Excel文件，系统将依次分析每个文件中的股权结构信息\n- 上传的Excel文件请确保包含公司名称、股东信息、持股比例等关键字段\n- 提供详细的分析要求可以获得更精准的结果\n- 分析完成后，可以在后续步骤中查看和编辑AI识别的信息\n- 您可以随时查看或删除已上传的文件*""")


# 步骤2: 添加顶级实体/股东
elif st.session_state.current_step == "top_entities":
    # 添加一个从名称中提取百分比的函数
    def extract_percentage_from_name(name_text):
        """从名称文本中提取百分比数值"""
        import re
        # 匹配常见的百分比格式：(42.71%), 42.71%等
        match = re.search(r'[\(\[\s]([\d.]+)%[\)\]\s]?', name_text)
        if match:
            try:
                percentage = float(match.group(1))
                # 确保在有效范围内
                if 0 <= percentage <= 100:
                    return percentage
            except ValueError:
                pass
        return None
    
    st.subheader("👤 添加顶级实体/股东")
    
    if st.session_state.equity_data["core_company"]:
        st.markdown(f"**核心公司**: {st.session_state.equity_data['core_company']}")
    
    # 显示已添加的顶级实体
    if st.session_state.equity_data["top_level_entities"]:
        st.markdown("### 已添加的顶级实体/股东")
        for i, entity in enumerate(st.session_state.equity_data["top_level_entities"]):
            # 修复：处理可能没有percentage字段的情况
            percentage_text = f" - {entity.get('percentage', 'N/A')}%" if entity.get('percentage') else ""
            with st.expander(f"{entity['name']}{percentage_text}"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("编辑", key=f"edit_top_entity_{i}"):
                        st.session_state.editing_entity = ("top_entity", i)
                        st.rerun()
                with col2:
                    if st.button("删除", key=f"delete_top_entity_{i}", type="secondary"):
                        # 从列表中移除
                        removed_entity = st.session_state.equity_data["top_level_entities"].pop(i)
                        # 从all_entities中移除
                        st.session_state.equity_data["all_entities"] = [
                            e for e in st.session_state.equity_data["all_entities"] 
                            if e["name"] != removed_entity["name"]
                        ]
                        st.success(f"已删除: {removed_entity['name']}")
                        st.rerun()
    
    # 编辑现有实体
    editing_index = None
    if st.session_state.editing_entity and st.session_state.editing_entity[0] == "top_entity":
        editing_index = st.session_state.editing_entity[1]
        if editing_index < len(st.session_state.equity_data["top_level_entities"]):
            entity = st.session_state.equity_data["top_level_entities"][editing_index]
            
            with st.form("edit_top_entity_form"):
                st.subheader("编辑顶级实体")
                name = st.text_input("实体名称", value=entity["name"])
                
                # 自动从名称中提取比例
                extracted_percentage = extract_percentage_from_name(name)
                # 优先使用从名称提取的比例，如果没有则使用现有比例或默认值
                default_percentage = extracted_percentage if extracted_percentage is not None else entity.get("percentage", 10.0)
                
                # 修复：处理可能没有percentage字段的情况，提供默认值
                percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=default_percentage, step=0.01)
                entity_type = st.selectbox("实体类型", ["company", "person"], index=0 if entity.get("type", "company") == "company" else 1)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("保存修改", type="primary"):
                        if name.strip():
                            # 更新实体信息
                            st.session_state.equity_data["top_level_entities"][editing_index]["name"] = name
                            st.session_state.equity_data["top_level_entities"][editing_index]["percentage"] = percentage
                            
                            # 更新all_entities
                            for e in st.session_state.equity_data["all_entities"]:
                                if e["name"] == entity["name"]:
                                    e["name"] = name
                                    e["type"] = entity_type
                                    break
                            
                            st.session_state.editing_entity = None
                            st.success("实体信息已更新！")
                            st.rerun()
                        else:
                            st.error("请输入实体名称")
                
                with col2:
                    if st.form_submit_button("取消", type="secondary"):
                        st.session_state.editing_entity = None
                        st.rerun()
    else:
        # 添加新实体
        with st.form("add_top_entity_form"):
            st.subheader("添加新的顶级实体/股东")
            col1, col2 = st.columns([1, 1])
            with col1:
                name = st.text_input("实体名称", placeholder="如：Mr. Ho Kuk Sing 或 Shinva Medical Instrument Co., Ltd. 或 方庆熙 (42.71%)")
            
            # 自动从名称中提取比例
            extracted_percentage = extract_percentage_from_name(name) if name else None
            # 如果从名称中提取到比例，则使用提取的值，否则使用默认值10.0
            default_percentage = extracted_percentage if extracted_percentage is not None else 10.0
            
            with col2:
                percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=default_percentage, step=0.01)
            
            entity_type = st.selectbox("实体类型", ["company", "person"], help="选择实体是公司还是个人")
            
            # 修改1：删除保存并继续按钮，只保留添加按钮
            if st.form_submit_button("添加顶级实体", type="primary"):
                if name.strip():
                    # 检查是否已存在
                    exists = any(e["name"] == name for e in st.session_state.equity_data["top_level_entities"])
                    if not exists:
                        # 添加实体时包含百分比
                        st.session_state.equity_data["top_level_entities"].append({
                            "name": name,
                            "type": entity_type,
                            "percentage": percentage
                        })
                        
                        # 添加到所有实体列表
                        if not any(e["name"] == name for e in st.session_state.equity_data["all_entities"]):
                            st.session_state.equity_data["all_entities"].append({
                                "name": name,
                                "type": entity_type
                            })
                        
                        st.success(f"已添加顶级实体: {name}")
                        # 修改：无论是否继续，都添加后立即刷新页面，实现实时显示
                        st.rerun()
                    else:
                        st.error("该实体已存在")
                else:
                    st.error("请输入实体名称")
        
        # 新增：从Excel导入股东信息
        st.subheader("📊 从Excel导入股东信息")
        st.info("上传Excel文件，系统将自动提取名称和出资比例信息")
        
        # 添加文件上传器
        uploaded_file = st.file_uploader("选择Excel文件", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            try:
                # 检查是否安装了pandas和openpyxl
                try:
                    import pandas as pd
                except ImportError:
                    st.error("需要安装pandas库来读取Excel文件")
                    if st.button("安装依赖库"):
                            import subprocess
                            import sys
                            subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
                            st.success("依赖库已安装，请刷新页面重试")
                            st.stop()
                
                # 读取Excel文件
                # 修改：尝试不同的方式读取Excel，处理可能的空白行或特殊格式
                # 首先尝试常规读取
                try:
                    df = pd.read_excel(uploaded_file)
                except Exception as e:
                    # 如果失败，尝试跳过前几行或使用其他选项
                    st.warning(f"常规读取方式失败: {str(e)}")
                    st.info("尝试使用其他方式读取文件...")
                    # 尝试跳过前几行
                    df = pd.read_excel(uploaded_file, header=1)
                
                # 如果列名仍然是Unnamed，尝试重置列名
                if any('Unnamed' in str(col) for col in df.columns):
                    # 重置列名，使用数字索引
                    df.columns = [f'Column_{i}' for i in range(len(df.columns))]
                    st.info("Excel文件没有明确的列名，已使用数字索引作为列名")
                
                # 修改：确保数据类型一致性，避免Arrow转换错误
                # 将所有列转换为字符串类型进行显示
                df_display = df.astype(str)
                
                # 显示前几行数据供用户确认
                st.markdown("### 数据预览")
                st.dataframe(df_display.head(10))  # 显示转换后的数据
                
                # 自动检测包含名称和比例的列
                name_column = None
                percentage_column = None
                
                # 扩展检测规则，处理可能的数字列名
                for col in df.columns:
                    col_str = str(col)
                    col_lower = col_str.lower()
                    # 名称列检测
                    if not name_column:
                        # 检查列名是否包含关键词
                        if any(keyword in col_lower for keyword in ["名称", "股东", "公司", "name", "investor"]):
                            name_column = col
                        else:
                            # 尝试检查第一行数据，如果包含文本可能是名称列
                            try:
                                first_value = str(df[col].iloc[0])
                                # 如果是字符串且较长，可能是名称
                                if len(first_value.strip()) > 5:
                                    name_column = col
                            except:
                                pass
                    
                    # 比例列检测
                    if not percentage_column:
                        # 检查列名是否包含关键词
                        if any(keyword in col_lower for keyword in ["比例", "持股", "出资", "percent", "percentage"]):
                            percentage_column = col
                        else:
                            # 尝试检查第一行数据，如果包含数字且小于等于100可能是比例列
                            try:
                                first_value = df[col].iloc[0]
                                # 如果是数字且在0-100之间，可能是比例
                                if isinstance(first_value, (int, float)) and 0 <= first_value <= 100:
                                    percentage_column = col
                            except:
                                pass
                
                # 让用户确认或选择列
                st.markdown("### 列选择")
                col1, col2 = st.columns([1, 1])
                with col1:
                    # 如果没有检测到名称列，默认选择第一列
                    name_col_index = 0
                    if name_column is not None:
                        # 找到name_column对应的索引位置
                        name_col_index = list(df.columns).index(name_column)
                    name_col_selected = st.selectbox("选择名称列", df.columns, index=name_col_index)
                    
                    # 显示所选列的前几个值供参考 - 使用安全转换
                    st.markdown("**名称列预览:**")
                    try:
                        name_preview = df[name_col_selected].head(5).astype(str).tolist()
                        st.write(name_preview)
                    except Exception as e:
                        st.warning(f"无法显示预览: {str(e)}")
                
                with col2:
                    # 如果没有检测到比例列，默认选择第二列
                    percentage_col_index = 1 if len(df.columns) > 1 else 0
                    if percentage_column is not None:
                        # 找到percentage_column对应的索引位置
                        percentage_col_index = list(df.columns).index(percentage_column)
                    percentage_col_selected = st.selectbox("选择比例列", df.columns, index=percentage_col_index)
                    
                    # 显示所选列的前几个值供参考 - 使用安全转换
                    st.markdown("**比例列预览:**")
                    try:
                        percent_preview = df[percentage_col_selected].head(5).astype(str).tolist()
                        st.write(percent_preview)
                    except Exception as e:
                        st.warning(f"无法显示预览: {str(e)}")
                
                # 添加一个选项来跳过某些行（如标题行）
                skip_rows = st.number_input("跳过前几行（如果数据上方有标题或说明）", min_value=0, max_value=10, value=0)
                
                # 选择实体类型
                default_entity_type = st.selectbox("默认实体类型", ["company", "person"], help="导入的实体默认类型")
                
                # 导入按钮
                if st.button("开始导入", type="primary"):
                    # 添加导入过程的日志（内部日志，不全部显示在界面）
                    import logging
                    logging.basicConfig(level=logging.INFO)
                    logger = logging.getLogger("excel_import")
                    
                    # 显示正在处理的信息
                    processing_placeholder = st.info("正在处理导入...")
                    
                    # 保存原始列索引而不是列名
                    name_col_index = list(df.columns).index(name_col_selected)
                    percentage_col_index = list(df.columns).index(percentage_col_selected)
                    
                    # 重新读取并跳过指定的行数
                    df_processing = None
                    try:
                        if skip_rows > 0:
                            df_processing = pd.read_excel(uploaded_file, skiprows=skip_rows)
                            # 再次处理列名
                            if any('Unnamed' in str(col) for col in df_processing.columns):
                                df_processing.columns = [f'Column_{i}' for i in range(len(df_processing.columns))]
                        else:
                            # 如果不跳过行，直接使用原始数据
                            df_processing = df.copy()
                    except Exception as e:
                        processing_placeholder.empty()
                        st.error(f"读取数据失败: {str(e)}")
                        st.stop()
                    
                    # 确保索引有效
                    if name_col_index >= len(df_processing.columns) or percentage_col_index >= len(df_processing.columns):
                        processing_placeholder.empty()
                        st.error("选择的列索引超出数据范围！")
                        st.stop()
                    
                    # 根据索引获取实际的列名
                    actual_name_col = df_processing.columns[name_col_index]
                    actual_percentage_col = df_processing.columns[percentage_col_index]
                    
                    imported_count = 0
                    skipped_count = 0
                    errors = []
                    
                    # 处理每一行数据
                    for index, row in df_processing.iterrows():
                        try:
                            # 获取名称和比例 - 安全转换为字符串
                            try:
                                entity_name = str(row[actual_name_col]).strip()
                            except Exception as e:
                                raise ValueError(f"获取名称失败: {str(e)}")
                            
                            try:
                                percentage_value = row[actual_percentage_col]
                            except Exception as e:
                                raise ValueError(f"获取比例失败: {str(e)}")
                            
                            logger.info(f"处理行 {index+1}: 名称='{entity_name}', 比例值='{percentage_value}'")
                            
                            # 跳过空名称或无效名称
                            if not entity_name or entity_name.lower() in ["nan", "none", "null", "", "-"]:
                                skipped_count += 1
                                continue
                            
                            # 尝试将比例转换为数字
                            percentage = None
                            try:
                                percentage = float(percentage_value)
                                # 确保比例在有效范围内
                                if percentage < 0 or percentage > 100:
                                    skipped_count += 1
                                    errors.append(f"第{index+1}行: 比例 {percentage} 超出有效范围")
                                    continue
                            except (ValueError, TypeError):
                                # 尝试从字符串中提取数字（处理如"30%"这样的值）
                                try:
                                    import re
                                    # 尝试从字符串中提取数字
                                    num_str = re.search(r'\d+(\.\d+)?', str(percentage_value))
                                    if num_str:
                                        percentage = float(num_str.group())
                                        if not (0 <= percentage <= 100):
                                            skipped_count += 1
                                            errors.append(f"第{index+1}行: 提取的比例 {percentage} 超出有效范围")
                                            continue
                                    else:
                                        skipped_count += 1
                                        errors.append(f"第{index+1}行: 无法从 '{percentage_value}' 中提取比例")
                                        continue
                                except Exception as e:
                                    # 如果无法转换为数字，跳过
                                    skipped_count += 1
                                    errors.append(f"第{index+1}行: 比例转换失败 - {str(e)}")
                                    continue
                            
                            # 检查是否已存在
                            exists = False
                            for i, entity in enumerate(st.session_state.equity_data["top_level_entities"]):
                                if entity["name"] == entity_name:
                                    # 更新现有实体的百分比
                                    st.session_state.equity_data["top_level_entities"][i]["percentage"] = percentage
                                    exists = True
                                    imported_count += 1
                                    logger.info(f"第{index+1}行: 更新现有实体 '{entity_name}' 的比例为 {percentage}%")
                                    break
                            
                            # 如果不存在，添加新实体
                            if not exists:
                                st.session_state.equity_data["top_level_entities"].append({
                                    "name": entity_name,
                                    "type": default_entity_type,
                                    "percentage": percentage
                                })
                                
                                # 添加到所有实体列表
                                if not any(e["name"] == entity_name for e in st.session_state.equity_data["all_entities"]):
                                    st.session_state.equity_data["all_entities"].append({
                                        "name": entity_name,
                                        "type": default_entity_type
                                    })
                                
                                imported_count += 1
                                logger.info(f"第{index+1}行: 新增实体 '{entity_name}' 比例为 {percentage}%")
                        except Exception as e:
                            skipped_count += 1
                            error_msg = f"第{index+1}行: 处理失败 - {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                    
                    # 更新占位符为处理完成
                    processing_placeholder.empty()
                    
                    # 显示导入结果，使用更醒目的格式
                    st.markdown("### 导入结果")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("成功导入", imported_count)
                    with col2:
                        st.metric("跳过记录", skipped_count)
                    
                    # 如果有错误，显示错误信息
                    if errors:
                        st.warning(f"共 {len(errors)} 条记录处理失败:")
                        # 使用expander折叠错误信息，避免占用太多空间
                        with st.expander("查看详细错误信息"):
                            for error in errors:
                                st.code(error)
                    
                    # 添加一个确认按钮再刷新，让用户有时间查看结果
                    if st.button("确认并刷新列表", type="primary"):
                        st.rerun()
                    else:
                        st.info("点击上方按钮刷新列表，查看导入结果")
                    
                    
            except Exception as e:
                st.error(f"导入出错: {str(e)}")

# 步骤3: 添加子公司
elif st.session_state.current_step == "subsidiaries":
    st.subheader("🏢 添加子公司")
    
    if st.session_state.equity_data["core_company"]:
        st.markdown(f"**核心公司**: {st.session_state.equity_data['core_company']}")
    
    # 显示已添加的子公司
    if st.session_state.equity_data["subsidiaries"]:
        st.markdown("### 已添加的子公司")
        for i, subsidiary in enumerate(st.session_state.equity_data["subsidiaries"]):
            with st.expander(f"{subsidiary['name']} - {subsidiary['percentage']}%"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("编辑", key=f"edit_subsidiary_{i}"):
                        st.session_state.editing_entity = ("subsidiary", i)
                        st.rerun()
                with col2:
                    if st.button("删除", key=f"delete_subsidiary_{i}", type="secondary"):
                        # 从列表中移除
                        removed_subsidiary = st.session_state.equity_data["subsidiaries"].pop(i)
                        # 从all_entities中移除
                        st.session_state.equity_data["all_entities"] = [
                            e for e in st.session_state.equity_data["all_entities"] 
                            if e["name"] != removed_subsidiary["name"]
                        ]
                        st.success(f"已删除: {removed_subsidiary['name']}")
                        st.rerun()
    
    # Excel导入子公司信息
    st.subheader("📊 从Excel导入子公司")
    st.markdown("上传Excel文件，批量导入子公司信息。系统会自动匹配公司名称和持股比例。")
    
    # 检查pandas是否已安装
    pandas_available = False
    try:
        import pandas as pd
        pandas_available = True
    except ImportError:
        pass
    
    # 文件上传器
    uploaded_file_sub = st.file_uploader("选择Excel文件", type=["xlsx", "xls"], key="subsidiary_excel")
    
    if uploaded_file_sub and pandas_available:
        try:
            import pandas as pd
            # 尝试常规读取
            df_sub = pd.read_excel(uploaded_file_sub)
            
            # 如果列名有问题，尝试跳过首行作为新的列名
            if any('Unnamed' in str(col) for col in df_sub.columns):
                uploaded_file_sub.seek(0)
                df_sub = pd.read_excel(uploaded_file_sub)
            
            # 将所有列转换为字符串类型，避免Arrow错误
            for col in df_sub.columns:
                df_sub[col] = df_sub[col].astype(str)
            
            # 显示文件预览
            st.subheader("文件预览")
            st.dataframe(df_sub.head(10))
            
            # 让用户选择哪一列包含公司名称和持股比例
            st.subheader("列映射")
            col1, col2 = st.columns(2)
            
            with col1:
                name_col_selected_sub = st.selectbox(
                    "选择包含子公司名称的列", 
                    df_sub.columns.tolist(),
                    help="请选择包含子公司名称的列"
                )
            
            with col2:
                percentage_col_selected_sub = st.selectbox(
                    "选择包含持股比例的列", 
                    df_sub.columns.tolist(),
                    help="请选择包含持股比例的列"
                )
            
            # 让用户设置是否跳过表头行
            skip_rows_sub = st.number_input(
                "跳过前几行（如果有表头或说明文字）", 
                min_value=0, 
                max_value=10, 
                value=0, 
                step=1
            )
            
            # 导入按钮
            if st.button("开始导入子公司", type="primary"):
                # 添加导入过程的日志（内部日志，不全部显示在界面）
                import logging
                logging.basicConfig(level=logging.INFO)
                logger = logging.getLogger("excel_subsidiary_import")
                
                # 显示正在处理的信息
                processing_placeholder = st.info("正在处理导入...")
                
                # 保存原始列索引而不是列名
                name_col_index = list(df_sub.columns).index(name_col_selected_sub)
                percentage_col_index = list(df_sub.columns).index(percentage_col_selected_sub)
                
                # 重新读取并跳过指定的行数
                df_processing = None
                try:
                    if skip_rows_sub > 0:
                        df_processing = pd.read_excel(uploaded_file_sub, skiprows=skip_rows_sub)
                        # 再次处理列名
                        if any('Unnamed' in str(col) for col in df_processing.columns):
                            df_processing.columns = [f'Column_{i}' for i in range(len(df_processing.columns))]
                    else:
                        # 如果不跳过行，直接使用原始数据
                        df_processing = df_sub.copy()
                except Exception as e:
                    processing_placeholder.empty()
                    st.error(f"读取数据失败: {str(e)}")
                    st.stop()
                
                # 确保索引有效
                if name_col_index >= len(df_processing.columns) or percentage_col_index >= len(df_processing.columns):
                    processing_placeholder.empty()
                    st.error("选择的列索引超出数据范围！")
                    st.stop()
                
                # 根据索引获取实际的列名
                actual_name_col = df_processing.columns[name_col_index]
                actual_percentage_col = df_processing.columns[percentage_col_index]
                
                imported_count = 0
                skipped_count = 0
                errors = []
                
                # 处理每一行数据
                for index, row in df_processing.iterrows():
                    try:
                        # 获取名称和比例 - 安全转换为字符串
                        try:
                            subsidiary_name = str(row[actual_name_col]).strip()
                        except Exception as e:
                            raise ValueError(f"获取名称失败: {str(e)}")
                        
                        try:
                            percentage_value = row[actual_percentage_col]
                        except Exception as e:
                            raise ValueError(f"获取比例失败: {str(e)}")
                        
                        logger.info(f"处理行 {index+1}: 名称='{subsidiary_name}', 比例值='{percentage_value}'")
                        
                        # 跳过空名称或无效名称
                        if not subsidiary_name or subsidiary_name.lower() in ["nan", "none", "null", "", "-"]:
                            skipped_count += 1
                            continue
                        
                        # 尝试将比例转换为数字
                        percentage = None
                        try:
                            percentage = float(percentage_value)
                            # 确保比例在有效范围内
                            if percentage < 0 or percentage > 100:
                                skipped_count += 1
                                errors.append(f"第{index+1}行: 比例 {percentage} 超出有效范围")
                                continue
                        except (ValueError, TypeError):
                            # 尝试从字符串中提取数字（处理如"30%"这样的值）
                            try:
                                import re
                                # 尝试从字符串中提取数字
                                num_str = re.search(r'\d+(\.\d+)?', str(percentage_value))
                                if num_str:
                                    percentage = float(num_str.group())
                                    if not (0 <= percentage <= 100):
                                        skipped_count += 1
                                        errors.append(f"第{index+1}行: 提取的比例 {percentage} 超出有效范围")
                                        continue
                                else:
                                    skipped_count += 1
                                    errors.append(f"第{index+1}行: 无法从 '{percentage_value}' 中提取比例")
                                    continue
                            except Exception as e:
                                # 如果无法转换为数字，跳过
                                skipped_count += 1
                                errors.append(f"第{index+1}行: 比例转换失败 - {str(e)}")
                                continue
                        
                        # 检查是否已存在
                        exists = False
                        for i, sub in enumerate(st.session_state.equity_data["subsidiaries"]):
                            if sub["name"] == subsidiary_name:
                                # 更新现有子公司的百分比
                                st.session_state.equity_data["subsidiaries"][i]["percentage"] = percentage
                                
                                # 更新对应的关系
                                if st.session_state.equity_data["core_company"]:
                                    for j, rel in enumerate(st.session_state.equity_data["entity_relationships"]):
                                        if rel["parent"] == st.session_state.equity_data["core_company"] and rel["child"] == subsidiary_name:
                                            st.session_state.equity_data["entity_relationships"][j]["percentage"] = percentage
                                            break
                                
                                exists = True
                                imported_count += 1
                                logger.info(f"第{index+1}行: 更新现有子公司 '{subsidiary_name}' 的比例为 {percentage}%")
                                break
                        
                        # 如果不存在，添加新子公司
                        if not exists:
                            st.session_state.equity_data["subsidiaries"].append({
                                "name": subsidiary_name,
                                "type": "company",
                                "percentage": percentage
                            })
                            
                            # 添加到所有实体列表
                            if not any(e["name"] == subsidiary_name for e in st.session_state.equity_data["all_entities"]):
                                st.session_state.equity_data["all_entities"].append({
                                    "name": subsidiary_name,
                                    "type": "company"
                                })
                            
                            # 建立与核心公司的关系
                            if st.session_state.equity_data["core_company"]:
                                st.session_state.equity_data["entity_relationships"].append({
                                    "parent": st.session_state.equity_data["core_company"],
                                    "child": subsidiary_name,
                                    "percentage": percentage
                                })
                            
                            imported_count += 1
                            logger.info(f"第{index+1}行: 新增子公司 '{subsidiary_name}' 比例为 {percentage}%")
                    except Exception as e:
                        skipped_count += 1
                        error_msg = f"第{index+1}行: 处理失败 - {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                # 更新占位符为处理完成
                processing_placeholder.empty()
                
                # 显示导入结果，使用更醒目的格式
                st.markdown("### 导入结果")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("成功导入", imported_count)
                with col2:
                    st.metric("跳过记录", skipped_count)
                
                # 如果有错误，显示错误信息
                if errors:
                    st.warning(f"共 {len(errors)} 条记录处理失败:")
                    # 使用expander折叠错误信息，避免占用太多空间
                    with st.expander("查看详细错误信息"):
                        for error in errors:
                            st.code(error)
                
                # 添加一个确认按钮再刷新，让用户有时间查看结果
                if st.button("确认并刷新列表", type="primary"):
                    st.rerun()
                else:
                    st.info("点击上方按钮刷新列表，查看导入结果")
        
        except Exception as e:
            st.error(f"读取文件失败: {str(e)}")
    elif uploaded_file_sub and not pandas_available:
        # 如果pandas未安装，提供安装选项
        st.warning("需要安装pandas库来处理Excel文件。")
        if st.button("安装pandas"):
            try:
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
                st.success("pandas安装成功，请刷新页面重试。")
            except Exception as e:
                st.error(f"安装pandas失败: {str(e)}")
    
    # 编辑现有子公司
    editing_index = None
    if st.session_state.editing_entity and st.session_state.editing_entity[0] == "subsidiary":
        editing_index = st.session_state.editing_entity[1]
        if editing_index < len(st.session_state.equity_data["subsidiaries"]):
            subsidiary = st.session_state.equity_data["subsidiaries"][editing_index]
            
            with st.form("edit_subsidiary_form"):
                st.subheader("编辑子公司")
                name = st.text_input("子公司名称", value=subsidiary["name"])
                percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=subsidiary["percentage"], step=0.01)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("保存修改", type="primary"):
                        if name.strip():
                            # 更新子公司信息
                            st.session_state.equity_data["subsidiaries"][editing_index]["name"] = name
                            st.session_state.equity_data["subsidiaries"][editing_index]["percentage"] = percentage
                            
                            # 更新all_entities
                            for e in st.session_state.equity_data["all_entities"]:
                                if e["name"] == subsidiary["name"]:
                                    e["name"] = name
                                    break
                            
                            # 更新关系
                            if st.session_state.equity_data["core_company"]:
                                for rel in st.session_state.equity_data["entity_relationships"]:
                                    if rel["parent"] == st.session_state.equity_data["core_company"] and rel["child"] == subsidiary["name"]:
                                        rel["child"] = name
                                        rel["percentage"] = percentage
                                        break
                            
                            st.session_state.editing_entity = None
                            st.success("子公司信息已更新！")
                            st.rerun()
                        else:
                            st.error("请输入子公司名称")
                
                with col2:
                    if st.form_submit_button("取消", type="secondary"):
                        st.session_state.editing_entity = None
                        st.rerun()
    else:
        # 添加新子公司
        with st.form("add_subsidiary_form"):
            st.subheader("添加新的子公司")
            col1, col2 = st.columns([1, 1])
            with col1:
                name = st.text_input("子公司名称", placeholder="如：Yunnan Vastec Medical Equipment Co., Ltd.")
            with col2:
                percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=51.0, step=0.01)
                
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.form_submit_button("添加子公司", type="primary"):
                    if name.strip():
                        # 检查是否已存在
                        exists = any(s["name"] == name for s in st.session_state.equity_data["subsidiaries"])
                        if not exists:
                            # 添加到子公司列表
                            st.session_state.equity_data["subsidiaries"].append({
                                "name": name,
                                "percentage": percentage
                            })
                            
                            # 添加到所有实体列表
                            if not any(e["name"] == name for e in st.session_state.equity_data["all_entities"]):
                                st.session_state.equity_data["all_entities"].append({
                                    "name": name,
                                    "type": "company"
                                })
                            
                            # 子公司自动与核心公司建立关系
                            if st.session_state.equity_data["core_company"]:
                                # 检查关系是否已存在
                                relationship_exists = any(
                                    r["parent"] == st.session_state.equity_data["core_company"] and r["child"] == name
                                    for r in st.session_state.equity_data["entity_relationships"]
                                )
                                if not relationship_exists:
                                    st.session_state.equity_data["entity_relationships"].append({
                                        "parent": st.session_state.equity_data["core_company"],
                                        "child": name,
                                        "percentage": percentage
                                    })
                            
                            st.success(f"已添加子公司: {name}")
                            # 修改：无论是否继续，都添加后立即刷新页面，实现实时显示
                            st.rerun()
                        else:
                            st.error("该子公司已存在")
                    else:
                        st.error("请输入子公司名称")

# 步骤4: 定义关系
elif st.session_state.current_step == "relationships":
    st.subheader("🔗 定义关系")
    
    # 添加概览信息，显示已添加的核心公司、主要股东和子公司
    st.markdown("### 📋 已添加实体概览")
    
    # 核心公司信息
    if st.session_state.equity_data["core_company"]:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.info(f"**核心公司**: {st.session_state.equity_data['core_company']}")
        if st.session_state.equity_data["actual_controller"]:
            with col2:
                st.info(f"**实际控制人**: {st.session_state.equity_data['actual_controller']}")
    
    # 主要股东信息
    if st.session_state.equity_data["top_level_entities"]:
        st.markdown("#### 主要股东/顶级实体")
        cols = st.columns(3)
        for i, entity in enumerate(st.session_state.equity_data["top_level_entities"]):
            with cols[i % 3]:
                # 修复：处理可能没有percentage字段的情况
                percentage = entity.get('percentage', 'N/A')
                st.write(f"- {entity['name']} ({percentage}%)")
    
    # 子公司信息
    if st.session_state.equity_data["subsidiaries"]:
        st.markdown("#### 子公司")
        cols = st.columns(3)
        for i, subsidiary in enumerate(st.session_state.equity_data["subsidiaries"]):
            with cols[i % 3]:
                st.write(f"- {subsidiary['name']} ({subsidiary['percentage']}%)")
    
    # 显示分隔线
    st.divider()
    
    # 获取所有实体名称列表
    all_entity_names = [e["name"] for e in st.session_state.equity_data["all_entities"]]
    
    # 显示股权关系
    st.markdown("### 股权关系")
    if st.session_state.equity_data["entity_relationships"]:
        # 添加一个函数来获取实体的持股比例
        def get_entity_percentage_for_display(entity_name):
            """从顶级实体列表或子公司列表中获取指定实体的持股比例"""
            # 先从顶级实体列表中查找
            for entity in st.session_state.equity_data["top_level_entities"]:
                if entity["name"] == entity_name and "percentage" in entity and entity["percentage"] > 0:
                    return entity["percentage"]
            # 再从子公司列表中查找（针对公司之间的持股关系）
            for subsidiary in st.session_state.equity_data["subsidiaries"]:
                if subsidiary["name"] == entity_name and "percentage" in subsidiary and subsidiary["percentage"] > 0:
                    return subsidiary["percentage"]
            # 从所有实体中查找
            for entity in st.session_state.equity_data.get("all_entities", []):
                if entity["name"] == entity_name and "percentage" in entity and entity["percentage"] > 0:
                    return entity["percentage"]
            return None
            
        for i, rel in enumerate(st.session_state.equity_data["entity_relationships"]):
            # 兼容from/to和parent/child两种格式
            from_entity = rel.get('from', rel.get('parent', '未知'))
            to_entity = rel.get('to', rel.get('child', '未知'))
            
            # 获取百分比值，优先级：1.关系中的percentage字段 2.从实体信息中获取 3.默认N/A
            percentage = rel.get('percentage', None)
            if percentage is None or percentage == 0 or percentage == 'N/A':
                percentage = get_entity_percentage_for_display(from_entity)
            
            percentage_display = f"{percentage:.1f}" if isinstance(percentage, (int, float)) and percentage > 0 else 'N/A'
            
            with st.expander(f"{from_entity} → {to_entity} ({percentage_display}%)"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("编辑", key=f"edit_rel_{i}"):
                        st.session_state.editing_relationship = ("entity", i)
                        st.rerun()
                with col2:
                    if st.button("删除", key=f"delete_rel_{i}", type="secondary"):
                        # 兼容from/to和parent/child两种格式
                        from_entity = rel.get('from', rel.get('parent', '未知'))
                        to_entity = rel.get('to', rel.get('child', '未知'))
                        st.session_state.equity_data["entity_relationships"].pop(i)
                        st.success(f"已删除关系: {from_entity} → {to_entity}")
                        st.rerun()
    else:
        st.info("尚未添加股权关系")
    
    # 显示控制关系
    st.markdown("### 控制关系（虚线表示）")
    if st.session_state.equity_data.get("control_relationships", []):
        for i, rel in enumerate(st.session_state.equity_data["control_relationships"]):
            # 兼容from/to和parent/child两种格式
            from_entity = rel.get('from', rel.get('parent', '未知'))
            to_entity = rel.get('to', rel.get('child', '未知'))
            with st.expander(f"{from_entity} ⤳ {to_entity} ({rel.get('description', '控制关系')})"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("编辑", key=f"edit_control_rel_{i}"):
                        st.session_state.editing_relationship = ("control", i)
                        st.rerun()
                with col2:
                    if st.button("删除", key=f"delete_control_rel_{i}", type="secondary"):
                        # 兼容from/to和parent/child两种格式
                        from_entity = rel.get('from', rel.get('parent', '未知'))
                        to_entity = rel.get('to', rel.get('child', '未知'))
                        st.session_state.equity_data["control_relationships"].pop(i)
                        st.success(f"已删除控制关系: {from_entity} ⤳ {to_entity}")
                        st.rerun()
    else:
        st.info("尚未添加控制关系")
    
    # 编辑现有关系
    editing_relationship_displayed = False
    if st.session_state.editing_relationship:
        rel_type, index = st.session_state.editing_relationship
        
        if rel_type == "entity" and index < len(st.session_state.equity_data["entity_relationships"]):
            editing_relationship_displayed = True
            rel = st.session_state.equity_data["entity_relationships"][index]
            
            with st.form("edit_entity_relationship_form"):
                st.subheader("编辑股权关系")
                
                # 添加一个函数来获取实体的持股比例
                def get_entity_percentage(entity_name):
                    """从顶级实体列表中获取指定实体的持股比例"""
                    for entity in st.session_state.equity_data["top_level_entities"]:
                        if entity["name"] == entity_name and "percentage" in entity:
                            return entity["percentage"]
                    return 51.0  # 默认值
                
                # 保存上一次选择的parent，用于判断是否需要重置手动修改标志
                prev_parent_edit = st.session_state.get('prev_parent_edit', None)
                
                # 兼容from/to和parent/child两种格式
                rel_parent = rel.get('parent', rel.get('from', ''))
                rel_child = rel.get('child', rel.get('to', ''))
                
                parent_options = [name for name in all_entity_names if name != rel_child]
                parent = st.selectbox("母公司/股东", parent_options, index=parent_options.index(rel_parent) if rel_parent in parent_options else 0)
                
                # 如果parent改变了，重置手动修改标志
                if parent != prev_parent_edit:
                    st.session_state.manual_percentage_changed_edit = False
                st.session_state.prev_parent_edit = parent
                
                child_options = [name for name in all_entity_names if name != parent]
                child = st.selectbox("子公司/被投资方", child_options, index=child_options.index(rel_child) if rel_child in child_options else 0)
                
                # 初始化手动修改标志
                if 'manual_percentage_changed_edit' not in st.session_state:
                    st.session_state.manual_percentage_changed_edit = False
                
                # 当选择了母公司/股东后，自动填充其持股比例，但尊重用户手动修改
                if st.session_state.manual_percentage_changed_edit:
                    # 如果用户已经手动修改，保持当前值
                    default_percentage_edit = st.session_state.current_percentage_edit
                else:
                    # 否则，从实体中获取默认比例或使用现有关系的比例
                    entity_percentage = get_entity_percentage(parent) if parent else rel.get('percentage', 51.0)
                    default_percentage_edit = entity_percentage
                
                # 百分比输入框
                percentage_value_edit = st.number_input("修改持股比例 (%)", min_value=0.01, max_value=100.0, value=default_percentage_edit, step=0.01, help="默认为实体的持股比例，可手动修改")
                # 更新当前百分比值
                st.session_state.current_percentage_edit = percentage_value_edit
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("保存修改", type="primary"):
                        # 更新关系，使用from/to格式以保持与AI分析一致
                        st.session_state.equity_data["entity_relationships"][index] = {
                            "from": parent,
                            "to": child,
                            "percentage": percentage_value_edit
                        }
                        # 重置状态
                        st.session_state.manual_percentage_changed_edit = False
                        st.session_state.editing_relationship = None
                        st.success("关系已更新！")
                        st.rerun()
                with col2:
                    if st.form_submit_button("取消", type="secondary"):
                        st.session_state.editing_relationship = None
                        st.rerun()
        
        elif rel_type == "control" and index < len(st.session_state.equity_data["control_relationships"]):
            editing_relationship_displayed = True
            rel = st.session_state.equity_data["control_relationships"][index]
            
            with st.form("edit_control_relationship_form"):
                st.subheader("编辑控制关系")
                
                parent_options = [name for name in all_entity_names if name != rel['child']]
                parent = st.selectbox("控制方", parent_options, index=parent_options.index(rel['parent']) if rel['parent'] in parent_options else 0)
                
                child_options = [name for name in all_entity_names if name != parent]
                child = st.selectbox("被控制方", child_options, index=child_options.index(rel['child']) if rel['child'] in child_options else 0)
                
                description = st.text_input("关系描述", value=rel.get('description', ''), placeholder="如：Collective control, Ultimate control 等")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.form_submit_button("保存修改", type="primary"):
                        # 更新关系
                        st.session_state.equity_data["control_relationships"][index] = {
                            "parent": parent,
                            "child": child,
                            "description": description
                        }
                        st.session_state.editing_relationship = None
                        st.success("关系已更新！")
                        st.rerun()
                with col2:
                    if st.form_submit_button("取消", type="secondary"):
                        st.session_state.editing_relationship = None
                        st.rerun()
    
    # AI分析报告显示区域
    if st.session_state.current_step == "relationships":
        st.subheader("📊 AI股权结构分析报告")
        
        # 分析功能区域
        with st.expander("🔍 股权结构分析设置", expanded=True):
            # 分析深度选择
            analysis_depth = st.selectbox(
                "选择分析深度",
                options=["基础分析", "详细分析", "完整分析"],
                index=1,
                help="基础分析：仅包含基本信息和总结\n详细分析：包含主要股东和控制关系\n完整分析：包含所有可用信息"
            )
            
            # API密钥输入
            dashscope_api_key = st.text_input(
                "🔐 DashScope API密钥（可选）",
                value=st.session_state.get("dashscope_api_key", ""),
                type="password",
                placeholder="请输入您的DashScope API密钥，用于调用AI分析模型"
            )
            # 保存API密钥到会话状态
            if dashscope_api_key:
                st.session_state.dashscope_api_key = dashscope_api_key
                st.success("API密钥已保存到当前会话")
            
            # 帮助信息
            st.info("""💡 提示：
            - 没有API密钥也可以使用，系统将提供模拟分析结果
            - 密钥仅保存在当前会话中，不会被持久化存储
            - 分析基于当前已定义的股权关系数据
            - 如有未显示的子公司关系，可能需要在股权关系设置中添加更多关系""")
            
            # 分析按钮
            if st.button("📈 执行股权结构分析"):
                # 检查多种可能的数据存储位置
                has_entity_relationships = (st.session_state.get("entity_relationships") or 
                                          st.session_state.get("equity_data", {}).get("entity_relationships", []))
                has_control_relationships = (st.session_state.get("control_relationships") or 
                                           st.session_state.get("equity_data", {}).get("control_relationships", []))
                
                if not has_entity_relationships and not has_control_relationships:
                    st.warning("请先添加股权关系或控制关系数据，再进行分析")
                else:
                    try:
                        # 导入必要的模块
                        import re
                        # 导入新的LLM分析模块和原有分析函数
                        from src.utils.ai_equity_analyzer import generate_analysis_report, identify_actual_controller, generate_summary
                        from src.utils.equity_llm_analyzer import analyze_equity_with_llm
                        
                        # 获取equity_data（优先从session_state中获取）
                        equity_data = st.session_state.get("equity_data", {})
                        
                        # 准备分析数据，优先从equity_data获取，然后是session_state
                        analysis_data = {
                            "core_company": equity_data.get("core_company", st.session_state.get("core_company", "未命名公司")),
                            "actual_controller": equity_data.get("actual_controller", st.session_state.get("actual_controller", "")),
                            "top_level_entities": equity_data.get("top_level_entities", []),
                            "subsidiaries": equity_data.get("subsidiaries", []),
                            "control_relationships": equity_data.get("control_relationships", st.session_state.get("control_relationships", [])),
                            "entity_relationships": equity_data.get("entity_relationships", st.session_state.get("entity_relationships", []))
                        }
                        
                        # 从实体关系中提取股东信息（使用正确的entity_relationships来源）
                        shareholders_set = set()
                        entity_relationships = analysis_data["entity_relationships"]
                        core_company = analysis_data["core_company"]
                        
                        for rel in entity_relationships:
                            if rel.get("relationship_type") == "持股" and rel.get("to") == core_company:
                                percentage_match = re.search(r'\d+(?:\.\d+)?', rel["description"])
                                percentage = float(percentage_match.group()) if percentage_match else 0
                                shareholders_set.add((rel["from"], percentage))
                        
                        # 转换为所需格式
                        for name, percentage in shareholders_set:
                            analysis_data["top_level_entities"].append({
                                "name": name,
                                "percentage": percentage,
                                "entity_type": "自然人"  # 默认类型，可根据需要调整
                            })
                        
                        # 从实体关系中提取子公司信息（使用正确的entity_relationships来源）
                        subsidiary_set = set()
                        for rel in entity_relationships:
                            if rel.get("relationship_type") == "持股" and rel.get("from") == core_company:
                                percentage_match = re.search(r'\d+(?:\.\d+)?', rel.get("description", ""))
                                percentage = float(percentage_match.group()) if percentage_match else 0
                                subsidiary_set.add((rel.get("to", "未知"), percentage))
                        
                        # 转换为所需格式
                        for name, percentage in subsidiary_set:
                            analysis_data["subsidiaries"].append({
                                "name": name,
                                "parent_entity": core_company,
                                "percentage": percentage
                            })
                        
                        # 调用分析函数
                        st.session_state.analysis_data = analysis_data
                        
                        # 获取API密钥（如果在会话状态中存在）
                        api_key = st.session_state.get("dashscope_api_key", "")
                        
                        # 根据分析深度显示不同内容
                        if analysis_depth == "基础分析":
                            # 显示基本信息和总结
                            st.subheader("📋 基础分析结果")
                            controller_info = identify_actual_controller(analysis_data)
                            st.markdown(f"**核心公司：** {analysis_data['core_company']}")
                            st.markdown(f"**实际控制人：** {controller_info['name']}")
                            st.markdown(f"**确认依据：** {controller_info['reason']}")
                            st.markdown("\n**股权结构总结：**")
                            summary = generate_summary(analysis_data)
                            st.info(summary)
                        elif analysis_depth == "详细分析":
                            # 使用LLM生成详细报告
                            st.subheader("📊 LLM详细分析报告")
                            with st.spinner("正在使用AI分析股权结构..."):
                                llm_report, errors = analyze_equity_with_llm(analysis_data, api_key)
                                st.session_state.llm_report = llm_report
                                
                                # 显示报告
                                st.markdown(llm_report)
                                
                                # 如果有错误，显示错误信息
                                if errors:
                                    with st.expander("显示分析过程中的问题"):
                                        for error in errors:
                                            st.warning(error)
                        else:  # 完整分析
                            # 使用LLM生成完整报告
                            st.subheader("📑 LLM完整分析报告")
                            with st.spinner("正在使用AI分析股权结构..."):
                                llm_report, errors = analyze_equity_with_llm(analysis_data, api_key)
                                st.session_state.llm_report = llm_report
                                
                                # 显示完整报告
                                st.text_area("分析报告", llm_report, height=500)
                                
                                # 添加下载按钮
                                st.download_button(
                                    label="💾 下载分析报告",
                                    data=llm_report,
                                    file_name=f"{analysis_data['core_company']}_股权分析报告_AI.txt",
                                    mime="text/plain"
                                )
                                
                                # 如果有错误，显示错误信息
                                if errors:
                                    with st.expander("显示分析过程中的问题"):
                                        for error in errors:
                                            st.warning(error)
                            
                    except Exception as e:
                        st.error(f"分析过程中发生错误：{str(e)}")
            
            # 显示当前数据统计
            # 从equity_data中获取数据，如果不存在则从session_state根级别获取
            equity_data = st.session_state.get("equity_data", {})
            entity_relationships = equity_data.get("entity_relationships", st.session_state.get("entity_relationships", []))
            control_relationships = equity_data.get("control_relationships", st.session_state.get("control_relationships", []))
            
            # 计算实体数量（从股权关系中提取所有唯一实体）
            total_entities = len(set(rel["from"] for rel in entity_relationships).union(
                               set(rel["to"] for rel in entity_relationships)))
            total_relationships = len(entity_relationships)
            total_control_relationships = len(control_relationships)
            
            st.info(f"当前数据统计：实体数量 {total_entities} 个，股权关系 {total_relationships} 条，控制关系 {total_control_relationships} 条")
        
        # 显示分析报告
        if "analysis_data" in st.session_state and st.session_state.analysis_data:
            st.markdown("### 🔍 分析结果已生成")
            st.info("请使用上方的分析功能区域查看和管理分析结果")
        else:
            # 没有分析结果时的提示
            st.info("💡 提示：点击上方的'生成股权结构分析报告'按钮，对当前股权结构进行AI分析。")
            
            st.markdown("---")

# 实时预览功能 - 移动到添加股权关系标题的正上方
        st.markdown("---")

        st.subheader("🔍 实时预览")
        
        # 添加一个开关控制预览显示
        show_preview = st.checkbox("显示股权结构预览", value=False)
        
        if show_preview and st.session_state.equity_data["core_company"]:
            try:
                # 转换数据格式以匹配mermaid_function所需格式
                data_for_mermaid = {
                    "main_company": st.session_state.equity_data.get("core_company", ""),
                    "core_company": st.session_state.equity_data.get("core_company", ""),
                    "shareholders": st.session_state.equity_data.get("shareholders", []),
                    "subsidiaries": st.session_state.equity_data.get("subsidiaries", []),
                    "controller": st.session_state.equity_data.get("actual_controller", ""),
                    "top_entities": st.session_state.equity_data.get("top_level_entities", []),
                    "entity_relationships": st.session_state.equity_data.get("entity_relationships", []),
                    "control_relationships": st.session_state.equity_data.get("control_relationships", []),
                    "all_entities": st.session_state.equity_data.get("all_entities", [])
                }
                
                # 生成Mermaid代码
                with st.spinner("正在生成预览图表..."):
                    preview_mermaid_code = generate_mermaid_diagram(data_for_mermaid)
                
                # 显示预览图表
                st.markdown("### 📊 关系预览")
                st_mermaid(preview_mermaid_code, key="preview_mermaid_chart")
                st.caption("注意：此预览将随您的关系设置实时更新")
                
            except Exception as e:
                st.error(f"生成预览时出错: {str(e)}")
        elif show_preview:
            st.info("请先设置核心公司以查看预览")
        else:
            st.caption("勾选上方复选框以查看关系设置的实时预览")
            
        tab1, tab2 = st.tabs(["添加股权关系", "添加控制关系"])
        
        with tab1:
            # 初始化会话状态
            if 'edit_percentage_mode' not in st.session_state:
                st.session_state.edit_percentage_mode = False
            if 'modified_percentage' not in st.session_state:
                st.session_state.modified_percentage = 51.0
            if 'last_selected_parent' not in st.session_state:
                st.session_state.last_selected_parent = None
            if 'last_selected_child' not in st.session_state:
                st.session_state.last_selected_child = None
            
            st.subheader("添加股权关系")
            
            if not all_entity_names:
                st.error("请先添加实体后再定义关系")
            else:
                # 外部区域：选择器和编辑按钮
                col1, col2 = st.columns([1, 1])
                
                # 添加一个函数来获取实体的持股比例
                def get_entity_percentage(entity_name):
                        """从顶级实体列表中获取指定实体的持股比例"""
                        for entity in st.session_state.equity_data["top_level_entities"]:
                            if entity["name"] == entity_name and "percentage" in entity:
                                return entity["percentage"]
                        return 51.0  # 默认值
                    
                # 在第一个列中显示母公司/股东选择
                with col1:
                    core_company = st.session_state.equity_data["core_company"]
                    subsidiary_names = get_subsidiary_names()
                    
                    # 母公司/股东选项 - 只包含顶级实体（个人和公司）
                    parent_options = []
                    for entity_name in get_top_level_entity_names():
                        if entity_name not in subsidiary_names:
                            parent_options.append(entity_name)
                    
                    if not parent_options:
                        st.error("没有可用的母公司/股东选项。请添加顶级实体。")
                        parent = None
                    else:
                        # 直接使用selectbox选择母公司/股东
                        parent = st.selectbox(
                            "母公司/股东", 
                            parent_options, 
                            help="选择关系中的上级实体",
                            key="parent_selector"
                        )
                
                # 在第二个列中显示被投资方选择
                with col2:
                    core_company = st.session_state.equity_data["core_company"]
                    subsidiary_names = get_subsidiary_names()
                    
                    # 被投资方选项 - 包含核心公司和所有顶级实体，不包含子公司
                    valid_investee_options = []
                    
                    # 首先添加核心公司（如果存在）
                    if core_company:
                        valid_investee_options.append(core_company)
                    
                    # 添加所有顶级实体，排除子公司和核心公司（避免重复）
                    for entity_name in get_top_level_entity_names():
                        if entity_name not in subsidiary_names and entity_name != core_company:
                            valid_investee_options.append(entity_name)
                    
                    if not valid_investee_options:
                        st.error("没有可用的被投资方选项。")
                        child = None
                    else:
                        # 默认选择第一个选项
                        child = st.selectbox(
                            "被投资方", 
                            valid_investee_options, 
                            index=0,
                            help="选择关系中的下级实体",
                            key="child_selector"
                        )
                
                # 初始化编辑模式状态
                if 'edit_percentage_mode' not in st.session_state:
                    st.session_state.edit_percentage_mode = False
                
                # 当选择新的parent时，重置编辑模式和百分比值
                if parent and ('last_selected_parent' not in st.session_state or 
                              st.session_state.last_selected_parent != parent):
                    st.session_state.edit_percentage_mode = False
                    st.session_state.last_selected_parent = parent
                    # 选择新parent时，更新modified_percentage为新parent的默认值
                    st.session_state.modified_percentage = get_entity_percentage(parent) if parent else 51.0
                
                # 获取默认百分比值
                default_percentage = get_entity_percentage(parent) if parent else 51.0
                
                # 初始化修改后的百分比值为默认值
                if 'modified_percentage' not in st.session_state:
                    st.session_state.modified_percentage = default_percentage
                
                # 显示当前百分比和修改按钮
                col_percentage, col_button = st.columns([3, 1])
                
                with col_percentage:
                    # 显示当前百分比值（默认值或修改后的值）
                    if st.session_state.edit_percentage_mode:
                        # 编辑模式：显示输入框
                        st.session_state.modified_percentage = st.number_input(
                            "修改持股比例 (%)", 
                            min_value=0.01, 
                            max_value=100.0, 
                            value=st.session_state.modified_percentage,
                            step=0.01, 
                            help=f"原值: {default_percentage}%，输入新的百分比值",
                            key="percentage_input"
                        )
                    else:
                        # 正常模式：显示只读信息
                        display_percentage = st.session_state.modified_percentage
                        st.info(f"当前持股比例: {display_percentage}%")
                        
                        # 显示来源信息
                        if display_percentage == default_percentage:
                            st.caption(f"继承自 {parent} 的默认比例")
                        else:
                            st.caption(f"已修改（原值: {default_percentage}%）")
                
                with col_button:
                    # 修改按钮（在表单外部）
                    if not st.session_state.edit_percentage_mode:
                        # 开始修改按钮
                        if st.button("修改比例", key="edit_button"):
                            st.session_state.edit_percentage_mode = True
                            # 进入编辑模式时，默认显示原值
                            st.session_state.modified_percentage = default_percentage
                
                # 提交表单（只包含提交按钮）
                with st.form("submit_equity_form"):
                    # 显示信息摘要
                    if parent and child:
                        st.info(f"将添加股权关系: {parent} → {child} ({st.session_state.modified_percentage}%)")
                    
                    # 提交按钮 - 在主表单中
                    if st.form_submit_button("添加股权关系", type="primary"):
                            # 检查关系是否有效
                            if parent and child and parent != child:
                                # 检查关系是否已存在
                                exists = any(
                                    (r.get("parent", r.get("from")) == parent and r.get("child", r.get("to")) == child)
                                    for r in st.session_state.equity_data["entity_relationships"]
                                )
                                if not exists:
                                    # 添加关系，使用修改后的比例
                                    percentage_to_use = st.session_state.modified_percentage
                                    st.session_state.equity_data["entity_relationships"].append({
                                        "parent": parent,
                                        "child": child,
                                        "percentage": percentage_to_use
                                    })
                                    st.success(f"已添加股权关系: {parent} → {child} ({percentage_to_use}%)")
                                    # 清除相关状态以重置
                                    if 'edit_percentage_mode' in st.session_state:
                                        del st.session_state['edit_percentage_mode']
                                    if 'modified_percentage' in st.session_state:
                                        del st.session_state['modified_percentage']
                                    if 'last_selected_parent' in st.session_state:
                                        del st.session_state['last_selected_parent']
                                    if 'last_selected_child' in st.session_state:
                                        del st.session_state['last_selected_child']
                                    st.rerun()
                                else:
                                    st.error("该关系已存在")
                            else:
                                st.error("请确保选择了不同的母公司/股东和被投资方")
                
        with tab2:
            st.subheader("添加控制关系")
            
            if not all_entity_names:
                st.error("请先添加实体后再定义关系")
            else:
                # 控制关系定义部分，完全按照股权关系的模式实现
                col1, col2 = st.columns([1, 1])
                
                # 在第一个列中显示控制方选择
                with col1:
                    # 控制方选项 - 只包含顶级实体（个人和公司）
                    controller_options = []
                    for entity_name in get_top_level_entity_names():
                        controller_options.append(entity_name)
                    
                    if not controller_options:
                        st.error("没有可用的控制方选项。请添加顶级实体。")
                        controller = None
                    else:
                        controller = st.selectbox("控制方", controller_options, help="选择控制方，仅显示顶级实体")
                
                # 在第二个列中显示被控制方选择
                with col2:
                    # 被控制方可以是任何实体，除了控制方本身
                    controlled_options = []
                    for entity_name in all_entity_names:
                        if controller and entity_name == controller:
                            continue
                        controlled_options.append(entity_name)
                    
                    if not controlled_options:
                        st.error("没有可用的被控制方选项。")
                        controlled = None
                    else:
                        # 默认选择第一个选项
                        default_index = 0
                        controlled = st.selectbox("被控制方", controlled_options, index=default_index, help="选择被控制方")
                
                description = st.text_input("关系描述", placeholder="如：Collective control, Ultimate control 等")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("添加控制关系", type="primary"):
                        # 检查关系是否有效
                        if controller and controlled and controller != controlled:
                            # 检查关系是否已存在
                            exists = any(
                                (r.get("parent", r.get("from")) == controller and r.get("child", r.get("to")) == controlled)
                                for r in st.session_state.equity_data["control_relationships"]
                            )
                            if not exists:
                                # 添加关系
                                st.session_state.equity_data["control_relationships"].append({
                                    "parent": controller,
                                    "child": controlled,
                                    "description": description
                                })
                                st.success(f"已添加控制关系: {controller} → {controlled}")
                                st.rerun()
                            else:
                                st.error("该关系已存在")
                        
                        # 分析按钮
                        if st.button("开始AI分析", type="primary", key="ai_analysis_button"):
                            if (analysis_mode == "输入文本" and not input_text.strip()) or \
                               (analysis_mode == "上传文档" and not uploaded_file):
                                st.error("请提供分析内容：输入文本或上传文档")
                            else:
                                try:
                                    with st.spinner("正在进行AI分析，请稍候..."):
                                        # 准备分析参数
                                        analysis_params = {
                                            "analysis_scope": analysis_scope,
                                            "clear_existing": clear_existing
                                        }
                                         
                                        # 调用AI分析函数
                                        if analysis_mode == "输入文本":
                                            result = analyze_equity_with_ai(
                                                text_content=input_text,
                                                params=analysis_params
                                            )
                                        else:
                                            # 对于文件上传，我们需要处理文件内容
                                            file_content = uploaded_file.getvalue()
                                            result = analyze_equity_with_ai(
                                                file_content=file_content,
                                                file_type=uploaded_file.type,
                                                params=analysis_params
                                            )
                                        
                                        # 处理分析结果
                                        if result and "status" in result:
                                            if result["status"] == "success":
                                                # 保存分析结果到session_state
                                                st.session_state.ai_analysis_result = result
                                                
                                                # 显示分析成功信息
                                                st.success("AI分析完成！")
                                                
                                                # 显示分析结果摘要
                                                st.markdown("### 分析结果摘要")
                                                
                                                # 显示提取到的实体和关系数量
                                                if "entities" in result and isinstance(result["entities"], dict):
                                                    entities = result["entities"]
                                                    col1, col2, col3 = st.columns(3)
                                                    if "core_company" in entities:
                                                        with col1:
                                                            st.metric("核心公司", 1 if entities["core_company"] else 0)
                                                    if "shareholders" in entities:
                                                        with col2:
                                                            st.metric("股东数量", len(entities["shareholders"]))
                                                    if "subsidiaries" in entities:
                                                        with col3:
                                                            st.metric("子公司数量", len(entities["subsidiaries"]))
                                                
                                                # 显示提取的核心公司
                                                if "core_company" in result:
                                                    st.info(f"**核心公司**: {result['core_company']}")
                                                
                                                # 显示提取的股权关系数量
                                                if "relationships" in result:
                                                    st.info(f"提取到 {len(result['relationships'])} 条股权关系")
                                                
                                                # 询问用户是否应用分析结果
                                                st.markdown("---")
                                                if st.button("应用分析结果到当前项目", type="primary"):
                                                    try:
                                                        # 应用分析结果到会话状态
                                                        if clear_existing:
                                                            # 清空现有数据
                                                            st.session_state.equity_data = {
                                                                "core_company": "",
                                                                "shareholders": [],
                                                                "subsidiaries": [],
                                                                "controller": "",
                                                                "top_level_entities": [],
                                                                "entity_relationships": [],
                                                                "control_relationships": [],
                                                                "all_entities": []
                                                            }
                                                        
                                                        # 应用核心公司
                                                        if "core_company" in result and result["core_company"]:
                                                            st.session_state.equity_data["core_company"] = result["core_company"]
                                                            # 添加到all_entities
                                                            if not any(e["name"] == result["core_company"] for e in st.session_state.equity_data["all_entities"]):
                                                                st.session_state.equity_data["all_entities"].append({
                                                                    "name": result["core_company"],
                                                                    "type": "company"
                                                                })
                                                        
                                                        # 应用股东信息
                                                        if "shareholders" in result:
                                                            for shareholder in result["shareholders"]:
                                                                # 检查是否已存在
                                                                if not any(e["name"] == shareholder["name"] for e in st.session_state.equity_data["top_level_entities"]):
                                                                    st.session_state.equity_data["top_level_entities"].append({
                                                                        "name": shareholder["name"],
                                                                        "type": shareholder.get("type", "company"),
                                                                        "percentage": shareholder.get("percentage", 0)
                                                                    })
                                                                    # 添加到all_entities
                                                                    if not any(e["name"] == shareholder["name"] for e in st.session_state.equity_data["all_entities"]):
                                                                        st.session_state.equity_data["all_entities"].append({
                                                                            "name": shareholder["name"],
                                                                            "type": shareholder.get("type", "company")
                                                                        })
                                                        
                                                        # 应用子公司信息
                                                        if "subsidiaries" in result:
                                                            for subsidiary in result["subsidiaries"]:
                                                                # 检查是否已存在
                                                                if not any(e["name"] == subsidiary["name"] for e in st.session_state.equity_data["subsidiaries"]):
                                                                    st.session_state.equity_data["subsidiaries"].append({
                                                                        "name": subsidiary["name"],
                                                                        "percentage": subsidiary.get("percentage", 0)
                                                                    })
                                                                    # 添加到all_entities
                                                                    if not any(e["name"] == subsidiary["name"] for e in st.session_state.equity_data["all_entities"]):
                                                                        st.session_state.equity_data["all_entities"].append({
                                                                            "name": subsidiary["name"],
                                                                            "type": "company"
                                                                        })
                                                        
                                                        # 应用股权关系
                                                        if "relationships" in result:
                                                            for rel in result["relationships"]:
                                                                # 检查关系是否已存在
                                                                exists = any(
                                                                    r["parent"] == rel["parent"] and r["child"] == rel["child"]
                                                                    for r in st.session_state.equity_data["entity_relationships"]
                                                                )
                                                                if not exists:
                                                                    st.session_state.equity_data["entity_relationships"].append(rel)
                                                        
                                                        # 应用控制关系
                                                        if "control_relationships" in result:
                                                            for rel in result["control_relationships"]:
                                                                # 检查关系是否已存在
                                                                exists = any(
                                                                    r["parent"] == rel["parent"] and r["child"] == rel["child"]
                                                                    for r in st.session_state.equity_data["control_relationships"]
                                                                )
                                                                if not exists:
                                                                    st.session_state.equity_data["control_relationships"].append(rel)
                                                        
                                                        st.success("分析结果已成功应用！")
                                                        st.rerun()
                                                    except Exception as e:
                                                        st.error(f"应用分析结果时出错: {str(e)}")
                                                        import traceback
                                                        st.exception(traceback.format_exc())
                                except Exception as e:
                                    st.error(f"AI分析过程中出错: {str(e)}")
                                    import traceback
                                    st.exception(traceback.format_exc())

# 步骤5: 生成图表
elif st.session_state.current_step == "generate":
    st.subheader("📊 生成股权结构图")
    
    # 显示数据预览
    with st.expander("查看生成的数据结构"):
        st.json(st.session_state.equity_data)
    
    # 添加返回编辑按钮
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("返回编辑", type="secondary", key="back_to_edit"):
            # 验证数据后再跳转
            data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
            if data_valid:
                st.session_state.current_step = "relationships"
                st.rerun()
            else:
                st.error("数据验证失败，无法返回编辑。请检查数据后重试。")
    
    # 生成Mermaid图表
    if st.button("生成图表", type="primary"):
        try:
            # 确保核心公司已设置
            if not st.session_state.equity_data["core_company"]:
                st.error("请先设置核心公司")
            else:
                # 转换数据格式以匹配mermaid_function所需格式
                # 注意：我们需要同时设置main_company和core_company以确保兼容性
                data_for_mermaid = {
                    "main_company": st.session_state.equity_data["core_company"],
                    "core_company": st.session_state.equity_data["core_company"],
                    "shareholders": st.session_state.equity_data["shareholders"],
                    "subsidiaries": st.session_state.equity_data["subsidiaries"],
                    "controller": st.session_state.equity_data.get("actual_controller", ""),
                    "top_entities": st.session_state.equity_data["top_level_entities"],
                    "entity_relationships": st.session_state.equity_data["entity_relationships"],
                    "control_relationships": st.session_state.equity_data["control_relationships"],
                    "all_entities": st.session_state.equity_data["all_entities"]
                }
                
                # 生成Mermaid代码
                with st.spinner("正在生成图表..."):
                    st.session_state.mermaid_code = generate_mermaid_diagram(data_for_mermaid)
                    
                st.success("图表生成成功！")
        except Exception as e:
            st.error(f"生成图表时出错: {str(e)}")
    
    # 显示图表（如果已生成）
    if st.session_state.mermaid_code:
        st.markdown("### 📊 股权结构图表")
        # 修改5：添加全屏编辑按钮
        if st.button("全屏编辑图表", key="fullscreen_edit_button"):
            st.session_state.fullscreen_mode = not st.session_state.get("fullscreen_mode", False)
            st.rerun()
        
        # 检查是否处于全屏模式
        if st.session_state.get("fullscreen_mode", False):
            # 全屏模式：隐藏其他内容，只显示图表和退出按钮
            st.markdown("<style>.reportview-container .main .block-container { max-width: none; }</style>", unsafe_allow_html=True)
            st.markdown("<style>.sidebar {display: none;}</style>", unsafe_allow_html=True)
            st.markdown("### 📊 全屏编辑模式")
            st_mermaid(st.session_state.mermaid_code, key="unique_mermaid_chart_fullscreen")
            if st.button("退出全屏模式", key="exit_fullscreen_button"):
                st.session_state.fullscreen_mode = False
                st.rerun()
        else:
            # 普通模式
            st_mermaid(st.session_state.mermaid_code, key="unique_mermaid_chart")
    
    # 提供下载选项
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.download_button(
            label="下载 JSON 数据",
            data=json.dumps(st.session_state.equity_data, ensure_ascii=False, indent=2),
            file_name="equity_structure.json",
            mime="application/json"
        ):
            st.success("JSON文件已下载")
    
    with col2:
        if st.session_state.mermaid_code and st.download_button(
            label="下载 Mermaid 代码",
            data=st.session_state.mermaid_code,
            file_name="equity_structure.mmd",
            mime="text/plain"
        ):
            st.success("Mermaid文件已下载")
    
    # 返回编辑按钮
    if st.button("返回编辑", type="secondary"):
        # 验证数据后再跳转
        data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
        if data_valid:
            st.session_state.current_step = "relationships"
            st.rerun()
        else:
            st.error("数据验证失败，无法返回编辑。请检查数据后重试。")

# 底部导航按钮已移至顶部全局导航栏