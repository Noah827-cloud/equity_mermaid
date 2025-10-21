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
    """Format to English label: 'Registered Capital: RMB{X}M' where X = 万/100, M = 百万.

    Returns None if cannot parse.
    """
    amount_wan = normalize_amount_to_wan(raw)
    if amount_wan is None:
        return None
    formatted_capital = format_capital_for_display(amount_wan)
    if formatted_capital:
        return f"Registered Capital: {formatted_capital}"
    return None


def format_subscribed_capital_display(raw: str | float | int | None) -> Optional[str]:
    """Format to English label: 'Subscribed Capital: RMB{X}M' where X = 万/100, M = 百万.

    Returns None if cannot parse.
    """
    amount_wan = normalize_amount_to_wan(raw)
    if amount_wan is None:
        return None
    formatted_capital = format_capital_for_display(amount_wan)
    if formatted_capital:
        return f"Subscribed Capital: {formatted_capital}"
    return None


def format_date_for_display(date_str: str | None) -> Optional[str]:
    """Format date for display: 'Established in {Month}.{Year}' or 'Established in {Year}'.

    Args:
        date_str: Date string in YYYY-MM-DD format or other common formats
    
    Returns:
        Formatted string like "Established in June.2010" or "Established in 2010"
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
            return f"Established in {dt.year}"
        return f"Established in {month_name}.{dt.year}"
    # full date -> use month.year
    month_name = _MONTH_NAMES[dt.month]
    return f"Established in {month_name}.{dt.year}"


def format_established_display(raw_date: str | None) -> Optional[str]:
    """Format to English label like 'Established in June.2010' or 'Established in 2010'.

    Accepts YYYY, YYYY-MM, YYYY-MM-DD and common separators.
    """
    return format_date_for_display(raw_date)


