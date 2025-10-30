from typing import Optional
import re

from urllib.parse import quote_plus, urljoin

import requests
import streamlit as st
import streamlit.components.v1 as components

_BAIDU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.baidu.com/",
}
_FIRST_RESULT_PATTERN = re.compile(
    r'<h3[^>]+class="[^"]*(?:t|c-title)[^"]*"[^>]*>\s*<a[^>]+href=["\'](?P<href>[^"\']+)',
    re.IGNORECASE,
)


def _resolve_baidu_urls(query: str) -> dict:
    """
    Resolve the Baidu search URL and best-effort first-result URL for the query.
    """
    encoded_query = quote_plus(query)
    lucky_url = f"https://www.baidu.com/s?ie=utf-8&tn=se_opn_frstpg&wd={encoded_query}"
    search_url = f"https://www.baidu.com/s?ie=utf-8&wd={encoded_query}"
    first_url: Optional[str] = None

    try:
        lucky_resp = requests.get(
            lucky_url,
            headers=_BAIDU_HEADERS,
            timeout=5,
            allow_redirects=False,
        )
        if lucky_resp.status_code in (301, 302, 303, 307, 308):
            location = lucky_resp.headers.get("Location")
            if location:
                first_url = urljoin(lucky_url, location)
    except Exception:
        pass

    if not first_url:
        try:
            resp = requests.get(
                search_url,
                headers=_BAIDU_HEADERS,
                timeout=6,
            )
            if (
                resp.status_code == 200
                and "百度安全验证" not in resp.text
                and "antispider" not in resp.text.lower()
            ):
                match = _FIRST_RESULT_PATTERN.search(resp.text)
                if match:
                    first_url = urljoin("https://www.baidu.com", match.group("href"))
        except Exception:
            pass

    return {
        "search": search_url,
        "first": first_url,
    }


def _normalize_entry(entry) -> dict:
    """Ensure stored search entries follow the expected dictionary structure."""
    if isinstance(entry, dict):
        return entry
    if isinstance(entry, str):
        return {"search": entry, "first": None}
    return {}


def render_baidu_name_checker(container, key_prefix: str) -> Optional[str]:
    """
    Render a quick search helper that opens Baidu results for English name
    verification, including a Tianyancha-focused query.
    """
    section_key = f"{key_prefix}_baidu_checker"
    urls_key = f"{section_key}_urls"
    company_key = f"{section_key}_company"
    trigger_key = f"{section_key}_open_flag"
    last_company_key = f"{section_key}_last_company"

    container.markdown("### 🌐 英文名校验")
    company_name = container.text_input(
        "输入中文企业名称",
        placeholder="如：力诺集团股份有限公司",
        key=company_key,
    )

    if not isinstance(st.session_state.get(urls_key), dict):
        st.session_state[urls_key] = {}
    urls_state = st.session_state[urls_key]

    search_variants = [
        (
            "baidu",
            "🔎 百度校验英文名",
            "",
            "根据中文企业名称快速打开百度搜索结果，核对官方英文名称。",
        ),
        (
            "tianyancha",
            "🧭 天眼查英文名",
            " 天眼查",
            "附加“天眼查”关键词，方便直接查看天眼查的英文名称记录。",
        ),
    ]

    stripped_name = (company_name or "").strip()
    for variant_id, button_label, extra_keyword, help_text in search_variants:
        if container.button(
            button_label,
            key=f"{section_key}_{variant_id}_button",
            help=help_text,
        ):
            if not stripped_name:
                container.warning("请输入需要校验的中文企业名称")
            else:
                query = f"{stripped_name} 英文名称{extra_keyword}"
                urls_state[variant_id] = _resolve_baidu_urls(query)
                st.session_state[last_company_key] = stripped_name
                st.session_state[trigger_key] = variant_id

    last_company = st.session_state.get(last_company_key)
    urls = st.session_state.get(urls_key, {})
    opened_variant = st.session_state.pop(trigger_key, None)

    for variant_id, _, extra_keyword, _ in search_variants:
        entry = _normalize_entry(urls.get(variant_id))
        search_url = entry.get("search")
        first_result_url = entry.get("first")
        if not (search_url and last_company):
            continue
        link_label = (
            f"在百度查看「{last_company}」英文名称"
            if not extra_keyword
            else f"在百度查看「{last_company}」英文名称（含天眼查）"
        )
        primary_url = first_result_url or search_url
        primary_label = (
            f"打开首条结果：{link_label}"
            if first_result_url
            else f"查看百度搜索结果：{link_label}"
        )
        container.markdown(
            f'<a href="{primary_url}" target="_blank" style="color: white; text-decoration: underline;">{primary_label}</a>',
            unsafe_allow_html=True,
        )
        if first_result_url and first_result_url != search_url:
            container.markdown(
                f'<a href="{search_url}" target="_blank" style="color: #d0e0ff; font-size: 0.85rem;">改为查看搜索结果页</a>',
                unsafe_allow_html=True,
            )
        if opened_variant == variant_id and primary_url:
            components.html(
                f"<script>window.open('{primary_url}', '_blank');</script>",
                height=0,
            )

    if opened_variant and opened_variant in urls:
        entry = _normalize_entry(urls[opened_variant])
        return entry.get("first") or entry.get("search")

    if urls:
        # fall back to the default Baidu URL if it exists
        entry = _normalize_entry(urls.get(search_variants[0][0]))
        if entry:
            return entry.get("first") or entry.get("search")
        first_entry = _normalize_entry(next(iter(urls.values())))
        return first_entry.get("first") or first_entry.get("search")

    return None
