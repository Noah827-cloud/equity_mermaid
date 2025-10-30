#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Display formatting helpers for capital and establishment date strings.
These helpers are used by both Mermaid and HTML renderers to avoid duplication.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional


def normalize_amount_to_wan(value: str | float | int | None) -> Optional[float]:
    """Normalize various amount strings to '万' (ten-thousand) unit as float.

    Examples:
    - "1000万元" -> 1000.0
    - "1亿元" -> 10000.0
    - "500000元" -> 50.0
    - "1000" (no unit) -> 1000.0 (assume 万)
    - 1200 -> 1200.0
    """
    if value is None:
        return None
    try:
        # numeric passthrough
        if isinstance(value, (int, float)):
            return float(value)

        raw = str(value).strip()
        if not raw:
            return None

        # detect unit
        has_yi = ('亿元' in raw) or ('亿' in raw)
        has_wan = ('万元' in raw) or ('万' in raw)
        has_yuan = ('元' in raw) and not (has_yi or has_wan)

        # extract number
        m = re.search(r"([-+]?[0-9]*\.?[0-9]+)", raw.replace(',', ''))
        if not m:
            return None
        num = float(m.group(1))

        if has_yi:
            return num * 10000.0
        if has_yuan:
            return num / 10000.0
        # default assume 万
        return num
    except Exception:
        return None


_MONTH_NAMES = [
    None,
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _parse_date_flexible(raw: str | None) -> Optional[datetime]:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # try common formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m", "%Y/%m", "%Y.%m", "%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    # try to extract numbers
    m = re.search(r"(\d{4})(?:[-/.年 ](\d{1,2}))?(?:[-/.日 ](\d{1,2}))?", s)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2)) if m.group(2) else 1
        d = int(m.group(3)) if m.group(3) else 1
        try:
            return datetime(y, mo, d)
        except Exception:
            return datetime(y, 1, 1)
    return None


def format_capital_for_display(amount_wan: float, unit: str = "万元") -> Optional[str]:
    """Format capital amount for display: 'RMB{X}M' where X = 万/100, M = 百万.
    
    Args:
        amount_wan: Amount in 万元 (ten-thousand)
        unit: Unit string (default: "万元")
    
    Returns:
        Formatted string like "RMB{X}M" or None if invalid
    """
    if amount_wan is None:
        return None
    # convert from 万 to 百万 (divide by 100)
    x = amount_wan / 100.0
    if abs(x - int(x)) < 1e-9:
        num_str = f"{int(x)}"
    else:
        num_str = f"{x:.2f}".rstrip('0').rstrip('.')
    return f"RMB{num_str}M"


def format_registered_capital_display(raw: str | float | int | None) -> Optional[str]:
    """Format to English label: 'Cap: RMB{X}M' where X = 万/100, M = 百万.

    Returns None if cannot parse.
    """
    amount_wan = normalize_amount_to_wan(raw)
    if amount_wan is None:
        return None
    formatted_capital = format_capital_for_display(amount_wan)
    if formatted_capital:
        return f"Cap: {formatted_capital}"
    return None


def format_subscribed_capital_display(raw: str | float | int | None) -> Optional[str]:
    """Format to English label: 'Cap: RMB{X}M' where X = 万/100, M = 百万.

    Returns None if cannot parse.
    """
    amount_wan = normalize_amount_to_wan(raw)
    if amount_wan is None:
        return None
    formatted_capital = format_capital_for_display(amount_wan)
    if formatted_capital:
        return f"Cap: {formatted_capital}"
    return None


def format_date_for_display(date_str: str | None) -> Optional[str]:
    """Format date for display: 'Established: {Month}.{Year}' or 'Established: {Year}'.

    Args:
        date_str: Date string in YYYY-MM-DD format or other common formats
    
    Returns:
        Formatted string like "Established: June.2010" or "Established: 2010"
    """
    dt = _parse_date_flexible(date_str)
    if not dt:
        return None
    # if only year was provided, month may be January from parser; detect from raw
    s = str(date_str) if date_str is not None else ""
    ym_only = bool(re.fullmatch(r"\d{4}$", s.strip()))
    y_or_ym = ym_only or bool(re.fullmatch(r"\d{4}[-/.]\d{1,2}$", s.strip()))
    if y_or_ym:
        month_name = _MONTH_NAMES[dt.month]
        if ym_only:
            # year only
            return f"Established: {dt.year}"
        return f"Established: {month_name}.{dt.year}"
    # full date -> use month.year
    month_name = _MONTH_NAMES[dt.month]
    return f"Established: {month_name}.{dt.year}"


