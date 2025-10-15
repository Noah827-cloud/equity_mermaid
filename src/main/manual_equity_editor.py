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
import time
import streamlit as st
from datetime import datetime
from streamlit_mermaid import st_mermaid
import pathlib
from src.utils.state_persistence import make_snapshot, apply_snapshot, autosave, find_autosave

# --- Excel 导入辅助：登记状态判断 ---
def _is_inactive_status(value: str) -> bool:
    """登记状态是否为注销/吊销（含变体）。"""
    if value is None:
        return False
    s = str(value).strip()
    if not s:
        return False
    for kw in ("注销", "吊销"):
        if kw in s:
            return True
    return False

def _find_status_column(df, analysis_result):
    """优先从智能识别结果中找 registration_status，其次按列名关键词匹配。"""
    try:
        detected = (analysis_result or {}).get('detected_columns', {})
        for col, col_type in detected.items():
            if col_type == 'registration_status' and col in df.columns:
                return col
    except Exception:
        pass
    try:
        for c in df.columns:
            cs = str(c)
            if any(k in cs for k in ("登记状态", "经营状态", "状态", "注册状态")):
                return c
    except Exception:
        pass
    return None


def _infer_child_from_filename(file_name: str) -> str:
    """Infer child entity name from shareholder file naming patterns."""
    if not file_name:
        return ""
    import re as _re

    base = os.path.splitext(file_name)[0].strip()
    if not base:
        return ""

    # 🔥 移除序号前缀（如 "2_", "4_" 等）
    base = _re.sub(r'^\d+_', '', base)

    # 🔥 移除时间戳后缀（如 "-20251014164519"）
    base = _re.sub(r'-\d{14}$', '', base)
    
    normalized = base.replace("—", "-").replace("－", "-").replace("–", "-").replace("_", "-")
    parts = [_part.strip() for _part in _re.split(r"-+", normalized) if _part.strip()]
    
    # 🔥 改进：寻找包含公司关键词的部分作为候选
    company_keywords = [
        "有限公司", "有限责任公司", "股份有限公司", "股份公司", "集团",
        "有限合伙", "合伙企业", "Co.", "Ltd.", "Corp.", "Inc."
    ]
    
    candidate = ""
    for part in parts:
        # 检查是否包含公司关键词
        if any(keyword in part for keyword in company_keywords):
            candidate = part
            break
    
    # 如果没找到包含公司关键词的部分，使用第一部分
    if not candidate:
        candidate = parts[0] if parts else normalized.strip()
    
    if not candidate:
        return ""

    cleanup_suffixes = [
        "股东信息", "股东明细", "股东名单", "股权信息", "股东情况", "工商登记",
        "投资人信息", "投资人名单", "股东", "股权", "清单", "明细", "列表"
    ]
    candidate_clean = candidate
    lower_candidate = candidate_clean.lower()
    for suffix in cleanup_suffixes:
        suffix_lower = suffix.lower()
        if lower_candidate.endswith(suffix_lower):
            candidate_clean = candidate_clean[: -len(suffix)].strip(" ()（）-")
            lower_candidate = candidate_clean.lower()

    candidate_clean = candidate_clean.strip(" ()（）-")
    return candidate_clean or candidate

def _infer_parent_from_filename(file_name: str) -> str:
    """Infer parent entity name from investment/control file naming patterns."""
    if not file_name:
        return ""
    import re as _re

    base = os.path.splitext(file_name)[0].strip()
    if not base:
        return ""

    # 🔥 移除序号前缀（如 "2_", "4_" 等）
    base = _re.sub(r'^\d+_', '', base)
    
    # 🔥 移除时间戳后缀（如 "-20251014164519"）
    base = _re.sub(r'-\d{14}$', '', base)

    normalized = base.replace("—", "-").replace("－", "-").replace("–", "-").replace("_", "-")
    parts = [_part.strip() for _part in _re.split(r"-+", normalized) if _part.strip()]
    
    # 检查是否包含对外投资或控制企业的关键词
    investment_keywords = [
        "对外投资", "控制企业", "投资企业", "子公司", "关联企业", 
        "控股企业", "参股企业", "投资公司", "被投资企业"
    ]
    
    # 🔥 改进：寻找包含公司关键词的部分作为parent候选
    company_keywords = [
        "有限公司", "有限责任公司", "股份有限公司", "股份公司", "集团",
        "有限合伙", "合伙企业", "Co.", "Ltd.", "Corp.", "Inc."
    ]
    
    parent_candidate = ""
    
    # 首先查找包含公司关键词的部分
    for part in parts:
        # 跳过包含投资关键词的部分
        if any(keyword in part for keyword in investment_keywords):
            continue
        # 检查是否包含公司关键词
        if any(keyword in part for keyword in company_keywords):
            parent_candidate = part
            break
    
    # 如果没有找到，使用第一部分作为候选
    if not parent_candidate:
        parent_candidate = parts[0] if parts else normalized.strip()
    
    if not parent_candidate:
        return ""

    # 清理后缀
    cleanup_suffixes = [
        "对外投资", "控制企业", "投资企业", "子公司", "关联企业", 
        "控股企业", "参股企业", "投资公司", "被投资企业",
        "信息", "明细", "名单", "清单", "列表"
    ]
    
    candidate_clean = parent_candidate
    lower_candidate = candidate_clean.lower()
    for suffix in cleanup_suffixes:
        suffix_lower = suffix.lower()
        if lower_candidate.endswith(suffix_lower):
            candidate_clean = candidate_clean[: -len(suffix)].strip(" ()（）-")
            lower_candidate = candidate_clean.lower()

    candidate_clean = candidate_clean.strip(" ()（）-")
    return candidate_clean or parent_candidate

def _detect_file_type_from_filename(file_name: str) -> str:
    """Detect file type from filename to determine auto-link strategy."""
    if not file_name:
        return "unknown"
    
    file_lower = file_name.lower()
    
    # 检查是否为对外投资/控制企业文件
    investment_keywords = [
        "对外投资", "控制企业", "投资企业", "子公司", "关联企业", 
        "控股企业", "参股企业", "投资公司", "被投资企业"
    ]
    
    for keyword in investment_keywords:
        if keyword in file_lower:
            return "investment"  # 对外投资文件
    
    # 检查是否为股东文件
    shareholder_keywords = [
        "股东信息", "股东明细", "股东名单", "股权信息", "股东情况",
        "投资人信息", "投资人名单", "股东", "股权"
    ]
    
    for keyword in shareholder_keywords:
        if keyword in file_lower:
            return "shareholder"  # 股东文件
    
    return "unknown"

# --- Excel 导入辅助：根据关键词自动将某一行作为表头 ---
def _apply_header_detection(df, keywords, announce: bool = True):
    """
    改进的表头检测函数
    能够更好地识别真正的表头行，跳过标题行和空行
    """
    try:
        import pandas as _pd  # noqa
    except Exception:
        return df
    try:
        max_check = min(len(df), 8)  # 增加检查范围
        header_row_idx = None
        
        # 定义排除的关键词（这些通常不是表头）
        exclude_keywords = [
            "股东信息", "工商登记", "企业信息", "公司信息", 
            "基本信息", "详细信息", "数据", "信息", "登记",
            "None", "nan", "null", "", " ", "　"
        ]
        
        # 定义表头特征关键词（这些通常出现在真正的表头中）
        header_features = [
            "序号", "编号", "ID", "id", "index",
            "名称", "姓名", "企业名称", "公司名称", "股东名称", "发起人名称",
            "类型", "企业类型", "股东类型", "发起人类型",
            "比例", "持股比例", "出资比例", "投资比例",
            "金额", "出资额", "认缴出资额", "实缴出资额", "投资数额",
            "日期", "出资日期", "认缴出资日期", "实缴出资日期", "成立日期",
            "状态", "登记状态", "经营状态", "企业状态"
        ]
        
        best_score = 0
        best_row_idx = None
        
        for i in range(max_check):
            row_vals = [str(v).strip() for v in df.iloc[i].tolist()]
            
            # 跳过空行或几乎全空的行
            non_empty_vals = [v for v in row_vals if v and v.lower() not in ['none', 'nan', 'null', '']]
            if len(non_empty_vals) < 2:  # 至少要有2个非空值
                continue
            
            # 计算匹配分数
            keyword_hits = 0
            feature_hits = 0
            exclude_hits = 0
            
            for v in row_vals:
                v_lower = v.lower()
                # 检查关键词匹配
                if any(k in v for k in keywords):
                    keyword_hits += 1
                # 检查表头特征
                if any(f in v for f in header_features):
                    feature_hits += 1
                # 检查排除关键词
                if any(ex in v_lower for ex in exclude_keywords):
                    exclude_hits += 1
            
            # 计算综合分数
            # 基础分数：关键词匹配
            base_score = keyword_hits
            
            # 特征加分：表头特征匹配
            feature_bonus = feature_hits * 0.5
            
            # 排除扣分：排除关键词匹配
            exclude_penalty = exclude_hits * 0.3
            
            # 长度加分：合适的列数（3-8列通常是表头）
            length_bonus = 0.2 if 3 <= len(non_empty_vals) <= 8 else 0
            
            # 最终分数
            final_score = base_score + feature_bonus - exclude_penalty + length_bonus
            
            # 更新最佳匹配
            if final_score > best_score:
                best_score = final_score
                best_row_idx = i
        
        # 如果找到合适的表头行（分数至少为2）
        if best_row_idx is not None and best_score >= 2:
            header_row_idx = best_row_idx
            
            # 设置新的列名
            new_cols = []
            for j, v in enumerate(df.iloc[header_row_idx].tolist()):
                name = str(v).strip()
                if not name or name.lower() in ("none", "nan", "null", "") or name.lower().startswith("column_"):
                    name = f"Column_{j}"
                new_cols.append(name)
            
            # 重新设置DataFrame
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
            df.columns = new_cols
            
            if announce:
                try:
                    st.info(f"✅ 检测到第 {header_row_idx + 1} 行为表头（匹配分数: {best_score:.1f}），已据此设置列名。")
                except Exception:
                    pass
        else:
            if announce:
                try:
                    st.warning(f"⚠️ 未检测到合适的表头行（最高分数: {best_score:.1f}），使用默认列名。")
                except Exception:
                    pass
        
        return df
    except Exception as e:
        if announce:
            try:
                st.error(f"表头检测出错: {str(e)}")
            except Exception:
                pass
        return df

# --- Excel 智能识别：实体名称(股东/子公司)识别 ---
def _find_name_column(df, analysis_result, synonyms=None):
    """
    ????(??/???)?????:
    1) ???????????(?????/????/???/?????/?????/??/???)
    2) ???????? entity_name_column
    3) ???????(??�??/??�??????)
    """
    try:
        cols = list(df.columns)
    except Exception:
        return None

    default_synonyms = [
        "?????", "????", "????", "??", "???", "?????", "?????",
        "?????", "??", "??"
    ]
    keys = synonyms or default_synonyms
    try:
        for c in cols:
            cs = str(c)
            if any(k in cs for k in keys):
                return c
    except Exception:
        pass

    try:
        detected_name = (analysis_result or {}).get('entity_name_column')
        if detected_name in cols:
            return detected_name
    except Exception:
        pass

    try:
        for c in cols:
            cs = str(c)
            if not any(k in cs for k in ("??", "??", "??")):
                return c
    except Exception:
        pass
    return cols[0] if cols else None

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
def _safe_switch_page(rel_path: str):
    """安全跳转页面：处理不同运行环境下的页面跳转。
    
    当从pages目录运行时，使用相对路径；当从src/main目录运行时，调整路径。
    """
    try:
        # 直接尝试跳转
        st.switch_page(rel_path)
    except Exception as e:
        # 如果失败，尝试调整路径
        if rel_path.startswith("pages/"):
            # 如果是从pages目录运行，去掉pages/前缀
            adjusted_path = rel_path.replace("pages/", "")
            try:
                st.switch_page(adjusted_path)
            except Exception:
                st.warning(f"页面跳转失败: {rel_path}")
        else:
            st.warning(f"页面跳转失败: {rel_path}")


