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
from src.utils.state_persistence import (
    apply_snapshot,
    autosave,
    find_autosave,
    list_autosaves,
    make_snapshot,
    sanitize_workspace_name,
)
from src.utils.alicloud_translator import get_access_key
from src.utils.translator_service import translate_text, QuotaExceededError
from src.utils.translation_usage import get_monthly_usage, set_month_limit, get_admin_password

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

# --- 文件名解析函数（用于自动创建实体关系） ---
def _detect_file_type_from_filename(filename: str) -> str:
    """
    从文件名检测文件类型
    
    Args:
        filename: 上传的文件名
        
    Returns:
        str: 'investment' (对外投资文件) 或 'shareholder' (股东文件) 或 'unknown'
    """
    if not filename:
        return 'unknown'
    
    filename_lower = filename.lower()
    
    # 对外投资关键词（移除宽泛的'投资'关键词，避免误判）
    investment_keywords = ['对外投资', '控制企业', '子公司', '被投资企业', '被投资', 'investment', 'subsidiary']
    # 股东关键词
    shareholder_keywords = ['股东', '发起人', '投资人', '投资方', 'shareholder', 'investor', '股东信息', '股东明细', '股东名单']
    
    # 🔥 修复逻辑：优先根据文件名后缀判断，而不是公司名称
    # 首先检查文件名后缀（"-"后面的部分）
    filename_parts = filename.split('-')
    if len(filename_parts) > 1:
        filename_suffix = '-'.join(filename_parts[1:]).lower()
        
        # 如果后缀包含股东关键词，判断为股东文件
        if any(kw in filename_suffix for kw in shareholder_keywords):
            return 'shareholder'
        # 如果后缀包含对外投资关键词，判断为对外投资文件
        elif any(kw in filename_suffix for kw in investment_keywords):
            return 'investment'
    
    # 如果后缀无法判断，再检查整个文件名
    # 优先匹配股东关键词（因为"投资人"也可能出现在股东文件中）
    if any(kw in filename_lower for kw in shareholder_keywords):
        return 'shareholder'
    elif any(kw in filename_lower for kw in investment_keywords):
        return 'investment'
    
    return 'unknown'

def _extract_company_name_from_filename(filename: str) -> str:
    """
    从文件名中提取公司名称
    
    处理流程（参考FILENAME_PARSING_IMPROVEMENTS.md）：
    1. 移除扩展名
    2. 移除序号前缀（^\d+_）
    3. 移除时间戳后缀（-\d{14}$）
    4. 按分隔符拆分
    5. 查找包含公司关键词的部分
    6. 返回清理后的公司名称
    
    Args:
        filename: 上传的文件名
        
    Returns:
        str: 提取的公司名称，如果无法提取则返回空字符串
    """
    import re
    
    if not filename:
        return ""
    
    # 1. 移除扩展名
    name = filename
    if '.' in name:
        name = name.rsplit('.', 1)[0]
    
    # 2. 移除序号前缀（如 "2_", "10_"）
    name = re.sub(r'^\d+_', '', name)
    
    # 3. 移除时间戳后缀（如 "-20251014164519"）
    name = re.sub(r'-\d{14}$', '', name)
    name = re.sub(r'-\d{8}$', '', name)  # 也处理8位日期格式
    
    # 4. 按分隔符拆分
    separators = ['-', '_', '—', '－', '–']
    parts = [name]
    for sep in separators:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(sep))
        parts = new_parts
    
    # 去除空白
    parts = [p.strip() for p in parts if p.strip()]
    
    # 5. 查找包含公司关键词的部分
    company_keywords = [
        '有限公司', '有限责任公司', '股份有限公司', '股份公司',
        '集团', '有限合伙', '合伙企业',
        'Co.', 'Ltd.', 'Corp.', 'Inc.', 'Limited', 'Corporation',
        '公司', '企业'
    ]
    
    # 优先查找包含明确公司关键词的部分
    for part in parts:
        for keyword in company_keywords:
            if keyword in part:
                # 找到了包含公司关键词的部分
                # 清理多余的后缀关键词（如"股东信息"、"对外投资"等）
                cleanup_keywords = [
                    '股东信息', '股东明细', '股东名单', '股东',
                    '对外投资', '投资', '控制企业', '子公司',
                    'shareholder', 'investor', 'investment', 'subsidiary'
                ]
                cleaned = part
                for ck in cleanup_keywords:
                    if cleaned.endswith(ck):
                        cleaned = cleaned[:-len(ck)].strip()
                
                if cleaned:
                    return cleaned
    
    # 如果没有找到明确的公司关键词，返回第一个非关键词的部分
    exclude_keywords = [
        '股东信息', '股东明细', '股东名单', '股东',
        '对外投资', '投资', '控制企业', '子公司',
        'shareholder', 'investor', 'investment', 'subsidiary'
    ]
    
    for part in parts:
        # 跳过仅包含排除关键词的部分
        if not any(ek in part.lower() for ek in [k.lower() for k in exclude_keywords]):
            if len(part) > 2:  # 至少3个字符
                return part
    
    # 实在找不到，返回第一个部分
    return parts[0] if parts else ""

def _infer_child_from_filename(filename: str) -> str:
    """
    股东文件：推断child实体（被投资的公司）
    
    从文件名中提取公司名称，该公司是被股东投资的对象
    例如："2_力诺电力集团股份有限公司-股东信息.xlsx" -> "力诺电力集团股份有限公司"
    
    Args:
        filename: 上传的文件名
        
    Returns:
        str: 被投资的公司名称
    """
    return _extract_company_name_from_filename(filename)

def _infer_parent_from_filename(filename: str) -> str:
    """
    对外投资文件：推断parent实体（投资方公司）
    
    从文件名中提取公司名称，该公司是对外投资的主体
    例如："4_力诺集团股份有限公司-对外投资.xlsx" -> "力诺集团股份有限公司"
    
    Args:
        filename: 上传的文件名
        
    Returns:
        str: 投资方的公司名称
    """
    return _extract_company_name_from_filename(filename)

def _batch_translate_entities(entity_list_key: str):
    """批量翻译指定实体列表中的中文名称为英文"""
    try:
        # 先检查阿里云翻译凭证，避免逐条报错
        access_key_id, access_key_secret = get_access_key()
        if not access_key_id or not access_key_secret:
            st.error("未找到阿里云翻译配置，请在环境变量或config.json中配置 AccessKey")
            return
        
        entities = st.session_state.equity_data.get(entity_list_key, [])
        if not entities:
            st.warning("没有找到需要翻译的实体")
            return
        
        # 统计需要翻译的实体
        need_translate = []
        for entity in entities:
            if not entity.get("english_name") and entity.get("name"):
                need_translate.append(entity)
        
        if not need_translate:
            st.info("所有实体都已有英文名称，无需翻译")
            return
        
        st.info(f"开始翻译 {len(need_translate)} 个实体的名称...")
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, entity in enumerate(need_translate):
            entity_name = entity.get("name", "")
            status_text.text(f"正在翻译: {entity_name}")
            
            try:
                translated_text = translate_text(entity_name, 'zh', 'en')
                if translated_text:
                    entity["english_name"] = translated_text
                    success_count += 1
            except QuotaExceededError:
                st.warning("当月翻译额度已用完，已跳过剩余翻译。")
                break
            except Exception as e:
                failed_count += 1
                st.warning(f"翻译异常: {entity_name} - {str(e)}")
            
            # 更新进度
            progress_bar.progress((i + 1) / len(need_translate))
            time.sleep(0.1)  # 避免API调用过快
        
        # 显示结果
        status_text.text("翻译完成")
        st.success(f"翻译完成！成功: {success_count}, 失败: {failed_count}, 跳过: {skipped_count}")
        
        # 将已翻译的英文名同步到所有相关实体列表，确保渲染可用
        _sync_english_names_across_lists()
        
        # 刷新页面
        st.rerun()
        
    except Exception as e:
        st.error(f"批量翻译过程中发生错误: {str(e)}")

def _batch_translate_all_entities():
    """批量翻译所有实体（包括top_level_entities、subsidiaries、all_entities等）"""
    try:
        # 先检查阿里云翻译凭证，避免逐条报错
        access_key_id, access_key_secret = get_access_key()
        if not access_key_id or not access_key_secret:
            st.error("未找到阿里云翻译配置，请在环境变量或config.json中配置 AccessKey")
            return
        
        # 收集所有需要翻译的实体
        all_entities_to_translate = []
        
        # 从各个实体列表中收集
        for entity_list_key in ["top_level_entities", "subsidiaries", "all_entities"]:
            entities = st.session_state.equity_data.get(entity_list_key, [])
            for entity in entities:
                if not entity.get("english_name") and entity.get("name"):
                    # 避免重复翻译同一个实体
                    entity_name = entity.get("name")
                    if not any(e["name"] == entity_name for e in all_entities_to_translate):
                        all_entities_to_translate.append({
                            "entity": entity,
                            "list_key": entity_list_key,
                            "name": entity_name
                        })
        
        # 核心公司
        core_company = st.session_state.equity_data.get("core_company", "")
        if core_company and not any(e["name"] == core_company for e in all_entities_to_translate):
            # 在all_entities中查找核心公司
            core_entity = None
            for entity in st.session_state.equity_data.get("all_entities", []):
                if entity.get("name") == core_company:
                    core_entity = entity
                    break
            
            if core_entity and not core_entity.get("english_name"):
                all_entities_to_translate.append({
                    "entity": core_entity,
                    "list_key": "all_entities",
                    "name": core_company
                })
        
        # 🔥 关键修复：从entity_relationships中收集需要翻译的实体名称
        entity_relationships = st.session_state.equity_data.get("entity_relationships", [])
        for rel in entity_relationships:
            parent_name = rel.get("parent", rel.get("from", ""))
            child_name = rel.get("child", rel.get("to", ""))
            
            # 检查parent实体是否需要翻译
            if parent_name and not any(e["name"] == parent_name for e in all_entities_to_translate):
                # 在all_entities中查找parent实体
                parent_entity = None
                for entity in st.session_state.equity_data.get("all_entities", []):
                    if entity.get("name") == parent_name:
                        parent_entity = entity
                        break
                
                if parent_entity and not parent_entity.get("english_name"):
                    all_entities_to_translate.append({
                        "entity": parent_entity,
                        "list_key": "all_entities",
                        "name": parent_name
                    })
            
            # 检查child实体是否需要翻译
            if child_name and not any(e["name"] == child_name for e in all_entities_to_translate):
                # 在all_entities中查找child实体
                child_entity = None
                for entity in st.session_state.equity_data.get("all_entities", []):
                    if entity.get("name") == child_name:
                        child_entity = entity
                        break
                
                if child_entity and not child_entity.get("english_name"):
                    all_entities_to_translate.append({
                        "entity": child_entity,
                        "list_key": "all_entities",
                        "name": child_name
                    })
        
        # 🔥 关键修复：从control_relationships中收集需要翻译的实体名称
        control_relationships = st.session_state.equity_data.get("control_relationships", [])
        for rel in control_relationships:
            controller_name = rel.get("parent", rel.get("from", rel.get("controller", "")))
            controlled_name = rel.get("child", rel.get("to", rel.get("controlled", "")))
            
            # 检查controller实体是否需要翻译
            if controller_name and not any(e["name"] == controller_name for e in all_entities_to_translate):
                # 在all_entities中查找controller实体
                controller_entity = None
                for entity in st.session_state.equity_data.get("all_entities", []):
                    if entity.get("name") == controller_name:
                        controller_entity = entity
                        break
                
                if controller_entity and not controller_entity.get("english_name"):
                    all_entities_to_translate.append({
                        "entity": controller_entity,
                        "list_key": "all_entities",
                        "name": controller_name
                    })
            
            # 检查controlled实体是否需要翻译
            if controlled_name and not any(e["name"] == controlled_name for e in all_entities_to_translate):
                # 在all_entities中查找controlled实体
                controlled_entity = None
                for entity in st.session_state.equity_data.get("all_entities", []):
                    if entity.get("name") == controlled_name:
                        controlled_entity = entity
                        break
                
                if controlled_entity and not controlled_entity.get("english_name"):
                    all_entities_to_translate.append({
                        "entity": controlled_entity,
                        "list_key": "all_entities",
                        "name": controlled_name
                    })
        
        if not all_entities_to_translate:
            st.info("所有实体都已有英文名称，无需翻译")
            return
        
        st.info(f"开始翻译 {len(all_entities_to_translate)} 个实体的名称...")
        
        success_count = 0
        failed_count = 0
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, item in enumerate(all_entities_to_translate):
            entity = item["entity"]
            entity_name = item["name"]
            status_text.text(f"正在翻译: {entity_name}")
            
            try:
                translated_text = translate_text(entity_name, 'zh', 'en')
                if translated_text:
                    entity["english_name"] = translated_text
                    success_count += 1
            except QuotaExceededError:
                st.warning("当月翻译额度已用完，已跳过剩余翻译。")
                break
            except Exception as e:
                failed_count += 1
                st.warning(f"翻译异常: {entity_name} - {str(e)}")
            
            # 更新进度
            progress_bar.progress((i + 1) / len(all_entities_to_translate))
            time.sleep(0.1)  # 避免API调用过快
        
        # 显示结果
        status_text.text("翻译完成")
        st.success(f"翻译完成！成功: {success_count}, 失败: {failed_count}")
        
        # 将已翻译的英文名同步到所有相关实体列表，确保渲染可用
        _sync_english_names_across_lists()
        
        # 刷新页面
        st.rerun()
        
    except Exception as e:
        st.error(f"批量翻译过程中发生错误: {str(e)}")

def _sync_english_names_across_lists():
    """在session_state的各实体列表之间按名称同步english_name。"""
    try:
        data = st.session_state.get("equity_data", {})
        lists = [
            data.get("top_level_entities", []),
            data.get("subsidiaries", []),
            data.get("all_entities", []),
        ]
        # 收集所有名称->英文名映射
        name_to_english = {}
        for entity_list in lists:
            for e in entity_list:
                name = e.get("name")
                en = e.get("english_name")
                if name and en:
                    name_to_english[name] = en
        # 将映射写回所有列表
        for entity_list in lists:
            for e in entity_list:
                name = e.get("name")
                if name in name_to_english and not e.get("english_name"):
                    e["english_name"] = name_to_english[name]
    except Exception:
        # 同步失败不应影响主流程
        pass

def _get_english_name_for(entity_name: str) -> str:
    """根据名称在各实体列表中查找并返回英文名（若存在）。"""
    data = st.session_state.get("equity_data", {})
    for e in data.get("all_entities", []):
        if e.get("name") == entity_name and e.get("english_name"):
            return e.get("english_name")
    for e in data.get("top_level_entities", []):
        if e.get("name") == entity_name and e.get("english_name"):
            return e.get("english_name")
    for e in data.get("subsidiaries", []):
        if e.get("name") == entity_name and e.get("english_name"):
            return e.get("english_name")
    return ""

def _format_cn_en(entity_name: str) -> str:
    """组合中文名与英文名用于UI显示。"""
    en = _get_english_name_for(entity_name)
    return f"{entity_name} / {en}" if en else entity_name

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