def format_established_display(raw_date: str | None) -> Optional[str]:
    """Format to English label like 'Established: June.2010' or 'Established: 2010'.

    Accepts YYYY, YYYY-MM, YYYY-MM-DD and common separators.
    """
    return format_date_for_display(raw_date)


def format_chinese_person_name(name: str) -> str:
    """
    格式化中文人名为标准格式，将连写的人名分开
    
    示例：
    - "Shen Yingming" -> "Shen Ying Ming"
    - "Wang Xiaoming" -> "Wang Xiao Ming"
    - "Li Ming" -> "Li Ming" (已经是正确格式)
    - "Zhang Wei" -> "Zhang Wei" (已经是正确格式)
    
    Args:
        name: 待格式化的中文人名
        
    Returns:
        str: 格式化后的人名
    """
    if not name or not isinstance(name, str):
        return name
    
    # 按空格分割
    parts = name.strip().split()
    if len(parts) != 2:
        return name  # 如果不是标准的"姓 名"格式，直接返回
    
    surname, given_name = parts
    
    # 检查名字部分是否包含多个字符且没有空格
    # 如果名字长度大于3且是字母，尝试分离
    if len(given_name) > 3 and given_name.isalpha() and not ' ' in given_name:
        # 尝试分离连写的名字
        # 常见的分离模式：在元音后分离，或者按音节分离
        separated_name = _separate_chinese_name(given_name)
        if separated_name != given_name:
            return f"{surname} {separated_name}"
    
    return name


def _separate_chinese_name(name: str) -> str:
    """
    分离连写的中文名字，基于中文拼音韵母组合规则
    
    示例：
    - "yingming" -> "Ying Ming"
    - "xiaoming" -> "Xiao Ming"
    - "weiming" -> "Wei Ming"
    - "xiaoli" -> "Xiao Li"
    - "bingjie" -> "Bing Jie"
    """
    if len(name) <= 1:
        return name.capitalize()
    
    # 如果名字太短（3个字符或更少），不分离
    if len(name) <= 3:
        return name.capitalize()
    
    # 特殊处理一些常见的中文名字模式（优先检查）
    common_patterns = {
        'lili': 'Li Li',  # 处理 "Lili" 格式
        'lishuo': 'Li Shuo',  # 处理 "Lishuo" 格式
        'bingjie': 'Bing Jie',  # 处理 "Bingjie" 格式
        'xiaoli': 'Xiao Li',
        'xiaoming': 'Xiao Ming',
        'yingming': 'Ying Ming',
        'weiming': 'Wei Ming',
        'yuankun': 'Yuan Kun',
        'weimingn': 'Wei Ming',  # 处理 "Weiming N" 合并后的情况
        'xiaohong': 'Xiao Hong',
        'xiaohongn': 'Xiao Hong',  # 处理 "Xiaohong N" 合并后的情况
        'xiaofang': 'Xiao Fang',
        'xiaojun': 'Xiao Jun',
        'xiaoliang': 'Xiao Liang',
        'xiaohui': 'Xiao Hui',
        'xiaoyan': 'Xiao Yan',
        'xiaojie': 'Xiao Jie',
        'xiaohua': 'Xiao Hua',
        'xiaojing': 'Xiao Jing',
        'xiaofeng': 'Xiao Feng',
        'xiaogang': 'Xiao Gang',
        'xiaohai': 'Xiao Hai',
    }
    
    # 检查是否是已知的模式
    if name.lower() in common_patterns:
        return common_patterns[name.lower()]
    
    # 基于中文拼音韵母组合规则的智能分割
    separated = _intelligent_pinyin_separation(name)
    if separated != name:
        return separated
    
    # 如果无法分离，返回首字母大写的原名字
    return name.capitalize()