with st.sidebar:
    # 侧边栏标题
    st.sidebar.title("股权分析平台") 
    
    st.sidebar.subheader("功能导航") 
    
    # 导航按钮，使用Unicode图标
    if st.sidebar.button("🏠 主页", help="返回主页面"):
        _safe_switch_page("main_page.py")
        
    if st.sidebar.button("🔍 图像识别模式", help="使用AI识别股权结构图", use_container_width=True):
        _safe_switch_page("pages/1_图像识别模式.py")
        
    if st.sidebar.button("📊 手动编辑模式", help="手动创建和编辑股权结构", use_container_width=True):
        _safe_switch_page("pages/2_手动编辑模式.py")
    
    # 使用展开面板显示使用说明
    with st.expander("ℹ️ 使用说明", expanded=False):
        st.write("## 手动编辑模式操作步骤")
        st.write("1. **设置核心公司**: 输入公司名称")
        st.write("2. **添加主要股东**: 添加股东及持股比例")
        st.write("3. **添加子公司**: 添加子公司及持股比例")
        st.write("4. **股权合并**: 合并小比例股东，简化图表显示")
        st.write("5. **关系设置**: 设置实际控制关系")
        st.write("6. **生成图表**: 实时预览和生成股权结构图")
        st.write("   - **Mermaid图表**: 传统流程图样式，支持文本编辑和代码导出")
        st.write("   - **交互式HTML图表**: 专业层级结构图，支持拖拽、缩放、节点高亮")
        st.write("7. **导出数据**: 下载Mermaid代码、JSON数据或HTML图表")
    
    st.sidebar.markdown("---")

    # 添加版权说明
    current_year = datetime.now().year
    st.sidebar.markdown(
        f'<h6>© {current_year} Noah 版权所有</h6>',
        unsafe_allow_html=True,
    )

# 导入Mermaid生成功能
from src.utils.mermaid_function import generate_mermaid_from_data as generate_mermaid_diagram
from src.utils.visjs_equity_chart import generate_visjs_html
from src.utils.excel_smart_importer import create_smart_excel_importer

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
        filtered_entities_info = []  # 收集过滤信息
        
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
            filter_reason = ""
            
            # 检查是否为实际控制人（不应该被过滤）
            is_actual_controller = entity_name == data_for_chart.get("actual_controller", "")
            
            # 检查是否为明确不需要的实体（如空名称、无效数据等）
            if not entity_name or entity_name.strip() == "":
                should_filter = True
                filter_reason = "空名称实体"
            elif entity.get("percentage", 0) <= 0 and not is_actual_controller:
                # 实际控制人即使持股比例为0也不应该被过滤
                should_filter = True
                filter_reason = f"无持股比例的实体: {entity_name}"
            
            if should_filter:
                filtered_entities_info.append(f"❌ 过滤掉无效实体: {entity_name}")
            else:
                # 正常股东，保留
                filtered_top_entities.append(entity)
                if has_relationship:
                    filtered_entities_info.append(f"✅ 保留有关系的股东: {entity_name}")
                else:
                    filtered_entities_info.append(f"✅ 保留正常股东（将自动生成关系）: {entity_name}")
        
        # 统一显示过滤调试信息
        if filtered_entities_info:
            with st.expander("🔍 过滤调试信息", expanded=False):
                for info in filtered_entities_info:
                    st.write(info)
        
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
            # 调试信息（默认收起）
            with st.expander("📊 调试信息", expanded=False):
                st.write(f"共有 {len(data_for_chart['all_entities'])} 个实体，{len(data_for_chart['entity_relationships'])} 个股权关系，{len(data_for_chart['control_relationships'])} 个控制关系")
            
            # 显示层级调试信息（默认收起）
            if hasattr(st.session_state, 'debug_level_info'):
                with st.expander("层级调整调试信息", expanded=False):
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
                core_company = st.session_state.equity_data.get("core_company", "未知公司")
                page_title = f"{core_company} - 交互式HTML股权结构图"
                html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                            level_separation=level_separation,
                                                            node_spacing=node_spacing,
                                                            tree_spacing=tree_spacing,
                                                            subgraphs=subgraphs,
                                                            page_title=page_title)
                
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
            
            core_company = st.session_state.equity_data.get("core_company", "未知公司")
            page_title = f"{core_company} - 交互式HTML股权结构图"
            html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                        level_separation=level_separation,
                                                        node_spacing=node_spacing,
                                                        tree_spacing=tree_spacing,
                                                        subgraphs=subgraphs,
                                                        page_title=page_title)
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
            show_visjs_preview = st.checkbox("显示实时VIS预览", value=False, key="visjs_preview_toggle")
        
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
                
                # 调试信息：显示层级分组情况（收起）
                with st.expander("🔍 层级分组调试信息", expanded=False):
                    st.info(f"层级分组情况: {dict(level_groups)}")
                
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
                
                # 调试信息：显示生成的分组（收起）
                with st.expander("🔍 分组生成调试信息", expanded=False):
                    st.info(f"生成的分组数量: {len(subgraphs)}")
                    for i, subgraph in enumerate(subgraphs):
                        st.info(f"分组 {i+1}: {subgraph['label']} (节点: {subgraph['nodes']})")
                
                # 生成HTML内容
                core_company = st.session_state.equity_data.get("core_company", "未知公司")
                page_title = f"{core_company} - 交互式HTML股权结构图"
                html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                            level_separation=level_separation,
                                                            node_spacing=node_spacing,
                                                            tree_spacing=tree_spacing,
                                                            subgraphs=subgraphs,
                                                            page_title=page_title)
                
                # 在Streamlit中显示
                components.html(html_content, height=600, scrolling=True)
                
                st.success("✅ VIS图表已实时更新")
                
            except Exception as e:
                st.error(f"显示VIS预览时出错: {str(e)}")
                st.info("📊 建议使用'全屏查看图表'或'下载HTML图表'功能查看完整的交互式图表")
        else:
            # 生成并显示图表
            st.info("📊 勾选'显示实时VIS预览'以查看实时更新的交互式图表，或使用'全屏查看图表'功能")
        
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
    page_title="股权结构手动编辑器 - V2",
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

    # 关系设置步骤：保存/恢复进度（快照导出/导入 + 自动保存）
    try:
        if st.session_state.get("current_step") == "relationships":
            # ðŸ”¥ é¦–æ¬¡è¿›å…¥æ—¶ï¼Œå¦‚æžœæœ‰åŽ†å²å¿«ç…§ï¼Œåˆ™æ­¤è½®è¿‡æ»¤è‡ªåŠ¨ä¿å­˜ï¼Œé¿å…è¦†ç›–
            try:
                if "checked_autosave" not in st.session_state:
                    ws_chk = st.session_state.get("workspace_name", "default")
                    p_chk = find_autosave(ws_chk)
                    if p_chk:
                        st.session_state["_pending_autosave_path"] = str(p_chk)
                        st.session_state["_last_autosave_ts"] = time.time()
                else:
                    # æ— æ„ä¹‰çŠ¶æ€�ï¼šä¸è‡ªåŠ¨ä¿å­˜
                    eq0 = st.session_state.get("equity_data", {}) or {}
                    placeholders0 = {"æœªå‘½åå…¬å¸", "æœªå‘½å", "Unnamed", "N/A", "None", "null"}
                    name0 = str(eq0.get("core_company", "")).strip()
                    has_meaning0 = bool(name0 and name0 not in placeholders0) or any(
                        len(eq0.get(k, [])) > 0 for k in [
                            "top_level_entities", "subsidiaries", "entity_relationships",
                            "control_relationships", "all_entities"
                        ]
                    )
                    if not has_meaning0:
                        st.session_state["_last_autosave_ts"] = time.time()
            except Exception:
                pass
            with st.expander("💾 保存/恢复进度", expanded=False):
                core_company_name = ""
                try:
                    core_company_name = (st.session_state.get("equity_data", {}) or {}).get("core_company", "")
                except Exception:
                    core_company_name = ""
                placeholders = {"未命名公司", "未命名", "Unnamed", "N/A", "None", "null"}
                cc_valid = core_company_name.strip() if core_company_name and core_company_name.strip() not in placeholders else ""
                default_ws = st.session_state.get("workspace_name") or (cc_valid or f"workspace-{time.strftime('%Y%m%d-%H%M')}")
                ws = st.text_input("工作区名称", value=default_ws, key="ws_name_rel_top")
                st.session_state["workspace_name"] = ws

                # 导出
                try:
                    snapshot = make_snapshot()
                except Exception:
                    snapshot = {}
                st.download_button(
                    "导出当前进度（JSON）",
                    data=json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"),
                    file_name=f"{ws}-{int(time.time())}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_snapshot_rel_top",
                )

                # 导入
                up = st.file_uploader("导入进度（JSON）", type=["json"], key="import_progress_rel_top")
                if up and st.button("恢复进度", type="primary", use_container_width=True, key="restore_progress_rel_top"):
                    try:
                        snap = json.loads(up.read().decode("utf-8"))
                        ok, msg = apply_snapshot(snap)
                        st.success(msg) if ok else st.error(msg)
                        st.rerun()
                    except Exception as e:
                        st.error(f"导入失败: {e}")

                st.checkbox("自动保存到本地（user_data/autosave）", value=True, key="auto")
                st.caption("开启后每隔 15 秒或状态更新时将自动写入快照。")

            # 自动保存触发（每15秒且在有明确步骤时进行）
            try:
                if st.session_state.get("workspace_name") and st.session_state.get("current_step"):
                    last = st.session_state.get("_last_autosave_ts", 0.0)
                    if st.session_state.get("auto", True) and (time.time() - last) > 5:
                        path = autosave(make_snapshot(), st.session_state["workspace_name"])
                        st.session_state["_last_autosave_ts"] = time.time()
                        st.session_state["_last_autosave_path"] = str(path)
            except Exception:
                pass

            # 首次进入时提示是否恢复上次自动保存
            if "checked_autosave" not in st.session_state:
                st.session_state["checked_autosave"] = True
                ws = st.session_state.get("workspace_name", "default")
                p = find_autosave(ws)
                if p:
                    with st.expander("🔄 检测到上次自动保存，是否恢复？", expanded=True):
                        st.write(f"快照文件：`{p}`")
                        if st.button("恢复上次自动保存", key="restore_autosave_button_rel_top"):
                            try:
                                snap = json.loads(p.read_text(encoding="utf-8"))
                                ok, msg = apply_snapshot(snap)
                                st.success(msg) if ok else st.error(msg)
                                st.rerun()
                            except Exception as e:
                                st.error(f"恢复失败: {e}")
    except Exception:
        pass

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
    "top_entities": "2. 主要股东",
    "subsidiaries": "3. 子公司",
    "merge_entities": "4. 股权合并",
    "relationships": "5. 关系设置",
    "generate": "6. 生成图表"
}

# 标题
st.title("✏️ 股权结构手动编辑器 - V2")