def render_page():
    """渲染手动编辑模式页面"""
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
    
        /* 设置侧边栏按钮背景为透明，文字为白色 */
        [data-testid="stSidebar"] button,[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],[data-testid="stSidebar"] [data-testid="stButton"] > button {
            background: transparent !important;
            background-color: transparent !important;
            color: #ffffff !important;  /* 白色文字 */
            border: none !important;
            box-shadow: none !important;
            opacity: 1 !important;
            background-image: none !important;
            border-radius: 0 !important;
            padding: 0.5rem 1rem !important;
        }
    
        /* 确保按钮内的所有内容都透明，文字为白色 */
        [data-testid="stSidebar"] button *,[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] * {
            background-color: transparent !important;
            background: transparent !important;
            box-shadow: none !important;
            color: #ffffff !important;  /* 保持白色一致 */
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
            background: rgba(0, 0, 0, 0.05) !important;  /* 浅灰背景 */
            background-color: rgba(0, 0, 0, 0.05) !important;
            color: #ffffff !important;  /* 悬停时保持白色文字 */
            box-shadow: none !important;
            transform: translateX(4px);
        }
    
        /* 密码输入框的眼睛图标按钮特殊样式 - 使用更高的权重 */
        [data-testid="stSidebar"] div[data-testid="stPasswordInput"] button,
        [data-testid="stSidebar"] input[type="password"] + div button,
        [data-testid="stSidebar"] button[kind="icon"],
        [data-testid="stSidebar"] button[data-testid="baseButton-icon"] {
            background: #0c3f98 !important;
            background-color: #0c3f98 !important;
            color: #ffffff !important;
            border: 1px solid rgba(12, 63, 152, 0.55) !important;
            border-radius: 6px !important;
            min-width: 2.4rem !important;
            height: 2.4rem !important;
            box-shadow: 0 2px 4px rgba(12, 63, 152, 0.2) !important;
        }
    
        /* 眼睛图标的颜色 */
        [data-testid="stSidebar"] div[data-testid="stPasswordInput"] button svg,
        [data-testid="stSidebar"] input[type="password"] + div button svg,
        [data-testid="stSidebar"] button[kind="icon"] svg {
            color: #ffffff !important;
            fill: #ffffff !important;
        }
    
        /* 密码输入框眼睛图标按钮的悬停效果 */
        [data-testid="stSidebar"] div[data-testid="stPasswordInput"] button:hover,
        [data-testid="stSidebar"] input[type="password"] + div button:hover,
        [data-testid="stSidebar"] button[kind="icon"]:hover {
            background: #0a2d6b !important;
            background-color: #0a2d6b !important;
            transform: none !important; /* 覆盖通用悬停效果 */
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
        with st.sidebar.expander("ℹ️ 使用说明", expanded=False):
            st.write("## 使用说明")
            st.write("1. **设置核心公司**：输入公司名称")
            st.write("2. **添加主要股东**：录入股东及持股比例")
            st.write("3. **添加子公司**：维护子公司名称及信息")
            st.write("4. **补充数据**：完善注册资本、成立日期等辅助字段")
            st.write("5. **整理结构**：使用右侧工具调整图谱层级")
            st.write("6. **生成图表**：生成后可在主页面预览 Mermaid / HTML 图")
            st.write("7. **导出数据**：支持导出 Mermaid 代码、JSON、HTML")

            st.write("### 翻译额度管理")
            try:
                usage = get_monthly_usage()
                used = usage.get('used', 0)
                limit = usage.get('limit', 0)
                remaining = max(0, limit - used)
                st.write(f"**本月已用/额度：** {used} / {limit}（剩余 {remaining}）")

                admin_pwd = st.text_input("管理员密码", type="password", key="translation_admin_pwd")
                adjust = st.number_input("调整阈值（正数增加/负数减少）", min_value=-5000, max_value=5000, step=1000, value=0, key="translation_adjust_delta")
                if st.button("应用阈值调整", key="apply_translation_limit_change"):
                    if admin_pwd == get_admin_password():
                        new_limit = max(0, int(limit) + int(adjust))
                        result = set_month_limit(new_limit, actor="admin", reason="sidebar adjust")
                        st.success(f"阈值已更新：{result['old']} → {result['new']}")
                    else:
                        st.error("密码错误")
            except Exception as e:
                st.error(f"翻译额度管理加载失败: {str(e)}")

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
            
                # 过滤掉隐藏实体的关系和被隐藏的关系
                filtered_entity_relationships = []
                for rel in st.session_state.equity_data["entity_relationships"]:
                    from_entity = rel.get("from", rel.get("parent", ""))
                    to_entity = rel.get("to", rel.get("child", ""))
                
                    # 检查关系是否被隐藏
                    rel_id = f"{from_entity}→{to_entity}"
                    is_hidden_relationship = rel_id in st.session_state.get("hidden_relationships", [])
                
                    # 如果关系中的实体都没有被隐藏，且关系本身没有被隐藏，则保留这个关系
                    if (from_entity not in st.session_state.get("hidden_entities", []) and 
                        to_entity not in st.session_state.get("hidden_entities", []) and
                        not is_hidden_relationship):
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
                        st.text(f"{i+1}. {_format_cn_en(from_e)} -> {_format_cn_en(to_e)} ({pct}%)")
                
                    st.write("**Control Relationships (控制关系):**")
                    for i, rel in enumerate(data_for_chart['control_relationships'][:20]):
                        from_e = rel.get("from", rel.get("parent", ""))
                        to_e = rel.get("to", rel.get("child", ""))
                        desc = rel.get("description", "控制")
                        st.text(f"{i+1}. {_format_cn_en(from_e)} -> {_format_cn_en(to_e)} ({desc})")
                
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
                    core_company_name = st.session_state.equity_data.get("core_company", "股权结构图")
                    page_title = f"{core_company_name} - 交互式HTML股权结构图"
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
            
                core_company_name = st.session_state.equity_data.get("core_company", "股权结构图")
                page_title = f"{core_company_name} - 交互式HTML股权结构图"
                html_content = generate_fullscreen_visjs_html(nodes, edges,
                                                            level_separation=level_separation,
                                                            node_spacing=node_spacing,
                                                            tree_spacing=tree_spacing,
                                                            subgraphs=subgraphs,
                                                            page_title=page_title)
                # 使用核心公司名称作为下载文件名
                safe_filename = core_company_name.replace(" ", "_").replace("/", "_")
                if st.download_button(
                    label="📥 下载HTML图表",
                    data=html_content.encode('utf-8'),
                    file_name=f"{safe_filename}_股权结构图.html",
                    mime="text/html; charset=utf-8",
                    use_container_width=True,
                    key="download_html_visjs"
                ):
                    st.success("HTML文件已下载")
        
            # 显示图表
            st.markdown("#### 🎯 交互式股权结构图")
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
                    core_company_name = st.session_state.equity_data.get("core_company", "股权结构图")
                    page_title = f"{core_company_name} - 交互式HTML股权结构图"
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
            st.markdown("#### 📈 图表数据预览")
            preview_col1, preview_col2 = st.columns(2)
        
            with preview_col1:
                st.markdown("**节点列表**")
                # 🔥 按层级从高到低排序（-4最高，0最低）
                sorted_nodes = sorted(nodes, key=lambda x: x.get('level', 0), reverse=False)
                for i, node in enumerate(sorted_nodes):  # 显示所有节点
                    label = node.get('label', '未命名')
                    level = node.get('level', 'N/A')
                    st.text(f"{i+1}. {label} (层级: {level})")
        
            with preview_col2:
                st.markdown("**关系列表**")
                # 🔥 按起始节点的层级排序，与节点列表顺序保持一致
                sorted_edges = sorted(edges, key=lambda edge: nodes[edge['from']].get('level', 0))
                for i, edge in enumerate(sorted_edges):  # 显示所有关系
                    from_node = nodes[edge['from']]['label']
                    to_node = nodes[edge['to']]['label']
                    label = edge.get('label', '')
                    st.text(f"{i+1}. {from_node} → {to_node} ({label})")
        
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
        st.session_state.core_company = ""
    if "dashscope_api_key" not in st.session_state:
        st.session_state.dashscope_api_key = ""
    if "equity_data" not in st.session_state:
        st.session_state.equity_data = {
            "core_company": "",
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
    
        /* Mermaid图表自适应样式 */
        iframe[title="streamlit_mermaid.st_mermaid"] {
            width: 100% !important;
            min-height: 800px !important;
            height: auto !important;
            border: none !important;
        }
    
        .stMarkdown svg {
            width: 100% !important;
            height: auto !important;
            max-width: 100% !important;
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
        
            /* 移动端Mermaid图表优化 */
            iframe[title="streamlit_mermaid.st_mermaid"] {
                font-size: 12px !important;
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
        # 🔥 修复：确保equity_data始终存在且不为None
        if 'equity_data' not in st.session_state or st.session_state.equity_data is None:
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
                    # 🔥 改进核心公司名称获取逻辑
                    core_company_name = ""
                    try:
                        equity_data = st.session_state.get("equity_data", {}) or {}
                        core_company_name = equity_data.get("core_company", "") or ""
                    except Exception:
                        core_company_name = ""
                
                    # 🔥 扩展占位符检查，包含更多空值情况
                    placeholders = {
                        "未命名公司", "未命名", "Unnamed", "N/A", "None", "null", 
                        "", " ", "  ", "　", "未设置", "待设置", "请输入", "请填写",
                        "公司名称", "企业名称", "核心公司", "目标公司"
                    }
                
                    # 🔥 改进核心公司名称验证逻辑
                    cc_valid = ""
                    if core_company_name and isinstance(core_company_name, str):
                        cc_clean = core_company_name.strip()
                        if cc_clean and cc_clean not in placeholders and len(cc_clean) > 1:
                            cc_valid = cc_clean
                
                    # 🔥 改进工作区名称生成逻辑
                    existing_ws = st.session_state.get("workspace_name", "")
                    if existing_ws and not existing_ws.startswith("workspace-"):
                        # 如果已有非workspace的工作区名称，优先使用
                        default_ws = existing_ws
                    elif cc_valid:
                        # 如果有有效的核心公司名称，使用它
                        default_ws = cc_valid
                    else:
                        # 最后才使用workspace-时间戳
                        default_ws = f"workspace-{time.strftime('%Y%m%d-%H%M')}"
                
                    # 🔥 添加调试信息
                    if st.checkbox("🔍 显示工作区命名调试信息", key="debug_ws_naming"):
                        st.write(f"**调试信息：**")
                        st.write(f"- 原始核心公司名称: `{core_company_name}`")
                        st.write(f"- 清理后核心公司名称: `{cc_valid}`")
                        st.write(f"- 现有工作区名称: `{existing_ws}`")
                        st.write(f"- 最终默认工作区名称: `{default_ws}`")
                
                    ws_key = "ws_name_rel_top"
                    if "_workspace_origin" not in st.session_state:
                        st.session_state["_workspace_origin"] = "auto"

                    if st.session_state.get("_workspace_origin") != "manual":
                        if cc_valid:
                            current_ws_state = st.session_state.get("workspace_name", "")
                            if sanitize_workspace_name(current_ws_state) != sanitize_workspace_name(cc_valid):
                                st.session_state["workspace_name"] = cc_valid
                                st.session_state["_workspace_origin"] = "auto"
                                st.session_state[ws_key] = cc_valid
                        elif not st.session_state.get("workspace_name"):
                            st.session_state["workspace_name"] = default_ws
                            st.session_state[ws_key] = default_ws

                    if ws_key not in st.session_state:
                        st.session_state[ws_key] = st.session_state.get("workspace_name", default_ws)

                    ws = st.text_input("工作区名称", value=st.session_state[ws_key], key=ws_key)
                    if ws != st.session_state.get("workspace_name"):
                        st.session_state["workspace_name"] = ws

                    if cc_valid:
                        if sanitize_workspace_name(ws) == sanitize_workspace_name(cc_valid):
                            st.session_state["_workspace_origin"] = "auto"
                        elif ws.strip():
                            st.session_state["_workspace_origin"] = "manual"
                    elif ws.strip():
                        st.session_state["_workspace_origin"] = "manual"

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
                    st.caption("检测到变更后约 5 秒写入本地，并保留最近 10 个历史版本。")
                    last_path = st.session_state.get("_last_autosave_path")
                    if last_path:
                        saved_at = st.session_state.get("_last_autosave_saved_at")
                        saved_label = saved_at or "时间未知"
                        st.caption(f"最近自动保存：{saved_label} · `{last_path}`")

                # 🔥 改进自动保存触发逻辑
                try:
                    if st.session_state.get("current_step"):
                        # 🔥 智能工作区名称生成
                        current_ws = st.session_state.get("workspace_name", "")
                        if not current_ws or current_ws.startswith("workspace-"):
                            # 尝试从核心公司名称生成更好的工作区名称
                            try:
                                equity_data = st.session_state.get("equity_data", {}) or {}
                                core_company = equity_data.get("core_company", "") or ""
                                if core_company and core_company.strip() and len(core_company.strip()) > 1:
                                    # 清理核心公司名称作为工作区名称
                                    clean_name = core_company.strip()
                                    placeholders = {
                                        "未命名公司", "未命名", "Unnamed", "N/A", "None", "null", 
                                        "", " ", "  ", "　", "未设置", "待设置", "请输入", "请填写",
                                        "公司名称", "企业名称", "核心公司", "目标公司"
                                    }
                                    if clean_name not in placeholders:
                                        st.session_state["workspace_name"] = clean_name
                                        current_ws = clean_name
                            except Exception:
                                pass
                    
                        if current_ws:
                            last = st.session_state.get("_last_autosave_ts", 0.0)
                            if st.session_state.get("auto", True) and (time.time() - last) > 5:
                                snapshot_to_save = make_snapshot()
                                sanitized_ws = sanitize_workspace_name(current_ws)
                                path, created = autosave(snapshot_to_save, sanitized_ws)
                                prev_path = st.session_state.get("_last_autosave_path")
                                if created or str(path) != prev_path:
                                    st.session_state["_last_autosave_path"] = str(path)
                                st.session_state["_last_autosave_ts"] = time.time()
                                st.session_state["_last_autosave_saved_at"] = snapshot_to_save.get("saved_at")
                except Exception:
                    pass

                # 自动保存历史与恢复
                try:
                    ws_for_history = st.session_state.get("workspace_name", "default")
                    history = list_autosaves(ws_for_history, limit=10)
                except Exception:
                    history = []
                if history and "_autosave_prefetched" not in st.session_state:
                    st.session_state["_autosave_prefetched"] = True
                    st.session_state["_pending_autosave_path"] = str(history[0]["path"])
                    st.session_state.setdefault("_last_autosave_ts", time.time())
                if history:
                    expanded = not st.session_state.get("_autosave_history_seen", False)
                    with st.expander("查看自动保存历史", expanded=expanded):
                        st.session_state["_autosave_history_seen"] = True
                        st.caption("保留最近 10 个版本，内容未变化时不会重复写入。")
                        for idx, entry in enumerate(history):
                            saved_label = entry.get("saved_at") or "时间未知"
                            size_value = entry.get("size")
                            size_label = f"{size_value / 1024:.1f} KB" if size_value else "大小未知"
                            filename = entry.get("filename") or f"autosave-{idx}.json"
                            try:
                                raw_content = entry["path"].read_text(encoding="utf-8")
                            except Exception:
                                raw_content = None
                            cols = st.columns([4, 1, 1], gap="small")
                            with cols[0]:
                                st.write(f"{saved_label} · {filename} · {size_label}")
                            with cols[1]:
                                if st.button("恢复", key=f"restore_autosave_{idx}"):
                                    if raw_content is None:
                                        st.error("读取自动保存文件失败")
                                    else:
                                        try:
                                            snap = json.loads(raw_content)
                                            ok, msg = apply_snapshot(snap)
                                            st.success(msg) if ok else st.error(msg)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"恢复失败: {e}")
                            with cols[2]:
                                if raw_content is not None:
                                    st.download_button(
                                        "下载",
                                        data=raw_content.encode("utf-8"),
                                        file_name=filename,
                                        mime="application/json",
                                        key=f"download_autosave_{idx}",
                                    )
                                else:
                                    st.caption("不可用")
                else:
                    st.caption("暂无自动保存记录，完成一次编辑后将自动生成。")
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

    # 🔥 安全检查函数：确保equity_data不为None
    def ensure_equity_data():
        """确保equity_data存在且不为None，如果为None则重新初始化"""
        if 'equity_data' not in st.session_state or st.session_state.equity_data is None:
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
            st.warning("检测到数据异常，已自动重新初始化")
            return True  # 表示重新初始化了
        return False  # 表示数据正常

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

    # 🔥 安全检查：确保equity_data不为None
    ensure_equity_data()

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
                # 清理工作区与自动保存相关状态，避免残留旧公司名称
                st.session_state["workspace_name"] = f"workspace-{time.strftime('%Y%m%d-%H%M')}"
                st.session_state["_workspace_origin"] = "auto"
                # 清除自动保存指针/状态
                for _k in [
                    "_last_autosave_path",
                    "_last_autosave_ts",
                    "_last_autosave_saved_at",
                    "_pending_autosave_path",
                    "_autosave_prefetched",
                    "_autosave_history_seen",
                    "ws_name_rel_top",
                ]:
                    if _k in st.session_state:
                        del st.session_state[_k]
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
        # 🔥 安全检查：确保equity_data不为None
        ensure_equity_data()
    
        st.subheader("📌 设置核心公司（Obligor）")
    
        with st.form("core_company_form"):
            core_company = st.text_input(
                "核心公司名称", 
                value=st.session_state.equity_data.get("core_company", ""),
                placeholder="请输入核心公司名称（如：Vastec Medical Equipment (Shanghai) Co., Ltd）"
            )
        
            controller = st.text_input(
                "实际控制人（可选）", 
                value=st.session_state.equity_data.get("actual_controller", ""),
                placeholder="请输入实际控制人名称（如：Collective control 或 个人/公司名称）"
            )
        
            # 新增：核心公司英文名/注册资本/成立日期
            _core_entity = None
            try:
                _core_name_current = st.session_state.equity_data.get("core_company", "")
                for _e in st.session_state.equity_data.get("all_entities", []):
                    if _e.get("name") == _core_name_current:
                        _core_entity = _e
                        break
            except Exception:
                _core_entity = None
            # 🔥 修复：安全访问_core_entity的属性
            english_name_core_default = ""
            registration_capital_core_default = ""
            if _core_entity:
                english_name_core_default = _core_entity.get("english_name", "") or ""
                registration_capital_core_default = (_core_entity.get("registration_capital") or _core_entity.get("registered_capital", "")) or ""
            _date_default = None
            try:
                _date_str = (_core_entity.get("establishment_date") or _core_entity.get("established_date")) if _core_entity else None
                if _date_str:
                    from datetime import datetime as _dt
                    _date_default = _dt.strptime(_date_str, "%Y-%m-%d").date()
            except Exception:
                _date_default = None
            english_name_core = st.text_input("核心公司英文名称（可选）", value=english_name_core_default)
            registration_capital_core = st.text_input("核心公司注册资本（可选）", value=registration_capital_core_default)
            establishment_date_core = st.date_input("核心公司成立日期（可选）", value=_date_default)
        
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.form_submit_button("保存并继续", type="primary"):
                    if core_company.strip():
                        # 保存旧的核心公司名称
                        old_core_company = st.session_state.equity_data["core_company"]
                    
                        # 更新核心公司信息
                        st.session_state.equity_data["core_company"] = core_company
                        st.session_state.equity_data["actual_controller"] = controller
                    
                        # 🔥 自动更新工作区名称
                        if core_company.strip():
                            current_ws = st.session_state.get("workspace_name", "")
                            workspace_origin = st.session_state.get("_workspace_origin", "auto")
                            new_ws = core_company.strip()
                            should_update_ws = (
                                not current_ws
                                or current_ws.startswith("workspace-")
                                or workspace_origin != "manual"
                            )
                            if should_update_ws:
                                st.session_state["workspace_name"] = new_ws
                                st.session_state["_workspace_origin"] = "auto"
                                st.session_state["ws_name_rel_top"] = new_ws
                                if current_ws != new_ws:
                                    st.success(f"工作区别名已同步为核心公司：{new_ws}")
                    
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
                    
                        # 更新/插入核心公司到 all_entities，并写入可选字段
                        def _upsert_core_company_entity(old_name: str, new_name: str):
                            ae = st.session_state.equity_data.get("all_entities", [])
                            # 如果名称变化，先尝试更新旧名称的记录到新名称
                            updated = False
                            for ent in ae:
                                if ent.get("name") == old_name and old_name:
                                    ent["name"] = new_name
                                    ent["type"] = "company"
                                    if english_name_core.strip():
                                        ent["english_name"] = english_name_core.strip()
                                    if registration_capital_core.strip():
                                        ent["registration_capital"] = registration_capital_core.strip()
                                    if establishment_date_core:
                                        ent["establishment_date"] = establishment_date_core.strftime("%Y-%m-%d")
                                    updated = True
                                    break
                            # 若未更新到旧记录，则查找是否已有新名称记录
                            if not updated:
                                for ent in ae:
                                    if ent.get("name") == new_name:
                                        ent["type"] = "company"
                                        if english_name_core.strip():
                                            ent["english_name"] = english_name_core.strip()
                                        if registration_capital_core.strip():
                                            ent["registration_capital"] = registration_capital_core.strip()
                                        if establishment_date_core:
                                            ent["establishment_date"] = establishment_date_core.strftime("%Y-%m-%d")
                                        updated = True
                                        break
                            # 若仍未找到，则插入新记录
                            if not updated and new_name:
                                new_ent = {"name": new_name, "type": "company"}
                                if english_name_core.strip():
                                    new_ent["english_name"] = english_name_core.strip()
                                if registration_capital_core.strip():
                                    new_ent["registration_capital"] = registration_capital_core.strip()
                                if establishment_date_core:
                                    new_ent["establishment_date"] = establishment_date_core.strftime("%Y-%m-%d")
                                ae.append(new_ent)
                            st.session_state.equity_data["all_entities"] = ae

                        _upsert_core_company_entity(old_core_company, core_company)

                        # 如果填写了实际控制人，则将其映射到顶级实体与所有实体，便于在关系步骤中选择
                        if controller and not any(e.get("name") == controller for e in st.session_state.equity_data.get("top_level_entities", [])):
                            st.session_state.equity_data["top_level_entities"].append({
                                "name": controller,
                                "type": "person",
                                "percentage": 0.0
                            })
                        if controller and not any(e.get("name") == controller for e in st.session_state.equity_data.get("all_entities", [])):
                            st.session_state.equity_data["all_entities"].append({"name": controller, "type": "person"})

                        # 将可能更新的核心公司可选字段传播到同名实体（所有列表）
                        try:
                            def _propagate_core_fields(entity_name: str):
                                updates = {}
                                if english_name_core.strip():
                                    updates["english_name"] = english_name_core.strip()
                                if registration_capital_core.strip():
                                    updates["registration_capital"] = registration_capital_core.strip()
                                if establishment_date_core:
                                    updates["establishment_date"] = establishment_date_core.strftime("%Y-%m-%d")
                                if not updates:
                                    return
                                data = st.session_state.equity_data
                                for list_key in ["top_level_entities", "subsidiaries", "all_entities"]:
                                    for ent in data.get(list_key, []):
                                        if ent.get("name") == entity_name:
                                            ent.update(updates)
                            _propagate_core_fields(core_company)
                        except Exception:
                            pass
                    
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
                st.markdown("### 📁 已上传的文件")
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
                                        st.markdown("### ❌ 验证错误")
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
                                        st.markdown("#### 🔍 数据完整性检查")
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
        # 🔥 安全检查：确保equity_data不为None
        ensure_equity_data()
    
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
    
        # 已添加的顶级实体/股东列表已移动至页面底部显示
    
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

                    # 新增：英文名、注册资本、成立日期可编辑
                    english_name_val = st.text_input("英文名称（可选）", value=entity.get("english_name", ""))
                    registration_capital_val = st.text_input("注册资本（可选）", value=entity.get("registration_capital", ""))
                    # 将字符串日期解析为date对象
                    existing_date_str = entity.get("establishment_date") or entity.get("established_date")
                    existing_date = None
                    try:
                        if existing_date_str:
                            from datetime import datetime as _dt
                            existing_date = _dt.strptime(existing_date_str, "%Y-%m-%d").date()
                    except Exception:
                        existing_date = None
                    establishment_date_val = st.date_input("成立日期（可选）", value=existing_date)
                
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.form_submit_button("保存修改", type="primary"):
                            if name.strip():
                                # 更新实体信息
                                old_name = entity["name"]
                                st.session_state.equity_data["top_level_entities"][editing_index]["name"] = name
                                st.session_state.equity_data["top_level_entities"][editing_index]["percentage"] = percentage
                                st.session_state.equity_data["top_level_entities"][editing_index]["type"] = entity_type
                                # 写回可选字段
                                if english_name_val.strip():
                                    st.session_state.equity_data["top_level_entities"][editing_index]["english_name"] = english_name_val.strip()
                                if registration_capital_val.strip():
                                    st.session_state.equity_data["top_level_entities"][editing_index]["registration_capital"] = registration_capital_val.strip()
                                if establishment_date_val:
                                    st.session_state.equity_data["top_level_entities"][editing_index]["establishment_date"] = establishment_date_val.strftime("%Y-%m-%d")
                            
                                # 更新all_entities
                                for e in st.session_state.equity_data["all_entities"]:
                                    if e["name"] == old_name:
                                        e["name"] = name
                                        e["type"] = entity_type
                                        # 同步英文名/注册资本/成立日期
                                        if english_name_val.strip():
                                            e["english_name"] = english_name_val.strip()
                                        if registration_capital_val.strip():
                                            e["registration_capital"] = registration_capital_val.strip()
                                        if establishment_date_val:
                                            e["establishment_date"] = establishment_date_val.strftime("%Y-%m-%d")
                                        break

                                # 将修改过的可选字段传播到同名实体（所有列表）
                                def _propagate_entity_fields(entity_name: str, updates: dict):
                                    data = st.session_state.get("equity_data", {})
                                    for list_key in ["top_level_entities", "subsidiaries", "all_entities"]:
                                        for ent in data.get(list_key, []):
                                            if ent.get("name") == entity_name:
                                                for k, v in updates.items():
                                                    if v is not None and v != "":
                                                        ent[k] = v
                                _propagate_entity_fields(name, {
                                    "english_name": english_name_val.strip(),
                                    "registration_capital": registration_capital_val.strip(),
                                    "establishment_date": establishment_date_val.strftime("%Y-%m-%d") if establishment_date_val else "",
                                })
                            
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
            with st.expander("🗂️ 从Excel导入股东信息（单个文件）", expanded=False):
                st.info("上传 Excel 文件，系统将自动/手动映射列，并支持按'登记状态'跳过注销/吊销的记录。")
        
                # 🔥 添加文件类型指导
                with st.expander("📋 文件类型选择指导", expanded=False):
                    st.markdown("""
                **请根据您的文件内容选择正确的导入功能：**
            
                **📊 股东信息导入**（当前功能）：
                - 文件名示例：`公司A-股东信息.xlsx`
                - 文件内容：公司A的股东列表
                - 关系方向：Excel中的股东 → 公司A
            
                **🏢 子公司导入**（下方功能）：
                - 文件名示例：`公司A-对外投资.xlsx` 或 `公司A-子公司.xlsx`
                - 文件内容：公司A投资的子公司列表
                - 关系方向：公司A → Excel中的子公司
            
                **⚠️ 如果您的文件名包含"对外投资"、"子公司"等关键词，请使用下方的"子公司导入"功能！**
                """)
        
                # 🔥 添加清除缓存按钮
                if st.button("🔄 清除文件类型检测缓存", help="如果文件类型检测有误，点击此按钮清除缓存"):
                    # 清除可能的缓存
                    if hasattr(st.session_state, 'file_type_cache'):
                        del st.session_state.file_type_cache
                    st.success("缓存已清除，请重新上传文件")
                    st.rerun()

                uploaded_file_top = st.file_uploader("选择Excel文件", type=["xlsx", "xls"], key="top_entities_excel")
                if uploaded_file_top is not None:
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
                    col_a, col_b, col_c, col_d = st.columns(4)
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
                        # 英文名列选择器
                        english_name_options = ["（不使用）"] + list(df_top.columns)
                        english_name_idx = 0
                        if import_summary_top.get('english_name_column') in list(df_top.columns):
                            english_name_idx = 1 + list(df_top.columns).index(import_summary_top['english_name_column'])
                        english_name_choice_top = st.selectbox(
                            "选择英文名列（可选）",
                            english_name_options,
                            index=english_name_idx,
                            help="如果Excel中有英文名称列，可选择映射",
                            key="english_name_col_selected_top_ui2",
                        )
                        st.session_state["english_name_col_selected_top"] = None if english_name_choice_top == "（不使用）" else english_name_choice_top
                    with col_d:
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

                    # 可选：认缴出资额/注册资本/成立日期（单位：默认万元），自动默认选中已识别的列
                    st.caption("单位说明：认缴出资额/注册资本默认单位为万元；成立日期支持 年-月 或 年-月-日。")
                    try:
                        file_type_top = _detect_file_type_from_filename(uploaded_file_top.name)
                    except Exception:
                        file_type_top = None
                    def _default_index_by_keywords(cols, keywords):
                        try:
                            for idx, c in enumerate(cols):
                                s = str(c)
                                if any(k in s for k in keywords):
                                    return idx + 1  # +1: 前置“（不使用）”
                        except Exception:
                            pass
                        return 0
                    opt_cols = ["（不使用）"] + list(df_top.columns)
                    if file_type_top == 'investment':
                        rc_default_idx = _default_index_by_keywords(df_top.columns, ["注册资本", "registered", "capital"])
                        registration_capital_choice_top = st.selectbox(
                            "选择注册资本列（可选）",
                            opt_cols,
                            index=rc_default_idx,
                            key="registration_capital_col_selected_top_ui",
                        )
                        st.session_state["registration_capital_col_selected_top"] = None if registration_capital_choice_top == "（不使用）" else registration_capital_choice_top
                    else:
                        sc_default_idx = _default_index_by_keywords(df_top.columns, ["认缴", "出资额", "认缴出资额"])
                        subscribed_capital_choice_top = st.selectbox(
                            "选择认缴出资额列（可选）",
                            opt_cols,
                            index=sc_default_idx,
                            key="subscribed_capital_col_selected_top_ui",
                        )
                        st.session_state["subscribed_capital_col_selected_top"] = None if subscribed_capital_choice_top == "（不使用）" else subscribed_capital_choice_top
                    est_default_idx = _default_index_by_keywords(df_top.columns, ["成立", "注册日期", "设立", "date", "registration"])
                    establish_date_choice_top = st.selectbox(
                        "选择成立日期列（可选）",
                        opt_cols,
                        index=est_default_idx,
                        key="establish_date_col_selected_top_ui",
                    )
                    st.session_state["establish_date_col_selected_top"] = None if establish_date_choice_top == "（不使用）" else establish_date_choice_top

                    skip_rows_top = st.number_input("跳过前几行（如有表头/说明）", min_value=0, max_value=10, value=0, key="skip_rows_top")
                    auto_detect_type_top = st.checkbox("启用自动类型判断", value=True, help="根据名称自动判断公司/个人", key="auto_detect_type_top")
                    default_entity_type_top = st.selectbox("默认类型", ["company","person"], index=0, key="default_entity_type_top")

                    if st.button("开始导入股东（主要股东）", type="primary", key="import_top_entities_now"):
                        if uploaded_file_top is None:
                            st.error("请先上传Excel文件")
                            st.stop()
                    
                        # 立即检查session_state状态
                        st.write(f"🔍 导入开始前 - session_state中是否有imported_file_entities: {'imported_file_entities' in st.session_state}")
                        if "imported_file_entities" in st.session_state:
                            st.write(f"🔍 导入开始前 - imported_file_entities: {list(st.session_state.imported_file_entities)}")
                    
                        # 🔥 从文件名推断关联的公司（autolink功能）
                        file_type = _detect_file_type_from_filename(uploaded_file_top.name)
                        child_company = None
                    
                        # 显示文件名解析调试信息
                        with st.expander("🔍 文件名解析调试信息", expanded=True):
                            st.write(f"**原始文件名**: {uploaded_file_top.name}")
                            st.write(f"**识别文件类型**: {file_type}")
                        
                            if file_type == 'shareholder':
                                # 股东文件：从文件名提取被投资公司
                                child_company = _infer_child_from_filename(uploaded_file_top.name)
                                st.write(f"**提取的被投资公司**: {child_company}")
                                if child_company:
                                    st.success(f"✅ 从文件名识别到被投资公司: {child_company}")
                                else:
                                    st.warning("⚠️ 未能从文件名中提取到被投资公司名称")
                            else:
                                # 默认或未知类型，尝试提取公司名
                                child_company = _extract_company_name_from_filename(uploaded_file_top.name)
                                st.write(f"**提取的公司名称**: {child_company}")
                                if child_company:
                                    st.info(f"📌 从文件名提取到公司名称: {child_company}")
                                else:
                                    st.warning("⚠️ 未能从文件名中提取到公司名称")
                    
                        # 🔥 记录文件名实体到session_state中，用于简化显示
                        st.write(f"🔍 调试：child_company = '{child_company}'")
                        if child_company:
                            if "imported_file_entities" not in st.session_state:
                                st.session_state.imported_file_entities = set()
                            st.session_state.imported_file_entities.add(child_company)
                            st.write(f"✅ 已将 '{child_company}' 添加到imported_file_entities")
                            st.write(f"📋 当前imported_file_entities: {list(st.session_state.imported_file_entities)}")
                        else:
                            st.write(f"⚠️ child_company为空，无法添加到imported_file_entities")
                    
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
                        except Exception:
                            st.error("列映射无效，请重新选择。")
                            st.stop()
                        actual_name_col_top = df_proc.columns[name_idx2]
                        actual_pct_col_top = df_proc.columns[pct_idx2]
                    
                        # 处理英文名列
                        english_name_col_top = st.session_state.get("english_name_col_selected_top")
                        actual_english_name_col_top = None
                        if english_name_col_top and english_name_col_top in df_proc.columns:
                            actual_english_name_col_top = english_name_col_top
                    
                        status_col_main = st.session_state.get("status_col_selected_top") or _find_status_column(df_proc, analysis_result_top)
                        subscribed_capital_col = st.session_state.get("subscribed_capital_col_selected_top")
                        registration_capital_col_top = st.session_state.get("registration_capital_col_selected_top")
                        establish_date_col = st.session_state.get("establish_date_col_selected_top")

                        imported_count, skipped_count = 0, 0
                        errors = []
                        created_relationships = []  # 记录创建的关系
                        for idx, row in df_proc.iterrows():
                            try:
                                entity_name = str(row[actual_name_col_top]).strip()
                                if not entity_name or entity_name.lower() in ["nan","none","null","",""]:
                                    skipped_count += 1
                                    errors.append(f"第{idx+1}行: 实体名称为空或无效")
                                    continue
                            
                                # 处理英文名
                                english_name = None
                                if actual_english_name_col_top:
                                    try:
                                        english_name_val = str(row[actual_english_name_col_top]).strip()
                                        if english_name_val and english_name_val.lower() not in ["nan","none","null","",""]:
                                            english_name = english_name_val
                                    except Exception:
                                        pass
                                
                                # 处理认缴出资额/注册资本
                                subscribed_capital_amount = None
                                registration_capital = None
                                capital_unit = "万元"
                                if subscribed_capital_col and subscribed_capital_col in df_proc.columns:
                                    try:
                                        sc_val = str(row[subscribed_capital_col]).strip()
                                        if sc_val and sc_val.lower() not in ["nan","none","null","",""]:
                                            from src.utils.display_formatters import normalize_amount_to_wan
                                            subscribed_capital_amount = normalize_amount_to_wan(sc_val)
                                    except Exception:
                                        pass
                                if registration_capital_col_top and registration_capital_col_top in df_proc.columns:
                                    try:
                                        rc_val = str(row[registration_capital_col_top]).strip()
                                        if rc_val and rc_val.lower() not in ["nan","none","null","",""]:
                                            from src.utils.display_formatters import normalize_amount_to_wan
                                            registration_capital = normalize_amount_to_wan(rc_val)
                                    except Exception:
                                        pass
                                
                                # 处理成立日期
                                establishment_date = None
                                if establish_date_col and establish_date_col in df_proc.columns:
                                    try:
                                        ed_val = str(row[establish_date_col]).strip()
                                        if ed_val and ed_val.lower() not in ["nan","none","null","",""]:
                                            from src.utils.display_formatters import _parse_date_flexible
                                            parsed_date = _parse_date_flexible(ed_val)
                                            if parsed_date:
                                                establishment_date = parsed_date.strftime("%Y-%m-%d")
                                    except Exception:
                                        pass
                            
                                pct_val = row[actual_pct_col_top]
                                try:
                                    percentage = float(pct_val)
                                    if not (0<=percentage<=100):
                                        raise ValueError("比例范围无效")
                                except Exception:
                                    import re as _re
                                    m = _re.search(r"\d+(\.\d+)?", str(pct_val))
                                    if not m:
                                        skipped_count += 1
                                        errors.append(f"第{idx+1}行: 无法提取比例")
                                        continue
                                    percentage = float(m.group())
                                    if not (0<=percentage<=100):
                                        skipped_count += 1
                                        errors.append(f"第{idx+1}行: 比例 {percentage} 超出范围")
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
                                        # 更新可选字段
                                        if subscribed_capital_amount is not None:
                                            st.session_state.equity_data["top_level_entities"][i]["subscribed_capital_amount"] = subscribed_capital_amount
                                            st.session_state.equity_data["top_level_entities"][i]["capital_unit"] = capital_unit
                                        if registration_capital is not None:
                                            st.session_state.equity_data["top_level_entities"][i]["registration_capital"] = registration_capital
                                            st.session_state.equity_data["top_level_entities"][i]["capital_unit"] = capital_unit
                                        if establishment_date:
                                            st.session_state.equity_data["top_level_entities"][i]["establishment_date"] = establishment_date
                                        
                                        # 同步到all_entities
                                        for j, ae in enumerate(st.session_state.equity_data.get("all_entities", [])):
                                            if ae.get("name") == entity_name:
                                                if subscribed_capital_amount is not None:
                                                    st.session_state.equity_data["all_entities"][j]["subscribed_capital_amount"] = subscribed_capital_amount
                                                    st.session_state.equity_data["all_entities"][j]["capital_unit"] = capital_unit
                                                if registration_capital is not None:
                                                    st.session_state.equity_data["all_entities"][j]["registration_capital"] = registration_capital
                                                    st.session_state.equity_data["all_entities"][j]["capital_unit"] = capital_unit
                                                if establishment_date:
                                                    st.session_state.equity_data["all_entities"][j]["establishment_date"] = establishment_date
                                                break
                                        
                                        exists = True
                                        imported_count += 1
                                        break
                            
                                # 如果实体不存在，创建新实体
                                if not exists:
                                    # 创建实体对象，包含英文名和可选字段
                                    entity_data = {
                                        "name": entity_name,
                                        "type": entity_type,
                                        "percentage": percentage
                                    }
                                    if english_name:
                                        entity_data["english_name"] = english_name
                                    if subscribed_capital_amount is not None:
                                        entity_data["subscribed_capital_amount"] = subscribed_capital_amount
                                        entity_data["capital_unit"] = capital_unit
                                    if registration_capital is not None:
                                        entity_data["registration_capital"] = registration_capital
                                        entity_data["capital_unit"] = capital_unit
                                    if establishment_date:
                                        entity_data["establishment_date"] = establishment_date
                                
                                    st.session_state.equity_data["top_level_entities"].append(entity_data)
                                
                                    # 添加到all_entities
                                    if not any(e.get("name")==entity_name for e in st.session_state.equity_data.get("all_entities", [])):
                                        all_entity_data = {
                                            "name": entity_name,
                                            "type": entity_type
                                        }
                                        if english_name:
                                            all_entity_data["english_name"] = english_name
                                        if subscribed_capital_amount is not None:
                                            all_entity_data["subscribed_capital_amount"] = subscribed_capital_amount
                                            all_entity_data["capital_unit"] = capital_unit
                                        if registration_capital is not None:
                                            all_entity_data["registration_capital"] = registration_capital
                                            all_entity_data["capital_unit"] = capital_unit
                                        if establishment_date:
                                            all_entity_data["establishment_date"] = establishment_date
                                        st.session_state.equity_data["all_entities"].append(all_entity_data)
                                    else:
                                        # 如果实体已存在，更新可选字段
                                        for i, ae in enumerate(st.session_state.equity_data.get("all_entities", [])):
                                            if ae.get("name") == entity_name:
                                                if subscribed_capital_amount is not None:
                                                    st.session_state.equity_data["all_entities"][i]["subscribed_capital_amount"] = subscribed_capital_amount
                                                    st.session_state.equity_data["all_entities"][i]["capital_unit"] = capital_unit
                                                if registration_capital is not None:
                                                    st.session_state.equity_data["all_entities"][i]["registration_capital"] = registration_capital
                                                    st.session_state.equity_data["all_entities"][i]["capital_unit"] = capital_unit
                                                if establishment_date:
                                                    st.session_state.equity_data["all_entities"][i]["establishment_date"] = establishment_date
                                                break
                            
                                # 🔥 关键修复：无论实体是否存在，都需要处理关系创建
                                # 优先使用从文件名提取的公司，其次使用核心公司
                                target_company = child_company if child_company else st.session_state.equity_data.get("core_company", "")
                            
                                # 🔥 特殊处理：如果文件名后缀包含"对外投资"关键词，关系方向应该反转
                                # 只检查"-"后面的部分，不检查企业名称
                                filename_parts = uploaded_file_top.name.split('-')
                                filename_suffix = '-'.join(filename_parts[1:]) if len(filename_parts) > 1 else ""
                                filename_contains_investment = any(keyword in filename_suffix for keyword in ['对外投资', '投资', '子公司', '控制企业'])
                            
                                # 添加关系创建调试信息
                                if target_company:
                                    st.write(f"🔍 关系创建调试 - 文件名后缀: '{filename_suffix}'")
                                    if filename_contains_investment:
                                        st.write(f"🔍 关系创建调试 - 文件名后缀包含投资关键词，关系方向反转")
                                        st.write(f"🔍 关系创建调试 - 投资方: {target_company}, 被投资方: {entity_name}, 比例: {percentage}%")
                                    else:
                                        st.write(f"🔍 关系创建调试 - 股东: {entity_name}, 目标公司: {target_company}, 比例: {percentage}%")
                                
                                    # 确保两个实体都在all_entities中
                                    for company_name in [target_company, entity_name]:
                                        if not any(e.get("name") == company_name for e in st.session_state.equity_data.get("all_entities", [])):
                                            st.session_state.equity_data["all_entities"].append({
                                                "name": company_name,
                                                "type": "company"
                                            })
                                            st.write(f"✅ 已将 '{company_name}' 添加到all_entities")
                                
                                    # 根据文件名是否包含投资关键词决定关系方向
                                    if filename_contains_investment:
                                        # 对外投资关系：文件名中的公司(parent) -> Excel中的公司(child)
                                        parent_entity = target_company
                                        child_entity = entity_name
                                        relationship_desc = f"对外投资{percentage}%"
                                    else:
                                        # 股东关系：Excel中的股东(parent) -> 文件名中的公司(child)
                                        parent_entity = entity_name
                                        child_entity = target_company
                                        relationship_desc = f"持股{percentage}%"
                                
                                    # 检查关系是否已存在
                                    relationship_exists = any(
                                        r.get("parent", r.get("from", "")) == parent_entity and 
                                        r.get("child", r.get("to", "")) == child_entity
                                        for r in st.session_state.equity_data.get("entity_relationships", [])
                                    )
                                
                                    if relationship_exists:
                                        st.write(f"⚠️ 关系已存在: {parent_entity} -> {child_entity}")
                                    else:
                                        # 创建股权关系
                                        relationship_data = {
                                            "parent": parent_entity,
                                            "child": child_entity,
                                            "percentage": percentage,
                                            "relationship_type": "持股" if not filename_contains_investment else "控股",
                                            "description": relationship_desc
                                        }
                                        st.session_state.equity_data["entity_relationships"].append(relationship_data)
                                        # 记录创建的关系
                                        created_relationships.append({
                                            "from": parent_entity,
                                            "to": child_entity,
                                            "percentage": percentage,
                                            "type": "股权关系"
                                        })
                                        st.write(f"✅ 创建关系: {parent_entity} -> {child_entity} ({percentage}%)")
                                else:
                                    st.write(f"⚠️ 无法创建关系: 目标公司为空 (child_company: {child_company}, core_company: {st.session_state.equity_data.get('core_company', '')})")
                            
                                # 只有新实体才增加imported_count
                                if not exists:
                                    imported_count += 1
                            except Exception as e:
                                skipped_count += 1
                                errors.append(f"第{idx+1}行: 处理失败 - {str(e)}")

                        st.markdown("### 📊 导入结果")
                        cc1, cc2, cc3 = st.columns(3)
                        with cc1:
                            st.metric("成功导入", imported_count)
                        with cc2:
                            st.metric("跳过记录", skipped_count)
                        with cc3:
                            st.metric("创建关系", len(created_relationships))
                    
                        # 显示创建的关系详情
                        if created_relationships:
                            st.markdown("### 🔗 创建的关系")
                            st.info(f"本次导入共创建了 {len(created_relationships)} 个股权关系：")
                        
                            # 创建关系表格
                            relationship_data = []
                            for rel in created_relationships:
                                relationship_data.append({
                                    "投资方": rel["from"],
                                    "被投资方": rel["to"],
                                    "持股比例": f"{rel['percentage']}%",
                                    "关系类型": rel["type"]
                                })
                        
                            if relationship_data:
                                import pandas as pd
                                df_relationships = pd.DataFrame(relationship_data)
                                st.dataframe(df_relationships, use_container_width=True)
                        
                            # 显示关系创建详情
                            with st.expander("📋 关系创建详情", expanded=True):
                                for i, rel in enumerate(created_relationships, 1):
                                    st.write(f"**{i}.** {rel['from']} → {rel['to']} ({rel['percentage']}%)")
                    
                        if errors:
                            with st.expander("查看详细错误信息"):
                                for err in errors:
                                    st.code(err)
                        # 导入完成后检查session_state状态
                        st.write(f"🔍 导入完成后 - session_state中是否有imported_file_entities: {'imported_file_entities' in st.session_state}")
                        if "imported_file_entities" in st.session_state:
                            st.write(f"🔍 导入完成后 - imported_file_entities: {list(st.session_state.imported_file_entities)}")
                    
                        if st.button("确认并刷新列表", type="primary", key="top_import_refresh_done"):
                            st.rerun()
                    
                        # 添加批量翻译按钮
                        if imported_count > 0:
                            st.markdown("### 🌐 批量翻译")
                            st.info("为已导入的股东批量翻译中文名为英文名（需要阿里云翻译API配置）")
                        
                            # 仅保留“翻译所有实体”
                            if st.button("批量翻译所有实体", key="batch_translate_all_entities"):
                                _batch_translate_all_entities()

            

            # ===== 多文件批量导入功能 =====
            st.subheader("📚 从Excel导入股东信息（批量多文件）")
            st.info("一次上传多个Excel文件，系统将自动依次处理所有文件，显示进度条，最后统一展示导入结果。")
        
            # 多文件上传器
            uploaded_files_batch = st.file_uploader(
                "选择多个Excel文件", 
                type=["xlsx", "xls"], 
                accept_multiple_files=True,
                key="batch_shareholder_excel"
            )
        
            # 初始化状态
            if "removed_batch_files" not in st.session_state:
                st.session_state.removed_batch_files = set()
        
            # 🔥 清除删除记录按钮（如果有历史删除记录）
            if st.session_state.removed_batch_files:
                col_clear1, col_clear2 = st.columns([3, 1])
                with col_clear1:
                    st.warning(f"⚠️ 检测到 {len(st.session_state.removed_batch_files)} 个文件在删除记录中，这些文件即使重新上传也会被过滤")
                with col_clear2:
                    if st.button("🔄 清除删除记录", help="清除所有历史删除记录，允许重新上传这些文件"):
                        st.session_state.removed_batch_files.clear()
                        st.success("✅ 删除记录已清除")
                        st.rerun()
        
            if uploaded_files_batch:
                st.markdown("### 📋 已选择的文件列表")
            
                # 🔥 关键修复：直接使用上传器的文件列表，只过滤被删除的文件名
                # 每次都重新赋值，避免 Streamlit 文件对象失效问题
                st.session_state.batch_files_to_process = [
                    f for f in uploaded_files_batch if f.name not in st.session_state.removed_batch_files
                ]
            
                # 显示文件列表
                for i, file in enumerate(st.session_state.batch_files_to_process):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"📄 {file.name}")
                    with col2:
                        if st.button("删除", key=f"remove_file_{i}"):
                            # 标记该文件为已从自定义列表删除，并同步处理列表
                            st.session_state.removed_batch_files.add(file.name)
                            st.rerun()
            
                if len(st.session_state.batch_files_to_process) > 0:
                    st.success(f"✅ 已选择 {len(st.session_state.batch_files_to_process)} 个文件")
                
                    # 批量导入配置（使用默认配置）
                    st.markdown("### ⚙️ 批量导入配置")
                    col1, col2 = st.columns(2)
                    with col1:
                        auto_detect_type_batch = st.checkbox("启用自动类型判断", value=True, help="根据名称自动判断公司/个人", key="auto_detect_type_batch")
                        default_entity_type_batch = st.selectbox("默认类型", ["company","person"], index=0, key="default_entity_type_batch")
                    with col2:
                        skip_rows_batch = st.number_input("跳过前几行（如有表头/说明）", min_value=0, max_value=10, value=0, key="skip_rows_batch")
                
                    # 开始批量导入按钮
                    if st.button("开始批量导入所有文件", type="primary", key="batch_import_all_files"):
                        if not st.session_state.batch_files_to_process:
                            st.error("没有可处理的文件")
                            st.stop()
                    
                        # 初始化结果统计
                        total_files = len(st.session_state.batch_files_to_process)
                        success_list = []
                        failed_list = []
                        total_imported_entities = 0
                        total_created_relationships = 0
                    
                        # 创建进度条和状态显示
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                    
                        # 处理每个文件
                        for i, file in enumerate(st.session_state.batch_files_to_process):
                            status_text.text(f"正在处理: {file.name} ({i+1}/{total_files})")
                        
                            try:
                                # 清空每个文件处理前的缓存状态
                                if "imported_file_entities" in st.session_state:
                                    # 保存当前已导入的文件名实体，但清空当前文件的处理状态
                                    pass
                            
                                # 复用单文件导入的核心逻辑
                                file_imported_count = 0
                                file_relationship_count = 0
                            
                                # 1. 文件类型检测
                                file_type = _detect_file_type_from_filename(file.name)
                                child_company = None
                                parent_company = None
                            
                                # 2. 公司名提取 - 修复逻辑
                                if file_type == 'shareholder':
                                    # 股东文件：从文件名提取被投资公司
                                    child_company = _infer_child_from_filename(file.name)
                                elif file_type == 'investment':
                                    # 对外投资文件：从文件名提取投资方公司
                                    parent_company = _infer_parent_from_filename(file.name)
                                else:
                                    # 未知类型，尝试提取公司名作为被投资公司
                                    child_company = _extract_company_name_from_filename(file.name)
                            
                                # 3. Excel读取和数据处理
                                import pandas as pd
                                try:
                                    file.seek(0)
                                    if skip_rows_batch > 0:
                                        df = pd.read_excel(file, skiprows=skip_rows_batch)
                                        if any('Unnamed' in str(c) for c in df.columns):
                                            df.columns = [f"Column_{i}" for i in range(len(df.columns))]
                                    else:
                                        df = pd.read_excel(file)
                                        if any('Unnamed' in str(c) for c in df.columns):
                                            df.columns = [f"Column_{i}" for i in range(len(df.columns))]
                                except Exception as e:
                                    raise Exception(f"读取Excel文件失败: {str(e)}")
                            
                                # 4. 表头检测
                                df = _apply_header_detection(df, [
                                    "序号", "发起人名称", "发起人类型", "持股比例", 
                                    "认缴出资额", "认缴出资日期", "实缴出资额", "实缴出资日期",
                                    "股东名称", "股东类型", "出资比例", "出资额", "出资日期",
                                    "股东信息", "工商登记", "企业名称", "公司名称", "名称",
                                    "法定代表人", "注册资本", "投资比例", "投资数额", "成立日期", "登记状态"
                                ], announce=False)
                            
                                # 5. 智能分析
                                from src.utils.excel_smart_importer import create_smart_excel_importer
                                smart_importer = create_smart_excel_importer()
                                analysis_result = smart_importer.analyze_excel_columns(df)
                                import_summary = smart_importer.get_import_summary(df, analysis_result)
                            
                                # 调试信息
                                # 安全控制台输出，避免 Windows 下 OSError([Errno 22])
                                def _safe_console_log(m):
                                    try:
                                        print(m)
                                    except Exception:
                                        pass
                                _safe_console_log(f"🔍 调试 {file.name}:")
                                _safe_console_log(f"  - 文件类型: {file_type}")
                                _safe_console_log(f"  - 检测到的列: {analysis_result.get('detected_columns', {})}")
                                _safe_console_log(f"  - 名称列: {import_summary.get('entity_name_column')}")
                                _safe_console_log(f"  - 比例列: {import_summary.get('investment_ratio_column')}")
                                _safe_console_log(f"  - 数据行数: {len(df)}")
                                _safe_console_log(f"  - child_company: {child_company}")
                                _safe_console_log(f"  - parent_company: {parent_company}")
                            
                                # 6. 状态列检测
                                status_col = _find_status_column(df, analysis_result)
                                
                                # 7. 检测注册资本和成立日期列
                                registration_capital_col = None
                                subscribed_capital_col = None
                                establishment_date_col = None
                                
                                # 根据文件类型检测相应的资本列
                                if file_type == 'investment':
                                    # 对外投资文件：检测注册资本列
                                    for col in df.columns:
                                        col_str = str(col).lower()
                                        if any(keyword in col_str for keyword in ['注册资本', 'registered', 'capital']):
                                            registration_capital_col = col
                                            break
                                else:
                                    # 股东文件：检测认缴出资额列
                                    for col in df.columns:
                                        col_str = str(col).lower()
                                        if any(keyword in col_str for keyword in ['认缴', '出资额', '认缴出资额']):
                                            subscribed_capital_col = col
                                            break
                                
                                # 检测成立日期列
                                for col in df.columns:
                                    col_str = str(col).lower()
                                    if any(keyword in col_str for keyword in ['成立', '注册日期', '设立', 'date', 'registration']):
                                        establishment_date_col = col
                                        break
                            
                                # 7. 处理每一行数据
                                for index, row in df.iterrows():
                                    try:
                                        # 获取名称和比例列
                                        name_col = import_summary.get('entity_name_column')
                                        percentage_col = import_summary.get('investment_ratio_column')
                                    
                                        if not name_col or not percentage_col:
                                            continue
                                    
                                        entity_name = str(row[name_col]).strip()
                                        if not entity_name or entity_name.lower() in ['nan', 'none', '']:
                                            continue
                                    
                                        # 处理比例
                                        percentage_str = str(row[percentage_col]).strip()
                                        percentage = 0.0
                                        try:
                                            # 提取数字
                                            import re
                                            percentage_match = re.search(r'(\d+\.?\d*)', percentage_str)
                                            if percentage_match:
                                                percentage = float(percentage_match.group(1))
                                        except:
                                            continue
                                    
                                        if percentage <= 0:
                                            continue
                                    
                                        # 状态过滤
                                        if status_col:
                                            status_value = str(row[status_col]).strip().lower()
                                            if any(status in status_value for status in ['注销', '吊销', '撤销']):
                                                continue
                                        
                                        # 处理注册资本/认缴出资额和成立日期
                                        registration_capital = None
                                        subscribed_capital_amount = None
                                        establishment_date = None
                                        capital_unit = "万元"
                                        
                                        # 根据文件类型处理相应的资本字段
                                        if file_type == 'investment' and registration_capital_col:
                                            try:
                                                rc_val = str(row[registration_capital_col]).strip()
                                                if rc_val and rc_val.lower() not in ["nan","none","null","",""]:
                                                    from src.utils.display_formatters import normalize_amount_to_wan
                                                    registration_capital = normalize_amount_to_wan(rc_val)
                                            except Exception:
                                                pass
                                        elif file_type != 'investment' and subscribed_capital_col:
                                            try:
                                                sc_val = str(row[subscribed_capital_col]).strip()
                                                if sc_val and sc_val.lower() not in ["nan","none","null","",""]:
                                                    from src.utils.display_formatters import normalize_amount_to_wan
                                                    subscribed_capital_amount = normalize_amount_to_wan(sc_val)
                                            except Exception:
                                                pass
                                        
                                        # 处理成立日期
                                        if establishment_date_col:
                                            try:
                                                ed_val = str(row[establishment_date_col]).strip()
                                                if ed_val and ed_val.lower() not in ["nan","none","null","",""]:
                                                    from src.utils.display_formatters import _parse_date_flexible
                                                    parsed_date = _parse_date_flexible(ed_val)
                                                    if parsed_date:
                                                        establishment_date = parsed_date.strftime("%Y-%m-%d")
                                            except Exception:
                                                pass
                                    
                                        # 8. 实体创建
                                        if auto_detect_type_batch:
                                            try:
                                                entity_type = smart_importer.auto_detect_entity_type(entity_name)
                                            except Exception:
                                                entity_type = default_entity_type_batch
                                        else:
                                            entity_type = default_entity_type_batch
                                    
                                        # 添加到top_level_entities
                                        entity_data = {
                                            "name": entity_name,
                                            "type": entity_type,
                                            "percentage": percentage
                                        }
                                        # 添加可选字段
                                        if subscribed_capital_amount is not None:
                                            entity_data["subscribed_capital_amount"] = subscribed_capital_amount
                                            entity_data["capital_unit"] = capital_unit
                                        if registration_capital is not None:
                                            entity_data["registration_capital"] = registration_capital
                                            entity_data["capital_unit"] = capital_unit
                                        if establishment_date:
                                            entity_data["establishment_date"] = establishment_date
                                    
                                        # 检查是否已存在
                                        if not any(e.get("name") == entity_name for e in st.session_state.equity_data.get("top_level_entities", [])):
                                            st.session_state.equity_data["top_level_entities"].append(entity_data)
                                            file_imported_count += 1
                                    
                                        # 添加到all_entities
                                        if not any(e.get("name") == entity_name for e in st.session_state.equity_data.get("all_entities", [])):
                                            all_entity_data = {
                                                "name": entity_name,
                                                "type": entity_type
                                            }
                                            # 添加可选字段到all_entities
                                            if subscribed_capital_amount is not None:
                                                all_entity_data["subscribed_capital_amount"] = subscribed_capital_amount
                                                all_entity_data["capital_unit"] = capital_unit
                                            if registration_capital is not None:
                                                all_entity_data["registration_capital"] = registration_capital
                                                all_entity_data["capital_unit"] = capital_unit
                                            if establishment_date:
                                                all_entity_data["establishment_date"] = establishment_date
                                            st.session_state.equity_data["all_entities"].append(all_entity_data)
                                        else:
                                            # 如果实体已存在，更新可选字段
                                            for j, ae in enumerate(st.session_state.equity_data.get("all_entities", [])):
                                                if ae.get("name") == entity_name:
                                                    if subscribed_capital_amount is not None:
                                                        st.session_state.equity_data["all_entities"][j]["subscribed_capital_amount"] = subscribed_capital_amount
                                                        st.session_state.equity_data["all_entities"][j]["capital_unit"] = capital_unit
                                                    if registration_capital is not None:
                                                        st.session_state.equity_data["all_entities"][j]["registration_capital"] = registration_capital
                                                        st.session_state.equity_data["all_entities"][j]["capital_unit"] = capital_unit
                                                    if establishment_date:
                                                        st.session_state.equity_data["all_entities"][j]["establishment_date"] = establishment_date
                                                    break
                                    
                                        # 9. 关系创建 - 修复逻辑
                                        # 根据文件类型和提取的公司名决定关系方向
                                        if file_type == 'shareholder' and child_company:
                                            # 股东文件：Excel中的股东 -> 文件名中的被投资公司
                                            parent_entity = entity_name
                                            child_entity = child_company
                                            relationship_desc = f"持股{percentage}%"
                                        elif file_type == 'investment' and parent_company:
                                            # 对外投资文件：文件名中的投资方公司 -> Excel中的被投资公司
                                            parent_entity = parent_company
                                            child_entity = entity_name
                                            relationship_desc = f"对外投资{percentage}%"
                                        else:
                                            # 其他情况：使用核心公司作为被投资方
                                            target_company = st.session_state.equity_data.get("core_company", "")
                                            if target_company:
                                                parent_entity = entity_name
                                                child_entity = target_company
                                                relationship_desc = f"持股{percentage}%"
                                            else:
                                                # 没有目标公司，跳过关系创建
                                                continue
                                    
                                        # 确保两个实体都在all_entities中
                                        for company_name in [parent_entity, child_entity]:
                                            if not any(e.get("name") == company_name for e in st.session_state.equity_data.get("all_entities", [])):
                                                st.session_state.equity_data["all_entities"].append({
                                                    "name": company_name,
                                                    "type": "company"
                                                })
                                        
                                            # 检查关系是否已存在
                                            relationship_exists = any(
                                                r.get("parent", r.get("from", "")) == parent_entity and 
                                                r.get("child", r.get("to", "")) == child_entity
                                                for r in st.session_state.equity_data.get("entity_relationships", [])
                                            )
                                        
                                            if not relationship_exists:
                                                st.session_state.equity_data["entity_relationships"].append({
                                                    "parent": parent_entity,
                                                    "child": child_entity,
                                                    "percentage": percentage,
                                                    "relationship_type": "控股",
                                                    "description": relationship_desc
                                                })
                                                file_relationship_count += 1
                                    
                                    except Exception as e:
                                        continue  # 跳过有问题的行
                            
                                # 10. 记录文件名实体到session_state（股东图谱联动）
                                if "imported_file_entities" not in st.session_state:
                                    st.session_state.imported_file_entities = set()
                            
                                # 根据文件类型记录相应的公司名
                                if file_type == 'shareholder' and child_company:
                                    # 股东文件：记录被投资公司
                                    st.session_state.imported_file_entities.add(child_company)
                                elif file_type == 'investment' and parent_company:
                                    # 对外投资文件：记录投资方公司
                                    st.session_state.imported_file_entities.add(parent_company)
                            
                                # 记录成功结果
                                success_list.append({
                                    "filename": file.name,
                                    "imported_count": file_imported_count,
                                    "relationship_count": file_relationship_count
                                })
                                total_imported_entities += file_imported_count
                                total_created_relationships += file_relationship_count
                            
                            except Exception as e:
                                # 记录失败结果
                                failed_list.append({
                                    "filename": file.name,
                                    "error": str(e)
                                })
                        
                            # 更新进度
                            progress_bar.progress((i + 1) / total_files)
                    
                        # 显示最终结果
                        status_text.text("批量导入完成")
                        progress_bar.empty()
                    
                        # 结果摘要
                        st.markdown("### 📊 批量导入结果摘要")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("总文件数", total_files)
                        with col2:
                            st.metric("成功文件数", len(success_list))
                        with col3:
                            st.metric("导入实体数", total_imported_entities)
                        with col4:
                            st.metric("创建关系数", total_created_relationships)
                    
                        # 详细结果
                        if success_list:
                            st.markdown("#### ✅ 成功导入的文件")
                            for result in success_list:
                                st.success(f"📄 {result['filename']} - 导入 {result['imported_count']} 个实体，创建 {result['relationship_count']} 个关系")
                    
                        if failed_list:
                            st.markdown("#### ❌ 导入失败的文件")
                            for result in failed_list:
                                st.error(f"📄 {result['filename']} - 错误: {result['error']}")
                    
                        # 清空文件列表
                        st.session_state.batch_files_to_process = []
                    
                        if st.button("确认并刷新列表", type="primary", key="batch_import_refresh_done"):
                            st.rerun()
                else:
                    st.warning("请选择要导入的文件")

            # 添加新实体
            with st.form("add_top_entity_form"):
                st.subheader("➕ 添加新的顶级实体/股东")
                col1, col2 = st.columns([1, 1])
                with col1:
                    name = st.text_input("实体名称", placeholder="如：Mr. Ho Kuk Sing 或 Shinva Medical Instrument Co., Ltd. 或 方庆熙 (42.71%)")
            
                # 自动从名称中提取比例
                extracted_percentage = extract_percentage_from_name(name) if name else None
                # 如果从名称中提取到比例，则使用提取的值，否则使用默认值10.0
                default_percentage = extracted_percentage if extracted_percentage is not None else 10.0
            
                with col2:
                    percentage = st.number_input("持股比例 (%)", min_value=0.01, max_value=100.0, value=default_percentage, step=0.01)
            
                # 新增：英文名输入框
                english_name = st.text_input("英文名称（可选）", placeholder="如：Shenzhen Mindray Bio-Medical Electronics Co., Ltd.")
            
                # 新增：注册资本和成立日期
                col3, col4 = st.columns([1, 1])
                with col3:
                    registration_capital = st.text_input("注册资本（可选）", placeholder="如：1000万元")
                with col4:
                    establishment_date = st.date_input("成立日期（可选）", value=None, help="选择公司成立日期")
            
                entity_type = st.selectbox("实体类型", ["company", "person"], help="选择实体是公司还是个人")
            
                # 修改1：删除保存并继续按钮，只保留添加按钮
                if st.form_submit_button("添加顶级实体", type="primary"):
                    if name.strip():
                        # 检查是否已存在
                        exists = any(e["name"] == name for e in st.session_state.equity_data["top_level_entities"])
                        if not exists:
                            # 创建实体数据，包含所有字段
                            entity_data = {
                                "name": name,
                                "type": entity_type,
                                "percentage": percentage
                            }
                        
                            # 添加可选字段
                            if english_name.strip():
                                entity_data["english_name"] = english_name.strip()
                            if registration_capital.strip():
                                entity_data["registration_capital"] = registration_capital.strip()
                            if establishment_date:
                                entity_data["establishment_date"] = establishment_date.strftime("%Y-%m-%d")
                        
                            st.session_state.equity_data["top_level_entities"].append(entity_data)
                        
                            # 添加到所有实体列表
                            if not any(e["name"] == name for e in st.session_state.equity_data["all_entities"]):
                                all_entity_data = {
                                    "name": name,
                                    "type": entity_type
                                }
                                # 添加可选字段到all_entities
                                if english_name.strip():
                                    all_entity_data["english_name"] = english_name.strip()
                                if registration_capital.strip():
                                    all_entity_data["registration_capital"] = registration_capital.strip()
                                if establishment_date:
                                    all_entity_data["establishment_date"] = establishment_date.strftime("%Y-%m-%d")
                            
                                st.session_state.equity_data["all_entities"].append(all_entity_data)
                        
                            st.success(f"已添加顶级实体: {name}")
                            # 修改：无论是否继续，都添加后立即刷新页面，实现实时显示
                            st.rerun()
                        else:
                            st.error("该实体已存在")
                    else:
                        st.error("请输入实体名称")
        
            # --- 页面底部显示：已添加的顶级实体/股东 ---
            if st.session_state.equity_data["top_level_entities"]:
                st.markdown("### 👥 已添加的顶级实体/股东")
                for i, entity in enumerate(st.session_state.equity_data["top_level_entities"]):
                    # 修复：处理可能没有percentage字段的情况
                    percentage_text = f" - {entity.get('percentage', 'N/A')}%" if entity.get('percentage') else ""
                    title = f"{_format_cn_en(entity['name'])}{percentage_text}"
                    with st.expander(title):
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
                    
    # 步骤3: 添加子公司
    elif st.session_state.current_step == "subsidiaries":
        st.subheader("🏢 添加子公司")
    
        if st.session_state.equity_data["core_company"]:
            st.markdown(f"**核心公司**: {st.session_state.equity_data['core_company']}")
    
        # 显示已添加的子公司
        if st.session_state.equity_data["subsidiaries"]:
            st.markdown("### 🏢 已添加的子公司")
            for i, subsidiary in enumerate(st.session_state.equity_data["subsidiaries"]):
                with st.expander(f"{_format_cn_en(subsidiary['name'])} - {subsidiary['percentage']}%"):
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
    
        # 🔥 添加文件类型指导
        with st.expander("📋 子公司导入说明", expanded=False):
            st.markdown("""
            **🏢 子公司导入功能适用于：**
            - 文件名包含"对外投资"、"子公司"、"控制企业"等关键词
            - 文件内容：投资方公司的被投资企业列表
            - 关系方向：文件名中的投资方 → Excel中的被投资方
        
            **示例文件名：**
            - `力诺投资控股集团有限公司-对外投资.xlsx`
            - `某公司-子公司信息.xlsx`
            - `投资集团-控制企业.xlsx`
        
            **⚠️ 如果您的文件是股东信息（股东投资某公司），请使用上方的"股东信息导入"功能！**
            """)
    
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

                # 可选：注册资本/认缴出资额/成立日期（单位：默认万元），自动默认选中已识别的列
                st.caption("单位说明：注册资本/认缴出资额默认单位为万元；成立日期支持 年-月 或 年-月-日。")
                def _default_index_by_keywords_sub(cols, keywords):
                    try:
                        for idx, c in enumerate(cols):
                            s = str(c)
                            if any(k in s for k in keywords):
                                return idx + 1  # +1: 前置"（不使用）"
                    except Exception:
                        pass
                    return 0
                opt_cols_sub = ["（不使用）"] + list(df_sub.columns)
                
                # 根据文件类型决定默认选择的资本字段
                try:
                    file_type_sub = _detect_file_type_from_filename(uploaded_file_sub.name)
                except Exception:
                    file_type_sub = None
                
                if file_type_sub == 'investment':
                    # 对外投资文件：默认选择注册资本
                    rc_default_idx_sub = _default_index_by_keywords_sub(df_sub.columns, ["注册资本", "registered", "capital"])
                    registration_capital_choice_sub = st.selectbox(
                        "选择注册资本列（可选）",
                        opt_cols_sub,
                        index=rc_default_idx_sub,
                        key="registration_capital_col_selected_sub_ui",
                    )
                    st.session_state["registration_capital_col_selected_sub"] = None if registration_capital_choice_sub == "（不使用）" else registration_capital_choice_sub
                    st.session_state["subscribed_capital_col_selected_sub"] = None
                else:
                    # 其他文件：默认选择认缴出资额
                    sc_default_idx_sub = _default_index_by_keywords_sub(df_sub.columns, ["认缴", "出资额", "认缴出资额"])
                    subscribed_capital_choice_sub = st.selectbox(
                        "选择认缴出资额列（可选）",
                        opt_cols_sub,
                        index=sc_default_idx_sub,
                        key="subscribed_capital_col_selected_sub_ui",
                    )
                    st.session_state["subscribed_capital_col_selected_sub"] = None if subscribed_capital_choice_sub == "（不使用）" else subscribed_capital_choice_sub
                    st.session_state["registration_capital_col_selected_sub"] = None
                
                est_default_idx_sub = _default_index_by_keywords_sub(df_sub.columns, ["成立", "注册日期", "设立", "date", "registration"])
                establish_date_choice_sub = st.selectbox(
                    "选择成立日期列（可选）",
                    opt_cols_sub,
                    index=est_default_idx_sub,
                    key="establish_date_col_selected_sub_ui",
                )
                st.session_state["establish_date_col_selected_sub"] = None if establish_date_choice_sub == "（不使用）" else establish_date_choice_sub

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
                
                    # 🔥 从文件名推断关联的公司（autolink功能）
                    file_type = _detect_file_type_from_filename(uploaded_file_sub.name)
                    parent_company = None
                
                    # 显示文件名解析调试信息
                    with st.expander("🔍 文件名解析调试信息", expanded=True):
                        st.write(f"**原始文件名**: {uploaded_file_sub.name}")
                        st.write(f"**识别文件类型**: {file_type}")
                    
                        if file_type == 'investment':
                            # 对外投资文件：从文件名提取投资方公司
                            parent_company = _infer_parent_from_filename(uploaded_file_sub.name)
                            st.write(f"**提取的投资方公司**: {parent_company}")
                            if parent_company:
                                st.success(f"✅ 从文件名识别到投资方公司: {parent_company}")
                                st.info(f"📊 **关系方向**: {parent_company} (文件名/投资方/Parent) → Excel中的公司 (被投资方/子公司/Child)")
                            else:
                                st.warning("⚠️ 未能从文件名中提取到投资方公司名称")
                        else:
                            # 默认使用核心公司
                            parent_company = st.session_state.equity_data.get("core_company", "")
                            st.write(f"**使用核心公司**: {parent_company}")
                            if parent_company:
                                st.info(f"📌 使用核心公司: {parent_company}")
                                st.info(f"📊 **关系方向**: {parent_company} (核心公司/Parent) → Excel中的公司 (子公司/Child)")
                            else:
                                st.warning("⚠️ 未设置核心公司，将无法创建关系")
                
                    # 🔥 记录文件名实体到session_state中，用于简化显示
                    st.write(f"🔍 调试：parent_company = '{parent_company}'")
                    if parent_company:
                        if "imported_file_entities" not in st.session_state:
                            st.session_state.imported_file_entities = set()
                        st.session_state.imported_file_entities.add(parent_company)
                        st.write(f"✅ 已将 '{parent_company}' 添加到imported_file_entities")
                        st.write(f"📋 当前imported_file_entities: {list(st.session_state.imported_file_entities)}")
                    else:
                        st.write(f"⚠️ parent_company为空，无法添加到imported_file_entities")
                
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
                    created_relationships = []  # 记录创建的关系
                    # 统计总行数与已处理行数，用于在循环最后统一渲染结果
                    rows_total = len(df_processing)
                    rows_processed = 0

                    # 识别"登记状态"列（子公司导入）
                    try:
                        status_col_sub = _find_status_column(df_processing, analysis_result_sub)
                    except Exception:
                        status_col_sub = None
                    
                    # 获取注册资本/认缴出资额和成立日期列
                    registration_capital_col_sub = st.session_state.get("registration_capital_col_selected_sub")
                    subscribed_capital_col_sub = st.session_state.get("subscribed_capital_col_selected_sub")
                    establish_date_col_sub = st.session_state.get("establish_date_col_selected_sub")
                
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

                            # 处理注册资本/认缴出资额和成立日期
                            registration_capital = None
                            subscribed_capital_amount = None
                            establishment_date = None
                            capital_unit = "万元"
                            
                            if registration_capital_col_sub and registration_capital_col_sub in df_processing.columns:
                                try:
                                    rc_val = str(row[registration_capital_col_sub]).strip()
                                    if rc_val and rc_val.lower() not in ["nan","none","null","",""]:
                                        from src.utils.display_formatters import normalize_amount_to_wan
                                        registration_capital = normalize_amount_to_wan(rc_val)
                                except Exception:
                                    pass
                            
                            if subscribed_capital_col_sub and subscribed_capital_col_sub in df_processing.columns:
                                try:
                                    sc_val = str(row[subscribed_capital_col_sub]).strip()
                                    if sc_val and sc_val.lower() not in ["nan","none","null","",""]:
                                        from src.utils.display_formatters import normalize_amount_to_wan
                                        subscribed_capital_amount = normalize_amount_to_wan(sc_val)
                                except Exception:
                                    pass
                            
                            if establish_date_col_sub and establish_date_col_sub in df_processing.columns:
                                try:
                                    ed_val = str(row[establish_date_col_sub]).strip()
                                    if ed_val and ed_val.lower() not in ["nan","none","null","",""]:
                                        from src.utils.display_formatters import _parse_date_flexible
                                        parsed_date = _parse_date_flexible(ed_val)
                                        if parsed_date:
                                            establishment_date = parsed_date.strftime("%Y-%m-%d")
                                except Exception:
                                    pass

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
                                    # 更新可选字段
                                    if subscribed_capital_amount is not None:
                                        st.session_state.equity_data["subsidiaries"][i]["subscribed_capital_amount"] = subscribed_capital_amount
                                        st.session_state.equity_data["subsidiaries"][i]["capital_unit"] = capital_unit
                                    if registration_capital is not None:
                                        st.session_state.equity_data["subsidiaries"][i]["registration_capital"] = registration_capital
                                        st.session_state.equity_data["subsidiaries"][i]["capital_unit"] = capital_unit
                                    if establishment_date:
                                        st.session_state.equity_data["subsidiaries"][i]["establishment_date"] = establishment_date
                                    # 同步关系 - 使用从文件名提取的parent_company
                                    if parent_company:
                                        for j, rel in enumerate(st.session_state.equity_data["entity_relationships"]):
                                            if rel.get("parent") == parent_company and rel.get("child") == subsidiary_name:
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

                                # 创建子公司实体，包含可选字段
                                subsidiary_data = {
                                    "name": subsidiary_name,
                                    "type": entity_type_sub,
                                    "percentage": percentage
                                }
                                if subscribed_capital_amount is not None:
                                    subsidiary_data["subscribed_capital_amount"] = subscribed_capital_amount
                                    subsidiary_data["capital_unit"] = capital_unit
                                if registration_capital is not None:
                                    subsidiary_data["registration_capital"] = registration_capital
                                    subsidiary_data["capital_unit"] = capital_unit
                                if establishment_date:
                                    subsidiary_data["establishment_date"] = establishment_date
                                
                                st.session_state.equity_data["subsidiaries"].append(subsidiary_data)

                                # 加入 all_entities
                                if not any(e.get("name") == subsidiary_name for e in st.session_state.equity_data.get("all_entities", [])):
                                    all_entity_data = {
                                        "name": subsidiary_name,
                                        "type": entity_type_sub
                                    }
                                    if subscribed_capital_amount is not None:
                                        all_entity_data["subscribed_capital_amount"] = subscribed_capital_amount
                                        all_entity_data["capital_unit"] = capital_unit
                                    if registration_capital is not None:
                                        all_entity_data["registration_capital"] = registration_capital
                                        all_entity_data["capital_unit"] = capital_unit
                                    if establishment_date:
                                        all_entity_data["establishment_date"] = establishment_date
                                    st.session_state.equity_data["all_entities"].append(all_entity_data)
                                else:
                                    # 如果实体已存在，更新可选字段
                                    for j, ae in enumerate(st.session_state.equity_data.get("all_entities", [])):
                                        if ae.get("name") == subsidiary_name:
                                            if subscribed_capital_amount is not None:
                                                st.session_state.equity_data["all_entities"][j]["subscribed_capital_amount"] = subscribed_capital_amount
                                                st.session_state.equity_data["all_entities"][j]["capital_unit"] = capital_unit
                                            if registration_capital is not None:
                                                st.session_state.equity_data["all_entities"][j]["registration_capital"] = registration_capital
                                                st.session_state.equity_data["all_entities"][j]["capital_unit"] = capital_unit
                                            if establishment_date:
                                                st.session_state.equity_data["all_entities"][j]["establishment_date"] = establishment_date
                                            break

                                # 🔥 使用文件名自动创建股权关系（autolink功能）
                                if parent_company:
                                    # 确保父公司在all_entities中
                                    if not any(e.get("name") == parent_company for e in st.session_state.equity_data.get("all_entities", [])):
                                        st.session_state.equity_data["all_entities"].append({
                                            "name": parent_company,
                                            "type": "company"
                                        })
                                
                                    # 创建股权关系：投资方公司(parent) -> 子公司(child)
                                    st.session_state.equity_data["entity_relationships"].append({
                                        "parent": parent_company,
                                        "child": subsidiary_name,
                                        "percentage": percentage,
                                        "relationship_type": "控股",
                                        "description": f"持股{percentage}%"
                                    })
                                    # 记录创建的关系
                                    created_relationships.append({
                                        "from": parent_company,
                                        "to": subsidiary_name,
                                        "percentage": percentage,
                                        "type": "控股关系"
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
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("成功导入", imported_count)
                    with col2:
                        st.metric("跳过记录", skipped_count)
                    with col3:
                        st.metric("创建关系", len(created_relationships))
                
                    # 显示创建的关系详情
                    if created_relationships:
                        st.markdown("### 🔗 创建的关系")
                        st.info(f"本次导入共创建了 {len(created_relationships)} 个控股关系：")
                    
                        # 创建关系表格
                        relationship_data = []
                        for rel in created_relationships:
                            relationship_data.append({
                                "投资方": rel["from"],
                                "被投资方": rel["to"],
                                "持股比例": f"{rel['percentage']}%",
                                "关系类型": rel["type"]
                            })
                    
                        if relationship_data:
                            import pandas as pd
                            df_relationships = pd.DataFrame(relationship_data)
                            st.dataframe(df_relationships, use_container_width=True)
                    
                        # 显示关系创建详情
                        with st.expander("📋 关系创建详情", expanded=True):
                            for i, rel in enumerate(created_relationships, 1):
                                st.write(f"**{i}.** {rel['from']} → {rel['to']} ({rel['percentage']}%)")

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
                st.subheader("➕ 添加新的子公司")
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
    
    
        # --- 股东控股关系图谱 ---
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
            show_simplified = st.checkbox("简化显示", value=True, help="只显示个人股东、实际控制人和批量导入的文件名中的公司（包括被投资公司和投资方公司）")
    
        # 🔥 获取批量导入的文件名实体（从session_state中提取）
        imported_file_entities = set()
        if "imported_file_entities" in st.session_state:
            imported_file_entities = st.session_state.imported_file_entities
    
        # 显示简化显示调试信息
        if show_simplified:
            with st.expander("🔍 简化显示调试信息", expanded=False):
                st.write(f"**导入的文件名实体**: {list(imported_file_entities)}")
                st.write(f"**实际控制人**: {st.session_state.equity_data.get('actual_controller', '')}")
                st.write(f"**总显示实体数**: {len(display_entities)}")
                st.write(f"**session_state中是否有imported_file_entities**: {'imported_file_entities' in st.session_state}")
                if "imported_file_entities" in st.session_state:
                    st.write(f"**session_state.imported_file_entities**: {list(st.session_state.imported_file_entities)}")
                else:
                    st.write("**session_state中没有imported_file_entities键**")
            
                # 临时解决方案：手动添加文件名实体
                if not imported_file_entities:
                    st.warning("⚠️ 没有检测到导入的文件名实体，请手动添加：")
                    st.info("💡 说明：\n- 股东文件（如：公司A-股东信息.xlsx）→ 添加'公司A'\n- 对外投资文件（如：公司B-对外投资.xlsx）→ 添加'公司B'")
                    manual_entity = st.text_input("手动输入文件名实体（如：力诺投资控股集团有限公司）", key="manual_file_entity")
                    if st.button("添加文件名实体", key="add_manual_entity"):
                        if manual_entity.strip():
                            if "imported_file_entities" not in st.session_state:
                                st.session_state.imported_file_entities = set()
                            st.session_state.imported_file_entities.add(manual_entity.strip())
                            st.success(f"已添加文件名实体: {manual_entity.strip()}")
                            st.rerun()
                else:
                    st.success(f"✅ 已记录的文件名实体: {', '.join(sorted(imported_file_entities))}")
            
                # 显示所有实体的详细信息
                st.write("**所有显示实体详情**:")
                for i, entity in enumerate(display_entities):
                    entity_name = entity.get("name", "")
                    percentage = entity.get("percentage", 0)
                    # 检查实体类型
                    is_person = False
                    for e in st.session_state.equity_data.get("all_entities", []):
                        if e.get("name") == entity_name and e.get("type") == "person":
                            is_person = True
                            break
                    st.write(f"  {i+1}. {entity_name} ({percentage}%) - 类型: {'个人' if is_person else '公司'}")
    
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
            # 🔥 排序逻辑：个人股东按持股比例从大到小，公司按层级和持股比例排序
            def sort_entities(entity):
                entity_name = entity.get("name", "")
                actual_controller = st.session_state.equity_data.get("actual_controller", "")
            
                # 获取持股比例
                percentage = entity.get("percentage", 0)
                try:
                    percentage_val = float(percentage)
                except (ValueError, TypeError):
                    percentage_val = 0
            
                # 1. 实际控制人排在最前面
                if entity_name == actual_controller:
                    return (0, -percentage_val, entity_name)  # (优先级, 持股比例, 名称)
            
                # 2. 其他个人实体 - 按持股比例从大到小排序
                is_person = False
                for e in st.session_state.equity_data.get("all_entities", []):
                    if e.get("name") == entity_name and e.get("type") == "person":
                        is_person = True
                        break
            
                if is_person:
                    return (1, -percentage_val, entity_name)  # 负号表示降序
            
                # 3. 公司实体 - 按层级和持股比例排序
                def calculate_level(entity_name):
                    """计算实体在股权结构中的层级"""
                    if entity_name in relationship_graph:
                        # 有向下控制关系的实体，层级较高
                        return 0  # 高层级
                    else:
                        # 没有向下控制关系的实体，层级较低
                        return 1  # 低层级
            
                level = calculate_level(entity_name)
            
                # 公司实体排序：层级高的在前，同层级内持股比例高的在前
                return (2, level, -percentage_val, entity_name)  # 负号表示降序
        
            # 对实体进行排序
            sorted_entities = sorted(filtered_display_entities, key=sort_entities)
        
            for entity in sorted_entities:
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
        st.markdown("### 🔗 股权关系")
    
        def get_filtered_relationships():
            """获取过滤后的股权关系，考虑合并状态和隐藏关系"""
            filtered_relationships = []
        
            for rel in st.session_state.equity_data.get("entity_relationships", []):
                from_entity = rel.get('from', rel.get('parent', ''))
                to_entity = rel.get('to', rel.get('child', ''))
            
                # 检查关系是否被隐藏
                rel_id = f"{from_entity}→{to_entity}"
                is_hidden = rel_id in st.session_state.get("hidden_relationships", [])
            
                # 如果关系中的实体都没有被隐藏，且关系本身没有被隐藏，则保留这个关系
                if (from_entity not in st.session_state.get("hidden_entities", []) and 
                    to_entity not in st.session_state.get("hidden_entities", []) and
                    not is_hidden):
                    filtered_relationships.append(rel)
        
            # 🔥 关键修复：为合并后的实体添加新的关系
            for merged in st.session_state.get("merged_entities", []):
                merged_name = merged["merged_name"]
                total_percentage = merged["total_percentage"]
            
                # 收集所有被合并实体的关系，按目标公司分组
                target_relationships = {}  # {target_company: [relations]}
            
                for entity in merged["entities"]:
                    entity_name = entity["name"]
                    for rel in st.session_state.equity_data.get("entity_relationships", []):
                        from_entity = rel.get('from', rel.get('parent', ''))
                        to_entity = rel.get('to', rel.get('child', ''))
                    
                        if from_entity == entity_name:
                            if to_entity not in target_relationships:
                                target_relationships[to_entity] = []
                            target_relationships[to_entity].append({
                                "entity": entity_name,
                                "percentage": entity.get("percentage", 0),
                                "relationship": rel
                            })
            
                # 检查是否所有实体都指向同一个目标
                if len(target_relationships) == 1:
                    # 所有实体都指向同一个目标，可以合并
                    target_company = list(target_relationships.keys())[0]
                    relations = list(target_relationships.values())[0]
                    total_percentage = sum(rel["percentage"] for rel in relations)
                
                    filtered_relationships.append({
                        "from": merged_name,
                        "to": target_company,
                        "percentage": total_percentage,
                        "relationship_type": relations[0]["relationship"].get("relationship_type", "控股"),
                        "description": f"持股{total_percentage}%"
                    })
                else:
                    # 指向不同目标，不合并，保持原关系
                    st.warning(f"⚠️ 合并实体 '{merged_name}' 中的实体指向不同目标公司，无法合并：")
                    for target, relations in target_relationships.items():
                        entities_names = [rel["entity"] for rel in relations]
                        total_pct = sum(rel["percentage"] for rel in relations)
                        st.write(f"  - {', '.join(entities_names)} → {target} ({total_pct}%)")
                
                    # 保持原关系
                    for entity in merged["entities"]:
                        entity_name = entity["name"]
                        for rel in st.session_state.equity_data.get("entity_relationships", []):
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                        
                            if from_entity == entity_name:
                                filtered_relationships.append(rel)
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
            
            # 分组方式选择（不改变数据，仅改变展示）
            group_mode = st.radio("分组方式", ["按被投资方分组", "按母公司分组"], horizontal=True, key="entity_rel_group_mode")

            # 先按原顺序构建分组，确保组与组内条目顺序稳定
            grouped = {}
            for i, rel in enumerate(filtered_relationships):
                _from = rel.get('from', rel.get('parent', '未知'))
                _to = rel.get('to', rel.get('child', '未知'))
                key_entity = _to if group_mode == "按被投资方分组" else _from
                if key_entity not in grouped:
                    grouped[key_entity] = []
                grouped[key_entity].append((i, rel, _from, _to))

            # 按条数从多到少排序分组
            sorted_groups = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
        
            # 展示每个分组
            for group_entity, items in sorted_groups:
                with st.expander(f"{group_entity}（{len(items)} 条）", expanded=False):
                    for i, rel, from_entity, to_entity in items:
                        # 获取百分比值，优先级：1.关系中的percentage字段 2.从实体信息中获取 3.默认N/A
                        percentage = rel.get('percentage', None)
                        if percentage is None or percentage == 0 or percentage == 'N/A':
                            percentage = get_entity_percentage_for_display(from_entity)
                        percentage_display = f"{percentage:.1f}" if isinstance(percentage, (int, float)) and percentage > 0 else 'N/A'

                        with st.expander(f"{from_entity} → {to_entity} ({percentage_display}%)"):
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button("编辑", key=f"edit_rel_{i}"):
                                    # 保持原有逻辑：传递当前过滤列表索引，不更改数据结构
                                    st.session_state.editing_relationship = ("entity", i)
                                    st.rerun()
                            with col2:
                                if st.button("删除", key=f"delete_rel_{i}", type="secondary"):
                                    # 兼容from/to和parent/child两种格式
                                    from_entity_del = rel.get('from', rel.get('parent', '未知'))
                                    to_entity_del = rel.get('to', rel.get('child', '未知'))
                                    percentage_del = rel.get('percentage', 0)

                                    # 🔍 详细调试信息（收起）
                                    with st.expander("🔍 删除关系调试信息", expanded=False):
                                        st.write(f"准备删除关系 {from_entity_del} → {to_entity_del} ({percentage_del}%)")
                                        st.write(f"当前entity_relationships数量: {len(st.session_state.equity_data['entity_relationships'])}")

                                        # 显示所有关系用于调试
                                        st.write("当前所有entity_relationships:")
                                        for idx, rel_item in enumerate(st.session_state.equity_data["entity_relationships"]):
                                            rel_from = rel_item.get('from', rel_item.get('parent', ''))
                                            rel_to = rel_item.get('to', rel_item.get('child', ''))
                                            rel_percentage = rel_item.get('percentage', 0)
                                            st.write(f"  {idx}: {rel_from} → {rel_to} ({rel_percentage}%)")

                                        # 🔥 关键修复：在过滤后的关系中删除，而不是在原始关系中删除
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
                                            if orig_from == from_entity_del and orig_to == to_entity_del:
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
                                        st.success(f"✅ 已删除关系: {from_entity_del} → {to_entity_del}")
                                    else:
                                        st.success(f"✅ 已删除关系: {from_entity_del} → {to_entity_del} (仅从过滤列表中删除)")

                                    st.rerun()
        else:
            st.info("尚未添加股权关系")
    
        # 阈值隐藏功能
        st.markdown("### 👁️ 隐藏股权关系")
    
        if filtered_relationships:
            st.markdown("""
            本功能可以按持股比例阈值隐藏股权关系，让图表更简洁清晰。
            - 原始数据会保留，只是在图表中不显示
            - 可以随时恢复被隐藏的关系
            """)
        
            # 阈值设置
            col1, col2 = st.columns([1, 2])
            with col1:
                threshold = st.number_input(
                    "设置阈值 (%)", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=1.0, 
                    step=0.1,
                    help="持股比例小于此阈值的关系将被隐藏"
                )
        
            with col2:
                st.caption("💡 提示：设置阈值后，持股比例小于该值的关系将被隐藏，但不会删除原始数据")
        
            # 获取符合阈值的关系
            def get_threshold_relationships(threshold_value):
                """获取符合阈值条件的股权关系"""
                threshold_rels = []
                for i, rel in enumerate(filtered_relationships):
                    percentage = rel.get('percentage', None)
                    if percentage is None or percentage == 0 or percentage == 'N/A':
                        # 尝试从实体信息中获取持股比例
                        from_entity = rel.get('from', rel.get('parent', ''))
                        percentage = get_entity_percentage_for_display(from_entity)
                
                    if percentage is not None and isinstance(percentage, (int, float)) and percentage < threshold_value:
                        threshold_rels.append((i, rel, percentage))
            
                return threshold_rels
        
            threshold_relationships = get_threshold_relationships(threshold)
        
            if threshold_relationships:
                st.warning(f"⚠️ 发现 {len(threshold_relationships)} 个持股比例小于 {threshold}% 的关系")
            
                # 显示将被隐藏的关系
                with st.expander(f"查看将被隐藏的关系（{len(threshold_relationships)} 条）", expanded=False):
                    for i, rel, percentage in threshold_relationships:
                        from_entity = rel.get('from', rel.get('parent', '未知'))
                        to_entity = rel.get('to', rel.get('child', '未知'))
                        percentage_display = f"{percentage:.1f}" if isinstance(percentage, (int, float)) and percentage > 0 else 'N/A'
                        st.write(f"• {from_entity} → {to_entity} ({percentage_display}%)")
            
                # 确认隐藏按钮
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("👁️ 确认隐藏关系", type="primary", use_container_width=True, key="threshold_hide_confirm"):
                        # 初始化隐藏关系列表和隐藏实体列表
                        if "hidden_relationships" not in st.session_state:
                            st.session_state.hidden_relationships = []
                        if "hidden_entities" not in st.session_state:
                            st.session_state.hidden_entities = []
                    
                        # 收集需要隐藏的实体
                        entities_to_hide = set()
                    
                        # 添加关系索引到隐藏列表
                        hidden_count = 0
                        for i, rel, percentage in threshold_relationships:
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                            rel_id = f"{from_entity}→{to_entity}"
                        
                            if rel_id not in st.session_state.hidden_relationships:
                                st.session_state.hidden_relationships.append(rel_id)
                                hidden_count += 1
                        
                            # 收集关系中的实体
                            entities_to_hide.add(from_entity)
                            entities_to_hide.add(to_entity)
                    
                        # 检查这些实体是否还有其他关系，如果没有则隐藏实体
                        hidden_entities_count = 0
                        for entity in entities_to_hide:
                            # 检查实体是否还有其他未隐藏的关系
                            has_other_relationships = False
                            for rel in st.session_state.equity_data.get("entity_relationships", []):
                                rel_from = rel.get('from', rel.get('parent', ''))
                                rel_to = rel.get('to', rel.get('child', ''))
                                rel_id = f"{rel_from}→{rel_to}"
                            
                                # 如果这个关系没有被隐藏，且涉及当前实体
                                if (rel_id not in st.session_state.hidden_relationships and 
                                    (rel_from == entity or rel_to == entity)):
                                    has_other_relationships = True
                                    break
                        
                            # 如果没有其他关系，则隐藏实体
                            if not has_other_relationships and entity not in st.session_state.hidden_entities:
                                st.session_state.hidden_entities.append(entity)
                                hidden_entities_count += 1
                    
                        success_msg = f"✅ 已隐藏 {hidden_count} 个关系"
                        if hidden_entities_count > 0:
                            success_msg += f" 和 {hidden_entities_count} 个实体"
                        st.success(success_msg)
                        st.rerun()
            
                with col2:
                    if st.button("取消", use_container_width=True, key="threshold_hide_cancel"):
                        st.info("已取消隐藏操作")
            else:
                st.info(f"没有找到持股比例小于 {threshold}% 的关系")
    
        # 显示已隐藏的关系管理
        if st.session_state.get("hidden_relationships"):
            st.markdown("#### 已隐藏的关系管理")
            st.success(f"✅ 当前已隐藏 {len(st.session_state.hidden_relationships)} 个关系")
        
            with st.expander("查看已隐藏的关系", expanded=False):
                for rel_id in st.session_state.hidden_relationships:
                    st.write(f"• {rel_id}")
                
                    # 恢复按钮
                    if st.button(f"恢复: {rel_id}", key=f"restore_{rel_id}"):
                        st.session_state.hidden_relationships.remove(rel_id)
                    
                        # 解析关系ID获取实体名称
                        if "→" in rel_id:
                            from_entity, to_entity = rel_id.split("→", 1)
                        
                            # 检查这些实体是否应该被恢复
                            entities_to_check = [from_entity, to_entity]
                            restored_entities = []
                        
                            for entity in entities_to_check:
                                if entity in st.session_state.get("hidden_entities", []):
                                    # 检查实体是否还有其他未隐藏的关系
                                    has_other_relationships = False
                                    for rel in st.session_state.equity_data.get("entity_relationships", []):
                                        rel_from = rel.get('from', rel.get('parent', ''))
                                        rel_to = rel.get('to', rel.get('child', ''))
                                        other_rel_id = f"{rel_from}→{rel_to}"
                                    
                                        # 如果这个关系没有被隐藏，且涉及当前实体
                                        if (other_rel_id not in st.session_state.hidden_relationships and 
                                            (rel_from == entity or rel_to == entity)):
                                            has_other_relationships = True
                                            break
                                
                                    # 如果有其他关系，则恢复实体
                                    if has_other_relationships:
                                        st.session_state.hidden_entities.remove(entity)
                                        restored_entities.append(entity)
                        
                            success_msg = f"已恢复关系: {rel_id}"
                            if restored_entities:
                                success_msg += f" 和实体: {', '.join(restored_entities)}"
                            st.success(success_msg)
                        else:
                            st.success(f"已恢复关系: {rel_id}")
                        st.rerun()
        
            # 全部恢复按钮
            if st.button("🔄 恢复所有隐藏关系", type="secondary"):
                # 收集所有被隐藏关系中的实体
                entities_in_hidden_relationships = set()
                for rel_id in st.session_state.hidden_relationships:
                    if "→" in rel_id:
                        from_entity, to_entity = rel_id.split("→", 1)
                        entities_in_hidden_relationships.add(from_entity)
                        entities_in_hidden_relationships.add(to_entity)
            
                # 恢复关系
                st.session_state.hidden_relationships = []
            
                # 检查并恢复相关实体
                restored_entities = []
                for entity in entities_in_hidden_relationships:
                    if entity in st.session_state.get("hidden_entities", []):
                        # 检查实体是否还有其他未隐藏的关系
                        has_other_relationships = False
                        for rel in st.session_state.equity_data.get("entity_relationships", []):
                            rel_from = rel.get('from', rel.get('parent', ''))
                            rel_to = rel.get('to', rel.get('child', ''))
                            other_rel_id = f"{rel_from}→{rel_to}"
                        
                            # 如果这个关系没有被隐藏，且涉及当前实体
                            if (other_rel_id not in st.session_state.hidden_relationships and 
                                (rel_from == entity or rel_to == entity)):
                                has_other_relationships = True
                                break
                    
                        # 如果有其他关系，则恢复实体
                        if has_other_relationships:
                            st.session_state.hidden_entities.remove(entity)
                            restored_entities.append(entity)
            
                success_msg = "已恢复所有隐藏的关系"
                if restored_entities:
                    success_msg += f" 和实体: {', '.join(restored_entities)}"
                st.success(success_msg)
                st.rerun()
    
        # 显示控制关系（考虑合并状态）
        st.markdown("### ⚡ 控制关系（虚线表示）")
    
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
                    
                        # 过滤entity_relationships，移除涉及被隐藏实体的关系和被隐藏的关系
                        filtered_relationships = []
                        for rel in data_for_mermaid["entity_relationships"]:
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                        
                            # 检查关系是否被隐藏
                            rel_id = f"{from_entity}→{to_entity}"
                            is_hidden_relationship = rel_id in st.session_state.get("hidden_relationships", [])
                        
                            # 如果关系中的实体都没有被隐藏，且关系本身没有被隐藏，则保留这个关系
                            if (from_entity not in st.session_state.get("hidden_entities", []) and 
                                to_entity not in st.session_state.get("hidden_entities", []) and
                                not is_hidden_relationship):
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
                    
                        # 🔥 关键修复：为合并后的实体添加新的关系
                        for merged in st.session_state.get("merged_entities", []):
                            merged_name = merged["merged_name"]
                            total_percentage = merged["total_percentage"]
                        
                            # 收集所有被合并实体的关系，按目标公司分组
                            target_relationships = {}  # {target_company: [relations]}
                        
                            for entity in merged["entities"]:
                                entity_name = entity["name"]
                                for rel in st.session_state.equity_data.get("entity_relationships", []):
                                    from_entity = rel.get('from', rel.get('parent', ''))
                                    to_entity = rel.get('to', rel.get('child', ''))
                                
                                    if from_entity == entity_name:
                                        if to_entity not in target_relationships:
                                            target_relationships[to_entity] = []
                                        target_relationships[to_entity].append({
                                            "entity": entity_name,
                                            "percentage": entity.get("percentage", 0),
                                            "relationship": rel
                                        })
                        
                            # 检查是否所有实体都指向同一个目标
                            if len(target_relationships) == 1:
                                # 所有实体都指向同一个目标，可以合并
                                target_company = list(target_relationships.keys())[0]
                                relations = list(target_relationships.values())[0]
                                total_percentage = sum(rel["percentage"] for rel in relations)
                            
                                filtered_relationships.append({
                                    "from": merged_name,
                                    "to": target_company,
                                    "percentage": total_percentage,
                                    "relationship_type": relations[0]["relationship"].get("relationship_type", "控股"),
                                    "description": f"持股{total_percentage}%"
                                })
                            else:
                                # 指向不同目标，不合并，保持原关系
                                for entity in merged["entities"]:
                                    entity_name = entity["name"]
                                    for rel in st.session_state.equity_data.get("entity_relationships", []):
                                        from_entity = rel.get('from', rel.get('parent', ''))
                                        to_entity = rel.get('to', rel.get('child', ''))
                                    
                                        if from_entity == entity_name:
                                            filtered_relationships.append(rel)
                                            break
                    
                        data_for_mermaid["entity_relationships"] = filtered_relationships
                    else:
                        # 没有合并实体时，也需要过滤隐藏的关系
                        filtered_relationships = []
                        for rel in data_for_mermaid["entity_relationships"]:
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                        
                            # 检查关系是否被隐藏
                            rel_id = f"{from_entity}→{to_entity}"
                            is_hidden_relationship = rel_id in st.session_state.get("hidden_relationships", [])
                        
                            # 如果关系中的实体都没有被隐藏，且关系本身没有被隐藏，则保留这个关系
                            if (from_entity not in st.session_state.get("hidden_entities", []) and 
                                to_entity not in st.session_state.get("hidden_entities", []) and
                                not is_hidden_relationship):
                                filtered_relationships.append(rel)
                    
                        data_for_mermaid["entity_relationships"] = filtered_relationships
                    
                        # 过滤top_entities，移除被隐藏的实体
                        filtered_top_entities = []
                        for entity in data_for_mermaid["top_entities"]:
                            if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                                filtered_top_entities.append(entity)
                        data_for_mermaid["top_entities"] = filtered_top_entities
                    
                        # 过滤all_entities，移除被隐藏的实体
                        filtered_all_entities = []
                        for entity in data_for_mermaid["all_entities"]:
                            if entity.get("name", "") not in st.session_state.get("hidden_entities", []):
                                filtered_all_entities.append(entity)
                        data_for_mermaid["all_entities"] = filtered_all_entities
                
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
                    # 展示用于调试的Mermaid代码
                    with st.expander("查看Mermaid代码（预览）", expanded=False):
                        st.code(preview_mermaid_code, language="text")
                    # 使用动态key强制组件在代码变化时重新渲染，避免缓存导致的异常
                    preview_key = f"preview_mermaid_chart_{abs(hash(preview_mermaid_code))%1000000}"
                    st_mermaid(preview_mermaid_code, key=preview_key)
                    st.caption("注意：此预览将随您的关系设置实时更新")
                
                except Exception as e:
                    import traceback
                    st.error(f"生成预览时出错: {str(e)}")
                    with st.expander("查看错误详情（traceback）", expanded=False):
                        st.code(traceback.format_exc())
            elif show_preview:
                st.info("请先设置核心公司以查看预览")
            else:
                st.caption("勾选上方复选框以查看关系设置的实时预览")
            
            tab1, tab2 = st.tabs(["🔗 添加股权关系", "⚡ 添加控制关系"])
        
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
            
                st.subheader("🔗 添加股权关系")
            
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
    
        # 验证合并实体是否指向同一目标
        def validate_merge_entities(entities_to_merge, entity_type="shareholder"):
            """验证要合并的实体是否指向同一目标公司"""
            target_relationships = {}  # {target_company: [entities]}
        
            for entity in entities_to_merge:
                entity_name = entity["name"]
                for rel in st.session_state.equity_data.get("entity_relationships", []):
                    from_entity = rel.get('from', rel.get('parent', ''))
                    to_entity = rel.get('to', rel.get('child', ''))
                
                    if from_entity == entity_name:
                        if to_entity not in target_relationships:
                            target_relationships[to_entity] = []
                        target_relationships[to_entity].append(entity_name)
                        break
        
            if len(target_relationships) > 1:
                # 指向不同目标，显示警告
                st.error(f"⚠️ 无法合并：选中的{entity_type}指向不同目标公司")
                for target, entities in target_relationships.items():
                    st.write(f"  - {', '.join(entities)} → {target}")
                return False
            return True

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
                            elif not validate_merge_entities(shareholders_to_merge, "股东"):
                                # 验证失败，不执行合并
                                pass
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
                                elif not validate_merge_entities(shareholders_to_merge, "股东"):
                                    # 验证失败，不执行合并
                                    pass
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
                            elif not validate_merge_entities(subsidiaries_to_merge, "子公司"):
                                # 验证失败，不执行合并
                                pass
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
                available_subsidiaries = [
                    e for e in mergeable_subsidiaries
                    if e["name"] not in st.session_state.get("hidden_entities", [])
                ]
            
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
                    with st.container():
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
                                st.write(f"{float(entity.get('percentage') or 0):.2f}%")
                        
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
                                elif not validate_merge_entities(subsidiaries_to_merge, "子公司"):
                                    # 验证失败，不执行合并
                                    pass
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
                                    if "hidden_entities" not in st.session_state:
                                        st.session_state.hidden_entities = []
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
    
        # 操作按钮区域 - 三个按钮统一布局
        st.markdown("### 操作")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("返回编辑", type="secondary", key="back_to_edit", use_container_width=True):
                # 验证数据后再跳转
                data_valid, validation_logs = validate_equity_data(st.session_state.equity_data)
                if data_valid:
                    st.session_state.current_step = "merge_entities"
                    st.rerun()
                else:
                    st.error("数据验证失败，无法返回编辑。请检查数据后重试。")
    
        with col2:
            if st.button("翻译所有实体", key="batch_translate_all_before_generate", use_container_width=True):
                _batch_translate_all_entities()
    
        with col3:
            generate_clicked = st.button("生成图表", type="primary", key="generate_chart_btn", use_container_width=True)
    
        # 生成图表逻辑
        if generate_clicked:
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
                    
                        # 过滤entity_relationships，移除涉及被隐藏实体的关系和被隐藏的关系
                        filtered_relationships = []
                        for rel in data_for_mermaid["entity_relationships"]:
                            from_entity = rel.get('from', rel.get('parent', ''))
                            to_entity = rel.get('to', rel.get('child', ''))
                        
                            # 检查关系是否被隐藏
                            rel_id = f"{from_entity}→{to_entity}"
                            is_hidden_relationship = rel_id in st.session_state.get("hidden_relationships", [])
                        
                            # 如果关系中的实体都没有被隐藏，且关系本身没有被隐藏，则保留这个关系
                            if (from_entity not in st.session_state.hidden_entities and 
                                to_entity not in st.session_state.hidden_entities and
                                not is_hidden_relationship):
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
                index=1,  # 🔥 默认选择第二个选项（交互式HTML图表）
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

# 主程序入口
if __name__ == "__main__":
    render_page()