def _intelligent_pinyin_separation(name: str) -> str:
    """
    基于中文拼音韵母组合规则的智能分割
    """
    # 常见的韵母组合，这些通常作为一个整体
    common_finals = {
        'ing', 'ang', 'ong', 'eng', 'ian', 'iao', 'iang', 'iong',
        'uan', 'uai', 'uang', 'uei', 'uen', 'ueng', 'üan', 'üe'
    }
    
    # 常见的声母
    common_initials = {
        'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h',
        'j', 'q', 'x', 'zh', 'ch', 'sh', 'r', 'z', 'c', 's', 'y', 'w'
    }
    
    # 尝试在韵母组合后分割
    for i in range(len(name) - 1, 0, -1):
        # 检查是否以常见韵母结尾
        for final in common_finals:
            if name[i-len(final)+1:i+1].lower() == final:
                # 检查前面是否有合理的声母
                if i - len(final) >= 0:
                    remaining = name[:i-len(final)+1]
                    if len(remaining) >= 1:
                        first_part = remaining.capitalize()
                        second_part = name[i-len(final)+1:].capitalize()
                        return f"{first_part} {second_part}"
    
    # 尝试在常见声母后分割
    for i in range(1, len(name) - 1):
        # 检查双字母声母
        if i + 1 < len(name):
            two_char = name[i:i+2].lower()
            if two_char in ['zh', 'ch', 'sh']:
                first_part = name[:i].capitalize()
                second_part = name[i:].capitalize()
                return f"{first_part} {second_part}"
        
        # 检查单字母声母
        if name[i].lower() in common_initials:
            first_part = name[:i].capitalize()
            second_part = name[i:].capitalize()
            return f"{first_part} {second_part}"
    
    # 如果以上规则都不适用，尝试在中间分割
    if len(name) % 2 == 0 and len(name) > 4:
        mid = len(name) // 2
        first_part = name[:mid].capitalize()
        second_part = name[mid:].capitalize()
        return f"{first_part} {second_part}"
    
    return name