# 简介
st.markdown("""
本工具允许您手动添加公司、股东、子公司及它们之间的关系，生成股权结构图。
支持股权合并功能，可将小比例股东合并简化显示。提供双重图表模式：
- **Mermaid图表**：传统流程图样式，支持文本编辑和代码导出
- **交互式HTML图表**：专业层级结构图，支持拖拽、缩放、节点高亮等交互功能
按照步骤填写信息，最终可以生成专业的股权结构可视化图表。
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
                    # 保存旧的核心公司名称
                    old_core_company = st.session_state.equity_data["core_company"]
                    
                    # 更新核心公司信息
                    st.session_state.equity_data["core_company"] = core_company
                    st.session_state.equity_data["actual_controller"] = controller
                    
                    # 🔥 关键修复：更新所有涉及核心公司的股权关系
                    if old_core_company != core_company:
                        # 更新entity_relationships中涉及核心公司的关系
                        for rel in st.session_state.equity_data.get("entity_relationships", []):
                            # 更新parent字段（核心公司作为父实体）
                            if rel.get("parent") == old_core_company:
                                rel["parent"] = core_company
                            # 更新child字段（核心公司作为子实体）
                            if rel.get("child") == old_core_company:
                                rel["child"] = core_company
                            # 更新from字段（兼容其他格式）
                            if rel.get("from") == old_core_company:
                                rel["from"] = core_company
                            # 更新to字段（兼容其他格式）
                            if rel.get("to") == old_core_company:
                                rel["to"] = core_company
                        
                        # 更新control_relationships中涉及核心公司的关系
                        for rel in st.session_state.equity_data.get("control_relationships", []):
                            # 更新parent字段（核心公司作为被控制实体）
                            if rel.get("parent") == old_core_company:
                                rel["parent"] = core_company
                            # 更新child字段（核心公司作为被控制实体）
                            if rel.get("child") == old_core_company:
                                rel["child"] = core_company
                            # 更新from字段（兼容其他格式）
                            if rel.get("from") == old_core_company:
                                rel["from"] = core_company
                            # 更新to字段（兼容其他格式）
                            if rel.get("to") == old_core_company:
                                rel["to"] = core_company
                    
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
                        
                        with st.expander("🔍 合并实体调试信息", expanded=False):
                            st.write(f"开始检查合并实体，当前有 {len(st.session_state.get('merged_entities', []))} 个合并实体")
                            
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
                                            
                                            st.write(f"从合并实体 '{merged_entity['merged_name']}' 中移除股东: {removed_entity_name}")
                                            
                                            # 重新计算合并实体的总持股比例
                                            if merged_entity["entities"]:
                                                # 还有实体，重新计算总比例
                                                new_total_percentage = sum(entity.get("percentage", 0) for entity in merged_entity["entities"])
                                                merged_entity["total_percentage"] = new_total_percentage
                                                st.write(f"更新合并实体 '{merged_entity['merged_name']}' 的总持股比例为: {new_total_percentage}%")
                                            else:
                                                # 没有实体了，标记为删除
                                                merged_entities_to_remove.append(merged_idx)
                                                st.write(f"合并实体 '{merged_entity['merged_name']}' 为空，将删除")
                                            break
                                    
                                    if entity_found:
                                        break
                            
                            # 删除空的合并实体（从后往前删除，避免索引问题）
                            for idx in reversed(merged_entities_to_remove):
                                removed_merged_entity = st.session_state.merged_entities.pop(idx)
                                st.write(f"已删除空的合并实体: {removed_merged_entity['merged_name']}")
                            
                            st.write(f"同时删除了 {deleted_entity_relationships_count} 个股权关系和 {deleted_control_relationships_count} 个控制关系")
                            if merged_entities_updated:
                                st.write("已更新合并实体信息")
                        
                        st.success(f"已删除: {removed_entity_name}")
    
    # 编辑现有实体
    editing_index = None
    if st.session_state.editing_entity and st.session_state.editing_entity[0] == "top_entity":
        editing_index = st.session_state.editing_entity[1]
        if editing_index < len(st.session_state.equity_data["top_level_entities"]):
            entity = st.session_state.equity_data["top_level_entities"][editing_index]
            
            with st.form("edit_top_entity_form"):
                st.subheader("编辑顶级实体")
                name = st.text_input("实体名称", value=entity["name"])
                reg_capital = st.text_input("注册资本（可选）", value=str(entity.get("registration_capital", "")))
                est_date = st.text_input("成立日期（可选，YYYY-MM-DD）", value=str(entity.get("establishment_date", "")))
                
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
                            st.session_state.equity_data["top_level_entities"][editing_index]["registration_capital"] = reg_capital.strip() if reg_capital else None
                            st.session_state.equity_data["top_level_entities"][editing_index]["establishment_date"] = est_date.strip() if est_date else None
                            
                            # 更新all_entities
                            for e in st.session_state.equity_data["all_entities"]:
                                if e["name"] == entity["name"]:
                                    e["name"] = name
                                    e["type"] = entity_type
                                    if reg_capital:
                                        e["registration_capital"] = reg_capital.strip()
                                    if est_date:
                                        e["establishment_date"] = est_date.strip()
                                    break

                            # 同步更新涉及该顶级实体名称的股权关系（通常作为 parent 指向核心公司）
                            if "entity_relationships" in st.session_state.equity_data and isinstance(st.session_state.equity_data["entity_relationships"], list):
                                core_company_name = st.session_state.equity_data.get("core_company", "")
                                for rel in st.session_state.equity_data["entity_relationships"]:
                                    # 兼容两种键：parent/child 或 from/to
                                    parent_key = "parent" if "parent" in rel else ("from" if "from" in rel else None)
                                    child_key = "child" if "child" in rel else ("to" if "to" in rel else None)
                                    if parent_key:
                                        if rel.get(parent_key) == entity["name"]:
                                            rel[parent_key] = name
                                            # 若该关系指向核心公司，顺便同步比例信息
                                            if child_key and rel.get(child_key) == core_company_name:
                                                rel["percentage"] = percentage
                                                rel["description"] = f"持股{percentage}%"
                            
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
        # 先展示：从 Excel 批量导入顶级实体/股东（移动到手动添加之前）
        st.subheader("📊 从Excel导入股东信息（批量）")
        st.info("上传 Excel 文件，系统将自动/手动映射列，并支持按‘登记状态’跳过注销/吊销的记录。")

        uploaded_file_top = st.file_uploader("选择Excel文件", type=["xlsx", "xls"], key="top_entities_excel")
        if uploaded_file_top is not None:
            try:
                import pandas as pd
                try:
                    df_top = pd.read_excel(uploaded_file_top)
                except Exception:
                    uploaded_file_top.seek(0)
                    df_top = pd.read_excel(uploaded_file_top, header=1)
                if any('Unnamed' in str(c) for c in df_top.columns):
                    df_top.columns = [f"Column_{i}" for i in range(len(df_top.columns))]
                    st.info("Excel 未提供清晰表头，已用序号作为列名。")

                # 股东信息表头检测关键词
                header_keywords_top = [
                    "序号", "发起人名称", "发起人类型", "持股比例", 
                    "认缴出资额", "认缴出资日期", "实缴出资额", "实缴出资日期",
                    "股东名称", "股东类型", "出资比例", "出资额", "出资日期",
                    "股东信息", "工商登记", "企业名称", "公司名称", "名称",
                    "法定代表人", "注册资本", "投资比例", "投资数额", "成立日期", "登记状态"
                ]
                df_top = _apply_header_detection(df_top, header_keywords_top, announce=True)

                from src.utils.excel_smart_importer import create_smart_excel_importer
                smart_importer_top = create_smart_excel_importer()
                analysis_result_top = smart_importer_top.analyze_excel_columns(df_top)
                import_summary_top = smart_importer_top.get_import_summary(df_top, analysis_result_top)

                st.markdown("### 🔍 智能分析结果")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("总行数", import_summary_top.get('total_rows', 0))
                with c2:
                    st.metric("识别列数", import_summary_top.get('detected_columns', 0))
                with c3:
                    dist = import_summary_top.get('entity_type_distribution', {"company":0,"person":0})
                    st.metric("公司/个人", f"{dist.get('company',0)}/{dist.get('person',0)}")

                st.markdown("### 📊 数据预览")
                st.dataframe(df_top.head(10))

                st.markdown("### 📋 列映射")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    name_idx = 0
                    if import_summary_top.get('entity_name_column') in list(df_top.columns):
                        name_idx = list(df_top.columns).index(import_summary_top['entity_name_column'])
                    name_col_selected_top = st.selectbox("选择名称列", df_top.columns.tolist(), index=name_idx, key="name_col_selected_top_ui2")
                with col_b:
                    pct_idx = 1 if len(df_top.columns)>1 else 0
                    if import_summary_top.get('investment_ratio_column') in list(df_top.columns):
                        pct_idx = list(df_top.columns).index(import_summary_top['investment_ratio_column'])
                    percentage_col_selected_top = st.selectbox("选择持股比例列", df_top.columns.tolist(), index=pct_idx, key="pct_col_selected_top_ui2")
                with col_c:
                    try:
                        status_auto_top = _find_status_column(df_top, analysis_result_top)
                    except Exception:
                        status_auto_top = None
                    status_options_top = ["（不使用）"] + list(df_top.columns)
                    default_status_idx_top = 0
                    if status_auto_top and status_auto_top in df_top.columns:
                        default_status_idx_top = 1 + list(df_top.columns).index(status_auto_top)
                    status_choice_top = st.selectbox(
                        "选择登记状态列（可选）",
                        status_options_top,
                        index=default_status_idx_top,
                        help="若为注销/吊销将跳过导入",
                        key="status_col_selected_top_ui2",
                    )
                    st.session_state["status_col_selected_top"] = None if status_choice_top == "（不使用）" else status_choice_top

                # 🔥 添加数据质量检查（在列映射之后）
                st.markdown("### 🔍 数据质量检查")
                quality_col1, quality_col2, quality_col3 = st.columns(3)
                
                with quality_col1:
                    empty_names = df_top[name_col_selected_top].isna().sum() if name_col_selected_top in df_top.columns else 0
                    st.metric("空名称行数", empty_names)
                
                with quality_col2:
                    empty_pct = df_top[percentage_col_selected_top].isna().sum() if percentage_col_selected_top in df_top.columns else 0
                    st.metric("空比例行数", empty_pct)
                
                with quality_col3:
                    total_rows = len(df_top)
                    st.metric("总行数", total_rows)
                
                # 显示数据样本
                if name_col_selected_top in df_top.columns and percentage_col_selected_top in df_top.columns:
                    st.markdown("#### 📋 数据样本（前5行）")
                    sample_df = df_top[[name_col_selected_top, percentage_col_selected_top]].head(5)
                    st.dataframe(sample_df, use_container_width=True)

                current_filename = getattr(uploaded_file_top, "name", None) if uploaded_file_top else None
                last_filename = st.session_state.get("auto_child_target_last_filename")
                fallback_child = st.session_state.equity_data.get("core_company", "")
                
                # 🔥 新增：检测文件类型和自动推断目标实体
                file_type = "unknown"
                inferred_child_target = ""
                inferred_parent_target = ""
                
                if current_filename:
                    try:
                        file_type = _detect_file_type_from_filename(current_filename)
                        if file_type == "shareholder":
                            inferred_child_target = _infer_child_from_filename(current_filename)
                        elif file_type == "investment":
                            inferred_parent_target = _infer_parent_from_filename(current_filename)
                    except Exception:
                        inferred_child_target = ""
                        inferred_parent_target = ""

                # 🔥 根据文件类型设置不同的自动关联策略
                if current_filename and current_filename != last_filename:
                    if file_type == "investment":
                        # 对外投资文件：设置parent实体
                        new_auto_parent = inferred_parent_target or fallback_child or ""
                        st.session_state.auto_parent_target = new_auto_parent
                        st.session_state["auto_parent_target_input"] = new_auto_parent
                        st.session_state.auto_child_target = ""  # 清空child设置
                        st.session_state["auto_child_target_input"] = ""
                    else:
                        # 股东文件：设置child实体（原有逻辑）
                        new_auto_child = inferred_child_target or fallback_child or ""
                        st.session_state.auto_child_target = new_auto_child
                        st.session_state["auto_child_target_input"] = new_auto_child
                        st.session_state.auto_parent_target = ""  # 清空parent设置
                        st.session_state["auto_parent_target_input"] = ""
                    
                    st.session_state.auto_child_target_last_filename = current_filename
                elif current_filename is None and last_filename:
                    st.session_state.pop("auto_child_target_last_filename", None)
                    if "auto_child_target" not in st.session_state:
                        default_child = fallback_child or ""
                        st.session_state.auto_child_target = default_child
                        st.session_state["auto_child_target_input"] = default_child

                if "auto_child_target" not in st.session_state:
                    init_child = inferred_child_target or fallback_child or ""
                    st.session_state.auto_child_target = init_child
                    st.session_state["auto_child_target_input"] = init_child

                # 🔥 根据文件类型显示不同的UI
                if file_type == "investment":
                    st.info("🔍 检测到对外投资/控制企业文件，将自动设置母公司实体")
                    parent_default = st.session_state.get("auto_parent_target", "").strip()
                    auto_parent_value = st.text_input(
                        "Auto link parent entity",
                        value=parent_default,
                        help="从文件名推断的母公司实体，Excel中的数据将作为子公司与此实体关联",
                        key="auto_parent_target_input",
                    )
                    st.session_state.auto_parent_target = auto_parent_value.strip()
                    # 隐藏child设置
                    st.session_state.auto_child_target = ""
                else:
                    child_default = st.session_state.get("auto_child_target", "").strip()
                    auto_child_value = st.text_input(
                        "Auto link child entity",
                        value=child_default,
                        help="Leave empty to skip automatic relationship creation",
                        key="auto_child_target_input",
                    )
                    st.session_state.auto_child_target = auto_child_value.strip()
                    # 隐藏parent设置
                    st.session_state.auto_parent_target = ""

                skip_rows_top = st.number_input("跳过前几行（如有表头/说明）", min_value=0, max_value=10, value=0, key="skip_rows_top")
                auto_detect_type_top = st.checkbox("启用自动类型判断", value=True, help="根据名称自动判断公司/个人", key="auto_detect_type_top")
                default_entity_type_top = st.selectbox("默认类型", ["company","person"], index=0, key="default_entity_type_top")

                if st.button("开始导入股东（主要股东）", type="primary", key="import_top_entities_now"):
                    if uploaded_file_top is None:
                        st.error("请先上传Excel文件")
                        st.stop()
                    
                    try:
                        uploaded_file_top.seek(0)
                    except Exception:
                        pass
                    if skip_rows_top>0:
                        df_proc = pd.read_excel(uploaded_file_top, skiprows=skip_rows_top)
                        if any('Unnamed' in str(c) for c in df_proc.columns):
                            df_proc.columns = [f"Column_{i}" for i in range(len(df_proc.columns))]
                    else:
                        df_proc = df_top.copy()

                    # 股东信息表头检测关键词
                    df_proc = _apply_header_detection(df_proc, [
                        "序号", "发起人名称", "发起人类型", "持股比例", 
                        "认缴出资额", "认缴出资日期", "实缴出资额", "实缴出资日期",
                        "股东名称", "股东类型", "出资比例", "出资额", "出资日期",
                        "股东信息", "工商登记", "企业名称", "公司名称", "名称",
                        "法定代表人", "注册资本", "投资比例", "投资数额", "成立日期", "登记状态"
                    ], announce=False)
                    try:
                        name_idx2 = list(df_proc.columns).index(name_col_selected_top)
                        pct_idx2 = list(df_proc.columns).index(percentage_col_selected_top)
                    except ValueError as e:
                        st.error(f"列映射无效，请重新选择。错误详情: {str(e)}")
                        st.error(f"可用列: {list(df_proc.columns)}")
                        st.error(f"选择的名称列: '{name_col_selected_top}'")
                        st.error(f"选择的比例列: '{percentage_col_selected_top}'")
                        st.stop()
                    except Exception as e:
                        st.error(f"列映射处理失败: {str(e)}")
                        st.stop()
                    actual_name_col_top = df_proc.columns[name_idx2]
                    actual_pct_col_top = df_proc.columns[pct_idx2]
                    status_col_main = st.session_state.get("status_col_selected_top") or _find_status_column(df_proc, analysis_result_top)

                    auto_child_target_clean = st.session_state.get("auto_child_target", "").strip()
                    auto_parent_target_clean = st.session_state.get("auto_parent_target", "").strip()
                    auto_relationship_candidates = []
                    
                    # 🔥 处理child关联（原有逻辑）
                    if auto_child_target_clean:
                        all_entities_list = st.session_state.equity_data.get("all_entities", [])
                        if not any(e.get("name") == auto_child_target_clean for e in all_entities_list):
                            st.session_state.equity_data["all_entities"].append({
                                "name": auto_child_target_clean,
                                "type": "company"
                            })
                    
                    # 🔥 处理parent关联（新增逻辑）
                    if auto_parent_target_clean:
                        all_entities_list = st.session_state.equity_data.get("all_entities", [])
                        if not any(e.get("name") == auto_parent_target_clean for e in all_entities_list):
                            st.session_state.equity_data["all_entities"].append({
                                "name": auto_parent_target_clean,
                                "type": "company"
                            })

                    imported_count, skipped_count = 0, 0
                    errors = []
                    auto_results_local = None
                    for idx, row in df_proc.iterrows():
                        try:
                            entity_name = str(row[actual_name_col_top]).strip()
                            # 🔥 改进：更宽松的实体名称验证
                            if (not entity_name or 
                                entity_name.lower() in ["nan","none","null","","-","--","/","\\","#","*"] or
                                len(entity_name) < 1):
                                skipped_count += 1
                                errors.append(f"第{idx+1}行: 实体名称为空或无效: '{entity_name}'")
                                continue
                            pct_val = row[actual_pct_col_top]
                            try:
                                percentage = float(pct_val)
                                if not (0<=percentage<=100):
                                    raise ValueError("比例范围无效")
                            except Exception:
                                import re as _re
                                # 🔥 改进：支持更多百分比格式，包括带括号的格式
                                pct_str = str(pct_val).strip()
                                # 尝试多种格式：42.71%, (42.71%), 42.71, 42.71%等
                                patterns = [
                                    r'(\d+(?:\.\d+)?)%',  # 42.71%
                                    r'\((\d+(?:\.\d+)?)\)',  # (42.71)
                                    r'(\d+(?:\.\d+)?)',  # 42.71
                                ]
                                
                                percentage = None
                                for pattern in patterns:
                                    m = _re.search(pattern, pct_str)
                                    if m:
                                        try:
                                            percentage = float(m.group(1))
                                            break
                                        except ValueError:
                                            continue
                                
                                if percentage is None:
                                    skipped_count += 1
                                    errors.append(f"第{idx+1}行: 无法从 '{pct_val}' 中提取有效比例")
                                    continue
                                    
                                if not (0<=percentage<=100):
                                    skipped_count += 1
                                    errors.append(f"第{idx+1}行: 比例 {percentage}% 超出有效范围(0-100%)")
                                    continue

                            try:
                                status_val = row[status_col_main] if status_col_main and status_col_main in df_proc.columns else None
                            except Exception:
                                status_val = None
                            if _is_inactive_status(status_val):
                                skipped_count += 1
                                errors.append(f"第{idx+1}行: 登记状态为“{status_val}”，已跳过")
                                continue

                            if auto_detect_type_top:
                                try:
                                    entity_type = smart_importer_top.auto_detect_entity_type(entity_name)
                                except Exception:
                                    entity_type = default_entity_type_top
                            else:
                                entity_type = default_entity_type_top

                            exists = False
                            for i, entity in enumerate(st.session_state.equity_data["top_level_entities"]):
                                if entity["name"] == entity_name:
                                    st.session_state.equity_data["top_level_entities"][i]["percentage"] = percentage
                                    exists = True
                                    imported_count += 1
                                    break
                            if not exists:
                                st.session_state.equity_data["top_level_entities"].append({
                                    "name": entity_name,
                                    "type": entity_type,
                                    "percentage": percentage
                                })
                                if not any(e.get("name")==entity_name for e in st.session_state.equity_data.get("all_entities", [])):
                                    st.session_state.equity_data["all_entities"].append({
                                        "name": entity_name,
                                        "type": entity_type
                                    })
                                imported_count += 1

                            # 🔥 根据文件类型创建不同的关联关系
                            if auto_child_target_clean:
                                # 股东文件：股东 -> 目标公司
                                auto_relationship_candidates.append({
                                    "parent": entity_name,
                                    "child": auto_child_target_clean,
                                    "percentage": percentage,
                                    "row": idx + 1,
                                    "type": "child_link"
                                })
                            elif auto_parent_target_clean:
                                # 对外投资文件：母公司 -> 子公司
                                auto_relationship_candidates.append({
                                    "parent": auto_parent_target_clean,
                                    "child": entity_name,
                                    "percentage": percentage,
                                    "row": idx + 1,
                                    "type": "parent_link"
                                })
                        except Exception as e:
                            skipped_count += 1
                            errors.append(f"第{idx+1}行: 处理失败 - {str(e)}")

                    
                    # 🔥 支持两种自动关联类型
                    if auto_child_target_clean or auto_parent_target_clean:
                        existing_lookup = {}
                        for rel in st.session_state.equity_data.get("entity_relationships", []):
                            rel_parent = rel.get("parent") or rel.get("from")
                            rel_child = rel.get("child") or rel.get("to")
                            if rel_parent and rel_child:
                                existing_lookup[(rel_parent, rel_child)] = rel

                        created_details = []
                        updated_details = []
                        skipped_details = []

                        for candidate in auto_relationship_candidates:
                            parent_name = candidate["parent"]
                            child_name = candidate["child"]
                            percentage_value = candidate["percentage"]
                            row_number = candidate["row"]

                            if not parent_name or not child_name:
                                skipped_details.append({
                                    "parent": parent_name or "",
                                    "reason": "missing parent or child",
                                    "row": row_number
                                })
                                continue

                            if parent_name == child_name:
                                skipped_details.append({
                                    "parent": parent_name,
                                    "reason": "parent equals child",
                                    "row": row_number
                                })
                                continue

                            key = (parent_name, child_name)
                            existing_rel = existing_lookup.get(key)

                            if existing_rel:
                                existing_pct_raw = existing_rel.get("percentage")
                                try:
                                    existing_pct_value = float(existing_pct_raw)
                                except (TypeError, ValueError):
                                    try:
                                        import re as _re
                                        match = _re.search(r"\d+(\.\d+)?", str(existing_pct_raw))
                                        existing_pct_value = float(match.group()) if match else None
                                    except Exception:
                                        existing_pct_value = None

                                if existing_pct_value is None or abs(existing_pct_value - percentage_value) > 1e-6:
                                    existing_rel["percentage"] = percentage_value
                                    updated_details.append({
                                        "parent": parent_name,
                                        "percentage": percentage_value,
                                        "row": row_number
                                    })
                                else:
                                    skipped_details.append({
                                        "parent": parent_name,
                                        "reason": "unchanged",
                                        "row": row_number
                                    })
                            else:
                                new_relationship = {
                                    "parent": parent_name,
                                    "child": child_name,
                                    "percentage": percentage_value,
                                    "source": "auto_import"
                                }
                                st.session_state.equity_data["entity_relationships"].append(new_relationship)
                                existing_lookup[key] = new_relationship
                                created_details.append({
                                    "parent": parent_name,
                                    "percentage": percentage_value,
                                    "row": row_number
                                })

                        # 🔥 根据关联类型设置不同的结果信息
                        if auto_child_target_clean:
                            auto_results_local = {
                                "target": auto_child_target_clean,
                                "target_type": "child",
                                "created": created_details,
                                "updated": updated_details,
                                "skipped": skipped_details,
                                "total_candidates": len(auto_relationship_candidates)
                            }
                        elif auto_parent_target_clean:
                            auto_results_local = {
                                "target": auto_parent_target_clean,
                                "target_type": "parent",
                                "created": created_details,
                                "updated": updated_details,
                                "skipped": skipped_details,
                                "total_candidates": len(auto_relationship_candidates)
                            }
                    else:
                        auto_results_local = None

                    st.session_state["auto_link_results_top"] = auto_results_local

                    # 🔥 记录批量导入的文件名实体
                    if "imported_file_entities" not in st.session_state:
                        st.session_state.imported_file_entities = set()
                    
                    if auto_child_target_clean:
                        st.session_state.imported_file_entities.add(auto_child_target_clean)
                    if auto_parent_target_clean:
                        st.session_state.imported_file_entities.add(auto_parent_target_clean)
                    
                    st.markdown("### 导入结果")
                    cc1, cc2, cc3 = st.columns(3)
                    with cc1:
                        st.metric("成功导入", imported_count)
                    with cc2:
                        st.metric("跳过记录", skipped_count)
                    with cc3:
                        st.metric("错误数量", len(errors))
                    
                    # 🔥 添加调试信息
                    if imported_count == 0 and skipped_count > 0:
                        st.warning("⚠️ 没有成功导入任何记录，请检查数据格式和列映射")
                    elif imported_count > 0:
                        st.success(f"✅ 成功导入 {imported_count} 个股东记录")
                    if auto_results_local:
                        target_name = auto_results_local.get("target", "")
                        target_type = auto_results_local.get("target_type", "")
                        created = auto_results_local.get("created", [])
                        updated = auto_results_local.get("updated", [])
                        skipped = auto_results_local.get("skipped", [])
                        
                        if created or updated:
                            if target_type == "child":
                                st.success(f"✅ 自动关联 {len(created)} 条新增关系，{len(updated)} 条更新关系 -> {target_name}")
                            elif target_type == "parent":
                                st.success(f"✅ 自动关联 {len(created)} 条新增关系，{len(updated)} 条更新关系 <- {target_name}")
                        else:
                            if target_type == "child":
                                st.info(f"未为 {target_name or '指定子实体'} 创建新的自动关联")
                            elif target_type == "parent":
                                st.info(f"未为 {target_name or '指定母公司'} 创建新的自动关联")
                        
                        details_lines = []
                        for item in created:
                            if target_type == "child":
                                details_lines.append(f"新增: {item['parent']} -> {target_name} ({item['percentage']}%) [行 {item['row']}]")
                            elif target_type == "parent":
                                details_lines.append(f"新增: {target_name} -> {item['child']} ({item['percentage']}%) [行 {item['row']}]")
                        
                        for item in updated:
                            if target_type == "child":
                                details_lines.append(f"更新: {item['parent']} -> {target_name} ({item['percentage']}%) [行 {item['row']}]")
                            elif target_type == "parent":
                                details_lines.append(f"更新: {target_name} -> {item['child']} ({item['percentage']}%) [行 {item['row']}]")
                        
                        for item in skipped:
                            reason = item.get('reason', 'skipped')
                            if target_type == "child":
                                details_lines.append(f"忽略: {item.get('parent', '未知')} ({reason}) [行 {item.get('row', '?')}]")
                            elif target_type == "parent":
                                details_lines.append(f"忽略: {item.get('child', '未知')} ({reason}) [行 {item.get('row', '?')}]")
                        
                        if details_lines:
                            with st.expander("自动关联详情", expanded=False):
                                for line in details_lines:
                                    st.markdown(f"- {line}")
                    elif auto_child_target_clean or auto_parent_target_clean:
                        st.info("未检测到可用于自动关联的数据行")

                    if errors:
                        with st.expander("查看详细错误信息"):
                            for err in errors:
                                st.code(err)
                    if st.button("确认并刷新列表", type="primary", key="top_import_refresh_done"):
                        st.rerun()

            except Exception as e:
                st.error(f"导入出错: {str(e)}")

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

            col3, col4 = st.columns([1, 1])
            with col3:
                reg_capital_new_top = st.text_input("注册资本（可选）")
            with col4:
                est_date_new_top = st.text_input("成立日期（可选，YYYY-MM-DD）")
            
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
                            "percentage": percentage,
                            "registration_capital": reg_capital_new_top.strip() if reg_capital_new_top else None,
                            "establishment_date": est_date_new_top.strip() if est_date_new_top else None
                        })
                        
                        # 添加到所有实体列表
                        if not any(e["name"] == name for e in st.session_state.equity_data["all_entities"]):
                            st.session_state.equity_data["all_entities"].append({
                                "name": name,
                                "type": entity_type,
                                "registration_capital": reg_capital_new_top.strip() if reg_capital_new_top else None,
                                "establishment_date": est_date_new_top.strip() if est_date_new_top else None
                            })
                        
                        st.success(f"已添加顶级实体: {name}")
                        # 修改：无论是否继续，都添加后立即刷新页面，实现实时显示
                        st.rerun()
                    else:
                        st.error("该实体已存在")
                else:
                    st.error("请输入实体名称")
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
                        removed_subsidiary_name = removed_subsidiary["name"]
                        
                        # 从all_entities中移除
                        st.session_state.equity_data["all_entities"] = [
                            e for e in st.session_state.equity_data.get("all_entities", []) 
                            if e["name"] != removed_subsidiary_name
                        ]
                        
                        # 🔥 关键修复：同时删除对应的关系
                        # 删除entity_relationships中涉及该实体的关系
                        original_entity_relationships_count = len(st.session_state.equity_data["entity_relationships"])
                        st.session_state.equity_data["entity_relationships"] = [
                            rel for rel in st.session_state.equity_data["entity_relationships"]
                            if (rel.get("from", rel.get("parent", "")) != removed_subsidiary_name and 
                                rel.get("to", rel.get("child", "")) != removed_subsidiary_name)
                        ]
                        deleted_entity_relationships_count = original_entity_relationships_count - len(st.session_state.equity_data["entity_relationships"])
                        
                        # 删除control_relationships中涉及该实体的关系
                        original_control_relationships_count = len(st.session_state.equity_data["control_relationships"])
                        st.session_state.equity_data["control_relationships"] = [
                            rel for rel in st.session_state.equity_data["control_relationships"]
                            if (rel.get("from", rel.get("parent", "")) != removed_subsidiary_name and 
                                rel.get("to", rel.get("child", "")) != removed_subsidiary_name)
                        ]
                        deleted_control_relationships_count = original_control_relationships_count - len(st.session_state.equity_data["control_relationships"])
                        
                        # 🔥 关键修复：处理合并实体
                        # 检查删除的子公司是否在合并实体中
                        merged_entities_updated = False
                        merged_entities_to_remove = []
                        
                        with st.expander("🔍 合并实体调试信息", expanded=False):
                            st.write(f"开始检查合并实体，当前有 {len(st.session_state.get('merged_entities', []))} 个合并实体")
                            
                            if st.session_state.get("merged_entities"):
                                for merged_idx, merged_entity in enumerate(st.session_state.merged_entities):
                                    # 检查删除的子公司是否在这个合并实体中
                                    entity_found = False
                                    for entity_idx, entity in enumerate(merged_entity["entities"]):
                                        if entity["name"] == removed_subsidiary_name:
                                            entity_found = True
                                            # 从合并实体中移除该子公司
                                            removed_entity_from_merge = merged_entity["entities"].pop(entity_idx)
                                            merged_entities_updated = True
                                            
                                            st.write(f"从合并实体 '{merged_entity['merged_name']}' 中移除子公司: {removed_subsidiary_name}")
                                            
                                            # 重新计算合并实体的总持股比例
                                            if merged_entity["entities"]:
                                                # 还有实体，重新计算总比例
                                                new_total_percentage = sum(entity.get("percentage", 0) for entity in merged_entity["entities"])
                                                merged_entity["total_percentage"] = new_total_percentage
                                                st.write(f"更新合并实体 '{merged_entity['merged_name']}' 的总持股比例为: {new_total_percentage}%")
                                            else:
                                                # 没有实体了，标记为删除
                                                merged_entities_to_remove.append(merged_idx)
                                                st.write(f"合并实体 '{merged_entity['merged_name']}' 为空，将删除")
                                            break
                                    
                                    if entity_found:
                                        break
                            
                            # 删除空的合并实体（从后往前删除，避免索引问题）
                            for idx in reversed(merged_entities_to_remove):
                                removed_merged_entity = st.session_state.merged_entities.pop(idx)
                                st.write(f"已删除空的合并实体: {removed_merged_entity['merged_name']}")
                            
                            st.write(f"同时删除了 {deleted_entity_relationships_count} 个股权关系和 {deleted_control_relationships_count} 个控制关系")
                            if merged_entities_updated:
                                st.write("已更新合并实体信息")
                        
                        st.success(f"已删除: {removed_subsidiary_name}")
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
                # 若无明确列名（全部为 Unnamed/数字索引/空），为后续自动识别统一设置占位列名
                try:
                    import re as _re
                    cols_str = [str(c).strip() for c in df_sub.columns]
                    unnamed = any('unnamed' in s.lower() for s in cols_str)
                    numeric = all(_re.fullmatch(r"\d+", s) is not None for s in cols_str)
                    generic = all(_re.fullmatch(r"column_?\d+", s, _re.IGNORECASE) is not None for s in cols_str)
                    empty_like = any(s == '' for s in cols_str)
                    if unnamed or numeric or generic or empty_like:
                        df_sub.columns = [f'Column_{i}' for i in range(len(df_sub.columns))]
                        st.info("Excel文件未提供清晰表头，已使用序号作为列名以便后续自动识别。")
                except Exception:
                    pass
            
            # 将所有列转换为字符串类型，避免Arrow错误
            for col in df_sub.columns:
                df_sub[col] = df_sub[col].astype(str)

            # 试探性识别“表头行”：若前几行包含多项关键列名，则将该行作为真正表头
            try:
                header_keywords = [
                    '被投资企业名称', '企业名称', '公司名称', '名称',
                    '法定代表人', '注册资本', '投资比例', '投资数额', '成立日期', '登记状态'
                ]
                header_row_idx = None
                max_check = min(len(df_sub), 6)
                for i in range(max_check):
                    row_vals = [str(v).strip() for v in df_sub.iloc[i].tolist()]
                    hits = sum(1 for v in row_vals if any(k in v for k in header_keywords))
                    if hits >= 2:
                        header_row_idx = i
                        break

                if header_row_idx is not None:
                    new_cols = []
                    for j, v in enumerate(df_sub.iloc[header_row_idx].tolist()):
                        name = str(v).strip()
                        if not name or name.lower().startswith('column_') or name.lower() == 'nan':
                            name = f'Column_{j}'
                        new_cols.append(name)
                    df_sub = df_sub.iloc[header_row_idx+1:].reset_index(drop=True)
                    df_sub.columns = new_cols
                    st.info(f"检测到第 {header_row_idx} 行为表头，已据此设置列名。")
            except Exception:
                pass
            
            # 🔥 智能Excel分析（子公司）
            try:
                smart_importer_sub = create_smart_excel_importer()
                analysis_result_sub = smart_importer_sub.analyze_excel_columns(df_sub)
                import_summary_sub = smart_importer_sub.get_import_summary(df_sub, analysis_result_sub)
                
                # 显示智能分析结果
                st.markdown("### 🔍 智能分析结果")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("总行数", import_summary_sub['total_rows'])
                with col2:
                    st.metric("识别列数", import_summary_sub['detected_columns'])
                with col3:
                    company_count = import_summary_sub['entity_type_distribution']['company']
                    person_count = import_summary_sub['entity_type_distribution']['person']
                    st.metric("公司/个人", f"{company_count}/{person_count}")
                
                # 显示列识别结果
                if analysis_result_sub['detected_columns']:
                    st.markdown("**自动识别的列:**")
                    for col, col_type in analysis_result_sub['detected_columns'].items():
                        confidence = analysis_result_sub['confidence_scores'].get(col, 0)
                        suggestion = analysis_result_sub['column_suggestions'].get(col, '')
                        st.write(f"• {col} → {suggestion} (置信度: {confidence:.1%})")
                else:
                    st.warning("⚠️ 未能自动识别任何列，请手动选择")
                    
            except Exception as smart_error:
                st.error(f"智能分析出错: {str(smart_error)}")
                st.info("将使用传统列选择方式")
                # 设置默认值
                import_summary_sub = {
                    'entity_name_column': None,
                    'investment_ratio_column': None,
                    'total_rows': len(df_sub),
                    'detected_columns': 0,
                    'entity_type_distribution': {'company': 0, 'person': 0}
                }
            
            # 显示文件预览
            st.subheader("📊 文件预览")
            st.dataframe(df_sub.head(10))
            
            # 🔥 智能列选择（子公司）
            st.subheader("📋 列映射")
            col1, col2 = st.columns(2)
            
            with col1:
                # 🔥 完全忽略智能识别，强制使用与主要股东相同的逻辑
                # 使用智能识别结果作为默认项，若不可用则回退到第0列
                name_col_index_sub = 0
                try:
                    if 'import_summary_sub' in locals() and import_summary_sub.get('entity_name_column') in list(df_sub.columns):
                        name_col_index_sub = list(df_sub.columns).index(import_summary_sub['entity_name_column'])
                except Exception:
                    pass
                
                name_col_selected_sub = st.selectbox(
                    "选择包含子公司名称的列", 
                    df_sub.columns.tolist(),
                    index=name_col_index_sub,
                    help="默认选择第0列（与主要股东一致）"
                )
            
            with col2:
                # 🔥 完全忽略智能识别，强制使用与主要股东相同的逻辑
                # 使用智能识别结果作为默认项，若不可用则回退到第1列
                percentage_col_index_sub = 1 if len(df_sub.columns) > 1 else 0
                try:
                    if 'import_summary_sub' in locals() and import_summary_sub.get('investment_ratio_column') in list(df_sub.columns):
                        percentage_col_index_sub = list(df_sub.columns).index(import_summary_sub['investment_ratio_column'])
                except Exception:
                    pass
                
                percentage_col_selected_sub = st.selectbox(
                    "选择包含持股比例的列", 
                    df_sub.columns.tolist(),
                    index=percentage_col_index_sub,
                    help="默认选择第1列（与主要股东一致）"
                )
            
            # 选择登记状态列（可选，子公司）
            try:
                status_auto_sub = _find_status_column(df_sub, analysis_result_sub)
            except Exception:
                status_auto_sub = None
            status_options_sub = ["（不使用）"] + df_sub.columns.tolist()
            default_status_idx_sub = 0
            if status_auto_sub and status_auto_sub in df_sub.columns:
                default_status_idx_sub = 1 + list(df_sub.columns).index(status_auto_sub)
            status_choice_sub = st.selectbox(
                "选择登记状态列（可选）",
                status_options_sub,
                index=default_status_idx_sub,
                help="若为注销/吊销将跳过导入",
                key="status_col_selected_sub_ui",
            )
            st.session_state["status_col_selected_sub"] = None if status_choice_sub == "（不使用）" else status_choice_sub

            # 子公司导入是否自动判断实体类型
            auto_detect_sub_type = st.checkbox("启用自动类型判断（子公司）", value=True, help="根据名称自动判断是公司还是个人")

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
                if uploaded_file_sub is None:
                    st.error("请先上传Excel文件")
                    st.stop()
                
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
                # 统计总行数与已处理行数，用于在循环最后统一渲染结果
                rows_total = len(df_processing)
                rows_processed = 0

                # 识别“登记状态”列（子公司导入）
                try:
                    status_col_sub = _find_status_column(df_processing, analysis_result_sub)
                except Exception:
                    status_col_sub = None
                
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

                        # 若登记状态为注销/吊销，则跳过
                        try:
                            status_value = row[status_col_sub] if status_col_sub and status_col_sub in df_processing.columns else None
                        except Exception:
                            status_value = None
                        if _is_inactive_status(status_value):
                            skipped_count += 1
                            errors.append(f"第{index+1}行: 登记状态为“{status_value}”，已跳过")
                            continue
                        
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
                                skipped_count += 1
                                errors.append(f"第{index+1}行: 比例转换失败 - {str(e)}")
                                continue

                        # 检查是否已存在
                        exists = False
                        for i, sub in enumerate(st.session_state.equity_data["subsidiaries"]):
                            if sub.get("name") == subsidiary_name:
                                # 更新现有子公司的百分比
                                st.session_state.equity_data["subsidiaries"][i]["percentage"] = percentage
                                # 同步关系
                                if st.session_state.equity_data.get("core_company"):
                                    for j, rel in enumerate(st.session_state.equity_data["entity_relationships"]):
                                        if rel.get("parent") == st.session_state.equity_data["core_company"] and rel.get("child") == subsidiary_name:
                                            st.session_state.equity_data["entity_relationships"][j]["percentage"] = percentage
                                            st.session_state.equity_data["entity_relationships"][j]["description"] = f"持股{percentage}%"
                                            break
                                exists = True
                                imported_count += 1
                                break

                        # 如果不存在，新增子公司并自动判定类型
                        if not exists:
                            try:
                                if 'auto_detect_sub_type' in locals() and auto_detect_sub_type:
                                    entity_type_sub = smart_importer_sub.auto_detect_entity_type(subsidiary_name)
                                else:
                                    entity_type_sub = "company"
                            except Exception:
                                entity_type_sub = "company"

                            st.session_state.equity_data["subsidiaries"].append({
                                "name": subsidiary_name,
                                "type": entity_type_sub,
                                "percentage": percentage
                            })

                            # 加入 all_entities
                            if not any(e.get("name") == subsidiary_name for e in st.session_state.equity_data.get("all_entities", [])):
                                st.session_state.equity_data["all_entities"].append({
                                    "name": subsidiary_name,
                                    "type": entity_type_sub
                                })

                            # 与核心公司建立关系
                            if st.session_state.equity_data.get("core_company"):
                                st.session_state.equity_data["entity_relationships"].append({
                                    "parent": st.session_state.equity_data["core_company"],
                                    "child": subsidiary_name,
                                    "percentage": percentage,
                                    "relationship_type": "控股",
                                    "description": f"持股{percentage}%"
                                })
                            imported_count += 1

                    except Exception as e:
                        skipped_count += 1
                        errors.append(f"第{index+1}行: 处理失败 - {str(e)}")

                # 循环结束后统一展示导入结果
                try:
                    processing_placeholder.empty()
                except Exception:
                    pass
                st.markdown("### 导入结果")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("成功导入", imported_count)
                with col2:
                    st.metric("跳过记录", skipped_count)

                if errors:
                    st.warning(f"共 {len(errors)} 条记录处理失败:")
                    with st.expander("查看详细错误信息"):
                        for error in errors:
                            st.code(error)

                if st.button("确认并刷新列表", type="primary", key="subsidiary_import_refresh_final"):
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
                reg_capital = st.text_input("注册资本（可选）", value=str(subsidiary.get("registration_capital", "")))
                est_date = st.text_input("成立日期（可选，YYYY-MM-DD）", value=str(subsidiary.get("establishment_date", "")))
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
                            st.session_state.equity_data["subsidiaries"][editing_index]["registration_capital"] = reg_capital.strip() if reg_capital else None
                            st.session_state.equity_data["subsidiaries"][editing_index]["establishment_date"] = est_date.strip() if est_date else None
                            
                            # 更新all_entities
                            for e in st.session_state.equity_data["all_entities"]:
                                if e["name"] == subsidiary["name"]:
                                    e["name"] = name
                                    if reg_capital:
                                        e["registration_capital"] = reg_capital.strip()
                                    if est_date:
                                        e["establishment_date"] = est_date.strip()
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
            col3, col4 = st.columns([1, 1])
            with col3:
                reg_capital_new = st.text_input("注册资本（可选）")
            with col4:
                est_date_new = st.text_input("成立日期（可选，YYYY-MM-DD）")
                
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
                                "percentage": percentage,
                                "registration_capital": reg_capital_new.strip() if reg_capital_new else None,
                                "establishment_date": est_date_new.strip() if est_date_new else None
                            })
                            
                            # 添加到所有实体列表
                            if not any(e.get("name") == name for e in st.session_state.equity_data.get("all_entities", [])):
                                st.session_state.equity_data["all_entities"].append({
                                    "name": name,
                                    "type": "company",
                                    "registration_capital": reg_capital_new.strip() if reg_capital_new else None,
                                    "establishment_date": est_date_new.strip() if est_date_new else None
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
    
    # --- 股东控股关系图谱 ---
    display_entities = get_display_entities()
    hidden_entities = set(st.session_state.get("hidden_entities", []))

    def _build_relationship_graph():
        """构建 parent -> children 映射，便于展开查看股权路径"""
        graph = {}
        for rel in st.session_state.equity_data.get("entity_relationships", []):
            parent = rel.get("parent") or rel.get("from", "")
            child = rel.get("child") or rel.get("to", "")
            if not parent or not child:
                continue
            if parent in hidden_entities or child in hidden_entities:
                continue
            graph.setdefault(parent, []).append({
                "child": child,
                "percentage": rel.get("percentage"),
                "description": rel.get("description"),
                "relationship_type": rel.get("relationship_type"),
            })
        return graph

    relationship_graph = _build_relationship_graph()

    def _format_percentage(value):
        if value in (None, "", "N/A"):
            return ""
        try:
            num = float(value)
            if int(num) == num:
                return f" ({int(num)}%)"
            return f" ({num:.2f}%)"
        except Exception:
            return f" ({value})"

    def _render_branch(anchor, depth=0, visited=None):
        if visited is None:
            visited = set()
        if anchor in visited:
            return
        visited.add(anchor)
        children = relationship_graph.get(anchor, [])

        def _sort_key(item):
            pct = item.get("percentage")
            try:
                pct_val = float(pct)
            except Exception:
                pct_val = -1
            return (-pct_val, item.get("child", ""))

        for child_info in sorted(children, key=_sort_key):
            child_name = child_info.get("child", "")
            pct_text = _format_percentage(child_info.get("percentage"))
            extra_desc = child_info.get("description") or ""
            desc_text = f" <span style='color:#888'>{extra_desc}</span>" if extra_desc else ""
            indent = "&nbsp;" * depth * 4
            st.markdown(f"{indent}• {child_name}{pct_text}{desc_text}", unsafe_allow_html=True)
            if child_name not in visited:
                _render_branch(child_name, depth + 1, visited.copy())

    st.markdown("### 🧭 股东控股关系图谱")
    
    # 🔥 添加过滤选项
    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        st.caption("📌 提示：可以通过过滤选项简化图谱显示，只保留关键股东关系")
    with filter_col2:
        show_simplified = st.checkbox("简化显示", value=False, help="只显示个人股东、实际控制人和批量导入的文件名实体")
    
    # 🔥 获取批量导入的文件名实体（从session_state中提取）
    imported_file_entities = set()
    if "imported_file_entities" in st.session_state:
        imported_file_entities = st.session_state.imported_file_entities
    
    # 🔥 过滤显示的实体
    filtered_display_entities = display_entities
    if show_simplified:
        actual_controller = st.session_state.equity_data.get("actual_controller", "")
        
        filtered_display_entities = []
        for entity in display_entities:
            entity_name = entity.get("name", "")
            if not entity_name:
                continue
            
            # 检查是否为个人（从all_entities中获取类型）
            is_person = False
            for e in st.session_state.equity_data.get("all_entities", []):
                if e.get("name") == entity_name and e.get("type") == "person":
                    is_person = True
                    break
            
            # 保留条件：
            # 1. 个人股东
            # 2. 实际控制人
            # 3. 批量导入的文件名实体
            if (is_person or 
                entity_name == actual_controller or 
                entity_name in imported_file_entities):
                filtered_display_entities.append(entity)
    
    if not filtered_display_entities:
        st.caption("暂无可展示的股东信息")
    else:
        for entity in filtered_display_entities:
            entity_name = entity.get("name", "")
            if not entity_name:
                continue
            pct_text = _format_percentage(entity.get("percentage"))
            label_suffix = "（合并股东）" if entity.get("type") == "merged_shareholder" else ""
            header_label = f"{entity_name}{pct_text}{label_suffix}"
            with st.expander(header_label, expanded=False):
                if entity_name in relationship_graph:
                    _render_branch(entity_name, depth=0, visited=set())
                else:
                    st.caption("未发现控股企业")

    core_company = st.session_state.equity_data.get("core_company")
    if core_company and core_company in relationship_graph:
        with st.expander(f"{core_company}（核心公司向下控股）", expanded=False):
            _render_branch(core_company, depth=0, visited=set())

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
        
        # 🔥 关键修复：为合并后的实体添加新的关系
        for merged in st.session_state.get("merged_entities", []):
            merged_name = merged["merged_name"]
            total_percentage = merged["total_percentage"]
            
            # 查找合并实体中第一个实体的关系作为模板
            if merged["entities"]:
                first_entity = merged["entities"][0]
                for rel in st.session_state.equity_data.get("entity_relationships", []):
                    from_entity = rel.get('from', rel.get('parent', ''))
                    to_entity = rel.get('to', rel.get('child', ''))
                    
                    # 如果是从被合并实体出发的关系
                    if from_entity == first_entity["name"]:
                        filtered_relationships.append({
                            "from": merged_name,
                            "to": to_entity,
                            "percentage": total_percentage,
                            "relationship_type": rel.get("relationship_type", "控股"),
                            "description": rel.get("description", f"持股{total_percentage}%")
                        })
                        break
                    # 如果是到被合并实体的关系
                    elif to_entity == first_entity["name"]:
                        filtered_relationships.append({
                            "from": from_entity,
                            "to": merged_name,
                            "percentage": total_percentage,
                            "relationship_type": rel.get("relationship_type", "控股"),
                            "description": rel.get("description", f"持股{total_percentage}%")
                        })
                        break
        
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
                        
                        # 🔍 详细调试信息（收起）
                        with st.expander("🔍 删除关系调试信息", expanded=False):
                            st.write(f"准备删除关系 {from_entity} → {to_entity} ({percentage}%)")
                            st.write(f"当前entity_relationships数量: {len(st.session_state.equity_data['entity_relationships'])}")
                            
                            # 显示所有关系用于调试
                            st.write("当前所有entity_relationships:")
                            for idx, rel_item in enumerate(st.session_state.equity_data["entity_relationships"]):
                                rel_from = rel_item.get('from', rel_item.get('parent', ''))
                                rel_to = rel_item.get('to', rel_item.get('child', ''))
                                rel_percentage = rel_item.get('percentage', 0)
                                st.write(f"  {idx}: {rel_from} → {rel_to} ({rel_percentage}%)")
                            
                            # 🔥 关键修复：在过滤后的关系中删除，而不是在原始关系中删除
                            # 因为显示的是过滤后的关系，删除也应该在过滤后的关系中删除
                            
                            # 首先从过滤后的关系中删除
                            filtered_relationships.pop(i)
                            st.write(f"从过滤列表中删除，剩余 {len(filtered_relationships)} 个关系")
                            
                            # 然后从原始关系中也删除（如果存在）
                            original_index = None
                            st.write("查找原始关系中的匹配项...")
                            for orig_i, orig_rel in enumerate(st.session_state.equity_data["entity_relationships"]):
                                orig_from = orig_rel.get('from', orig_rel.get('parent', ''))
                                orig_to = orig_rel.get('to', orig_rel.get('child', ''))
                                orig_percentage = orig_rel.get('percentage', 0)
                                st.write(f"检查原始关系 {orig_i}: {orig_from} → {orig_to} ({orig_percentage}%)")
                                if orig_from == from_entity and orig_to == to_entity:
                                    original_index = orig_i
                                    st.write(f"找到匹配关系，索引: {orig_i}")
                                    break
                            
                            if original_index is not None:
                                st.session_state.equity_data["entity_relationships"].pop(original_index)
                                st.write(f"从原始关系中删除，删除前有 {len(st.session_state.equity_data['entity_relationships']) + 1} 个关系，删除后有 {len(st.session_state.equity_data['entity_relationships'])} 个关系")
                                
                                # 显示删除后的关系列表
                                st.write("删除后的entity_relationships:")
                                for idx, rel_item in enumerate(st.session_state.equity_data["entity_relationships"]):
                                    rel_from = rel_item.get('from', rel_item.get('parent', ''))
                                    rel_to = rel_item.get('to', rel_item.get('child', ''))
                                    rel_percentage = rel_item.get('percentage', 0)
                                    st.write(f"  {idx}: {rel_from} → {rel_to} ({rel_percentage}%)")
                            else:
                                st.write("该关系不在原始关系中，可能是在过滤过程中自动添加的")
                        
                        # 显示成功信息
                        if original_index is not None:
                            st.success(f"✅ 已删除关系: {from_entity} → {to_entity}")
                        else:
                            st.success(f"✅ 已删除关系: {from_entity} → {to_entity} (仅从过滤列表中删除)")
                        
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
                            with st.expander("🔍 控制关系删除调试信息", expanded=False):
                                st.write(f"从原始控制关系中删除，删除前有 {len(st.session_state.equity_data['control_relationships']) + 1} 个控制关系，删除后有 {len(st.session_state.equity_data['control_relationships'])} 个控制关系")
                        else:
                            st.success(f"已删除控制关系: {from_entity} ⤳ {to_entity} (仅从过滤列表中删除)")
                            with st.expander("🔍 控制关系删除调试信息", expanded=False):
                                st.write("该控制关系不在原始控制关系中，可能是在过滤过程中自动添加的")
                        
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
                filtered_entities_info = []  # 收集过滤信息
                
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
                    filter_reason = ""
                    
                    # 检查是否为实际控制人（不应该被过滤）
                    is_actual_controller = entity_name == data_for_mermaid.get("controller", "")
                    
                    # 检查是否为明确不需要的实体（如空名称、无效数据等）
                    if not entity_name or entity_name.strip() == "":
                        should_filter = True
                        filter_reason = "空名称实体"
                    elif entity.get("percentage", 0) <= 0 and not is_actual_controller:
                        # 实际控制人即使持股比例为0也不应该被过滤
                        should_filter = True
                        filter_reason = f"无持股比例的实体: {entity_name}"
                    
                    if should_filter:
                        filtered_entities_info.append(f"❌ 过滤掉无效实体: {entity_name}")
                    else:
                        # 正常股东，保留
                        filtered_top_entities.append(entity)
                        if has_relationship:
                            filtered_entities_info.append(f"✅ 保留有关系的股东: {entity_name}")
                        else:
                            filtered_entities_info.append(f"✅ 保留正常股东（将自动生成关系）: {entity_name}")
                
                # 统一显示过滤调试信息
                if filtered_entities_info:
                    with st.expander("🔍 过滤调试信息", expanded=False):
                        for info in filtered_entities_info:
                            st.write(info)
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 🔥 特殊处理：检查是否有被过滤掉的合并实体需要恢复（实时预览）
                with st.expander("🔍 实时预览调试信息", expanded=False):
                    st.write(f"检查是否有被过滤掉的合并实体")
                    for entity in st.session_state.equity_data.get("top_level_entities", []):
                        entity_name = entity.get("name", "")
                        if entity_name not in [e["name"] for e in filtered_top_entities]:
                            # 检查是否在合并实体中
                            is_merged_entity = False
                            for merged in st.session_state.get("merged_entities", []):
                                if merged.get("merged_name") == entity_name:
                                    is_merged_entity = True
                                    st.write(f"发现被过滤的合并实体: {entity_name}")
                                    # 恢复合并实体
                                    filtered_top_entities.append(entity)
                                    break
                            
                            if not is_merged_entity:
                                st.write(f"被过滤的非合并实体: {entity_name}")
                
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
                        # 根据合并实体的类型决定添加到哪个列表
                        if merged.get("entity_type") == "shareholder" or any(e["type"] == "shareholder" for e in merged["entities"]):
                            filtered_top_entities.append({
                                "name": merged["merged_name"],
                                "type": "company",
                                "percentage": merged["total_percentage"]
                            })
                        elif merged.get("entity_type") == "subsidiary" or all(e["type"] == "subsidiary" for e in merged["entities"]):
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
                    # 🔍 调试信息：显示传递给Mermaid的数据（收起）
                    with st.expander("🔍 Mermaid数据调试信息", expanded=False):
                        st.write("传递给Mermaid的数据:")
                        st.write(f"controller: '{data_for_mermaid['controller']}'")
                        st.write(f"actual_controller: '{st.session_state.equity_data.get('actual_controller', '')}'")
                        st.write(f"top_entities: {data_for_mermaid['top_entities']}")
                        st.write(f"all_entities: {data_for_mermaid['all_entities']}")
                        st.write(f"entity_relationships: {data_for_mermaid['entity_relationships']}")
                        st.write(f"control_relationships: {data_for_mermaid['control_relationships']}")
                        
                        # 检查实际控制人是否在top_entities中
                        controller_name = data_for_mermaid['controller']
                        if controller_name:
                            controller_in_top = any(e.get('name') == controller_name for e in data_for_mermaid['top_entities'])
                            controller_in_all = any(e.get('name') == controller_name for e in data_for_mermaid['all_entities'])
                            st.write(f"实际控制人 '{controller_name}' 在top_entities中: {controller_in_top}")
                            st.write(f"实际控制人 '{controller_name}' 在all_entities中: {controller_in_all}")
                    
                    preview_mermaid_code = generate_mermaid_diagram(data_for_mermaid)
                
                # 显示预览图表
                st.markdown("### 📊 关系预览")
                st_mermaid(
                    preview_mermaid_code,
                    key="preview_mermaid_chart",
                    width="1900px",
                    height="900px",
                )
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
                            # 🔍 调试信息：显示当前控制关系（收起）
                            with st.expander("🔍 控制关系调试信息", expanded=False):
                                st.write(f"当前control_relationships数量: {len(st.session_state.equity_data['control_relationships'])}")
                                st.write("当前所有control_relationships:")
                                for idx, rel in enumerate(st.session_state.equity_data["control_relationships"]):
                                    parent = rel.get("parent", rel.get("from", ""))
                                    child = rel.get("child", rel.get("to", ""))
                                    st.write(f"  {idx}: {parent} ⤳ {child}")
                            
                            # 检查关系是否已存在
                            exists = any(
                                (r.get("parent", r.get("from")) == controller and r.get("child", r.get("to")) == controlled)
                                for r in st.session_state.equity_data["control_relationships"]
                            )
                            
                            with st.expander("🔍 添加控制关系调试信息", expanded=False):
                                st.write(f"尝试添加控制关系: {controller} ⤳ {controlled}")
                                st.write(f"关系是否已存在: {exists}")
                            
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
    
    # 获取可合并的股东实体
    def get_mergeable_shareholders():
        """获取可合并的股东列表（包含持股比例）"""
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
        
        # 按持股比例排序
        entities_list.sort(key=lambda x: x["percentage"])
        return entities_list
    
    # 获取可合并的子公司实体
    def get_mergeable_subsidiaries():
        """获取可合并的子公司列表（包含持股比例）"""
        entities_list = []
        
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
    mergeable_shareholders = get_mergeable_shareholders()
    mergeable_subsidiaries = get_mergeable_subsidiaries()
    
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
    
    # 股东合并功能
    st.markdown("### 👥 股东合并")
    
    if not mergeable_shareholders:
        st.info("暂无可合并的股东。请先在「主要股东」中添加股东。")
    else:
        # 股东合并方式选择
        shareholder_merge_mode = st.radio(
            "股东合并方式",
            ["按阈值自动合并", "手动选择合并"],
            help="按阈值：自动合并小于指定比例的股东；手动选择：自由选择要合并的股东",
            key="shareholder_merge_mode"
        )
        
        if shareholder_merge_mode == "按阈值自动合并":
            # 阈值选择
            col1, col2 = st.columns([2, 1])
            with col1:
                threshold = st.slider(
                    "合并阈值（持股比例小于此值的股东将被合并）",
                    min_value=0.1,
                    max_value=10.0,
                    value=st.session_state.get("shareholder_merge_threshold", 1.0),
                    step=0.1,
                    format="%.1f%%",
                    help="例如选择1%，则所有持股比例小于1%的股东将被合并",
                    key="shareholder_threshold"
                )
                st.session_state.shareholder_merge_threshold = threshold
            
            # 筛选小于阈值的股东
            shareholders_to_merge = [e for e in mergeable_shareholders 
                                   if e["percentage"] < threshold 
                                   and e["name"] not in st.session_state.hidden_entities]
            
            if shareholders_to_merge:
                st.info(f"📋 找到 {len(shareholders_to_merge)} 个符合条件的股东（持股比例 < {threshold}%）")
                
                # 预览将被合并的股东
                with st.expander("预览将被合并的股东", expanded=True):
                    for entity in shareholders_to_merge:
                        st.markdown(f"- **{entity['name']}**: {entity['percentage']:.2f}%")
                
                # 合并后的总比例
                total_percentage = sum(e["percentage"] for e in shareholders_to_merge)
                st.markdown(f"**合并后总比例**: {total_percentage:.2f}%")
                
                # 自定义合并后名称
                col1, col2 = st.columns([2, 1])
                with col1:
                    merged_name = st.text_input(
                        "合并后股东名称",
                        value="其他股东",
                        help="可以自定义合并后的股东名称",
                        key="shareholder_merged_name"
                    )
                
                # 确认合并按钮
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ 确认合并股东", type="primary", use_container_width=True, key="shareholder_merge_confirm"):
                        if not merged_name.strip():
                            st.error("请输入合并后的股东名称")
                        else:
                            # 创建合并实体
                            merged_entity = {
                                "merged_name": merged_name,
                                "total_percentage": total_percentage,
                                "entities": shareholders_to_merge,
                                "merge_type": "threshold",
                                "threshold": threshold,
                                "entity_type": "shareholder"
                            }
                            
                            # 添加到合并列表
                            st.session_state.merged_entities.append(merged_entity)
                            
                            # 将原实体添加到隐藏列表
                            for entity in shareholders_to_merge:
                                if entity["name"] not in st.session_state.hidden_entities:
                                    st.session_state.hidden_entities.append(entity["name"])
                            
                            st.success(f"✅ 已合并 {len(shareholders_to_merge)} 个股东为 '{merged_name}'")
                            st.rerun()
                
                with col2:
                    if st.button("取消", use_container_width=True, key="shareholder_merge_cancel"):
                        st.info("已取消股东合并操作")
            else:
                st.warning(f"没有找到持股比例小于 {threshold}% 的股东")
        
        else:  # 手动选择合并股东
            st.markdown("#### 手动选择要合并的股东")
            
            # 显示可选股东列表
            available_shareholders = [e for e in mergeable_shareholders 
                                     if e["name"] not in st.session_state.hidden_entities]
            
            if not available_shareholders:
                st.warning("没有可用的股东进行合并")
            else:
                # 初始化选中状态
                if 'selected_shareholders_for_merge' not in st.session_state:
                    st.session_state.selected_shareholders_for_merge = []
                
                # 创建复选框形式的股东选择器
                st.markdown("**选择要合并的股东（勾选复选框）：**")
                
                # 使用复选框列表而不是data_editor
                selected_shareholders = []
                
                # 创建复选框容器
                checkbox_container = st.container()
                
                with checkbox_container:
                    for i, entity in enumerate(available_shareholders):
                        col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                        
                        with col1:
                            # 使用独立的checkbox，每个都有唯一的key
                            is_selected = st.checkbox(
                                "",
                                value=entity["name"] in st.session_state.selected_shareholders_for_merge,
                                key=f"shareholder_checkbox_{entity['name']}_{i}",
                                help=f"选择 {entity['name']}"
                            )
                            
                        with col2:
                            st.write(f"**{entity['name']}**")
                            
                        with col3:
                            st.write(f"{entity['percentage']:.2f}%")
                        
                        if is_selected:
                            selected_shareholders.append(entity["name"])
                
                # 更新选中状态
                st.session_state.selected_shareholders_for_merge = selected_shareholders
                
                if selected_shareholders:
                    # 获取选中的股东详情
                    shareholders_to_merge = [e for e in available_shareholders if e["name"] in selected_shareholders]
                    
                    st.markdown("---")
                    st.markdown("#### 📋 股东合并预览")
                    
                    # 预览选中的股东
                    with st.expander("预览选中的股东", expanded=True):
                        for entity in shareholders_to_merge:
                            st.markdown(f"- **{entity['name']}**: {entity['percentage']:.2f}%")
                    
                    # 合并后的总比例
                    total_percentage = sum(e["percentage"] for e in shareholders_to_merge)
                    st.markdown(f"**合并后总比例**: {total_percentage:.2f}%")
                    
                    # 自定义合并后名称
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        merged_name = st.text_input(
                            "合并后股东名称",
                            value="其他股东",
                            key="manual_shareholder_merge_name",
                            help="可以自定义合并后的股东名称"
                        )
                    
                    # 确认合并按钮
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ 确认合并股东", type="primary", use_container_width=True, key="manual_shareholder_merge_confirm"):
                            if not merged_name.strip():
                                st.error("请输入合并后的股东名称")
                            else:
                                # 创建合并实体
                                merged_entity = {
                                    "merged_name": merged_name,
                                    "total_percentage": total_percentage,
                                    "entities": shareholders_to_merge,
                                    "merge_type": "manual",
                                    "entity_type": "shareholder"
                                }
                                
                                # 添加到合并列表
                                st.session_state.merged_entities.append(merged_entity)
                                
                                # 将原实体添加到隐藏列表
                                for entity in shareholders_to_merge:
                                    if entity["name"] not in st.session_state.hidden_entities:
                                        st.session_state.hidden_entities.append(entity["name"])
                                
                                # 清空选中状态
                                st.session_state.selected_shareholders_for_merge = []
                                
                                st.success(f"✅ 已合并 {len(shareholders_to_merge)} 个股东为 '{merged_name}'")
                                st.rerun()
                    
                    with col2:
                        if st.button("取消", use_container_width=True, key="manual_shareholder_merge_cancel"):
                            st.session_state.selected_shareholders_for_merge = []
                            st.info("已取消股东合并操作")
                else:
                    st.info("请在上方表格中勾选要合并的股东")
    
    st.markdown("---")
    
    # 子公司合并功能
    st.markdown("### 🏢 子公司合并")
    
    if not mergeable_subsidiaries:
        st.info("暂无可合并的子公司。请先在「子公司」中添加子公司。")
    else:
        # 子公司合并方式选择
        subsidiary_merge_mode = st.radio(
            "子公司合并方式",
            ["按阈值自动合并", "手动选择合并"],
            help="按阈值：自动合并小于指定比例的子公司；手动选择：自由选择要合并的子公司",
            key="subsidiary_merge_mode"
        )
        
        if subsidiary_merge_mode == "按阈值自动合并":
            # 阈值选择
            col1, col2 = st.columns([2, 1])
            with col1:
                threshold = st.slider(
                    "合并阈值（持股比例小于此值的子公司将被合并）",
                    min_value=0.1,
                    max_value=10.0,
                    value=st.session_state.get("subsidiary_merge_threshold", 1.0),
                    step=0.1,
                    format="%.1f%%",
                    help="例如选择1%，则所有持股比例小于1%的子公司将被合并",
                    key="subsidiary_threshold"
                )
                st.session_state.subsidiary_merge_threshold = threshold
            
            # 筛选小于阈值的子公司
            subsidiaries_to_merge = [e for e in mergeable_subsidiaries 
                                   if e["percentage"] < threshold 
                                   and e["name"] not in st.session_state.hidden_entities]
            
            if subsidiaries_to_merge:
                st.info(f"📋 找到 {len(subsidiaries_to_merge)} 个符合条件的子公司（持股比例 < {threshold}%）")
                
                # 预览将被合并的子公司
                with st.expander("预览将被合并的子公司", expanded=True):
                    for entity in subsidiaries_to_merge:
                        st.markdown(f"- **{entity['name']}**: {entity['percentage']:.2f}%")
                
                # 合并后的总比例
                total_percentage = sum(e["percentage"] for e in subsidiaries_to_merge)
                st.markdown(f"**合并后总比例**: {total_percentage:.2f}%")
                
                # 自定义合并后名称
                col1, col2 = st.columns([2, 1])
                with col1:
                    merged_name = st.text_input(
                        "合并后子公司名称",
                        value="其他子公司",
                        help="可以自定义合并后的子公司名称",
                        key="subsidiary_merged_name"
                    )
                
                # 确认合并按钮
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✅ 确认合并子公司", type="primary", use_container_width=True, key="subsidiary_merge_confirm"):
                        if not merged_name.strip():
                            st.error("请输入合并后的子公司名称")
                        else:
                            # 创建合并实体
                            merged_entity = {
                                "merged_name": merged_name,
                                "total_percentage": total_percentage,
                                "entities": subsidiaries_to_merge,
                                "merge_type": "threshold",
                                "threshold": threshold,
                                "entity_type": "subsidiary"
                            }
                            
                            # 添加到合并列表
                            st.session_state.merged_entities.append(merged_entity)
                            
                            # 将原实体添加到隐藏列表
                            for entity in subsidiaries_to_merge:
                                if entity["name"] not in st.session_state.hidden_entities:
                                    st.session_state.hidden_entities.append(entity["name"])
                            
                            st.success(f"✅ 已合并 {len(subsidiaries_to_merge)} 个子公司为 '{merged_name}'")
                            st.rerun()
                
                with col2:
                    if st.button("取消", use_container_width=True, key="subsidiary_merge_cancel"):
                        st.info("已取消子公司合并操作")
            else:
                st.warning(f"没有找到持股比例小于 {threshold}% 的子公司")
        
        else:  # 手动选择合并子公司
            st.markdown("#### 手动选择要合并的子公司")
            
            # 显示可选子公司列表
            available_subsidiaries = [e for e in mergeable_subsidiaries 
                                     if e["name"] not in st.session_state.hidden_entities]
            
            if not available_subsidiaries:
                st.warning("没有可用的子公司进行合并")
            else:
                # 初始化选中状态
                if 'selected_subsidiaries_for_merge' not in st.session_state:
                    st.session_state.selected_subsidiaries_for_merge = []
                
                # 创建复选框形式的子公司选择器
                st.markdown("**选择要合并的子公司（勾选复选框）：**")
                
                # 使用复选框列表而不是data_editor
                selected_subsidiaries = []
                
                # 创建复选框容器
                checkbox_container = st.container()
                
                with checkbox_container:
                    for i, entity in enumerate(available_subsidiaries):
                        col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                        
                        with col1:
                            # 使用独立的checkbox，每个都有唯一的key
                            is_selected = st.checkbox(
                                "",
                                value=entity["name"] in st.session_state.selected_subsidiaries_for_merge,
                                key=f"subsidiary_checkbox_{entity['name']}_{i}",
                                help=f"选择 {entity['name']}"
                            )
                            
                        with col2:
                            st.write(f"**{entity['name']}**")
                            
                        with col3:
                            st.write(f"{entity['percentage']:.2f}%")
                        
                        if is_selected:
                            selected_subsidiaries.append(entity["name"])
                
                # 更新选中状态
                st.session_state.selected_subsidiaries_for_merge = selected_subsidiaries
                
                if selected_subsidiaries:
                    # 获取选中的子公司详情
                    subsidiaries_to_merge = [e for e in available_subsidiaries if e["name"] in selected_subsidiaries]
                    
                    st.markdown("---")
                    st.markdown("#### 📋 子公司合并预览")
                    
                    # 预览选中的子公司
                    with st.expander("预览选中的子公司", expanded=True):
                        for entity in subsidiaries_to_merge:
                            st.markdown(f"- **{entity['name']}**: {entity['percentage']:.2f}%")
                    
                    # 合并后的总比例
                    total_percentage = sum(e["percentage"] for e in subsidiaries_to_merge)
                    st.markdown(f"**合并后总比例**: {total_percentage:.2f}%")
                    
                    # 自定义合并后名称
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        merged_name = st.text_input(
                            "合并后子公司名称",
                            value="其他子公司",
                            key="manual_subsidiary_merge_name",
                            help="可以自定义合并后的子公司名称"
                        )
                    
                    # 确认合并按钮
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ 确认合并子公司", type="primary", use_container_width=True, key="manual_subsidiary_merge_confirm"):
                            if not merged_name.strip():
                                st.error("请输入合并后的子公司名称")
                            else:
                                # 创建合并实体
                                merged_entity = {
                                    "merged_name": merged_name,
                                    "total_percentage": total_percentage,
                                    "entities": subsidiaries_to_merge,
                                    "merge_type": "manual",
                                    "entity_type": "subsidiary"
                                }
                                
                                # 添加到合并列表
                                st.session_state.merged_entities.append(merged_entity)
                                
                                # 将原实体添加到隐藏列表
                                for entity in subsidiaries_to_merge:
                                    if entity["name"] not in st.session_state.hidden_entities:
                                        st.session_state.hidden_entities.append(entity["name"])
                                
                                # 清空选中状态
                                st.session_state.selected_subsidiaries_for_merge = []
                                
                                st.success(f"✅ 已合并 {len(subsidiaries_to_merge)} 个子公司为 '{merged_name}'")
                                st.rerun()
                    
                    with col2:
                        if st.button("取消", use_container_width=True, key="manual_subsidiary_merge_cancel"):
                            st.session_state.selected_subsidiaries_for_merge = []
                            st.info("已取消子公司合并操作")
                else:
                    st.info("请在上方表格中勾选要合并的子公司")

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
                filtered_entities_info = []  # 收集过滤信息
                
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
                    filter_reason = ""
                    
                    # 检查是否为实际控制人（不应该被过滤）
                    is_actual_controller = entity_name == data_for_mermaid.get("controller", "")
                    
                    # 检查是否为明确不需要的实体（如空名称、无效数据等）
                    if not entity_name or entity_name.strip() == "":
                        should_filter = True
                        filter_reason = "空名称实体"
                    elif entity.get("percentage", 0) <= 0 and not is_actual_controller:
                        # 实际控制人即使持股比例为0也不应该被过滤
                        should_filter = True
                        filter_reason = f"无持股比例的实体: {entity_name}"
                    
                    if should_filter:
                        filtered_entities_info.append(f"❌ 过滤掉无效实体: {entity_name}")
                    else:
                        # 正常股东，保留
                        filtered_top_entities.append(entity)
                        if has_relationship:
                            filtered_entities_info.append(f"✅ 保留有关系的股东: {entity_name}")
                        else:
                            filtered_entities_info.append(f"✅ 保留正常股东（将自动生成关系）: {entity_name}")
                
                # 统一显示过滤调试信息
                if filtered_entities_info:
                    with st.expander("🔍 过滤调试信息", expanded=False):
                        for info in filtered_entities_info:
                            st.write(info)
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 🔥 特殊处理：检查是否有被过滤掉的合并实体需要恢复
                with st.expander("🔍 合并实体调试信息", expanded=False):
                    st.write(f"检查是否有被过滤掉的合并实体")
                    for entity in st.session_state.equity_data.get("top_level_entities", []):
                        entity_name = entity.get("name", "")
                        if entity_name not in [e["name"] for e in filtered_top_entities]:
                            # 检查是否在合并实体中
                            is_merged_entity = False
                            for merged in st.session_state.get("merged_entities", []):
                                if merged.get("merged_name") == entity_name:
                                    is_merged_entity = True
                                    st.write(f"发现被过滤的合并实体: {entity_name}")
                                    # 恢复合并实体
                                    filtered_top_entities.append(entity)
                                    break
                            
                            if not is_merged_entity:
                                st.write(f"被过滤的非合并实体: {entity_name}")
                
                data_for_mermaid["top_entities"] = filtered_top_entities
                
                # 应用合并规则
                with st.expander("🔍 合并规则调试信息", expanded=False):
                    st.write(f"检查合并实体 - merged_entities: {st.session_state.get('merged_entities', [])}")
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
                        if merged.get("entity_type") == "shareholder" or any(e["type"] == "shareholder" for e in merged["entities"]):
                            # 如果包含股东，添加到top_entities
                            merged_filtered_top_entities.append({
                                "name": merged["merged_name"],
                                "type": "company",
                                "percentage": merged["total_percentage"]
                            })
                        elif merged.get("entity_type") == "subsidiary" or all(e["type"] == "subsidiary" for e in merged["entities"]):
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
                    # 🔍 调试信息：显示传递给Mermaid的数据（收起）
                    with st.expander("🔍 Mermaid数据调试信息", expanded=False):
                        st.write("传递给Mermaid的数据:")
                        st.write(f"controller: '{data_for_mermaid['controller']}'")
                        st.write(f"actual_controller: '{st.session_state.equity_data.get('actual_controller', '')}'")
                        st.write(f"top_entities: {data_for_mermaid['top_entities']}")
                        st.write(f"all_entities: {data_for_mermaid['all_entities']}")
                        st.write(f"entity_relationships: {data_for_mermaid['entity_relationships']}")
                        st.write(f"control_relationships: {data_for_mermaid['control_relationships']}")
                        
                        # 检查实际控制人是否在top_entities中
                        controller_name = data_for_mermaid['controller']
                        if controller_name:
                            controller_in_top = any(e.get('name') == controller_name for e in data_for_mermaid['top_entities'])
                            controller_in_all = any(e.get('name') == controller_name for e in data_for_mermaid['all_entities'])
                            st.write(f"实际控制人 '{controller_name}' 在top_entities中: {controller_in_top}")
                            st.write(f"实际控制人 '{controller_name}' 在all_entities中: {controller_in_all}")
                    
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
            st_mermaid(
                st.session_state.mermaid_code,
                key="unique_mermaid_chart",
                width="1900px",
                height="900px",
            )
            
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
