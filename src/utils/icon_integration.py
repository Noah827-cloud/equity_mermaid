"""
Figma图标集成工具

此模块提供了将Figma SVG图标集成到股权关系图表工具的实用函数，包括：
- SVG图标编码转换
- Mermaid图表图标增强
- Streamlit UI组件图标化
"""

import base64
import os
import re
from typing import Dict, Optional, List, Tuple


def svg_to_base64(svg_path: str) -> str:
    """
    将SVG文件转换为Base64编码字符串
    
    Args:
        svg_path: SVG文件的路径
    
    Returns:
        Base64编码的字符串
    """
    try:
        with open(svg_path, "rb") as svg_file:
            encoded_bytes = base64.b64encode(svg_file.read())
            return encoded_bytes.decode('utf-8')
    except Exception as e:
        print(f"SVG转换Base64失败: {e}")
        return ""


def get_icon_path(icon_name: str, icon_type: str = "company") -> str:
    """
    获取图标文件的路径
    
    Args:
        icon_name: 图标名称
        icon_type: 图标类型（company, user, action等）
    
    Returns:
        图标文件的绝对路径
    """
    # 构建图标路径
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_path = os.path.join(base_dir, "src", "assets", "icons", icon_type, f"{icon_name}.svg")
    
    return icon_path


def get_mermaid_icon_class(icon_base64: str, icon_size: int = 24) -> str:
    """
    生成Mermaid图表中使用的图标样式类
    
    Args:
        icon_base64: Base64编码的图标字符串
        icon_size: 图标尺寸（像素）
    
    Returns:
        Mermaid类定义字符串
    """
    # 注意：Mermaid不直接支持SVG图标，但可以通过CSS background-image模拟
    # 这里提供一个基础实现，实际应用中可能需要调整
    icon_class = f"""
    .node-icon {{ 
        background-image: url('data:image/svg+xml;base64,{icon_base64}'); 
        background-repeat: no-repeat; 
        background-position: left center; 
        padding-left: {icon_size + 8}px; 
    }}
    """
    
    return icon_class


def enhance_mermaid_entity_style(entity_type: str, base_style: str, icon_name: Optional[str] = None) -> str:
    """
    增强Mermaid实体样式，添加图标支持
    
    Args:
        entity_type: 实体类型（company, subsidiary, topEntity等）
        base_style: 基础样式字符串
        icon_name: 图标名称（可选）
    
    Returns:
        增强后的样式字符串
    """
    enhanced_style = base_style
    
    # 如果提供了图标名称，则添加图标相关样式
    if icon_name:
        # 在Mermaid中，我们可以通过添加HTML类来支持图标
        # 注意：这取决于Mermaid渲染器对HTML的支持程度
        icon_class = f"node-icon-{entity_type}"
        
        # 如果样式字符串不包含class，直接添加
        if not re.search(r'class\s*:', base_style):
            enhanced_style += f",class:'{icon_class}'"
        else:
            # 如果已经有class定义，追加图标类
            enhanced_style = re.sub(r"class:'([^']+)',", f"class:'\1 {icon_class}',", base_style)
    
    return enhanced_style


def create_feature_card_html(title: str, description: str, url: str, button_text: str, 
                            icon_name: Optional[str] = None, icon_type: str = "action") -> str:
    """
    创建带有图标的功能卡片HTML
    
    Args:
        title: 卡片标题
        description: 卡片描述
        url: 链接URL
        button_text: 按钮文本
        icon_name: 图标名称（可选）
        icon_type: 图标类型
    
    Returns:
        HTML字符串
    """
    icon_html = ""
    
    # 如果提供了图标名称，添加图标HTML
    if icon_name:
        icon_path = get_icon_path(icon_name, icon_type)
        if os.path.exists(icon_path):
            svg_base64 = svg_to_base64(icon_path)
            icon_html = f"""
            <div class="feature-icon">
                <img src="data:image/svg+xml;base64,{svg_base64}" width="48" height="48">
            </div>
            """
        else:
            # 使用FontAwesome作为备选
            icon_html = f"""
            <div class="feature-icon">
                <i class="fas fa-{icon_name}" style="font-size: 48px;"></i>
            </div>
            """
    
    # 创建完整的卡片HTML
    card_html = f"""
    <div class="feature-card">
        {icon_html}
        <h3>{title}</h3>
        <p>{description}</p>
        <a href="{url}" class="btn">{button_text}</a>
    </div>
    """
    
    return card_html


def get_sidebar_button_with_icon(label: str, icon_name: str, icon_type: str = "action") -> str:
    """
    获取带有图标的侧边栏按钮
    
    Args:
        label: 按钮标签
        icon_name: 图标名称
        icon_type: 图标类型
    
    Returns:
        按钮标签文本（带有图标标记）
    """
    # 在Streamlit中，我们可以使用emoji或内置图标
    # 这里使用emoji标记作为示例
    icon_emoji_map = {
        "chart": ":chart_with_upwards_trend:",
        "pencil": ":pencil:",
        "home": ":house:",
        "settings": ":gear:",
        "help": ":question_mark:",
        "upload": ":arrow_up:",
        "download": ":arrow_down:",
        "company": ":office:",
        "user": ":bust_in_silhouette:",
        "save": ":floppy_disk:",
        "refresh": ":arrows_counterclockwise:",
        "trash": ":wastebasket:",
        "add": ":plus:",
        "minus": ":minus:",
        "search": ":mag:",
    }
    
    # 使用映射的emoji或默认图标
    icon = icon_emoji_map.get(icon_name.lower(), ":star:")
    return f"{icon} {label}"


def generate_mermaid_icon_css(icon_mapping: Dict[str, Tuple[str, str]]) -> str:
    """
    生成包含所有图标的CSS样式
    
    Args:
        icon_mapping: 图标映射字典，格式为 {entity_type: (icon_name, icon_type)}
    
    Returns:
        CSS样式字符串
    """
    css_parts = []
    
    for entity_type, (icon_name, icon_type) in icon_mapping.items():
        icon_path = get_icon_path(icon_name, icon_type)
        if os.path.exists(icon_path):
            svg_base64 = svg_to_base64(icon_path)
            css_parts.append(f"""
            .node-icon-{entity_type} {{
                background-image: url('data:image/svg+xml;base64,{svg_base64}');
                background-repeat: no-repeat;
                background-position: 5px center;
                padding-left: 32px;
                min-height: 24px;
                display: inline-flex;
                align-items: center;
            }}
            """)
    
    return "\n".join(css_parts)


def get_default_icon_mapping() -> Dict[str, Tuple[str, str]]:
    """
    获取默认的图标映射
    
    Returns:
        默认图标映射字典
    """
    return {
        "coreCompany": ("building", "company"),
        "topEntity": ("user", "user"),
        "company": ("office", "company"),
        "subsidiary": ("office-building", "company"),
        "government": ("capitol", "company"),
    }