def format_english_company_name(name: str) -> str:
    """
    格式化英文公司名称为标准格式：首字母大写，其余字母小写（专有名词除外）
    
    示例：
    - "LINO INVESTMENT HOLDING GROUP LIMITED" -> "Lino Investment Holding Group Limited"
    - "linuo power group co., ltd" -> "Linuo Power Group Co., Ltd."
    - "SHANDONG HONGJITANG PHARMACEUTICAL GROUP CO., LTD." -> "Shandong Hongjitang Pharmaceutical Group Co., Ltd."
    - "mr.gao yuankun" -> "Mr. Gao Yuankun"
    - "ms.shen yingming" -> "Ms. Shen Ying Ming"
    - "mrs.smith" -> "Mrs. Smith"
    - "Ms.shen Yingming" -> "Ms. Shen Ying Ming"
    
    Args:
        name: 待格式化的英文公司名称或人名
        
    Returns:
        str: 格式化后的名称
    """
    if not name or not isinstance(name, str):
        return name
    
    # 首先检查是否是中文人名格式（如 "Shen Yingming"）
    # 如果包含称谓，先处理称谓
    formatted_name = name
    
    # 英文称谓处理：Mr., Mrs., Ms., Dr., Prof. 等
    titles = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'sir.', 'madam.', 'miss.']
    
    # 处理称谓后直接跟姓氏的情况（如 "Ms.shen" -> "Ms. shen"）
    for title in titles:
        # 匹配称谓后直接跟字母的情况（不区分大小写）
        pattern = rf'({title})([a-zA-Z])'
        formatted_name = re.sub(pattern, r'\1 \2', formatted_name, flags=re.IGNORECASE)
    
    # 检查是否包含称谓
    has_title = any(title in formatted_name.lower() for title in titles)
    
    # 检查是否是中文人名格式（无论是否有称谓）
    # 检查是否是 "Shen Yingming" 或 "Ms. Shen Yingming" 这样的格式
    parts = formatted_name.strip().split()
    
    # 如果有称谓，跳过称谓部分
    if has_title and len(parts) >= 2:
        # 跳过称谓，检查后面的部分
        name_parts = parts[1:]  # 跳过称谓
        if len(name_parts) == 1:
            # 处理单个人名，如 "Ms. Lili"
            given_name = name_parts[0]
            if (given_name.isalpha() and len(given_name) >= 4 and 
                given_name[0].isupper() and not ' ' in given_name):
                # 尝试分离中文人名
                separated_name = _separate_chinese_name(given_name)
                if separated_name != given_name:
                    return f"{parts[0]} {separated_name}"
        elif len(name_parts) == 2:
            surname, given_name = name_parts
            # 如果名字部分是字母且长度大于3，可能是连写的中文名
            if (given_name.isalpha() and len(given_name) > 3 and 
                surname.isalpha() and surname[0].isupper() and
                not ' ' in given_name):  # 确保没有空格
                # 尝试分离中文人名
                separated_name = _separate_chinese_name(given_name)
                if separated_name != given_name:
                    return f"{parts[0]} {surname} {separated_name}"
        elif len(name_parts) == 3:
            # 处理 "姓 名 N" 格式，如 "Gao Yuanku N"
            surname, given_name, last_char = name_parts
            if (last_char.upper() == 'N' and 
                surname.isalpha() and surname[0].isupper() and
                given_name.isalpha() and len(given_name) > 3):
                # 将 "N" 合并到名字中，然后分离
                combined_name = given_name + last_char.lower()
                separated_name = _separate_chinese_name(combined_name)
                if separated_name != combined_name:
                    return f"{parts[0]} {surname} {separated_name}"
    elif not has_title and len(parts) == 1:
        # 没有称谓的单个人名，如 "Lili"
        given_name = parts[0]
        if (given_name.isalpha() and len(given_name) >= 4 and 
            given_name[0].isupper() and not ' ' in given_name):
            # 尝试分离中文人名
            separated_name = _separate_chinese_name(given_name)
            if separated_name != given_name:
                return separated_name
    elif not has_title and len(parts) == 2:
        # 没有称谓的情况
        surname, given_name = parts
        # 如果名字部分是字母且长度大于3，可能是连写的中文名
        if (given_name.isalpha() and len(given_name) > 3 and 
            surname.isalpha() and surname[0].isupper() and
            not ' ' in given_name):  # 确保没有空格
            # 尝试分离中文人名
            separated_name = _separate_chinese_name(given_name)
            if separated_name != given_name:
                return f"{surname} {separated_name}"
    elif not has_title and len(parts) == 3:
        # 处理 "姓 名 N" 格式，如 "Gao Yuanku N"
        surname, given_name, last_char = parts
        if (last_char.upper() == 'N' and 
            surname.isalpha() and surname[0].isupper() and
            given_name.isalpha() and len(given_name) > 3):
            # 将 "N" 合并到名字中，然后分离
            combined_name = given_name + last_char.lower()
            separated_name = _separate_chinese_name(combined_name)
            if separated_name != combined_name:
                return f"{surname} {separated_name}"
    
    # 公司名称中常见的专有名词和缩写，需要保持特定格式
    company_abbreviations = {
        'co.', 'ltd.', 'inc.', 'corp.', 'llc.', 'llp.', 'lp.',
        'group', 'holdings', 'investment', 'international', 'global',
        'limited', 'corporation', 'incorporated', 'company'
    }
    
    # 特殊处理：保持某些常见缩写的大写格式
    special_abbreviations = {
        'co., ltd.': 'Co., Ltd.',
        'co., ltd': 'Co., Ltd.',
        'ltd.': 'Ltd.',
        'inc.': 'Inc.',
        'corp.': 'Corp.',
        'llc.': 'LLC.',
        'llp.': 'LLP.',
        'lp.': 'LP.'
    }
    
    # 转换为小写进行后续处理
    formatted_name = formatted_name.lower()
    
    # 然后处理特殊缩写（按长度排序，先处理长的）
    for abbrev in sorted(special_abbreviations.keys(), key=len, reverse=True):
        replacement = special_abbreviations[abbrev]
        formatted_name = formatted_name.replace(abbrev, replacement)
    
    # 按空格分割单词
    words = formatted_name.split()
    formatted_words = []
    
    for i, word in enumerate(words):
        # 跳过已经处理过的特殊缩写
        if word in special_abbreviations.values():
            formatted_words.append(word)
            continue
        
        # 处理英文称谓：Mr., Mrs., Ms., Dr., Prof. 等
        if word and word.lower() in titles:
            # 称谓首字母大写，其余小写
            formatted_word = word[0].upper() + word[1:].lower()
            formatted_words.append(formatted_word)
            
            # 如果下一个词存在，且不是特殊缩写，则保持大写（姓氏）
            if i + 1 < len(words):
                next_word = words[i + 1]
                if next_word not in special_abbreviations.values():
                    # 姓氏首字母大写，其余小写
                    formatted_surname = next_word[0].upper() + next_word[1:].lower()
                    formatted_words.append(formatted_surname)
                    # 跳过下一个词，因为已经处理了
                    words[i + 1] = None
            continue
            
        # 如果这个词是None（已经被处理过的姓氏），跳过
        if word is None:
            continue
            
        # 处理普通单词
        if word:
            # 首字母大写，其余小写
            formatted_word = word[0].upper() + word[1:].lower()
            formatted_words.append(formatted_word)
    
    result = ' '.join(formatted_words)

    def _restore_parenthetical_case(match: re.Match) -> str:
        """Ensure parenthetical words follow title casing where appropriate."""
        content = match.group(1)
        parts = re.split(r'(\s+)', content)

        def _title_case_token(token: str) -> str:
            if not token or token.isspace():
                return token
            # Leave fully upper-case tokens (e.g. abbreviations) untouched
            if token.isupper():
                return token
            # Only adjust alphabetic content
            if re.search(r"[A-Za-z]", token):
                return token[0].upper() + token[1:].lower()
            return token

        return "(" + "".join(_title_case_token(p) for p in parts) + ")"

    # Post-process parentheses so cities like "Shanghai" keep title casing.
    result = re.sub(r"\(([^)]+)\)", _restore_parenthetical_case, result)

    return result

