#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股权结构手动编辑工具

本模块提供手动添加公司、股东、子公司及关系的界面，生成与图片识别相同格式的JSON数据，
并使用相同的mermaid_function来生成图表。
"""

import os
import sys
import json
import streamlit as st
from datetime import datetime
from streamlit_mermaid import st_mermaid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 设置页面配置
st.set_page_config(
    page_title="股权结构图生成工具 - 手动编辑模式",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # 默认折叠侧边栏
)

# 添加CSS样式来隐藏默认的导航内容，但保留自定义侧边栏
st.markdown("""
<style>
    /* 设置主题变量 */
    :root {
        --primary-color: #0f4c81;
    }
    
    /* 隐藏默认的导航内容 */
    [data-testid="stSidebarNav"],[data-testid="stSidebar"] [href*="main_page"],[data-testid="stSidebar"] [href*="1_图像识别模式"],[data-testid="stSidebar"] [href*="2_手动编辑模式"] {display:none !important;visibility:hidden !important;height:0 !important;width:0 !important;opacity:0 !important;}
    
    /* 隐藏 sidebar header 上的 keyboard 提示 */ 
    [data-testid="stSidebar"] .streamlit-expanderHeader button div {display:none !important;}
    
    /* 侧边栏整体背景色与宽度 */ 
    [data-testid="stSidebar"] {
        background-color: var(--primary-color) !important; /* 使用主色调 */ 
        color: #ffffff !important;            /* 白色字体 */ 
        padding: 1rem 0.5rem;
        min-width: 250px !important;          /* 最小宽度 */ 
        max-width: 280px !important;          /* 最大宽度 */ 
    }
    
    /* 确保侧边栏内容区域也使用主色调背景 */
    [data-testid="stSidebar"] section,[data-testid="stSidebar"] .sidebar-content {
        background-color: var(--primary-color) !important;
        background: var(--primary-color) !important;
    }
    
    /* Sidebar 标题美化 */ 
    [data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 {color:#4fc3f7 !important;font-weight:700 !important;}
    
    /* 设置侧边栏按钮背景为透明 */
    [data-testid="stSidebar"] button,[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],[data-testid="stSidebar"] [data-testid="stButton"] > button {
        background: transparent !important;
        background-color: transparent !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
        opacity: 1 !important;
        background-image: none !important;
        border-radius: 0 !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* 确保按钮内的所有内容都透明 */
    [data-testid="stSidebar"] button *,[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] * {
        background-color: transparent !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    
    /* Sidebar 内文字统一 - 高优先级 */ 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #e0e0e0 !important;
        font-size: 14px !important;  /* 添加!important确保优先级 */
    }
    
    /* 侧边栏展开面板内容的更具体样式控制 - 最高优先级 */
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent {
        font-size: 14px !important !important;
        color: #e0e0e0 !important !important;
        text-align: left !important !important;
    }
    
    /* 确保展开面板内的所有文本元素都使用相同的字体大小 - 最高优先级 */
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent * {
        font-size: 14px !important !important;
        color: #e0e0e0 !important !important;
        text-align: left !important !important;
        line-height: 1.4 !important !important;
        font-weight: normal !important !important;
    }
    
    /* 针对展开面板内使用st.write()生成的内容的特定样式 */
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent p,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent h1,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent h2,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent h3,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent h4,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent h5,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent h6,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent li,
    [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent span {
        font-size: 14px !important !important;
        color: #e0e0e0 !important !important;
        text-align: left !important !important;
        line-height: 1.4 !important !important;
        font-weight: normal !important !important;
    }
    
    /* 确保按钮内文本大小一致 */
    [data-testid="stSidebar"] .stButton button,
    [data-testid="stSidebar"] .stButton button p {
        font-size: 14px !important !important;
    }
    
    /* 确保展开面板标题也使用相同的字体大小 */
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderToggleIcon"] + div {
        font-size: 14px !important;
        color: #e0e0e0 !important;
    }
    
    /* 添加悬停效果 */
    [data-testid="stSidebar"] button:hover,[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover,[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        box-shadow: none !important;
        transform: translateX(4px);
    }
</style>
""", unsafe_allow_html=True)

# 自定义侧边栏 - 复制main_page.py的样式，确保导航一致性
with st.sidebar:
    # 侧边栏标题
    st.sidebar.title("股权分析平台") 
    
    st.sidebar.subheader("功能导航") 
    
    # 导航按钮，使用Unicode图标
    if st.sidebar.button("🏠 主页", help="返回主页面"):
        # 使用正确的相对路径
        st.switch_page("main_page.py")
        
    if st.sidebar.button("🔍 图像识别模式", help="使用AI识别股权结构图", use_container_width=True):
        # 使用正确的相对路径
        st.switch_page("pages/1_图像识别模式.py")
        
    if st.sidebar.button("📊 手动编辑模式", help="手动创建和编辑股权结构", use_container_width=True):
        # 使用正确的相对路径
        st.switch_page("pages/2_手动编辑模式.py")
    
    # 使用展开面板显示使用说明
    with st.expander("ℹ️ 使用说明", expanded=False):
        st.write("## 手动编辑模式操作步骤")
        st.write("1. **设置核心公司**: 输入公司名称")
        st.write("2. **添加股权关系**: ")
        st.write("   - 添加股东及持股比例")
        st.write("   - 添加子公司及持股比例")
        st.write("   - 设置实际控制关系")
        st.write("3. **编辑和调整**: 随时修改和调整股权结构")
        st.write("4. **生成图表**: 实时预览和生成股权结构图")
        st.write("5. **导出数据**: 下载Mermaid代码或JSON数据")
    
    st.sidebar.markdown("---")

    # 添加版权说明
    current_year = datetime.now().year
    st.sidebar.markdown(
        f'<h6>© {current_year} Noah 版权所有</h6>',
        unsafe_allow_html=True,
    )

# 导入Mermaid生成功能
from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram

# 导入AI分析模块
from src.utils.ai_equity_analyzer import analyze_equity_with_ai

# 导入vis.js图表工具
from src.utils.visjs_equity_chart import convert_equity_data_to_visjs, generate_visjs_html, generate_fullscreen_visjs_html
import streamlit.components.v1 as components


# ============================================================================
# 辅助函数：显示交互式HTML图表
# ============================================================================
def _display_visjs_chart():
    """显示交互式HTML图表"""
    import tempfile
    import webbrowser
    
    try:
        # 准备数据（应用合并规则）
        data_for_chart = {
            "core_company": st.session_state.equity_data.get("core_company", ""),
            "actual_controller": st.session_state.equity_data.get("actual_controller", ""),
            "shareholders": st.session_state.equity_data.get("shareholders", []),
            "subsidiaries": st.session_state.equity_data.get("subsidiaries", []),
            "top_level_entities": st.session_state.equity_data.get("top_level_entities", []),
            "entity_relationships": st.session_state.equity_data.get("entity_relationships", []),
            "control_relationships": st.session_state.equity_data.get("control_relationships", []),
            "all_entities": st.session_state.equity_data.get("all_entities", [])
        }
        
        # 🔥 关键修复：过滤掉没有实际关系的股东（与实时预览和生成图表保持一致）
        # 检查每个top_entity是否在entity_relationships中有对应的关系
        filtered_top_entities = []
        for entity in data_for_chart["top_level_entities"]:
            entity_name = entity.get("name", "")
            has_relationship = False
            
            # 检查是否有股权关系
            for rel in data_for_chart["entity_relationships"]:
                from_entity = rel.get('from', rel.get('parent', ''))
                to_entity = rel.get('to', rel.get('child', ''))
                if from_entity == entity_name:
                    has_relationship = True
                    break
            
            # 检查是否有控制关系
            if not has_relationship:
                for rel in data_for_chart["control_relationships"]:
                    from_entity = rel.get('from', rel.get('parent', ''))
                    to_entity = rel.get('to', rel.get('child', ''))
                    if from_entity == entity_name:
                        has_relationship = True
                        break
            
            # 🔥 修复：对于正常股东，即使没有显式关系也保留（会自动生成关系）
            # 只有明确不需要的实体才过滤掉
            should_filter = False
            
            # 检查是否为明确不需要的实体（如空名称、无效数据等）
            if not entity_name or entity_name.strip() == "":
                should_filter = True
                st.write(f"🔍 调试信息: 过滤掉空名称实体")
            elif entity.get("percentage", 0) <= 0:
                should_filter = True
                st.write(f"🔍 调试信息: 过滤掉无持股比例的实体: {entity_name}")
            else:
                # 正常股东，保留
                filtered_top_entities.append(entity)
                if has_relationship:
                    st.write(f"✅ 保留有关系的股东: {entity_name}")
                else:
                    st.write(f"✅ 保留正常股东（将自动生成关系）: {entity_name}")
            
            if should_filter:
                st.write(f"❌ 过滤掉无效实体: {entity_name}")
        
        data_for_chart["top_level_entities"] = filtered_top_entities
        
        # 应用合并规则（与Mermaid图表保持一致）
        if st.session_state.get("merged_entities"):
            # 过滤top_entities（股东）- 使用已经过滤过的数据
            merged_filtered_top_entities = []
            for entity in data_for_chart["top_level_entities"]:
                if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                    merged_filtered_top_entities.append(entity)
            
            # 过滤subsidiaries
            filtered_subsidiaries = []
            for subsidiary in data_for_chart["subsidiaries"]:
                if subsidiary.get("name", "") not in st.session_state.get("hidden_entities", []):
                    filtered_subsidiaries.append(subsidiary)
            
            # 添加合并后的实体
            for merged in st.session_state.get("merged_entities", []):
                # 根据合并实体的类型决定添加到哪个列表
                if any(e["type"] == "shareholder" for e in merged["entities"]):
                    # 如果包含股东，添加到top_entities
                    merged_filtered_top_entities.append({
                        "name": merged["merged_name"],
                        "type": "company",
                        "percentage": merged["total_percentage"]
                    })
                else:
                    # 否则添加到subsidiaries
                    filtered_subsidiaries.append({
                        "name": merged["merged_name"],
                        "percentage": merged["total_percentage"]
                    })
            
            data_for_chart["top_level_entities"] = merged_filtered_top_entities
            data_for_chart["subsidiaries"] = filtered_subsidiaries
            
            # 过滤all_entities
            filtered_all_entities = []
            for entity in data_for_chart["all_entities"]:
                if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                    filtered_all_entities.append(entity)
            
            # 添加合并后的实体到all_entities
            for merged in st.session_state.get("merged_entities", []):
                filtered_all_entities.append({
                    "name": merged["merged_name"],
                    "type": "company"
                })
            
            data_for_chart["all_entities"] = filtered_all_entities
            
            # 过滤entity_relationships，移除涉及被隐藏实体的关系
            filtered_relationships = []
            for rel in data_for_chart["entity_relationships"]:
                from_entity = rel.get('from', rel.get('parent', ''))
                to_entity = rel.get('to', rel.get('child', ''))
                if (from_entity not in st.session_state.get("hidden_entities", []) and 
                    to_entity not in st.session_state.get("hidden_entities", [])):
                    filtered_relationships.append(rel)
            
            # 为合并后的实体添加新的关系
            for merged in st.session_state.get("merged_entities", []):
                merged_name = merged["merged_name"]
                total_percentage = merged["total_percentage"]
                
                # 查找合并实体中第一个实体的关系作为模板
                first_entity = merged["entities"][0]
                for rel in st.session_state.equity_data.get("entity_relationships", []):
                    from_entity = rel.get('from', rel.get('parent', ''))
                    to_entity = rel.get('to', rel.get('child', ''))
                    
                    # 如果是从被合并实体出发的关系
                    if from_entity == first_entity["name"]:
                        filtered_relationships.append({
                            "from": merged_name,
                            "to": to_entity,
                            "percentage": total_percentage
                        })
                        break
                    # 如果是到被合并实体的关系
                    elif to_entity == first_entity["name"]:
                        filtered_relationships.append({
                            "from": from_entity,
                            "to": merged_name,
                            "percentage": total_percentage
                        })
                        break
            
            # 🔥 关键修复：在合并规则分支中，使用过滤后的实体（包括合并后的实体）
            core_company = st.session_state.equity_data.get("core_company", "")
            # 使用过滤后的top_level_entities（已经包含合并后的实体，排除了被合并的原始实体）
            top_level_entities = data_for_chart.get("top_level_entities", [])
            subsidiaries = data_for_chart.get("subsidiaries", [])
            control_relationships = st.session_state.equity_data.get("control_relationships", [])
            
            # 🔥 关键修复：在使用filtered_control_relationships之前先定义它
            filtered_control_relationships = []
            for rel in control_relationships:
                from_entity = rel.get('from', rel.get('parent', ''))
                to_entity = rel.get('to', rel.get('child', ''))
                if (from_entity not in st.session_state.get("hidden_entities", []) and 
                    to_entity not in st.session_state.get("hidden_entities", [])):
                    filtered_control_relationships.append(rel)
            
            # 创建现有关系的键集合，避免重复
            existing_relationships = set()
            for rel in filtered_relationships:
                from_e = rel.get("from", rel.get("parent", ""))
                to_e = rel.get("to", rel.get("child", ""))
                existing_relationships.add(f"{from_e}_{to_e}")
            
            # 1. 为每个顶级实体（股东）添加/更新与核心公司的关系
            actual_controller = st.session_state.equity_data.get("actual_controller", "")
            
            # 🔥 关键修复：取消自动处理实控人关系，让用户完全手动控制
            # 注释掉自动处理逻辑，避免自动生成用户已删除的关系
            # if core_company and top_level_entities:
            #     st.write(f"🔍 调试信息: 处理 {len(top_level_entities)} 个顶级实体")
            #     for entity in top_level_entities:
            #         shareholder_name = entity.get("name", "")
            #         percentage = entity.get("percentage", 0)
            #         
            #         st.write(f"🔍 调试信息: 处理股东 {shareholder_name}, 持股比例 {percentage}%")
            #         
            #         if shareholder_name and percentage > 0:
            #             # 🔥 如果是实际控制人，检查或创建控制关系
            #             if shareholder_name == actual_controller:
            #                 # 先删除已存在的股权关系
            #                 filtered_relationships = [
            #                     rel for rel in filtered_relationships
            #                     if not (rel.get("from", rel.get("parent", "")) == shareholder_name and 
            #                            rel.get("to", rel.get("child", "")) == core_company)
            #                 ]
            #                 
            #                 # 检查是否已有控制关系
            #                 has_control_relationship = False
            #                 for control_rel in control_relationships:
            #                     controller_name = control_rel.get("parent", control_rel.get("from", ""))
            #                     controlled_entity = control_rel.get("child", control_rel.get("to", ""))
            #                     if controller_name == shareholder_name and controlled_entity == core_company:
            #                         has_control_relationship = True
            #                         break
            #                 
            #                 # 如果没有控制关系，添加一个
            #                 if not has_control_relationship:
            #                     # 检查是否已经在filtered_control_relationships中
            #                     already_exists = False
            #                     for existing_rel in filtered_control_relationships:
            #                         existing_from = existing_rel.get("parent", existing_rel.get("from", ""))
            #                         existing_to = existing_rel.get("child", existing_rel.get("to", ""))
            #                         if existing_from == shareholder_name and existing_to == core_company:
            #                             already_exists = True
            #                             break
            #                     
            #                     if not already_exists:
            #                         filtered_control_relationships.append({
            #                             "parent": shareholder_name,
            #                             "child": core_company,
            #                             "relationship_type": "控制",
            #                             "description": f"实际控制人（持股{percentage}%）"
            #                         })
            #                             # 跳过股权关系创建（已经删除了）
            #                             continue
            #                         
            #                         # 检查是否有控制关系，如果有则跳过股权关系
            #                         has_control_relationship = False
            #                         for control_rel in control_relationships:
            #                             controller_name = control_rel.get("parent", control_rel.get("from", ""))
            #                             controlled_entity = control_rel.get("child", control_rel.get("to", ""))
            #                             if controller_name == shareholder_name and controlled_entity == core_company:
            #                                 has_control_relationship = True
            #                                 break
            #                         
            #                         if not has_control_relationship:
            #                             relationship_key = f"{shareholder_name}_{core_company}"
            #                             
            #                             # 先检查关系是否已存在，如果存在则更新百分比
            #                             relationship_exists = False
            #                             for rel in filtered_relationships:
            #                                 rel_from = rel.get("from", rel.get("parent", ""))
            #                                 rel_to = rel.get("to", rel.get("child", ""))
            #                                 if rel_from == shareholder_name and rel_to == core_company:
            #                                     # 更新现有关系的百分比
            #                                     rel["percentage"] = percentage
            #                                     relationship_exists = True
            #                                     break
            #                             
            #                             # 如果关系不存在，则添加新关系
            #                             if not relationship_exists and relationship_key not in existing_relationships:
            #                                 filtered_relationships.append({
            #                                     "parent": shareholder_name,
            #                                     "child": core_company,
            #                                     "percentage": percentage,
            #                                     "relationship_type": "股权",
            #                                     "description": f"持股{percentage}%"
            #                                 })
            #                                 existing_relationships.add(relationship_key)
            #                                 st.write(f"🔍 调试信息: 添加关系 {shareholder_name} -> {core_company} ({percentage}%)")
            #                             else:
            #                                 st.write(f"🔍 调试信息: 关系已存在，跳过 {shareholder_name} -> {core_company}")
            
            # 2. 为每个子公司添加与核心公司的关系
            if core_company and subsidiaries:
                for subsidiary in subsidiaries:
                    subsidiary_name = subsidiary.get("name", "")
                    percentage = subsidiary.get("percentage", 0)
                    
                    if (subsidiary_name and 
                        subsidiary_name not in st.session_state.get("hidden_entities", []) and 
                        percentage > 0):
                        
                        relationship_key = f"{core_company}_{subsidiary_name}"
                        
                        # 如果关系不存在，则添加
                        if relationship_key not in existing_relationships:
                            filtered_relationships.append({
                                "parent": core_company,
                                "child": subsidiary_name,
                                "percentage": percentage,
                                "relationship_type": "控股",
                                "description": f"持股{percentage}%"
                            })
                            existing_relationships.add(relationship_key)
                            st.write(f"🔗 自动添加关系: {core_company} -> {subsidiary_name} ({percentage}%)")
            
            data_for_chart["entity_relationships"] = filtered_relationships
            data_for_chart["control_relationships"] = filtered_control_relationships
        else:
            # 没有合并规则时，直接过滤隐藏实体
            filtered_entities = []
            for entity in st.session_state.equity_data["all_entities"]:
                if entity.get("name") not in st.session_state.get("hidden_entities", []):
                    filtered_entities.append(entity)
            data_for_chart["all_entities"] = filtered_entities
            
            # 过滤掉隐藏实体的关系
            filtered_entity_relationships = []
            for rel in st.session_state.equity_data["entity_relationships"]:
                from_entity = rel.get("from", rel.get("parent", ""))
                to_entity = rel.get("to", rel.get("child", ""))
                if (from_entity not in st.session_state.get("hidden_entities", []) and 
                    to_entity not in st.session_state.get("hidden_entities", [])):
                    filtered_entity_relationships.append(rel)
            
            # 🔥 关键修复：在else分支中也定义filtered_control_relationships
            filtered_control_relationships = []
            for rel in st.session_state.equity_data["control_relationships"]:
                from_entity = rel.get('from', rel.get('parent', ''))
                to_entity = rel.get('to', rel.get('child', ''))
                if (from_entity not in st.session_state.get("hidden_entities", []) and 
                    to_entity not in st.session_state.get("hidden_entities", [])):
                    filtered_control_relationships.append(rel)
            
            # 只使用手动配置的关系，不自动生成
            # 但子公司关系需要自动生成（核心公司 -> 子公司）
            core_company = data_for_chart.get("core_company", "")
            subsidiaries = data_for_chart.get("subsidiaries", [])
            
            if core_company and subsidiaries:
                # 创建现有关系的键集合，避免重复
                existing_relationships = set()
                for rel in filtered_entity_relationships:
                    from_e = rel.get("from", rel.get("parent", ""))
                    to_e = rel.get("to", rel.get("child", ""))
                    existing_relationships.add(f"{from_e}_{to_e}")
                
                # 为每个子公司添加与核心公司的关系
                for subsidiary in subsidiaries:
                    subsidiary_name = subsidiary.get("name", "")
                    percentage = subsidiary.get("percentage", 0)
                    
                    if (subsidiary_name and 
                        subsidiary_name not in st.session_state.get("hidden_entities", []) and 
                        percentage > 0):
                        
                        relationship_key = f"{core_company}_{subsidiary_name}"
                        
                        # 如果关系不存在，则添加
                        if relationship_key not in existing_relationships:
                            filtered_entity_relationships.append({
                                "parent": core_company,
                                "child": subsidiary_name,
                                "percentage": percentage,
                                "relationship_type": "控股",
                                "description": f"持股{percentage}%"
                            })
                            existing_relationships.add(relationship_key)
            
            data_for_chart["entity_relationships"] = filtered_entity_relationships
            
            # 过滤掉隐藏实体的控制关系
            filtered_control_relationships = []
            for rel in st.session_state.equity_data["control_relationships"]:
                from_entity = rel.get("from", rel.get("controller", ""))
                to_entity = rel.get("to", rel.get("controlled", ""))
                if (from_entity not in st.session_state.get("hidden_entities", []) and 
                    to_entity not in st.session_state.get("hidden_entities", [])):
                    filtered_control_relationships.append(rel)
            data_for_chart["control_relationships"] = filtered_control_relationships
        
        # 🎛️ 间距调整控件
        st.markdown("### 🎛️ 图表间距调整")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            level_separation = st.slider(
                "上下间距 (层级间距)",
                min_value=50,
                max_value=500,
                value=150,
                step=25,
                help="调整不同层级之间的垂直间距"
            )
        
        with col2:
            node_spacing = st.slider(
                "左右间距 (节点间距)",
                min_value=50,
                max_value=400,
                value=200,
                step=25,
                help="调整同一层级内节点之间的水平间距"
            )
        
        with col3:
            tree_spacing = st.slider(
                "树间距",
                min_value=100,
                max_value=600,
                value=200,
                step=25,
                help="调整不同树结构之间的间距"
            )
        
        with col4:
            st.markdown("**当前设置**")
            st.write(f"上下: {level_separation}px")
            st.write(f"左右: {node_spacing}px")
            st.write(f"树间距: {tree_spacing}px")
        
        # 转换数据
        with st.spinner("正在生成交互式HTML图表..."):
            # 调试信息
            st.write(f"📊 调试信息：共有 {len(data_for_chart['all_entities'])} 个实体，{len(data_for_chart['entity_relationships'])} 个股权关系，{len(data_for_chart['control_relationships'])} 个控制关系")
            
            # 显示层级调试信息
            if hasattr(st.session_state, 'debug_level_info'):
                with st.expander("层级调整调试信息", expanded=True):
                    st.text(st.session_state.debug_level_info)
            
            # 显示关系详情
            with st.expander("查看关系详情（调试）", expanded=False):
                st.write("**Entity Relationships (股权关系):**")
                for i, rel in enumerate(data_for_chart['entity_relationships'][:20]):
                    from_e = rel.get("from", rel.get("parent", ""))
                    to_e = rel.get("to", rel.get("child", ""))
                    pct = rel.get("percentage", 0)
                    st.text(f"{i+1}. {from_e} -> {to_e} ({pct}%)")
                
                st.write("**Control Relationships (控制关系):**")
                for i, rel in enumerate(data_for_chart['control_relationships'][:20]):
                    from_e = rel.get("from", rel.get("parent", ""))
                    to_e = rel.get("to", rel.get("child", ""))
                    desc = rel.get("description", "控制")
                    st.text(f"{i+1}. {from_e} -> {to_e} ({desc})")
                
                # 检查是否有重复的控制关系
                control_pairs = []
                for rel in data_for_chart['control_relationships']:
                    from_e = rel.get("from", rel.get("parent", ""))
                    to_e = rel.get("to", rel.get("child", ""))
                    pair = f"{from_e}_{to_e}"
                    control_pairs.append(pair)
                
                from collections import Counter
                pair_counts = Counter(control_pairs)
                duplicates = {pair: count for pair, count in pair_counts.items() if count > 1}
                
                if duplicates:
                    st.write("**⚠️ 发现重复的控制关系:**")
                    for pair, count in duplicates.items():
                        st.text(f"  {pair}: {count} 次")
                else:
                    st.write("✅ 没有重复的控制关系")
                
                st.write("**All Entities:**")
                for i, ent in enumerate(data_for_chart['all_entities'][:20]):
                    st.text(f"{i+1}. {ent.get('name')} ({ent.get('type')})")
            
            nodes, edges = convert_equity_data_to_visjs(data_for_chart)
            st.write(f"✅ 生成了 {len(nodes)} 个节点，{len(edges)} 条边")
        
        # 图表操作按钮
        col_op1, col_op2, col_op3 = st.columns(3)
        
        with col_op1:
            # 全屏查看按钮
            if st.button("🔍 全屏查看图表", type="primary", use_container_width=True, key="fullscreen_visjs"):
                # 生成分组配置（与实时预览相同的逻辑）
                subgraphs = []
                
                # 初始化分组名称存储
                if 'custom_group_names' not in st.session_state:
                    st.session_state.custom_group_names = {}
                
                # 根据层级创建分组
                level_groups = {}
                for node in nodes:
                    level = node.get('level', 0)
                    if level not in level_groups:
                        level_groups[level] = []
                    level_groups[level].append(node['id'])
                
                # 为每个层级创建分组
                for level, node_ids in level_groups.items():
                    # 获取自定义名称
                    group_key = f"group_name_level_{level}"
                    custom_name = st.session_state.custom_group_names.get(group_key, f"🏢 第{level}层实体")
                    
                    subgraph = {
                        "id": f"level_{level}",
                        "label": custom_name,
                        "nodes": node_ids,
                        "color": f"rgba({(level * 50) % 255}, {(level * 100) % 255}, {(level * 150) % 255}, 0.1)",
                        "borderColor": f"hsl({(level * 60) % 360}, 70%, 50%)"
                    }
                    subgraphs.append(subgraph)
                
                # 生成全屏HTML，传递间距参数和分组配置
                html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                            level_separation=level_separation,
                                                            node_spacing=node_spacing,
                                                            tree_spacing=tree_spacing,
                                                            subgraphs=subgraphs)
                
                # 保存到临时文件
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, 'equity_visjs_chart.html')
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # 在浏览器中打开
                webbrowser.open_new_tab(temp_file_path)
                st.info("🔍 已在新标签页打开全屏图表")
        
        with col_op2:
            # 下载JSON数据按钮
            if st.download_button(
                label="📥 下载 JSON 数据",
                data=json.dumps(st.session_state.equity_data, ensure_ascii=False, indent=2),
                file_name="equity_structure.json",
                mime="application/json",
                use_container_width=True,
                key="download_json_visjs"
            ):
                st.success("JSON文件已下载")
        
        with col_op3:
            # 下载HTML图表
            # 生成分组配置（与实时预览相同的逻辑）
            subgraphs = []
            
            # 初始化分组名称存储
            if 'custom_group_names' not in st.session_state:
                st.session_state.custom_group_names = {}
            
            # 根据层级创建分组
            level_groups = {}
            for node in nodes:
                level = node.get('level', 0)
                if level not in level_groups:
                    level_groups[level] = []
                level_groups[level].append(node['id'])
            
            # 为每个层级创建分组
            for level, node_ids in level_groups.items():
                # 获取自定义名称
                group_key = f"group_name_level_{level}"
                custom_name = st.session_state.custom_group_names.get(group_key, f"🏢 第{level}层实体")
                
                subgraph = {
                    "id": f"level_{level}",
                    "label": custom_name,
                    "nodes": node_ids,
                    "color": f"rgba({(level * 50) % 255}, {(level * 100) % 255}, {(level * 150) % 255}, 0.1)",
                    "borderColor": f"hsl({(level * 60) % 360}, 70%, 50%)"
                }
                subgraphs.append(subgraph)
            
            html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                        level_separation=level_separation,
                                                        node_spacing=node_spacing,
                                                        tree_spacing=tree_spacing,
                                                        subgraphs=subgraphs)
            if st.download_button(
                label="📥 下载HTML图表",
                data=html_content.encode('utf-8'),
                file_name="equity_chart.html",
                mime="text/html; charset=utf-8",
                use_container_width=True,
                key="download_html_visjs"
            ):
                st.success("HTML文件已下载")
        
        # 显示图表
        st.markdown("#### 交互式股权结构图")
        st.caption("💡 提示：点击节点高亮相关关系，拖拽可移动视图，滚轮缩放，点击按钮可适应窗口或导出PNG")
        
        # 添加实时预览选项
        col_preview1, col_preview2 = st.columns([1, 1])
        
        with col_preview1:
            show_visjs_preview = st.checkbox("显示实时vis.js预览", value=False, key="visjs_preview_toggle")
        
        with col_preview2:
            if show_visjs_preview:
                if st.button("🔄 刷新图表", key="refresh_visjs"):
                    st.rerun()
        
        # 显示实时vis.js预览
        if show_visjs_preview:
            try:
                # 生成分组配置
                subgraphs = []
                
                # 根据层级创建分组
                level_groups = {}
                for node in nodes:
                    level = node.get('level', 0)
                    if level not in level_groups:
                        level_groups[level] = []
                    level_groups[level].append(node['id'])
                
                # 调试信息：显示层级分组情况
                st.info(f"🔍 调试信息 - 层级分组情况: {dict(level_groups)}")
                
                # 分组名称自定义设置
                st.markdown("##### 🏷️ 分组名称设置")
                
                # 初始化分组名称存储
                if 'custom_group_names' not in st.session_state:
                    st.session_state.custom_group_names = {}
                
                # 重置分组名称按钮
                col_reset1, col_reset2 = st.columns([1, 4])
                with col_reset1:
                    if st.button("🔄 重置为默认名称", key="reset_group_names"):
                        # 清空自定义名称，恢复默认
                        st.session_state.custom_group_names = {}
                        st.rerun()
                with col_reset2:
                    st.caption("💡 提示：可以为每个层级的分组设置自定义名称，支持emoji表情")
                
                # 为每个层级创建分组名称设置
                group_name_cols = st.columns(min(len(level_groups), 3))  # 最多3列
                for i, (level, node_ids) in enumerate(level_groups.items()):
                    with group_name_cols[i % 3]:
                        # 默认分组名称
                        default_name = f"🏢 第{level}层实体"
                        
                        # 获取或设置自定义名称
                        group_key = f"group_name_level_{level}"
                        if group_key not in st.session_state.custom_group_names:
                            st.session_state.custom_group_names[group_key] = default_name
                        
                        # 显示节点信息
                        node_count = len(node_ids)
                        st.caption(f"层级 {level} ({node_count} 个节点)")
                        
                        # 输入框
                        custom_name = st.text_input(
                            f"分组名称",
                            value=st.session_state.custom_group_names[group_key],
                            key=f"group_name_input_{level}",
                            help=f"自定义第{level}层分组的显示名称"
                        )
                        
                        # 更新存储的名称
                        st.session_state.custom_group_names[group_key] = custom_name
                
                # 为每个层级创建分组
                for level, node_ids in level_groups.items():
                    # 获取自定义名称
                    group_key = f"group_name_level_{level}"
                    custom_name = st.session_state.custom_group_names.get(group_key, f"🏢 第{level}层实体")
                    
                    subgraph = {
                        "id": f"level_{level}",
                        "label": custom_name,
                        "nodes": node_ids,
                        "color": f"rgba({(level * 50) % 255}, {(level * 100) % 255}, {(level * 150) % 255}, 0.1)",
                        "borderColor": f"hsl({(level * 60) % 360}, 70%, 50%)"
                    }
                    subgraphs.append(subgraph)
                
                # 调试信息：显示生成的分组
                st.info(f"🔍 调试信息 - 生成的分组数量: {len(subgraphs)}")
                for i, subgraph in enumerate(subgraphs):
                    st.info(f"🔍 分组 {i+1}: {subgraph['label']} (节点: {subgraph['nodes']})")
                
                # 生成HTML内容
                html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                            level_separation=level_separation,
                                                            node_spacing=node_spacing,
                                                            tree_spacing=tree_spacing,
                                                            subgraphs=subgraphs)
                
                # 在Streamlit中显示
                components.html(html_content, height=600, scrolling=True)
                
                st.success("✅ vis.js图表已实时更新")
                
            except Exception as e:
                st.error(f"显示vis.js预览时出错: {str(e)}")
                st.info("📊 建议使用'全屏查看图表'或'下载HTML图表'功能查看完整的交互式图表")
        else:
            # 生成并显示图表
            st.info("📊 勾选'显示实时vis.js预览'以查看实时更新的交互式图表，或使用'全屏查看图表'功能")
        
        # 显示简化的统计预览
        st.markdown("#### 图表数据预览")
        preview_col1, preview_col2 = st.columns(2)
        
        with preview_col1:
            st.markdown("**节点列表**")
            for i, node in enumerate(nodes[:10]):  # 只显示前10个
                label = node.get('label', '未命名')
                level = node.get('level', 'N/A')
                st.text(f"{i+1}. {label} (层级: {level})")
            if len(nodes) > 10:
                st.text(f"... 还有 {len(nodes)-10} 个节点")
        
        with preview_col2:
            st.markdown("**关系列表**")
            for i, edge in enumerate(edges[:10]):  # 只显示前10条关系
                from_node = nodes[edge['from']]['label']
                to_node = nodes[edge['to']]['label']
                label = edge.get('label', '')
                st.text(f"{i+1}. {from_node} → {to_node} ({label})")
            if len(edges) > 10:
                st.text(f"... 还有 {len(edges)-10} 条关系")
        
        # 显示统计信息
        st.markdown("---")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("节点数量", len(nodes))
        with col_stat2:
            st.metric("关系数量", len(edges))
        with col_stat3:
            entity_types = {}
            for node in nodes:
                # 从颜色推断类型
                if node["color"]["background"] == "#0d47a1":
                    entity_types["实际控制人"] = entity_types.get("实际控制人", 0) + 1
                elif node["color"]["background"] == "#fff8e1":
                    entity_types["核心公司"] = entity_types.get("核心公司", 0) + 1
                elif node["color"]["background"] == "#e8f5e9":
                    entity_types["个人"] = entity_types.get("个人", 0) + 1
                else:
                    entity_types["公司"] = entity_types.get("公司", 0) + 1
            
            type_str = ", ".join([f"{k}:{v}" for k, v in entity_types.items()])
            st.metric("实体类型", type_str if type_str else "无")
        
    except Exception as e:
        st.error(f"生成图表时出错: {str(e)}")
        st.exception(e)


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
        "subsidiaries": [],  # 也添加subsidiaries键以确保完整性
        "all_entities": []  # 添加all_entities键以避免KeyError
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
            # 使用st.write代替不存在的st.log方法
            st.write('Streamlit Cloud环境检测到，将使用环境变量配置')
    except ImportError:
        st.write('未找到alicloud_translator模块，继续运行')

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
    
    /* 主题变量 - 与图像识别模式保持一致 */
    :root {
        --primary-color: #0f4c81;
        --secondary-color: #17a2b8;
        --accent-color: rgba(255, 255, 255, 0.95);
        --text-color: #2c3e50;
        --light-text: #6c757d;
        --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        --transition: all 0.3s ease;
    }
    
    /* 按钮样式 - 改进主按钮，添加宽边框，确保不换行 */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: 2px solid var(--primary-color);
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        cursor: pointer;
        border-radius: 6px;
        transition: var(--transition);
        box-shadow: 0 2px 4px rgba(15, 76, 129, 0.2);
        white-space: nowrap;
        overflow-wrap: break-word;
        word-wrap: break-word;
    }
    
    .stButton>button:hover {
        background-color: #0c3e66;
        box-shadow: 0 4px 8px rgba(15, 76, 129, 0.3);
        transform: translateY(-1px);
    }
    
    .stButton>button:focus {
        outline: 2px solid rgba(15, 76, 129, 0.5);
        outline-offset: 2px;
    }
    
    /* 确保primary类型按钮使用正确的背景色 */
    .stButton>button[data-testid="baseButton-primary"] {
        background-color: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
    }
    
    .stButton>button[data-testid="baseButton-primary"]:hover {
        background-color: #0c3e66;
        border-color: #0c3e66;
    }
    
    /* 确保secondary类型按钮使用不同的样式 */
    .stButton>button[data-testid="baseButton-secondary"] {
        background-color: #f0f2f6;
        color: #333;
        border-color: #d9d9d9;
    }
    
    .stButton>button[data-testid="baseButton-secondary"]:hover {
        background-color: #e6e8eb;
        border-color: #bfbfbf;
    }
    
    /* 针对保存并继续、添加顶级实体、添加子公司、添加股权关系等按钮的样式 */
    .st-emotion-cache-1r970rc {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: 2px solid var(--primary-color) !important;
    }
    
    .st-emotion-cache-1r970rc:hover {
        background-color: #0c3e66 !important;
        border-color: #0c3e66 !important;
    }
    
    /* 使用data-testid选择器确保按钮样式正确应用 */
    button[data-testid="stBaseButton-primaryFormSubmit"] {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: 2px solid var(--primary-color) !important;
    }
    
    button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background-color: #0c3e66 !important;
        border-color: #0c3e66 !important;
    }
    
    /* 信息框样式优化 */
    .info-box {
        background-color: #f0f5ff;
        border-left: 4px solid var(--primary-color);
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .success-box {
        background-color: #f6ffed;
        border-left: 4px solid #52c41a;
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .error-box {
        background-color: #fff1f0;
        border-left: 4px solid #ff4d4f;
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* 实体卡片样式 - 更现代的设计 */
    .entity-card {
        background-color: white;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }
    
    .entity-card:hover {
        border-color: var(--primary-color);
        box-shadow: 0 4px 12px rgba(15, 76, 129, 0.1);
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
    """获取顶级实体名称列表，考虑合并状态"""
    entity_names = []
    
    # 添加未隐藏的顶级实体
    for entity in st.session_state.equity_data.get("top_level_entities", []):
        entity_name = entity.get("name", "")
        if entity_name and entity_name not in st.session_state.get("hidden_entities", []):
            entity_names.append(entity_name)
    
    # 添加合并后的股东实体
    for merged in st.session_state.get("merged_entities", []):
        if any(e["type"] == "shareholder" for e in merged["entities"]):
            merged_name = merged.get("merged_name", "")
            if merged_name:
                entity_names.append(merged_name)
    
    return entity_names

# 获取子公司名称列表
def get_subsidiary_names():
    """获取子公司名称列表，考虑合并状态"""
    subsidiary_names = []
    
    # 添加未隐藏的子公司
    for subsidiary in st.session_state.equity_data.get("subsidiaries", []):
        subsidiary_name = subsidiary.get("name", "")
        if subsidiary_name and subsidiary_name not in st.session_state.get("hidden_entities", []):
            subsidiary_names.append(subsidiary_name)
    
    # 添加合并后的子公司实体
    for merged in st.session_state.get("merged_entities", []):
        if not any(e["type"] == "shareholder" for e in merged["entities"]):
            merged_name = merged.get("merged_name", "")
            if merged_name:
                subsidiary_names.append(merged_name)
    
    return subsidiary_names

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

    # 合并功能相关状态
    if 'merged_entities' not in st.session_state:
        st.session_state.merged_entities = []  # 存储合并后的实体
    if 'hidden_entities' not in st.session_state:
        st.session_state.hidden_entities = []  # 存储被隐藏的原始实体
    if 'merge_threshold' not in st.session_state:
        st.session_state.merge_threshold = 1.0  # 默认阈值1%

initialize_session_state()

# 定义步骤列表
steps = ["core_company", "top_entities", "subsidiaries", "merge_entities", "relationships", "generate"]
# 定义步骤显示名称
step_names = {
    "core_company": "1. 核心公司",
    "top_entities": "2. 顶层实体",
    "subsidiaries": "3. 子公司",
    "merge_entities": "4. 股权合并",
    "relationships": "5. 关系设置",
    "generate": "6. 生成图表"
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
    
    # 重置按钮 - 修复版本，使用session_state管理确认状态
    # 初始化重置确认状态
    if 'show_step_reset_confirm' not in st.session_state:
        st.session_state.show_step_reset_confirm = False
    if 'step_to_reset' not in st.session_state:
        st.session_state.step_to_reset = None

    if nav_cols[2].button("🔄 重置当前步骤", use_container_width=True, type="secondary"):
        st.session_state.show_step_reset_confirm = True
        st.session_state.step_to_reset = st.session_state.current_step

    if st.session_state.show_step_reset_confirm:
        # 根据当前步骤显示确认信息
        if st.session_state.step_to_reset == "core_company":
            st.warning("⚠️ 确认重置核心公司设置？")
        elif st.session_state.step_to_reset == "top_entities":
            st.warning("⚠️ 确认重置顶级实体/股东？")
        elif st.session_state.step_to_reset == "subsidiaries":
            st.warning("⚠️ 确认重置子公司？")
        elif st.session_state.step_to_reset == "relationships":
            st.warning("⚠️ 确认重置关系设置？")
        elif st.session_state.step_to_reset == "generate":
            st.info("在图表生成步骤中无需重置")
            st.session_state.show_step_reset_confirm = False
            st.rerun()
        
        if st.session_state.step_to_reset != "generate":
            confirm_cols = st.columns([1, 1, 1])
            
            if confirm_cols[0].button("✅ 确认重置", type="primary"):
                # 根据步骤执行重置
                if st.session_state.step_to_reset == "core_company":
                    st.session_state.equity_data["core_company"] = ""
                    st.session_state.equity_data["actual_controller"] = ""
                    # 移除core_company实体
                    st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "core_company"]
                    st.success("核心公司设置已重置")
                elif st.session_state.step_to_reset == "top_entities":
                    st.session_state.equity_data["top_level_entities"] = []
                    # 移除相关实体
                    st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "top_entity"]
                    st.success("顶级实体/股东已重置")
                elif st.session_state.step_to_reset == "subsidiaries":
                    st.session_state.equity_data["subsidiaries"] = []
                    # 移除相关实体
                    st.session_state.equity_data["all_entities"] = [e for e in st.session_state.equity_data["all_entities"] if e.get("type") != "subsidiary"]
                    st.success("子公司已重置")
                elif st.session_state.step_to_reset == "relationships":
                    st.session_state.equity_data["entity_relationships"] = []
                    st.session_state.equity_data["control_relationships"] = []
                    st.success("关系设置已重置")
                
                # 重置确认状态
                st.session_state.show_step_reset_confirm = False
                st.session_state.step_to_reset = None
                st.rerun()
            
            if confirm_cols[1].button("❌ 取消", type="secondary"):
                st.session_state.show_step_reset_confirm = False
                st.session_state.step_to_reset = None
                st.rerun()
    
    # 危险操作 - 完全重置所有数据（修复版本）
    # 使用session_state来管理确认状态，避免嵌套按钮问题
    if 'show_reset_confirm' not in st.session_state:
        st.session_state.show_reset_confirm = False

    if st.button("⚠️ 完全重置所有数据", type="secondary", help="此操作将清除所有已输入的数据"):
        st.session_state.show_reset_confirm = True

    if st.session_state.show_reset_confirm:
        st.warning("⚠️ 确认完全重置所有数据？此操作不可撤销！")
        confirm_cols = st.columns([1, 1, 1])
        
        if confirm_cols[0].button("✅ 确认重置", type="primary"):
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
            st.session_state.show_reset_confirm = False
            st.success("所有数据已重置")
            st.rerun()
        
        if confirm_cols[1].button("❌ 取消", type="secondary"):
            st.session_state.show_reset_confirm = False
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
                    all_entities = [e for e in st.session_state.equity_data.get("all_entities", []) if e.get("type") != "core_company"]
                    all_entities.append({"name": core_company, "type": "company"})
                    # 如果填写了实际控制人，则将其映射到顶级实体与所有实体，便于在关系步骤中选择
                    if controller and not any(e.get("name") == controller for e in st.session_state.equity_data.get("top_level_entities", [])):
                        st.session_state.equity_data["top_level_entities"].append({
                            "name": controller,
                            "type": "person",
                            "percentage": 0.0
                        })
                    if controller and not any(e.get("name") == controller for e in all_entities):
                        all_entities.append({"name": controller, "type": "person"})
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
                # 映射示例中的实际控制人到顶级实体和所有实体，确保后续可被选择
                example_controller = st.session_state.equity_data.get("actual_controller", "")
                if example_controller:
                    if not any(e.get("name") == example_controller for e in st.session_state.equity_data.get("top_level_entities", [])):
                        st.session_state.equity_data["top_level_entities"].append({
                            "name": example_controller,
                            "type": "person",
                            "percentage": 0.0
                        })
                    if not any(e.get("name") == example_controller for e in st.session_state.equity_data.get("all_entities", [])):
                        st.session_state.equity_data["all_entities"].append({
                            "name": example_controller,
                            "type": "person"
                        })
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
        if st.button("🔍 使用AI分析股权结构", type="primary", key="ai_analysis_core_company"):
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
                            
                        # 分析完成后自动跳转到关系设置页面
                        st.success("AI分析完成！已自动填充股权结构信息")
                        st.session_state.current_step = "relationships"
                        st.rerun()  # 刷新页面，跳转到 relationships
                        
                        # 添加一个详细验证按钮（可选）
                        if st.button("📋 详细验证数据", type="secondary"):
                            # 使用通用数据验证函数
                            data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
                            
                            # 显示验证结果
                            if data_valid:
                                st.success("数据验证通过！")
                            else:
                                st.error("数据验证失败。")
                                # 显示关键错误
                                error_messages = [log for log in validation_logs if "错误" in log]
                                if error_messages:
                                    st.markdown("### 验证错误")
                                    for error in error_messages:
                                        st.error(error)
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
                        removed_entity_name = removed_entity["name"]
                        
                        # 从all_entities中移除
                        st.session_state.equity_data["all_entities"] = [
                            e for e in st.session_state.equity_data.get("all_entities", []) 
                            if e["name"] != removed_entity_name
                        ]
                        
                        # 🔥 关键修复：同时删除对应的关系
                        # 删除entity_relationships中涉及该实体的关系
                        original_entity_relationships_count = len(st.session_state.equity_data["entity_relationships"])
                        st.session_state.equity_data["entity_relationships"] = [
                            rel for rel in st.session_state.equity_data["entity_relationships"]
                            if (rel.get("from", rel.get("parent", "")) != removed_entity_name and 
                                rel.get("to", rel.get("child", "")) != removed_entity_name)
                        ]
                        deleted_entity_relationships_count = original_entity_relationships_count - len(st.session_state.equity_data["entity_relationships"])
                        
                        # 删除control_relationships中涉及该实体的关系
                        original_control_relationships_count = len(st.session_state.equity_data["control_relationships"])
                        st.session_state.equity_data["control_relationships"] = [
                            rel for rel in st.session_state.equity_data["control_relationships"]
                            if (rel.get("from", rel.get("parent", "")) != removed_entity_name and 
                                rel.get("to", rel.get("child", "")) != removed_entity_name)
                        ]
                        deleted_control_relationships_count = original_control_relationships_count - len(st.session_state.equity_data["control_relationships"])
                        
                        # 🔥 关键修复：处理合并实体
                        # 检查删除的股东是否在合并实体中
                        merged_entities_updated = False
                        merged_entities_to_remove = []
                        
                        st.write(f"🔍 调试信息: 开始检查合并实体，当前有 {len(st.session_state.get('merged_entities', []))} 个合并实体")
                        
                        if st.session_state.get("merged_entities"):
                            for merged_idx, merged_entity in enumerate(st.session_state.merged_entities):
                                # 检查删除的股东是否在这个合并实体中
                                entity_found = False
                                for entity_idx, entity in enumerate(merged_entity["entities"]):
                                    if entity["name"] == removed_entity_name:
                                        entity_found = True
                                        # 从合并实体中移除该股东
                                        removed_entity_from_merge = merged_entity["entities"].pop(entity_idx)
                                        merged_entities_updated = True
                                        
                                        st.write(f"🔍 调试信息: 从合并实体 '{merged_entity['merged_name']}' 中移除股东: {removed_entity_name}")
                                        
                                        # 重新计算合并实体的总持股比例
                                        if merged_entity["entities"]:
                                            # 还有实体，重新计算总比例
                                            new_total_percentage = sum(entity.get("percentage", 0) for entity in merged_entity["entities"])
                                            merged_entity["total_percentage"] = new_total_percentage
                                            st.write(f"🔍 调试信息: 更新合并实体 '{merged_entity['merged_name']}' 的总持股比例为: {new_total_percentage}%")
                                        else:
                                            # 没有实体了，标记为删除
                                            merged_entities_to_remove.append(merged_idx)
                                            st.write(f"🔍 调试信息: 合并实体 '{merged_entity['merged_name']}' 为空，将删除")
                                        break
                                
                                if entity_found:
                                    break
                        
                        # 删除空的合并实体（从后往前删除，避免索引问题）
                        for idx in reversed(merged_entities_to_remove):
                            removed_merged_entity = st.session_state.merged_entities.pop(idx)
                            st.write(f"🔍 调试信息: 已删除空的合并实体: {removed_merged_entity['merged_name']}")
                        
                        st.success(f"已删除: {removed_entity_name}")
                        st.write(f"🔍 调试信息: 同时删除了 {deleted_entity_relationships_count} 个股权关系和 {deleted_control_relationships_count} 个控制关系")
                        if merged_entities_updated:
                            st.write(f"🔍 调试信息: 已更新合并实体信息")
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
                
                # 修复：处理可能没有percentage字段的情况，提供默认值，确保不小于0.01
                safe_default_percentage = max(default_percentage, 0.01) if default_percentage > 0 else 10.0
                percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=safe_default_percentage, step=0.01)
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
                # 确保百分比值不小于0.01
                safe_percentage = max(subsidiary["percentage"], 0.01) if subsidiary["percentage"] > 0 else 51.0
                percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=safe_percentage, step=0.01)
                
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
                            if not any(e.get("name") == name for e in st.session_state.equity_data.get("all_entities", [])):
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
    
    # 主要股东信息（考虑合并状态）
    def get_display_entities():
        """获取用于显示的实体列表，考虑合并状态"""
        display_entities = []
        
        # 过滤掉被隐藏的实体
        for entity in st.session_state.equity_data["top_level_entities"]:
            if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                display_entities.append(entity)
        
        # 添加合并后的实体
        for merged in st.session_state.get("merged_entities", []):
            # 根据合并实体的类型决定显示位置
            if any(e["type"] == "shareholder" for e in merged["entities"]):
                display_entities.append({
                    "name": merged["merged_name"],
                    "percentage": merged["total_percentage"],
                    "type": "merged_shareholder"
                })
        
        return display_entities
    
    def get_display_subsidiaries():
        """获取用于显示的子公司列表，考虑合并状态"""
        display_subsidiaries = []
        
        # 过滤掉被隐藏的子公司
        for subsidiary in st.session_state.equity_data["subsidiaries"]:
            if subsidiary.get("name", "") not in st.session_state.get("hidden_entities", []):
                display_subsidiaries.append(subsidiary)
        
        # 添加合并后的子公司
        for merged in st.session_state.get("merged_entities", []):
            # 如果只包含子公司，添加到子公司列表
            if not any(e["type"] == "shareholder" for e in merged["entities"]):
                display_subsidiaries.append({
                    "name": merged["merged_name"],
                    "percentage": merged["total_percentage"],
                    "type": "merged_subsidiary"
                })
        
        return display_subsidiaries
    
    # 显示主要股东信息
    display_entities = get_display_entities()
    if display_entities:
        st.markdown("#### 主要股东/顶级实体")
        cols = st.columns(3)
        for i, entity in enumerate(display_entities):
            with cols[i % 3]:
                percentage = entity.get('percentage', 'N/A')
                entity_name = entity['name']
                # 如果是合并实体，添加特殊标记
                if entity.get('type') in ['merged_shareholder', 'merged_subsidiary']:
                    entity_name = f"🔀 {entity_name} (合并)"
                st.write(f"- {entity_name} ({percentage}%)")
    
    # 显示子公司信息
    display_subsidiaries = get_display_subsidiaries()
    if display_subsidiaries:
        st.markdown("#### 子公司")
        cols = st.columns(3)
        for i, subsidiary in enumerate(display_subsidiaries):
            with cols[i % 3]:
                subsidiary_name = subsidiary['name']
                # 如果是合并实体，添加特殊标记
                if subsidiary.get('type') == 'merged_subsidiary':
                    subsidiary_name = f"🔀 {subsidiary_name} (合并)"
                st.write(f"- {subsidiary_name} ({subsidiary['percentage']}%)")
    
    # 显示分隔线
    st.divider()
    
    # 获取所有实体名称列表 - 考虑合并状态
    def get_all_entity_names():
        """获取所有实体名称列表，考虑合并状态"""
        all_entity_names = []
        
        # 添加核心公司
        if st.session_state.equity_data.get("core_company"):
            all_entity_names.append(st.session_state.equity_data["core_company"])
        
        # 添加实际控制人
        if st.session_state.equity_data.get("actual_controller"):
            controller = st.session_state.equity_data["actual_controller"]
            if controller not in all_entity_names:
                all_entity_names.append(controller)
        
        # 添加未隐藏的顶级实体
        for entity in st.session_state.equity_data.get("top_level_entities", []):
            entity_name = entity.get("name", "")
            if entity_name and entity_name not in st.session_state.get("hidden_entities", []):
                if entity_name not in all_entity_names:
                    all_entity_names.append(entity_name)
        
        # 添加未隐藏的子公司
        for subsidiary in st.session_state.equity_data.get("subsidiaries", []):
            subsidiary_name = subsidiary.get("name", "")
            if subsidiary_name and subsidiary_name not in st.session_state.get("hidden_entities", []):
                if subsidiary_name not in all_entity_names:
                    all_entity_names.append(subsidiary_name)
        
        # 添加合并后的实体
        for merged in st.session_state.get("merged_entities", []):
            merged_name = merged.get("merged_name", "")
            if merged_name and merged_name not in all_entity_names:
                all_entity_names.append(merged_name)
        
        return all_entity_names
    
    all_entity_names = get_all_entity_names()
    
    # 显示股权关系（考虑合并状态）
    st.markdown("### 股权关系")
    
    def get_filtered_relationships():
        """获取过滤后的股权关系，考虑合并状态"""
        filtered_relationships = []
        
        for rel in st.session_state.equity_data.get("entity_relationships", []):
            from_entity = rel.get('from', rel.get('parent', ''))
            to_entity = rel.get('to', rel.get('child', ''))
            
            # 如果关系中的实体都没有被隐藏，则保留这个关系
            if (from_entity not in st.session_state.get("hidden_entities", []) and 
                to_entity not in st.session_state.get("hidden_entities", [])):
                filtered_relationships.append(rel)
        
        return filtered_relationships
    
    filtered_relationships = get_filtered_relationships()
    
    if filtered_relationships:
        # 添加一个函数来获取实体的持股比例
        def get_entity_percentage_for_display(entity_name):
            """从顶级实体列表或子公司列表中获取指定实体的持股比例，考虑合并状态"""
            # 先检查是否是合并后的实体
            for merged in st.session_state.get("merged_entities", []):
                if merged.get("merged_name") == entity_name:
                    return merged.get("total_percentage", 0)
            
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
            
        for i, rel in enumerate(filtered_relationships):
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
                        percentage = rel.get('percentage', 0)
                        
                        # 🔍 详细调试信息
                        st.write(f"🔍 调试信息: 准备删除关系 {from_entity} → {to_entity} ({percentage}%)")
                        st.write(f"🔍 调试信息: 当前entity_relationships数量: {len(st.session_state.equity_data['entity_relationships'])}")
                        
                        # 显示所有关系用于调试
                        st.write("🔍 调试信息: 当前所有entity_relationships:")
                        for idx, rel_item in enumerate(st.session_state.equity_data["entity_relationships"]):
                            rel_from = rel_item.get('from', rel_item.get('parent', ''))
                            rel_to = rel_item.get('to', rel_item.get('child', ''))
                            rel_percentage = rel_item.get('percentage', 0)
                            st.write(f"  {idx}: {rel_from} → {rel_to} ({rel_percentage}%)")
                        
                        # 🔥 关键修复：在过滤后的关系中删除，而不是在原始关系中删除
                        # 因为显示的是过滤后的关系，删除也应该在过滤后的关系中删除
                        
                        # 首先从过滤后的关系中删除
                        filtered_relationships.pop(i)
                        st.write(f"🔍 调试信息: 从过滤列表中删除，剩余 {len(filtered_relationships)} 个关系")
                        
                        # 然后从原始关系中也删除（如果存在）
                        original_index = None
                        st.write("🔍 调试信息: 查找原始关系中的匹配项...")
                        for orig_i, orig_rel in enumerate(st.session_state.equity_data["entity_relationships"]):
                            orig_from = orig_rel.get('from', orig_rel.get('parent', ''))
                            orig_to = orig_rel.get('to', orig_rel.get('child', ''))
                            orig_percentage = orig_rel.get('percentage', 0)
                            st.write(f"🔍 调试信息: 检查原始关系 {orig_i}: {orig_from} → {orig_to} ({orig_percentage}%)")
                            if orig_from == from_entity and orig_to == to_entity:
                                original_index = orig_i
                                st.write(f"🔍 调试信息: 找到匹配关系，索引: {orig_i}")
                                break
                        
                        if original_index is not None:
                            st.session_state.equity_data["entity_relationships"].pop(original_index)
                            st.success(f"✅ 已删除关系: {from_entity} → {to_entity}")
                            st.write(f"🔍 调试信息: 从原始关系中删除，删除前有 {len(st.session_state.equity_data['entity_relationships']) + 1} 个关系，删除后有 {len(st.session_state.equity_data['entity_relationships'])} 个关系")
                            
                            # 显示删除后的关系列表
                            st.write("🔍 调试信息: 删除后的entity_relationships:")
                            for idx, rel_item in enumerate(st.session_state.equity_data["entity_relationships"]):
                                rel_from = rel_item.get('from', rel_item.get('parent', ''))
                                rel_to = rel_item.get('to', rel_item.get('child', ''))
                                rel_percentage = rel_item.get('percentage', 0)
                                st.write(f"  {idx}: {rel_from} → {rel_to} ({rel_percentage}%)")
                        else:
                            st.success(f"✅ 已删除关系: {from_entity} → {to_entity} (仅从过滤列表中删除)")
                            st.write(f"🔍 调试信息: 该关系不在原始关系中，可能是在过滤过程中自动添加的")
                        
                        st.rerun()
    else:
        st.info("尚未添加股权关系")
    
    # 显示控制关系（考虑合并状态）
    st.markdown("### 控制关系（虚线表示）")
    
    def get_filtered_control_relationships():
        """获取过滤后的控制关系，考虑合并状态"""
        filtered_control_relationships = []
        
        for rel in st.session_state.equity_data.get("control_relationships", []):
            from_entity = rel.get('from', rel.get('parent', ''))
            to_entity = rel.get('to', rel.get('child', ''))
            
            # 如果关系中的实体都没有被隐藏，则保留这个关系
            if (from_entity not in st.session_state.get("hidden_entities", []) and 
                to_entity not in st.session_state.get("hidden_entities", [])):
                filtered_control_relationships.append(rel)
        
        return filtered_control_relationships
    
    filtered_control_relationships = get_filtered_control_relationships()
    
    if filtered_control_relationships:
        for i, rel in enumerate(filtered_control_relationships):
            # 兼容from/to和parent/child两种格式
            from_entity = rel.get('from', rel.get('parent', '未知'))
            to_entity = rel.get('to', rel.get('child', '未知'))
            with st.expander(f"{from_entity} ⤳ {to_entity} ({rel.get('description', '控制关系')})"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("编辑", key=f"edit_control_rel_{i}"):
                        # 找到原始控制关系列表中的索引
                        original_index = None
                        for orig_i, orig_rel in enumerate(st.session_state.equity_data["control_relationships"]):
                            orig_from = orig_rel.get('from', orig_rel.get('parent', ''))
                            orig_to = orig_rel.get('to', orig_rel.get('child', ''))
                            if orig_from == from_entity and orig_to == to_entity:
                                original_index = orig_i
                                break
                        
                        if original_index is not None:
                            st.session_state.editing_relationship = ("control", original_index)
                            st.rerun()
                with col2:
                    if st.button("删除", key=f"delete_control_rel_{i}", type="secondary"):
                        # 兼容from/to和parent/child两种格式
                        from_entity = rel.get('from', rel.get('parent', '未知'))
                        to_entity = rel.get('to', rel.get('child', '未知'))
                        
                        # 🔥 关键修复：在过滤后的控制关系中删除
                        # 首先从过滤后的控制关系中删除
                        filtered_control_relationships.pop(i)
                        
                        # 然后从原始控制关系中也删除（如果存在）
                        original_index = None
                        for orig_i, orig_rel in enumerate(st.session_state.equity_data["control_relationships"]):
                            orig_from = orig_rel.get('from', orig_rel.get('parent', ''))
                            orig_to = orig_rel.get('to', orig_rel.get('child', ''))
                            if orig_from == from_entity and orig_to == to_entity:
                                original_index = orig_i
                                break
                        
                        if original_index is not None:
                            st.session_state.equity_data["control_relationships"].pop(original_index)
                            st.success(f"已删除控制关系: {from_entity} ⤳ {to_entity}")
                            st.write(f"🔍 调试信息: 从原始控制关系中删除，删除前有 {len(st.session_state.equity_data['control_relationships']) + 1} 个控制关系，删除后有 {len(st.session_state.equity_data['control_relationships'])} 个控制关系")
                        else:
                            st.success(f"已删除控制关系: {from_entity} ⤳ {to_entity} (仅从过滤列表中删除)")
                            st.write(f"🔍 调试信息: 该控制关系不在原始控制关系中，可能是在过滤过程中自动添加的")
                        
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
                    """从顶级实体列表和合并实体中获取指定实体的持股比例"""
                    # 首先检查top_level_entities
                    for entity in st.session_state.equity_data["top_level_entities"]:
                        if entity["name"] == entity_name and "percentage" in entity:
                            return entity["percentage"]
                    
                    # 然后检查合并实体
                    if st.session_state.get("merged_entities"):
                        for merged in st.session_state.merged_entities:
                            if merged["merged_name"] == entity_name:
                                return merged["total_percentage"]
                    
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
                
                # 百分比输入框，确保默认值不小于0.01
                safe_default_percentage_edit = max(default_percentage_edit, 0.01) if default_percentage_edit > 0 else 51.0
                percentage_value_edit = st.number_input("修改持股比例 (%)", min_value=0.01, max_value=100.0, value=safe_default_percentage_edit, step=0.01, help="默认为实体的持股比例，可手动修改")
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
    
    # AI分析报告显示区域 - 已移动到添加股权关系tab中

    # 实时预览功能 - 移动到添加股权关系标题的正上方
    if st.session_state.current_step == "relationships":
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
                
                # 🔥 关键修复：过滤掉没有实际关系的股东
                # 检查每个top_entity是否在entity_relationships中有对应的关系
                filtered_top_entities = []
                for entity in data_for_mermaid["top_entities"]:
                    entity_name = entity.get("name", "")
                    has_relationship = False
                    
                    # 检查是否有股权关系
                    for rel in data_for_mermaid["entity_relationships"]:
                        from_entity = rel.get('from', rel.get('parent', ''))
                        to_entity = rel.get('to', rel.get('child', ''))
                        if from_entity == entity_name:
                            has_relationship = True
                            break
                    
                    # 检查是否有控制关系
                    if not has_relationship:
                        for rel in data_for_mermaid["control_relationships"]:
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                            if from_entity == entity_name:
                                has_relationship = True
                                break
                    
                    # 🔥 修复：对于正常股东，即使没有显式关系也保留（会自动生成关系）
                    # 只有明确不需要的实体才过滤掉
                    should_filter = False
                    
                    # 检查是否为明确不需要的实体（如空名称、无效数据等）
                    if not entity_name or entity_name.strip() == "":
                        should_filter = True
                        st.write(f"🔍 调试信息: 过滤掉空名称实体")
                    elif entity.get("percentage", 0) <= 0:
                        should_filter = True
                        st.write(f"🔍 调试信息: 过滤掉无持股比例的实体: {entity_name}")
                    else:
                        # 正常股东，保留
                        filtered_top_entities.append(entity)
                        if has_relationship:
                            st.write(f"✅ 保留有关系的股东: {entity_name}")
                        else:
                            st.write(f"✅ 保留正常股东（将自动生成关系）: {entity_name}")
                    
                    if should_filter:
                        st.write(f"❌ 过滤掉无效实体: {entity_name}")
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 🔥 特殊处理：检查是否有被过滤掉的合并实体需要恢复（实时预览）
                st.write(f"🔍 调试信息: 实时预览 - 检查是否有被过滤掉的合并实体")
                for entity in st.session_state.equity_data.get("top_level_entities", []):
                    entity_name = entity.get("name", "")
                    if entity_name not in [e["name"] for e in filtered_top_entities]:
                        # 检查是否在合并实体中
                        is_merged_entity = False
                        for merged in st.session_state.get("merged_entities", []):
                            if merged.get("merged_name") == entity_name:
                                is_merged_entity = True
                                st.write(f"🔍 调试信息: 实时预览 - 发现被过滤的合并实体: {entity_name}")
                                # 恢复合并实体
                                filtered_top_entities.append(entity)
                                break
                        
                        if not is_merged_entity:
                            st.write(f"🔍 调试信息: 实时预览 - 被过滤的非合并实体: {entity_name}")
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 应用合并规则到预览数据
                if st.session_state.get("merged_entities"):
                    # 过滤top_entities（股东）
                    filtered_top_entities = []
                    for entity in data_for_mermaid["top_entities"]:
                        if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                            filtered_top_entities.append(entity)
                    
                    # 过滤subsidiaries（子公司）
                    filtered_subsidiaries = []
                    for subsidiary in data_for_mermaid["subsidiaries"]:
                        if subsidiary.get("name", "") not in st.session_state.get("hidden_entities", []):
                            filtered_subsidiaries.append(subsidiary)
                    
                    # 添加合并后的实体
                    for merged in st.session_state.get("merged_entities", []):
                        if any(e["type"] == "shareholder" for e in merged["entities"]):
                            filtered_top_entities.append({
                                "name": merged["merged_name"],
                                "type": "company",
                                "percentage": merged["total_percentage"]
                            })
                        else:
                            filtered_subsidiaries.append({
                                "name": merged["merged_name"],
                                "percentage": merged["total_percentage"]
                            })
                    
                    data_for_mermaid["top_entities"] = filtered_top_entities
                    data_for_mermaid["subsidiaries"] = filtered_subsidiaries
                    
                    # 过滤all_entities
                    filtered_all_entities = []
                    for entity in data_for_mermaid["all_entities"]:
                        if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                            filtered_all_entities.append(entity)
                    
                    # 添加合并后的实体到all_entities
                    for merged in st.session_state.get("merged_entities", []):
                        filtered_all_entities.append({
                            "name": merged["merged_name"],
                            "type": "company"
                        })
                    
                    data_for_mermaid["all_entities"] = filtered_all_entities
                    
                    # 过滤entity_relationships，移除涉及被隐藏实体的关系
                    filtered_relationships = []
                    for rel in data_for_mermaid["entity_relationships"]:
                        from_entity = rel.get('from', rel.get('parent', ''))
                        to_entity = rel.get('to', rel.get('child', ''))
                        if (from_entity not in st.session_state.get("hidden_entities", []) and 
                            to_entity not in st.session_state.get("hidden_entities", [])):
                            filtered_relationships.append(rel)
                    
                    # 只使用手动配置的关系，不自动生成
                    # 但子公司关系需要自动生成（核心公司 -> 子公司）
                    core_company = data_for_mermaid.get("core_company", "")
                    subsidiaries = data_for_mermaid.get("subsidiaries", [])
                    
                    if core_company and subsidiaries:
                        # 创建现有关系的键集合，避免重复
                        existing_relationships = set()
                        for rel in filtered_relationships:
                            from_e = rel.get("from", rel.get("parent", ""))
                            to_e = rel.get("to", rel.get("child", ""))
                            existing_relationships.add(f"{from_e}_{to_e}")
                        
                        # 为每个子公司添加与核心公司的关系
                        for subsidiary in subsidiaries:
                            subsidiary_name = subsidiary.get("name", "")
                            percentage = subsidiary.get("percentage", 0)
                            
                            if (subsidiary_name and 
                                subsidiary_name not in st.session_state.get("hidden_entities", []) and 
                                percentage > 0):
                                
                                relationship_key = f"{core_company}_{subsidiary_name}"
                                
                                # 如果关系不存在，则添加
                                if relationship_key not in existing_relationships:
                                    filtered_relationships.append({
                                        "parent": core_company,
                                        "child": subsidiary_name,
                                        "percentage": percentage,
                                        "relationship_type": "控股",
                                        "description": f"持股{percentage}%"
                                    })
                                    existing_relationships.add(relationship_key)
                    
                    data_for_mermaid["entity_relationships"] = filtered_relationships
                
                # 生成Mermaid代码
                with st.spinner("正在生成预览图表..."):
                    # 🔍 调试信息：显示传递给Mermaid的数据
                    st.write("🔍 调试信息 - 传递给Mermaid的数据:")
                    st.write(f"top_entities: {data_for_mermaid['top_entities']}")
                    st.write(f"entity_relationships: {data_for_mermaid['entity_relationships']}")
                    st.write(f"control_relationships: {data_for_mermaid['control_relationships']}")
                    
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
                        """从顶级实体列表和合并实体中获取指定实体的持股比例"""
                        # 首先检查top_level_entities
                        for entity in st.session_state.equity_data["top_level_entities"]:
                            if entity["name"] == entity_name and "percentage" in entity:
                                return entity["percentage"]
                        
                        # 然后检查合并实体
                        if st.session_state.get("merged_entities"):
                            for merged in st.session_state.merged_entities:
                                if merged["merged_name"] == entity_name:
                                    return merged["total_percentage"]
                        
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
                        # 确保修改的百分比值不小于0.01
                        safe_modified_percentage = max(st.session_state.modified_percentage, 0.01) if st.session_state.modified_percentage > 0 else 51.0
                        st.session_state.modified_percentage = st.number_input(
                            "修改持股比例 (%)", 
                            min_value=0.01, 
                            max_value=100.0, 
                            value=safe_modified_percentage,
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
                
                # AI股权结构分析报告 - 移动到添加股权关系tab中
                st.markdown("---")
                st.subheader("📊 AI股权结构分析报告")
                
                # 分析功能区域 - 默认折叠
                with st.expander("🔍 股权结构分析设置", expanded=False):
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
                                        percentage_match = re.search(r'\d+(?:\.\d+)?', rel.get("description", ""))
                                        percentage = float(percentage_match.group()) if percentage_match else 0
                                        shareholders_set.add((rel.get("from", ""), percentage))
                                
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
                    
                    # 获取顶级实体数量
                    top_level_entities = equity_data.get("top_level_entities", [])
                    total_entities = len(top_level_entities)
                    total_relationships = len(entity_relationships)
                    total_control_relationships = len(control_relationships)
                    
                    st.info(f"当前数据统计：实体数量 {total_entities} 个，股权关系 {total_relationships} 条，控制关系 {total_control_relationships} 条")
                
                # 显示分析报告
                if "analysis_data" in st.session_state and st.session_state.analysis_data:
                    st.markdown("### 🔍 分析结果已生成")
                    st.info("请使用上方的分析功能区域查看和管理分析结果")
                else:
                    # 没有分析结果时的提示
                    st.info("💡 提示：点击上方的'执行股权结构分析'按钮，对当前股权结构进行AI分析。")
                
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
                            # 🔍 调试信息：显示当前控制关系
                            st.write(f"🔍 调试信息: 当前control_relationships数量: {len(st.session_state.equity_data['control_relationships'])}")
                            st.write("🔍 调试信息: 当前所有control_relationships:")
                            for idx, rel in enumerate(st.session_state.equity_data["control_relationships"]):
                                parent = rel.get("parent", rel.get("from", ""))
                                child = rel.get("child", rel.get("to", ""))
                                st.write(f"  {idx}: {parent} ⤳ {child}")
                            
                            # 检查关系是否已存在
                            exists = any(
                                (r.get("parent", r.get("from")) == controller and r.get("child", r.get("to")) == controlled)
                                for r in st.session_state.equity_data["control_relationships"]
                            )
                            
                            st.write(f"🔍 调试信息: 尝试添加控制关系: {controller} ⤳ {controlled}")
                            st.write(f"🔍 调试信息: 关系是否已存在: {exists}")
                            
                            if not exists:
                                # 正常添加控制关系
                                st.session_state.equity_data["control_relationships"].append({
                                    "parent": controller,
                                    "child": controlled,
                                    "relationship_type": "实际控制",
                                    "description": description or f"{controller}是{controlled}的实际控制人"
                                })
                                st.success(f"✅ 已添加控制关系: {controller} ⤳ {controlled}")
                                st.rerun()
                            else:
                                st.error(f"❌ 该控制关系已存在: {controller} ⤳ {controlled}")
                                st.info("💡 提示: 如果您想添加不同的控制关系，请选择不同的控制人或被控制实体")
                        
# 步骤4: 股权合并
elif st.session_state.current_step == "merge_entities":
    st.subheader("🔀 股权合并")
    
    st.markdown("""
    本功能可以将小比例股东或子公司合并为一个实体（如"其他股东"），让图表更简洁清晰。
    - 原始数据会保留，只是在图表中不显示
    - 可以随时撤销合并
    """)
    
    # 获取所有可合并的实体（从top_level_entities和subsidiaries中提取）
    def get_mergeable_entities():
        """获取可合并的实体列表（包含持股比例）"""
        entities_list = []
        
        # 从top_level_entities中提取股东
        for entity in st.session_state.equity_data.get("top_level_entities", []):
            name = entity.get("name", "")
            percentage = entity.get("percentage", 0)
            if name and name != st.session_state.equity_data.get("core_company", ""):
                entities_list.append({
                    "name": name,
                    "type": "shareholder",
                    "percentage": percentage,
                    "source": "top_level_entities"
                })
        
        # 从subsidiaries中提取子公司
        for subsidiary in st.session_state.equity_data.get("subsidiaries", []):
            name = subsidiary.get("name", "")
            percentage = subsidiary.get("percentage", 0)
            if name:
                entities_list.append({
                    "name": name,
                    "type": "subsidiary", 
                    "percentage": percentage,
                    "source": "subsidiaries"
                })
        
        # 按持股比例排序
        entities_list.sort(key=lambda x: x["percentage"])
        return entities_list
    
    # 获取可合并实体列表
    mergeable_entities = get_mergeable_entities()
    
    if not mergeable_entities:
        st.info("暂无可合并的实体。请先在「顶层实体」和「子公司」中添加实体。")
        if st.button("返回添加实体", type="primary"):
            st.session_state.current_step = "top_entities"
            st.rerun()
    else:
        # 显示当前合并状态
        if st.session_state.merged_entities:
            st.success(f"✅ 当前已有 {len(st.session_state.merged_entities)} 个合并实体")
            
            # 显示已合并实体详情
            with st.expander("查看已合并实体", expanded=True):
                for merged in st.session_state.merged_entities:
                    st.markdown(f"**{merged['merged_name']}** (合并了 {len(merged['entities'])} 个实体，总计: {merged['total_percentage']:.2f}%)")
                    st.caption("包含: " + ", ".join([e['name'] for e in merged['entities']]))
                    
                    # 撤销合并按钮
                    if st.button(f"撤销合并: {merged['merged_name']}", key=f"undo_{merged['merged_name']}"):
                        # 从隐藏列表中移除这些实体
                        for entity in merged['entities']:
                            if entity['name'] in st.session_state.hidden_entities:
                                st.session_state.hidden_entities.remove(entity['name'])
                        
                        # 移除合并实体
                        st.session_state.merged_entities.remove(merged)
                        st.success("已撤销合并")
                        st.rerun()
        
        st.markdown("---")
        
        # 合并方式选择
        merge_mode = st.radio(
            "选择合并方式",
            ["按阈值自动合并", "手动选择合并"],
            help="按阈值：自动合并小于指定比例的实体；手动选择：自由选择要合并的实体"
        )
        
        if merge_mode == "按阈值自动合并":
            # 阈值选择
            col1, col2 = st.columns([2, 1])
            with col1:
                threshold = st.slider(
                    "合并阈值（持股比例小于此值的实体将被合并）",
                    min_value=0.1,
                    max_value=10.0,
                    value=st.session_state.merge_threshold,
                    step=0.1,
                    format="%.1f%%",
                    help="例如选择1%，则所有持股比例小于1%的股东将被合并"
                )
                st.session_state.merge_threshold = threshold
            
            # 筛选小于阈值的实体
            entities_to_merge = [e for e in mergeable_entities 
                                if e["percentage"] < threshold 
                                and e["name"] not in st.session_state.hidden_entities]
            
            if entities_to_merge:
                st.info(f"📋 找到 {len(entities_to_merge)} 个符合条件的实体（持股比例 < {threshold}%）")
                
                # 预览将被合并的实体
                with st.expander("预览将被合并的实体", expanded=True):
                    for entity in entities_to_merge:
                        st.markdown(f"- **{entity['name']}**: {entity['percentage']:.2f}%")
                
                # 合并后的总比例
                total_percentage = sum(e["percentage"] for e in entities_to_merge)
                st.markdown(f"**合并后总比例**: {total_percentage:.2f}%")
                
                # 自定义合并后名称
                col1, col2 = st.columns([2, 1])
                with col1:
                    # 根据实体类型设置默认名称
                    default_name = "其他股东" if any(e["type"] == "shareholder" for e in entities_to_merge) else "其他子公司"
                    merged_name = st.text_input(
                        "合并后实体名称",
                        value=default_name,
                        help="可以自定义合并后的实体名称"
                    )
                
                # 确认合并按钮
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ 确认合并", type="primary", use_container_width=True):
                        if not merged_name.strip():
                            st.error("请输入合并后的实体名称")
                        else:
                            # 创建合并实体
                            merged_entity = {
                                "merged_name": merged_name,
                                "total_percentage": total_percentage,
                                "entities": entities_to_merge,
                                "merge_type": "threshold",
                                "threshold": threshold
                            }
                            
                            # 添加到合并列表
                            st.session_state.merged_entities.append(merged_entity)
                            
                            # 将原实体添加到隐藏列表
                            for entity in entities_to_merge:
                                if entity["name"] not in st.session_state.hidden_entities:
                                    st.session_state.hidden_entities.append(entity["name"])
                            
                            st.success(f"✅ 已合并 {len(entities_to_merge)} 个实体为 '{merged_name}'")
                            st.rerun()
                
                with col2:
                    if st.button("取消", use_container_width=True):
                        st.info("已取消合并操作")
            else:
                st.warning(f"没有找到持股比例小于 {threshold}% 的实体")
        
        else:  # 手动选择合并
            st.markdown("### 手动选择要合并的实体")
            
            # 显示可选实体列表
            available_entities = [e for e in mergeable_entities 
                                 if e["name"] not in st.session_state.hidden_entities]
            
            if not available_entities:
                st.warning("没有可用的实体进行合并")
            else:
                # 初始化选中状态
                if 'selected_entities_for_merge' not in st.session_state:
                    st.session_state.selected_entities_for_merge = []
                
                # 创建表格形式的实体选择器
                st.markdown("**选择要合并的实体（勾选复选框）：**")
                
                # 创建表格
                import pandas as pd
                
                # 准备表格数据
                table_data = []
                for entity in available_entities:
                    table_data.append({
                        "选择": entity["name"] in st.session_state.selected_entities_for_merge,
                        "实体名称": entity["name"],
                        "类型": "股东" if entity["type"] == "shareholder" else "子公司",
                        "持股比例": f"{entity['percentage']:.2f}%"
                    })
                
                df = pd.DataFrame(table_data)
                
                # 使用st.data_editor创建可编辑的表格
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "选择": st.column_config.CheckboxColumn(
                            "选择",
                            help="勾选要合并的实体",
                            default=False,
                        ),
                        "实体名称": st.column_config.TextColumn(
                            "实体名称",
                            disabled=True,
                        ),
                        "类型": st.column_config.TextColumn(
                            "类型",
                            disabled=True,
                        ),
                        "持股比例": st.column_config.TextColumn(
                            "持股比例",
                            disabled=True,
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="entity_selection_table"
                )
                
                # 更新选中状态
                selected_entities = edited_df[edited_df["选择"] == True]["实体名称"].tolist()
                st.session_state.selected_entities_for_merge = selected_entities
                
                if selected_entities:
                    # 获取选中的实体详情
                    entities_to_merge = [e for e in available_entities if e["name"] in selected_entities]
                    
                    st.markdown("---")
                    st.markdown("### 📋 合并预览")
                    
                    # 预览选中的实体
                    with st.expander("预览选中的实体", expanded=True):
                        for entity in entities_to_merge:
                            st.markdown(f"- **{entity['name']}** ({'股东' if entity['type'] == 'shareholder' else '子公司'}): {entity['percentage']:.2f}%")
                    
                    # 合并后的总比例
                    total_percentage = sum(e["percentage"] for e in entities_to_merge)
                    st.markdown(f"**合并后总比例**: {total_percentage:.2f}%")
                    
                    # 自定义合并后名称
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        # 根据实体类型设置默认名称
                        default_name = "其他股东" if any(e["type"] == "shareholder" for e in entities_to_merge) else "其他子公司"
                        merged_name = st.text_input(
                            "合并后实体名称",
                            value=default_name,
                            key="manual_merge_name",
                            help="可以自定义合并后的实体名称"
                        )
                    
                    # 确认合并按钮
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ 确认合并", type="primary", use_container_width=True, key="manual_merge_confirm"):
                            if not merged_name.strip():
                                st.error("请输入合并后的实体名称")
                            else:
                                # 创建合并实体
                                merged_entity = {
                                    "merged_name": merged_name,
                                    "total_percentage": total_percentage,
                                    "entities": entities_to_merge,
                                    "merge_type": "manual"
                                }
                                
                                # 添加到合并列表
                                st.session_state.merged_entities.append(merged_entity)
                                
                                # 将原实体添加到隐藏列表
                                for entity in entities_to_merge:
                                    if entity["name"] not in st.session_state.hidden_entities:
                                        st.session_state.hidden_entities.append(entity["name"])
                                
                                # 清空选中状态
                                st.session_state.selected_entities_for_merge = []
                                
                                st.success(f"✅ 已合并 {len(entities_to_merge)} 个实体为 '{merged_name}'")
                                st.rerun()
                    
                    with col2:
                        if st.button("取消", use_container_width=True, key="manual_merge_cancel"):
                            st.session_state.selected_entities_for_merge = []
                            st.info("已取消合并操作")
                else:
                    st.info("请在上方表格中勾选要合并的实体")

# 步骤6: 生成图表
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
                st.session_state.current_step = "merge_entities"
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
                    "shareholders": st.session_state.equity_data.get("shareholders", []),
                    "subsidiaries": st.session_state.equity_data["subsidiaries"],
                    "controller": st.session_state.equity_data.get("actual_controller", ""),
                    "top_entities": st.session_state.equity_data["top_level_entities"],
                    "entity_relationships": st.session_state.equity_data["entity_relationships"],
                    "control_relationships": st.session_state.equity_data["control_relationships"],
                    "all_entities": st.session_state.equity_data["all_entities"]
                }
                
                # 🔥 关键修复：过滤掉没有实际关系的股东（与实时预览保持一致）
                # 检查每个top_entity是否在entity_relationships中有对应的关系
                filtered_top_entities = []
                for entity in data_for_mermaid["top_entities"]:
                    entity_name = entity.get("name", "")
                    has_relationship = False
                    
                    # 检查是否有股权关系
                    for rel in data_for_mermaid["entity_relationships"]:
                        from_entity = rel.get('from', rel.get('parent', ''))
                        to_entity = rel.get('to', rel.get('child', ''))
                        if from_entity == entity_name:
                            has_relationship = True
                            break
                    
                    # 检查是否有控制关系
                    if not has_relationship:
                        for rel in data_for_mermaid["control_relationships"]:
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                            if from_entity == entity_name:
                                has_relationship = True
                                break
                    
                    # 🔥 修复：对于正常股东，即使没有显式关系也保留（会自动生成关系）
                    # 只有明确不需要的实体才过滤掉
                    should_filter = False
                    
                    # 检查是否为明确不需要的实体（如空名称、无效数据等）
                    if not entity_name or entity_name.strip() == "":
                        should_filter = True
                        st.write(f"🔍 调试信息: 过滤掉空名称实体")
                    elif entity.get("percentage", 0) <= 0:
                        should_filter = True
                        st.write(f"🔍 调试信息: 过滤掉无持股比例的实体: {entity_name}")
                    else:
                        # 正常股东，保留
                        filtered_top_entities.append(entity)
                        if has_relationship:
                            st.write(f"✅ 保留有关系的股东: {entity_name}")
                        else:
                            st.write(f"✅ 保留正常股东（将自动生成关系）: {entity_name}")
                    
                    if should_filter:
                        st.write(f"❌ 过滤掉无效实体: {entity_name}")
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 🔥 特殊处理：检查是否有被过滤掉的合并实体需要恢复
                st.write(f"🔍 调试信息: 检查是否有被过滤掉的合并实体")
                for entity in st.session_state.equity_data.get("top_level_entities", []):
                    entity_name = entity.get("name", "")
                    if entity_name not in [e["name"] for e in filtered_top_entities]:
                        # 检查是否在合并实体中
                        is_merged_entity = False
                        for merged in st.session_state.get("merged_entities", []):
                            if merged.get("merged_name") == entity_name:
                                is_merged_entity = True
                                st.write(f"🔍 调试信息: 发现被过滤的合并实体: {entity_name}")
                                # 恢复合并实体
                                filtered_top_entities.append(entity)
                                break
                        
                        if not is_merged_entity:
                            st.write(f"🔍 调试信息: 被过滤的非合并实体: {entity_name}")
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 应用合并规则
                st.write(f"🔍 调试信息: 检查合并实体 - merged_entities: {st.session_state.get('merged_entities', [])}")
                if st.session_state.merged_entities:
                    # 过滤top_entities（股东）- 使用已经过滤过的数据
                    merged_filtered_top_entities = []
                    for entity in data_for_mermaid["top_entities"]:
                        if entity.get("name", "") not in st.session_state.hidden_entities:
                            merged_filtered_top_entities.append(entity)
                    
                    # 过滤subsidiaries（子公司）
                    filtered_subsidiaries = []
                    for subsidiary in data_for_mermaid["subsidiaries"]:
                        if subsidiary.get("name", "") not in st.session_state.hidden_entities:
                            filtered_subsidiaries.append(subsidiary)
                    
                    # 添加合并后的实体
                    for merged in st.session_state.merged_entities:
                        # 根据合并实体的类型决定添加到哪个列表
                        if any(e["type"] == "shareholder" for e in merged["entities"]):
                            # 如果包含股东，添加到top_entities
                            merged_filtered_top_entities.append({
                                "name": merged["merged_name"],
                                "type": "company",
                                "percentage": merged["total_percentage"]
                            })
                        else:
                            # 如果只包含子公司，添加到subsidiaries
                            filtered_subsidiaries.append({
                                "name": merged["merged_name"],
                                "percentage": merged["total_percentage"]
                            })
                    
                    data_for_mermaid["top_entities"] = merged_filtered_top_entities
                    data_for_mermaid["subsidiaries"] = filtered_subsidiaries
                    
                    # 过滤all_entities
                    filtered_all_entities = []
                    for entity in data_for_mermaid["all_entities"]:
                        if entity.get("name", "") not in st.session_state.hidden_entities:
                            filtered_all_entities.append(entity)
                    
                    # 添加合并后的实体到all_entities
                    for merged in st.session_state.merged_entities:
                        filtered_all_entities.append({
                            "name": merged["merged_name"],
                            "type": "company"
                        })
                    
                    data_for_mermaid["all_entities"] = filtered_all_entities
                    
                    # 过滤entity_relationships，移除涉及被隐藏实体的关系
                    filtered_relationships = []
                    for rel in data_for_mermaid["entity_relationships"]:
                        from_entity = rel.get('from', rel.get('parent', ''))
                        to_entity = rel.get('to', rel.get('child', ''))
                        if (from_entity not in st.session_state.hidden_entities and 
                            to_entity not in st.session_state.hidden_entities):
                            filtered_relationships.append(rel)
                    
                    # 只使用手动配置的关系，不自动生成
                    # 但子公司关系需要自动生成（核心公司 -> 子公司）
                    core_company = data_for_mermaid.get("core_company", "")
                    subsidiaries = data_for_mermaid.get("subsidiaries", [])
                    
                    if core_company and subsidiaries:
                        # 创建现有关系的键集合，避免重复
                        existing_relationships = set()
                        for rel in filtered_relationships:
                            from_e = rel.get("from", rel.get("parent", ""))
                            to_e = rel.get("to", rel.get("child", ""))
                            existing_relationships.add(f"{from_e}_{to_e}")
                        
                        # 为每个子公司添加与核心公司的关系
                        for subsidiary in subsidiaries:
                            subsidiary_name = subsidiary.get("name", "")
                            percentage = subsidiary.get("percentage", 0)
                            
                            if (subsidiary_name and 
                                subsidiary_name not in st.session_state.hidden_entities and 
                                percentage > 0):
                                
                                relationship_key = f"{core_company}_{subsidiary_name}"
                                
                                # 如果关系不存在，则添加
                                if relationship_key not in existing_relationships:
                                    filtered_relationships.append({
                                        "parent": core_company,
                                        "child": subsidiary_name,
                                        "percentage": percentage,
                                        "relationship_type": "控股",
                                        "description": f"持股{percentage}%"
                                    })
                                    existing_relationships.add(relationship_key)
                    
                    data_for_mermaid["entity_relationships"] = filtered_relationships
                    
                    # 过滤control_relationships，移除涉及被隐藏实体的控制关系
                    filtered_control_relationships = []
                    for rel in data_for_mermaid["control_relationships"]:
                        from_entity = rel.get('from', rel.get('parent', ''))
                        to_entity = rel.get('to', rel.get('child', ''))
                        if (from_entity not in st.session_state.hidden_entities and 
                            to_entity not in st.session_state.hidden_entities):
                            filtered_control_relationships.append(rel)
                    data_for_mermaid["control_relationships"] = filtered_control_relationships
                
                # 生成Mermaid代码
                with st.spinner("正在生成图表..."):
                    # 🔍 调试信息：显示传递给Mermaid的数据
                    st.write("🔍 调试信息 - 传递给Mermaid的数据:")
                    st.write(f"top_entities: {data_for_mermaid['top_entities']}")
                    st.write(f"entity_relationships: {data_for_mermaid['entity_relationships']}")
                    st.write(f"control_relationships: {data_for_mermaid['control_relationships']}")
                    
                    st.session_state.mermaid_code = generate_mermaid_diagram(data_for_mermaid)
                    
                st.success("图表生成成功！")
        except Exception as e:
            st.error(f"生成图表时出错: {str(e)}")
    
    # 显示图表（如果已生成）
    if st.session_state.mermaid_code:
        st.markdown("### 📊 股权结构图表")
        
        # 添加图表类型选择器
        chart_type = st.radio(
            "选择图表类型：",
            options=["Mermaid图表", "交互式HTML图表"],
            horizontal=True,
            help="Mermaid图表：传统流程图样式；交互式HTML图表：可交互的专业层级结构图",
            key="chart_type_selector"
        )
        
        st.markdown("---")
        
        # 根据选择显示不同的图表
        if chart_type == "Mermaid图表":
            # 原有的Mermaid图表显示
            # 图表操作按钮
            col_op1, col_op2, col_op3 = st.columns(3)
            
            with col_op1:
                # 全屏查看按钮 - 使用增强版HTML
                if st.button("🔍 全屏编辑图表", type="primary", use_container_width=True, key="fullscreen_edit_button"):
                    # 获取Mermaid代码内容
                    mermaid_code_content = st.session_state.mermaid_code
                    
                    # 创建HTML模板，使用raw字符串避免转义问题
                    html_template = r'''
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Mermaid 预览器（双击同步修改代码）</title>
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      height: 100vh;
      overflow: hidden;
    }
    .header {
      padding: 12px 20px;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
      font-size: 16px;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .controls {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .controls input {
      padding: 4px 8px;
      font-size: 14px;
      border: 1px solid #ccc;
      border-radius: 4px;
    }
    .controls button {
      padding: 4px 10px;
      font-size: 14px;
      cursor: pointer;
    }
    .container {
      display: flex;
      height: calc(100vh - 80px);
      overflow: hidden;
    }
    #editor {
      height: 100%;
      min-width: 300px;
      max-width: 70%;
      display: flex;
      flex-direction: column;
      background: #fff;
    }
    #preview-container {
      flex: 1;
      min-width: 300px;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: white;
      overflow: hidden;
    }
    #editor textarea {
      flex: 1;
      padding: 14px;
      font-family: 'Consolas', monospace;
      font-size: 13px;
      line-height: 1.4;
      border: none;
      outline: none;
      resize: none;
      background: #fff;
      overflow: auto;
    }
    #preview {
      flex: 1;
      padding: 20px;
      overflow: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
      position: relative;
      cursor: default;
    }
    #preview svg {
      max-width: 100%;
      max-height: 100%;
      cursor: pointer;
    }
    #preview svg text {
      cursor: pointer;
      user-select: none;
    }
    #preview svg text:hover {
      fill: #1976d2 !important;
      font-weight: bold !important;
    }
    #preview.dragging {
      cursor: grab;
    }
    #preview.dragging svg {
      cursor: grabbing !important;
    }
    #resizer {
      width: 6px;
      background: #e0e0e0;
      cursor: col-resize;
      user-select: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #resizer:hover { background: #ccc; }
    #resizer::after {
      content: "⋮⋮";
      color: #999;
      font-size: 14px;
      writing-mode: vertical-rl;
    }
    .error {
      padding: 10px;
      color: #d32f2f;
      background: #ffebee;
      font-family: monospace;
      white-space: pre-wrap;
    }
    .fullscreen #editor,
    .fullscreen #resizer {
      display: none;
    }
    .fullscreen .container {
      height: calc(100vh - 60px);
    }
    .fullscreen #preview-container {
      position: relative;
    }
    .zoom-controls {
      position: absolute;
      bottom: 20px;
      right: 20px;
      background-color: white;
      border-radius: 25px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      padding: 5px;
      z-index: 1000; /* 提高层级确保在全屏模式下可见 */
    }
    .zoom-btn {
      background-color: #f8f9fa;
      border: none;
      border-radius: 50%;
      width: 35px;
      height: 35px;
      margin: 0 5px;
      font-size: 18px;
      cursor: pointer;
      transition: background-color 0.3s;
    }
    .zoom-btn:hover {
      background-color: #e9ecef;
    }
    .zoom-value {
      display: inline-block;
      line-height: 35px;
      padding: 0 10px;
      color: #495057;
      font-size: 14px;
    }
    .close-btn {
      background-color: #dc3545;
      color: white;
      border: none;
      padding: 4px 10px;
      font-size: 14px;
      cursor: pointer;
      border-radius: 4px;
    }
    .close-btn:hover {
      background-color: #c82333;
      color: white;
    }
  </style>
</head>
<body>
  <div class="header">
    📊 Mermaid 预览器（双击节点同步修改代码）
    <div class="controls">
        <input type="text" id="keywordInput" placeholder="输入关键词高亮">
        <button id="highlightBtn">高亮</button>
        <button id="clearBtn">清除高亮</button>
        <button id="copyCodeBtn">复制代码</button>
        <button id="fullscreenBtn">全屏预览</button>
        <button id="downloadPngBtn">下载PNG</button>
        <button class="close-btn" onclick="window.close()">关闭页面</button>
      </div>
  </div>
  <div class="container">
    <div id="editor">
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; background: #f8f9fa; border-bottom: 1px solid #e0e0e0;">
        <span style="font-size: 12px; color: #666;">Mermaid 代码</span>
      </div>
      <textarea id="source" spellcheck="false">CODE_PLACEHOLDER</textarea>
    </div>
    <div id="resizer"></div>
    <div id="preview-container">
      <div id="preview"></div>
      <div class="zoom-controls">
        <button class="zoom-btn" onclick="zoomDiagram(-0.1)">-</button>
        <span class="zoom-value" id="zoom-value">100%</span>
        <button class="zoom-btn" onclick="zoomDiagram(0.1)">+</button>
        <button class="zoom-btn" onclick="resetZoom()">⟲</button>
      </div>
    </div>
  </div>

  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';

    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'antiscript',
      flowchart: {
        useMaxWidth: false,
        htmlLabels: false,
        curve: 'linear'
      },
      fontFamily: '"Segoe UI", sans-serif'
    });

    const source = document.getElementById('source');
    const preview = document.getElementById('preview');
    const editor = document.getElementById('editor');
    const resizer = document.getElementById('resizer');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const keywordInput = document.getElementById('keywordInput');
    const highlightBtn = document.getElementById('highlightBtn');
    const clearBtn = document.getElementById('clearBtn');

    let currentSvgEl = null;
    let isFullscreen = false;
    let scale = 1;
    let translateX = 0;
    let translateY = 0;

    editor.style.width = '30%';

    // 工具函数
    function escapeRegExp(string) {
      // 简单的转义函数，避免复杂的正则表达式
      const specialChars = ['.', '*', '+', '?', '^', '$', '{', '}', '(', ')', '[', ']', '\\'];
      let result = string;
      for (const char of specialChars) {
        result = result.replace(new RegExp('\\' + char, 'g'), '\\' + char);
      }
      return result;
    }

    // 通过 nodeId + oldText 精准替换
    function updateMermaidCodeByNodeId(nodeId, oldText, newText) {
      const code = source.value;
      const escapedOld = escapeRegExp(oldText);
      const escapedNodeId = escapeRegExp(nodeId);
      
      // 构建简单的模式，避免复杂的正则表达式
      const patterns = [
        escapedNodeId + '\\$\\$"' + escapedOld + '"',
        escapedNodeId + '\\$"' + escapedOld + '\\$',
        escapedNodeId + '\\{"' + escapedOld + '"\\}'
      ];

      for (const pattern of patterns) {
        try {
          const regex = new RegExp(pattern, 'g');
          const newCode = code.replace(regex, (match) => {
            return match.replace(escapedOld, newText);
          });
          if (newCode !== code) {
            source.value = newCode;
            render();
            return true;
          }
        } catch (e) {
          // 如果正则表达式失败，跳过
        }
      }

      // 宽松匹配 - 使用简单的字符串替换
      if (code.includes(escapedNodeId) && code.includes(escapedOld)) {
        let newCode = code;
        let replaced = false;
        // 尝试在包含nodeId的行中替换oldText
        const lines = code.split('\\n');
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].includes(escapedNodeId) && lines[i].includes(escapedOld)) {
            // 只替换引号内的内容
            const parts = lines[i].split(/[\"\\']/);
            for (let j = 1; j < parts.length; j += 2) {
              if (parts[j].includes(oldText)) {
                parts[j] = parts[j].replace(oldText, newText);
                replaced = true;
                break;
              }
            }
            lines[i] = parts.join('"');
            if (replaced) break;
          }
        }
        newCode = lines.join('\\n');
        if (newCode !== code && replaced) {
          source.value = newCode;
          render();
          return true;
        }
      }

      return false;
    }

    // 通过全文本匹配
    function updateMermaidCodeByText(oldText, newText) {
      const code = source.value;
      // 统计oldText出现的次数
      const count = (code.match(new RegExp('"' + escapeRegExp(oldText) + '"', 'g')) || []).length;
      if (count !== 1) {
        return false;
      }

      // 简单的字符串替换
      const newCode = code.replace('"' + oldText + '"', '"' + newText + '"');
      if (newCode !== code) {
        source.value = newCode;
        render();
        return true;
      }
      return false;
    }

    // 渲染函数
    async function render() {
      const code = source.value.trim();
      preview.innerHTML = '';

      if (!code) {
        preview.textContent = '请输入 Mermaid 代码...';
        currentSvgEl = null;
        return;
      }

      try {
        const { svg: rawSvg } = await mermaid.render('chart', code);
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(rawSvg, 'image/svg+xml');
        currentSvgEl = svgDoc.documentElement;

        preview.innerHTML = '';
        preview.appendChild(currentSvgEl);

        applyTransform();

        // 绑定双击事件
        const texts = currentSvgEl.querySelectorAll('text');
        texts.forEach(text => {
          text.style.cursor = 'pointer';

          // 提取 nodeId
          let nodeId = '';
          let g = text.closest('g');
          if (g && g.id) {
            // 简化的nodeId提取，避免复杂的正则表达式
            const id = g.id;
            if (id.startsWith('flowchart-')) {
              // 移除'flowchart-'前缀和可能的数字后缀
              nodeId = id.replace('flowchart-', '').replace(/-[0-9]+$/, '');
            }
          }
          text.setAttribute('data-node-id', nodeId || 'unknown');
          text.setAttribute('data-original-text', text.textContent || '');

          const onDblClick = () => {
            const oldText = text.getAttribute('data-original-text') || text.textContent;
            const nodeId = text.getAttribute('data-node-id');
            const newText = prompt('请输入新节点文字：', oldText);
            if (newText === null || newText === oldText) return;

            // 更新 SVG
            text.textContent = newText;
            text.setAttribute('data-original-text', newText);
            const rect = text.closest('g')?.querySelector('rect');
            if (rect) {
              const x = parseFloat(rect.getAttribute('x')) || 0;
              const width = parseFloat(rect.getAttribute('width')) || 0;
              text.setAttribute('x', x + width / 2);
              text.setAttribute('text-anchor', 'middle');
            }

            // 尝试更新代码
            let updated = false;
            if (nodeId && nodeId !== 'unknown') {
              updated = updateMermaidCodeByNodeId(nodeId, oldText, newText);
            }
            if (!updated) {
              updated = updateMermaidCodeByText(oldText, newText);
            }
            if (!updated) {
              alert('未能自动更新代码，请手动修改左侧 Mermaid 内容。');
            }
          };

          text.removeEventListener('dblclick', onDblClick);
          text.addEventListener('dblclick', onDblClick);
        });

      } catch (e) {
        console.error(e);
        preview.innerHTML = '<div class="error">❌ ' + (e.message || e) + '</div>';
        currentSvgEl = null;
      }
    }

    function applyTransform() {
      if (currentSvgEl) {
        currentSvgEl.style.transformOrigin = '0 0';
        currentSvgEl.style.transform = 'scale(' + scale + ') translate(' + translateX + 'px, ' + translateY + 'px)';
        document.getElementById('zoom-value').textContent = Math.round(scale * 100) + '%';
      }
    }

    // 复制代码功能
    function copyCode() {
      const textarea = document.getElementById('source');
      
      // 保存当前的选择范围
      const startPos = textarea.selectionStart;
      const endPos = textarea.selectionEnd;
      
      // 选择所有文本
      textarea.focus();
      textarea.setSelectionRange(0, textarea.value.length);
      
      try {
        // 尝试使用现代的Clipboard API
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(textarea.value).then(() => {
            showNotification('✅ 代码已复制到剪贴板', 'success');
          }).catch((err) => {
            console.error('复制失败:', err);
            showNotification('❌ 复制失败，请手动选择复制', 'error');
          });
        } else {
          // 回退到传统方法
          const successful = document.execCommand('copy');
          if (successful) {
            showNotification('✅ 代码已复制到剪贴板', 'success');
          } else {
            showNotification('❌ 复制失败，请手动选择复制', 'error');
          }
        }
      } catch (err) {
        console.error('复制失败:', err);
        showNotification('❌ 复制失败，请手动选择复制', 'error');
      } finally {
        // 恢复之前的选择范围
        setTimeout(() => {
          textarea.focus();
          textarea.setSelectionRange(startPos, endPos);
        }, 100);
      }
    }

    // 通知显示函数
    function showNotification(message, type = 'info') {
      // 检查是否已存在通知元素，如有则移除
      const existingNotification = document.getElementById('notification');
      if (existingNotification) {
        existingNotification.remove();
      }
      
      // 创建通知元素
      const notification = document.createElement('div');
      notification.id = 'notification';
      notification.textContent = message;
      notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: slideIn 0.3s ease-out;
        transition: opacity 0.3s ease;
      `;
      
      // 设置不同类型的样式
      if (type === 'success') {
        notification.style.backgroundColor = '#28a745';
        notification.style.color = 'white';
      } else if (type === 'error') {
        notification.style.backgroundColor = '#dc3545';
        notification.style.color = 'white';
      } else {
        notification.style.backgroundColor = '#17a2b8';
        notification.style.color = 'white';
      }
      
      // 添加动画样式
      const style = document.createElement('style');
      style.textContent = `
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `;
      document.head.appendChild(style);
      
      // 添加通知到页面
      document.body.appendChild(notification);
      
      // 3秒后自动移除通知
      setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
          if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
          }
        }, 300);
      }, 3000);
    }

    // 高亮函数 - 在代码区域查找文字
    function highlightKeyword(keyword) {
      const textarea = document.getElementById('source');
      
      if (!keyword.trim()) {
        // 如果关键字为空，清除高亮并显示提示
        clearHighlight();
        alert('请输入要查找的关键词');
        return;
      }
      
      // 清除之前的选择
      textarea.focus();
      
      // 获取文本内容
      const text = textarea.value;
      const keywordLower = keyword.toLowerCase();
      const textLower = text.toLowerCase();
      
      // 查找所有匹配项
      let matches = [];
      let pos = 0;
      while (pos < textLower.length) {
        const index = textLower.indexOf(keywordLower, pos);
        if (index === -1) break;
        matches.push({start: index, end: index + keyword.length});
        pos = index + 1;
      }
      
      if (matches.length === 0) {
        alert(`未找到关键词：${keyword}`);
        return;
      }
      
      // 高亮第一个匹配项
      textarea.setSelectionRange(matches[0].start, matches[0].end);
      
      // 滚动到可见区域
      textarea.scrollTop = Math.max(0, 
        (matches[0].start / text.length) * textarea.scrollHeight - textarea.clientHeight / 2);
      
      // 如果有多个匹配项，显示找到的数量
      if (matches.length > 1) {
        alert(`找到 ${matches.length} 处匹配，已选中第一个`);
      }
    }
    
    function clearHighlight() {
      const textarea = document.getElementById('source');
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }

    // 拖拽平移逻辑
    let isDragging = false;
    let startX, startY, startTranslateX, startTranslateY;

    preview.addEventListener('mousedown', function(e) {
      // 移除全屏模式限制，允许在任何模式下拖拽
      if (e.target.tagName === 'text') return;

      isDragging = true;
      preview.classList.add('dragging');
      startX = e.clientX;
      startY = e.clientY;
      startTranslateX = translateX;
      startTranslateY = translateY;
      e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
      // 移除全屏模式限制，允许在任何模式下拖拽
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      translateX = startTranslateX + dx;
      translateY = startTranslateY + dy;
      applyTransform();
    });

    document.addEventListener('mouseup', function() {
      if (isDragging) {
        isDragging = false;
        preview.classList.remove('dragging');
      }
    });

    // 下载PNG功能
    function downloadPNG() {
      if (!currentSvgEl) {
        alert('没有可下载的图表，请先生成图表');
        return;
      }

      try {
        // 克隆SVG元素以避免修改原始视图
        const svgClone = currentSvgEl.cloneNode(true);
        
        // 移除可能导致问题的transform属性
        svgClone.removeAttribute('style');
        
        // 设置SVG尺寸
        const svgWidth = parseInt(svgClone.getAttribute('width') || '800');
        const svgHeight = parseInt(svgClone.getAttribute('height') || '600');
        svgClone.setAttribute('width', svgWidth);
        svgClone.setAttribute('height', svgHeight);
        
        // 创建内联SVG字符串
        const serializer = new XMLSerializer();
        const svgString = serializer.serializeToString(svgClone);
        
        // 创建Blob并转换为DataURL
        const blob = new Blob([svgString], {type: 'image/svg+xml'});
        const url = URL.createObjectURL(blob);
        
        // 创建Image对象加载SVG
        const img = new Image();
        img.onload = function() {
          // 创建Canvas
          const canvas = document.createElement('canvas');
          canvas.width = svgWidth;
          canvas.height = svgHeight;
          const ctx = canvas.getContext('2d');
          
          // 设置白色背景
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          
          // 绘制图像
          ctx.drawImage(img, 0, 0);
          
          // 转换为PNG并下载
          canvas.toBlob(function(blob) {
            const downloadLink = document.createElement('a');
            downloadLink.download = '股权结构图_' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.png';
            downloadLink.href = URL.createObjectURL(blob);
            downloadLink.click();
            
            // 清理
            URL.revokeObjectURL(url);
            URL.revokeObjectURL(downloadLink.href);
          }, 'image/png');
        };
        
        img.onerror = function() {
          alert('图表转换失败，请重试');
          URL.revokeObjectURL(url);
        };
        
        img.crossOrigin = 'anonymous';
        img.src = url;
        
      } catch (error) {
        console.error('下载PNG失败:', error);
        alert('下载PNG失败，请重试');
      }
    }

    // 缩放函数
    function zoomDiagram(delta) {
      scale = Math.max(0.1, Math.min(3.0, scale + delta));
      applyTransform();
    }

    function resetZoom() {
      scale = 1;
      translateX = 0;
      translateY = 0;
      applyTransform();
    }

    // 事件绑定
    let timer;
    source.addEventListener('input', function() {
      clearTimeout(timer);
      timer = setTimeout(render, 400);
    });

    highlightBtn.addEventListener('click', function() {
      highlightKeyword(keywordInput.value);
    });

    clearBtn.addEventListener('click', function() {
      clearHighlight();
    });

    // 复制代码按钮事件
    document.getElementById('copyCodeBtn').addEventListener('click', copyCode);

    keywordInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') highlightKeyword(keywordInput.value);
    });

    // 下载PNG按钮事件
    document.getElementById('downloadPngBtn').addEventListener('click', downloadPNG);

    // 拖拽分割条
    let isResizing = false;
    resizer.addEventListener('mousedown', function(e) {
      isResizing = true;
      document.body.style.cursor = 'col-resize';
      e.preventDefault();
    });
    document.addEventListener('mousemove', function(e) {
      if (!isResizing) return;
      const containerRect = document.querySelector('.container').getBoundingClientRect();
      let leftPercent = ((e.clientX - containerRect.left) / containerRect.width) * 100;
      leftPercent = Math.max(10, Math.min(70, leftPercent));
      editor.style.width = leftPercent + '%';
      render();
    });
    document.addEventListener('mouseup', function() {
      isResizing = false;
      document.body.style.cursor = 'default';
    });

    // 全屏切换
    fullscreenBtn.addEventListener('click', function() {
      document.body.classList.toggle('fullscreen');
      isFullscreen = !isFullscreen;
      fullscreenBtn.textContent = isFullscreen ? '退出全屏' : '全屏预览';
      render();

      if (!isFullscreen) {
        translateX = 0;
        translateY = 0;
        scale = 1;
        applyTransform();
      }
    });

    // Ctrl + 滚轮缩放
    preview.addEventListener('wheel', function(e) {
      if (e.ctrlKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        scale = Math.max(0.2, Math.min(scale + delta, 3));
        applyTransform();
      }
    }, { passive: false });

    // 初始渲染
    render();
  </script>
</body>
</html>'''
                    
                    # 转换代码占位符
                    html_content = html_template.replace("CODE_PLACEHOLDER", mermaid_code_content)
                    
                    # 保存到临时文件
                    import tempfile
                    import os
                    import webbrowser
                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(temp_dir, 'equity_mermaid_preview.html')
                    with open(temp_file_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # 在浏览器中打开
                    webbrowser.open_new_tab(temp_file_path)
                    
                    # 显示操作提示
                    st.info("🔍 已在新标签页打开全屏编辑器，可进行代码编辑和图表预览")
            
            with col_op2:
                # 下载Mermaid代码按钮
                if st.button("📥 下载Mermaid代码", use_container_width=True, key="download_mermaid_btn"):
                    st.download_button(
                        label="保存Mermaid代码",
                        data=st.session_state.mermaid_code,
                        file_name="股权结构.mmd",
                        mime="text/plain",
                        use_container_width=True,
                        key="download_mermaid"
                    )
            
            with col_op3:
                # 这里曾经有复制代码到剪贴板按钮，已移除
                pass

            # 显示图表
            st_mermaid(st.session_state.mermaid_code, key="unique_mermaid_chart")
            
            # 提供下载选项
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.download_button(
                    label="下载 JSON 数据",
                    data=json.dumps(st.session_state.equity_data, ensure_ascii=False, indent=2),
                    file_name="equity_structure.json",
                    mime="application/json",
                    key="mermaid_download_json"
                ):
                    st.success("JSON文件已下载")
            
            with col2:
                if st.download_button(
                    label="下载 Mermaid 代码",
                    data=st.session_state.mermaid_code,
                    file_name="equity_structure.mmd",
                    mime="text/plain",
                    key="mermaid_download_mmd"
                ):
                    st.success("Mermaid文件已下载")
        else:
            # 新的交互式HTML图表
            _display_visjs_chart()
    
    # 返回编辑按钮
    if st.button("返回编辑", type="secondary", key="return_to_edit"):
        # 验证数据后再跳转
        data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
        if data_valid:
            st.session_state.current_step = "relationships"
            st.rerun()
        else:
            st.error("数据验证失败，无法返回编辑。请检查数据后重试。")

# 底部导航按钮已移至顶部全局导航栏


# åº•éƒ¨å¯¼èˆªæŒ‰é’®å·²ç§»è‡³é¡¶éƒ¨å…¨å±€å¯¼èˆªæ 
