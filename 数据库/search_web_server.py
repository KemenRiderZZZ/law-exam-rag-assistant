#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ctypes
import html
import json
import re
import socket
import subprocess
import threading
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from search_chunks import (
    create_query_embedding,
    fetch_matches,
    get_db_driver,
    load_db_config,
    load_embedding_config,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_V2_DIST_DIR = PROJECT_ROOT / "\u6cd5\u8003\u5bf9\u8bdd\u524d\u7aef2.0" / "dist"
FRONTEND_DIST_DIR = PROJECT_ROOT / "\u6cd5\u8003\u5bf9\u8bdd\u524d\u7aef" / "dist"
LEGACY_STATIC_DIR = PROJECT_ROOT / "\u9875\u9762"
if FRONTEND_V2_DIST_DIR.exists():
    STATIC_DIR = FRONTEND_V2_DIST_DIR
elif FRONTEND_DIST_DIR.exists():
    STATIC_DIR = FRONTEND_DIST_DIR
else:
    STATIC_DIR = LEGACY_STATIC_DIR

SEARCH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 CodexLawExam/1.0"
MAX_FETCH_BYTES = 200_000
TRAFFIC_SUMMARY_PATH = SCRIPT_DIR / "traffic_summary.json"
TRAFFIC_SUMMARY_LOCK = threading.Lock()
CHINA_TZ = timezone(timedelta(hours=8))

NPC_HOSTS = ("npc.gov.cn", "flk.npc.gov.cn")
GOV_HOSTS = ("gov.cn", "www.gov.cn", "court.gov.cn", "moj.gov.cn", "mot.gov.cn")
TRUSTED_LEGAL_HOSTS = (
    "flk.npc.gov.cn",
    "npc.gov.cn",
    "gov.cn",
    "www.gov.cn",
    "court.gov.cn",
    "moj.gov.cn",
    "mot.gov.cn",
    "people.com.cn",
    "paper.people.com.cn",
    "qstheory.cn",
    "news.cn",
)
NEGATIVE_HOST_MARKERS = ("facebook", "youtube", "tiktok", "zhihu", "baidu", "cnki", "google")

TIME_SENSITIVE_KEYWORDS = (
    "\u6700\u65b0",
    "\u73b0\u884c",
    "\u76ee\u524d",
    "\u73b0\u5728",
    "\u4eca\u5929",
    "\u4eca\u65e5",
    "\u4fee\u8ba2",
    "\u4fee\u6b63",
    "\u65bd\u884c",
    "\u751f\u6548",
    "\u53d1\u5e03\u65e5\u671f",
    "\u4ec0\u4e48\u65f6\u5019",
    "\u54ea\u4e00\u5e74",
    "\u54ea\u4e00\u7248",
    "\u65f6\u95f4\u6548\u529b",
)

LEGAL_SUFFIX_PATTERN = (
    r"[\u4e00-\u9fa5A-Za-z]{2,40}"
    r"(?:\u6cd5|\u6761\u4f8b|\u89c4\u5b9a|\u529e\u6cd5|\u89e3\u91ca|\u8349\u6848)"
)

LEADING_NOISE_PATTERN = re.compile(
    r"^(?:\u6700\u65b0(?:\u7684)?|\u73b0\u884c(?:\u7684)?|\u76ee\u524d(?:\u7684)?|"
    r"\u73b0\u5728(?:\u7684)?|\u4eca\u5929(?:\u7684)?|\u4eca\u65e5(?:\u7684)?|"
    r"\u8bf7\u95ee|"
    r"\u5173\u4e8e)+"
)
TRAILING_QUESTION_PATTERN = re.compile(
    r"(?:\u4fee\u8ba2\u5728\u54ea\u4e00\u5e74.*|"
    r"\u4ec0\u4e48\u65f6\u5019(?:\u4fee\u8ba2|\u65bd\u884c|\u751f\u6548)?.*|"
    r"\u54ea\u4e00\u5e74.*|"
    r"\u4fee\u8ba2\u5e76\u8fd0\u884c\u7684.*|"
    r"\u662f\u5426(?:\u5df2)?(?:\u751f\u6548|\u65bd\u884c).*)$"
)

SOURCE_DISCLOSURE_MARKERS = (
    "\u51fa\u7248\u793e",
    "ISBN",
    "CIP",
    "\u6574\u7406\u8bf4\u660e",
    "OCR\u539f\u7a3f",
    "\u672c\u6848\u6765\u6e90\u4e8e",
    "\u8d44\u6599\u6765\u6e90",
    "\u6765\u6e90\uff1a",
    "\u6765\u6e90:",
    "\u53c2\u89c1",
    "\u7f16\u8457",
    "\u7248\u6743",
    "\u51fa\u7248\u53d1\u884c",
    "\u5370\u5237",
    "\u90ae\u7f16",
    "E-mail",
    "http",
)
EDITION_PATTERN = re.compile(r"[\(\uff08]\s*20\d{2}\s*\u7248\s*[\)\uff09]")
LAW_NAME_PATTERN = re.compile(r"(?:\u300a)?(?:\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd)?[\u4e00-\u9fa5A-Za-z]{2,30}(?:\u6cd5|\u6761\u4f8b|\u89c4\u5b9a|\u529e\u6cd5|\u89e3\u91ca|\u51b3\u5b9a)(?:\u300b)?")
ARTICLE_PATTERN = re.compile(r"\u7b2c[\u4e00-\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u96f6\u30070-9]+\u6761(?:\u4e4b[\u4e00-\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u96f6\u30070-9]+)?")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _strip_html(value: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", value)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return _clean_text(html.unescape(text))


def _extract_first(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return _clean_text(match.group(1))
    return ""


def _today_key() -> str:
    return datetime.now(CHINA_TZ).date().isoformat()


def _empty_traffic_day() -> dict:
    return {"search": 0, "chat": 0, "mindmap": 0}


def _load_traffic_summary_unlocked() -> dict:
    if not TRAFFIC_SUMMARY_PATH.exists():
        return {}
    try:
        data = json.loads(TRAFFIC_SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_traffic_summary_unlocked(data: dict) -> None:
    TRAFFIC_SUMMARY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_traffic_event(kind: str) -> None:
    if kind not in {"search", "chat", "mindmap"}:
        return
    with TRAFFIC_SUMMARY_LOCK:
        data = _load_traffic_summary_unlocked()
        today = _today_key()
        day_data = data.get(today)
        if not isinstance(day_data, dict):
            day_data = _empty_traffic_day()
        day_data[kind] = int(day_data.get(kind) or 0) + 1
        data[today] = day_data
        _save_traffic_summary_unlocked(data)


def get_traffic_summary(day: str | None = None) -> dict:
    target_day = day or _today_key()
    with TRAFFIC_SUMMARY_LOCK:
        data = _load_traffic_summary_unlocked()
    day_data = data.get(target_day)
    if not isinstance(day_data, dict):
        day_data = _empty_traffic_day()
    return {
        "ok": True,
        "date": target_day,
        "generatedAt": datetime.now(CHINA_TZ).isoformat(timespec="seconds"),
        "source": "app-counter",
        "searchCount": int(day_data.get("search") or 0),
        "chatCount": int(day_data.get("chat") or 0),
        "mindmapCount": int(day_data.get("mindmap") or 0),
    }


def _contains_any(text: str, values: tuple[str, ...] | list[str]) -> bool:
    return any(value in text for value in values)


def _host_matches(hostname: str, allowed_hosts: tuple[str, ...]) -> bool:
    hostname = (hostname or "").lower()
    return any(hostname == host or hostname.endswith(f".{host}") for host in allowed_hosts)


def _canonical_anchor_variants(value: str) -> list[str]:
    cleaned = _clean_text(value)
    variants: list[str] = []
    for item in (
        cleaned,
        cleaned.removeprefix("\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd"),
        cleaned.removeprefix("\u6700\u65b0\u7684"),
    ):
        item = _clean_text(item).strip("\u300a\u300b")
        if item and item not in variants:
            variants.append(item)
    return variants


def _normalize_legal_title(value: str) -> str:
    cleaned = _clean_text(value).strip("\u300a\u300b")
    cleaned = LEADING_NOISE_PATTERN.sub("", cleaned)
    cleaned = TRAILING_QUESTION_PATTERN.sub("", cleaned)
    cleaned = cleaned.strip("\uff0c\u3002\uff1f? \t\r\n")
    cleaned = cleaned.rstrip("\u7684")
    return _clean_text(cleaned)


def _extract_dates(text: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"(20\d{2})\s*\u5e74\s*(\d{1,2})\s*\u6708(?:\s*(\d{1,2})\s*\u65e5)?", text):
        year = match.group(1)
        month = match.group(2).zfill(2)
        day = (match.group(3) or "01").zfill(2)
        normalized = f"{year}-{month}-{day}"
        if normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def _parse_date_value(value: str) -> date | None:
    normalized = _clean_text(value)
    if not normalized:
        return None

    iso_match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", normalized)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None

    cn_match = re.search(r"(20\d{2})\s*\u5e74\s*(\d{1,2})\s*\u6708(?:\s*(\d{1,2})\s*\u65e5)?", normalized)
    if cn_match:
        try:
            return date(
                int(cn_match.group(1)),
                int(cn_match.group(2)),
                int(cn_match.group(3) or "1"),
            )
        except ValueError:
            return None
    return None


def _contains_source_disclosure(text: str) -> bool:
    normalized = _clean_text(text)
    return bool(normalized) and any(marker.lower() in normalized.lower() for marker in SOURCE_DISCLOSURE_MARKERS)


def _sanitize_public_knowledge_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in (text or "").replace("\r", "").split("\n"):
        line = EDITION_PATTERN.sub("", raw_line).strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if _contains_source_disclosure(line):
            continue
        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result


def _extract_legal_basis_title(text: str, index: int) -> str:
    last_law_name = ""
    for raw_line in (text or "").replace("\r", "").split("\n"):
        line = _clean_text(raw_line)
        if not line:
            continue
        law_matches = [match.group(0).strip("\u300a\u300b") for match in LAW_NAME_PATTERN.finditer(line)]
        article_matches = [match.group(0) for match in ARTICLE_PATTERN.finditer(line)]
        if law_matches:
            last_law_name = law_matches[-1]
        if article_matches:
            if law_matches:
                return f"{law_matches[-1]} {article_matches[0]}"
            if last_law_name:
                return f"{last_law_name} {article_matches[0]}"
            return article_matches[0]
    return f"\u6cd5\u6761\u4f9d\u636e {index}"


def _redact_search_result(row: dict, index: int) -> dict:
    sanitized_text = _sanitize_public_knowledge_text(str(row.get("text_content") or ""))
    return {
        "chunk_id": f"knowledge-{index}",
        "title": _extract_legal_basis_title(sanitized_text, index),
        "text_content": sanitized_text,
        "score": row.get("score"),
    }


def _pick_status(text: str, published_at: str = "", effective_at: str = "") -> str:
    corpus = _clean_text(text)
    today = date.today()
    effective_date = _parse_date_value(effective_at)

    draft_markers = (
        "\u4fee\u8ba2\u8349\u6848",
        "\u8349\u6848",
        "\u5f81\u6c42\u610f\u89c1",
        "\u672a\u901a\u8fc7",
        "\u5c1a\u672a\u901a\u8fc7",
    )
    draft_review_markers = (
        "\u4e00\u6b21\u5ba1\u8bae",
        "\u4e8c\u6b21\u5ba1\u8bae",
        "\u4e09\u6b21\u5ba1\u8bae",
        "\u5ba1\u8bae",
    )
    pending_effective_markers = (
        "\u5df2\u7531",
        "\u4fee\u8ba2\u901a\u8fc7",
        "\u901a\u8fc7",
        "\u73b0\u4e88\u516c\u5e03",
        "\u4e3b\u5e2d\u4ee4",
        "\u516c\u5e03",
        "\u53d1\u5e03",
    )
    active_markers = (
        "\u5df2\u7ecf\u751f\u6548",
        "\u73b0\u884c\u6709\u6548",
        "\u73b0\u884c",
        "\u8d77\u65bd\u884c",
        "\u65bd\u884c",
        "\u751f\u6548",
    )
    explicit_negative_markers = (
        "\u5c1a\u672a\u65bd\u884c",
        "\u5c1a\u672a\u751f\u6548",
        "\u672a\u65bd\u884c",
        "\u672a\u751f\u6548",
        "\u672a\u516c\u5e03\u5b9e\u65bd",
    )

    if any(marker in corpus for marker in draft_markers):
        return "\u8349\u6848\u5ba1\u8bae\u4e2d"

    if "\u8349\u6848" in corpus and any(marker in corpus for marker in draft_review_markers):
        return "\u8349\u6848\u5ba1\u8bae\u4e2d"

    if effective_date:
        if effective_date <= today:
            return "\u5df2\u6b63\u5f0f\u65bd\u884c"
        return "\u5df2\u4fee\u8ba2\u901a\u8fc7\uff0c\u5f85\u65bd\u884c"

    if any(marker in corpus for marker in explicit_negative_markers):
        return "\u5df2\u4fee\u8ba2\u901a\u8fc7\uff0c\u5f85\u65bd\u884c" if any(
            marker in corpus for marker in pending_effective_markers
        ) else "\u8349\u6848\u5ba1\u8bae\u4e2d"

    if any(marker in corpus for marker in pending_effective_markers):
        return "\u5df2\u4fee\u8ba2\u901a\u8fc7\uff0c\u5f85\u65bd\u884c"

    if any(marker in corpus for marker in active_markers):
        return "\u5df2\u6b63\u5f0f\u65bd\u884c"

    return ""


def _extract_anchor_terms(query: str) -> list[str]:
    normalized = _clean_text(query)
    patterns = [LEGAL_SUFFIX_PATTERN, r"\u300a[^\u300b]{2,40}\u300b"]
    items: list[str] = []
    seen = set()
    for pattern in patterns:
        for match in re.findall(pattern, normalized):
            item = _normalize_legal_title(match)
            for candidate in _canonical_anchor_variants(item):
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    items.append(candidate)
                if (
                    candidate
                    and candidate.endswith(("\u6cd5", "\u6761\u4f8b", "\u89c4\u5b9a", "\u529e\u6cd5", "\u89e3\u91ca"))
                    and not candidate.startswith("\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd")
                ):
                    full_name = f"\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd{candidate}"
                    if full_name not in seen:
                        seen.add(full_name)
                        items.append(full_name)
    return items[:4]


def _extract_fact_summary(page_text: str, title: str, snippet: str) -> dict[str, str]:
    corpus = "\n".join(part for part in (title, snippet, page_text) if part)
    published_at = ""
    effective_at = ""

    published_match = re.search(
        r"(\u516c\u5e03|\u53d1\u5e03|\u5ba1\u8bae|\u901a\u8fc7)[^\u3002\uff1b\n]{0,30}?"
        r"(20\d{2}\s*\u5e74\s*\d{1,2}\s*\u6708(?:\s*\d{1,2}\s*\u65e5)?)",
        corpus,
    )
    if published_match:
        published_at = _clean_text(published_match.group(2))

    effective_match = re.search(
        r"(\u81ea|\u4e8e)[^\u3002\uff1b\n]{0,15}?"
        r"(20\d{2}\s*\u5e74\s*\d{1,2}\s*\u6708(?:\s*\d{1,2}\s*\u65e5)?)"
        r"[^\u3002\uff1b\n]{0,15}?\u8d77\u65bd\u884c",
        corpus,
    )
    if effective_match:
        effective_at = _clean_text(effective_match.group(2))

    if not published_at:
        dates = _extract_dates(corpus)
        if dates:
            published_at = dates[0]

    if not effective_at:
        effective_match_alt = re.search(
            r"\u8d77\u65bd\u884c[^\u3002\uff1b\n]{0,15}?"
            r"(20\d{2}\s*\u5e74\s*\d{1,2}\s*\u6708(?:\s*\d{1,2}\s*\u65e5)?)",
            corpus,
        )
        if effective_match_alt:
            effective_at = _clean_text(effective_match_alt.group(1))

    status = _pick_status(corpus, published_at=published_at, effective_at=effective_at)
    authority = _extract_first(
        [
            r"(\u5168\u56fd\u4eba\u6c11\u4ee3\u8868\u5927\u4f1a\u5e38\u52a1\u59d4\u5458\u4f1a[^\u3002\uff1b\n]{0,40})",
            r"(\u4ea4\u901a\u8fd0\u8f93\u90e8[^\u3002\uff1b\n]{0,40})",
            r"(\u56fd\u52a1\u9662[^\u3002\uff1b\n]{0,40})",
            r"(\u6700\u9ad8\u4eba\u6c11\u6cd5\u9662[^\u3002\uff1b\n]{0,40})",
            r"(\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd\u4e3b\u5e2d\u4ee4[^\u3002\uff1b\n]{0,40})",
        ],
        corpus,
    )
    excerpt = _extract_first(
        [
            r"((?:\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd)?[^\u3002]{0,80}"
            r"(?:\u6d77\u5546\u6cd5|\u6761\u4f8b|\u89c4\u5b9a|\u529e\u6cd5|\u89e3\u91ca)"
            r"[^\u3002]{0,120}\u3002)",
            r"((?:\u8349\u6848|\u4fee\u8ba2\u8349\u6848)[^\u3002]{0,120}\u3002)",
        ],
        corpus,
    )
    return {
        "authority": authority,
        "published_at": published_at,
        "effective_at": effective_at,
        "status": status,
        "excerpt": excerpt,
    }


def _fetch_page_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": SEARCH_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=12) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw_bytes = response.read(MAX_FETCH_BYTES)
    return raw_bytes.decode(charset, errors="ignore")


def _looks_like_legal_source(result: dict[str, str]) -> bool:
    corpus = "\n".join(
        _clean_text(part).lower()
        for part in (result.get("title", ""), result.get("link", ""), result.get("snippet", ""))
        if part
    )
    hostname = urlsplit(result.get("link", "")).netloc.lower()
    positive = (
        "gov.cn",
        "court.gov.cn",
        "npc.gov.cn",
        "moj.gov.cn",
        "mot.gov.cn",
        "\u6d77\u5546\u6cd5",
        "\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd",
        "\u4fee\u8ba2\u8349\u6848",
        "\u65bd\u884c",
        "\u751f\u6548",
        "\u4e3b\u5e2d\u4ee4",
    )
    if any(marker in corpus for marker in NEGATIVE_HOST_MARKERS):
        return False
    return _host_matches(hostname, TRUSTED_LEGAL_HOSTS) or any(marker.lower() in corpus for marker in positive)


def _fetch_bing_rss_items(search_query: str) -> list[dict[str, str]]:
    rss_url = f"https://www.bing.com/search?format=rss&q={quote_plus(search_query)}"
    request = Request(
        rss_url,
        headers={
            "User-Agent": SEARCH_USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with urlopen(request, timeout=12) as response:
        xml_bytes = response.read()

    root = ElementTree.fromstring(xml_bytes)
    items: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        title = _clean_text(item.findtext("title", default=""))
        link = item.findtext("link", default="").strip()
        snippet = _clean_text(item.findtext("description", default=""))
        if not title and not snippet:
            continue
        items.append({"title": title, "link": link, "snippet": snippet})
    return items


def _build_live_search_queries(query: str) -> list[str]:
    normalized = _clean_text(query)
    anchors = _extract_anchor_terms(normalized)
    query_set: list[str] = []

    def add(value: str) -> None:
        cleaned = _clean_text(value)
        if cleaned and cleaned not in query_set:
            query_set.append(cleaned)

    for anchor in anchors:
        add(f'"{anchor}" \u4e3b\u5e2d\u4ee4')
        add(f'"{anchor}" \u4fee\u8ba2\u901a\u8fc7')
        add(f'"{anchor}" \u4fee\u8ba2\u8349\u6848')
        add(f'"{anchor}" \u65bd\u884c')
        add(f'"{anchor}" \u751f\u6548')
        add(f'"{anchor}" site:flk.npc.gov.cn')
        add(f'"{anchor}" site:npc.gov.cn')
        add(f'"{anchor}" site:gov.cn')
        add(f'"{anchor}" \u4e3b\u5e2d\u4ee4 site:gov.cn')
        add(f'"{anchor}" \u4fee\u8ba2\u8349\u6848 site:flk.npc.gov.cn')
        add(f'"{anchor}" \u4fee\u8ba2\u8349\u6848 site:npc.gov.cn')

    add(f"{normalized} site:flk.npc.gov.cn")
    add(f"{normalized} site:npc.gov.cn")
    add(f"{normalized} site:gov.cn")
    add(f"{normalized} site:court.gov.cn")

    return query_set[:12]


def _score_live_search_result(result: dict[str, str], anchors: list[str]) -> int:
    title = _clean_text(result.get("title", "")).lower()
    link = _clean_text(result.get("link", "")).lower()
    snippet = _clean_text(result.get("snippet", "")).lower()
    corpus = "\n".join((title, link, snippet))
    score = 0

    host_weights = (
        ("flk.npc.gov.cn", 14),
        ("npc.gov.cn", 12),
        ("gov.cn", 9),
        ("court.gov.cn", 8),
        ("moj.gov.cn", 7),
        ("mot.gov.cn", 7),
    )
    for host, weight in host_weights:
        if host in link:
            score += weight

    legal_markers = (
        "\u4fee\u8ba2\u8349\u6848",
        "\u8349\u6848",
        "\u65bd\u884c",
        "\u751f\u6548",
        "\u4e3b\u5e2d\u4ee4",
        "\u4fee\u8ba2\u901a\u8fc7",
        "\u6d77\u5546\u6cd5",
        "\u4e2d\u534e\u4eba\u6c11\u5171\u548c\u56fd",
    )
    for marker in legal_markers:
        if marker.lower() in corpus:
            score += 2

    for anchor in anchors:
        for variant in _canonical_anchor_variants(anchor):
            anchor_lower = variant.lower()
            if anchor_lower in title:
                score += 8
            elif anchor_lower in corpus:
                score += 4

    hostname = urlsplit(result.get("link", "")).netloc.lower()
    if not _host_matches(hostname, TRUSTED_LEGAL_HOSTS):
        score -= 10

    if any(marker in corpus for marker in NEGATIVE_HOST_MARKERS):
        score -= 12
    return score


def _result_matches_anchor(result: dict[str, str], anchors: list[str]) -> bool:
    if not anchors:
        return True
    corpus = "\n".join(
        _clean_text(part).lower()
        for part in (result.get("title", ""), result.get("link", ""), result.get("snippet", ""))
        if part
    )
    for anchor in anchors:
        for variant in _canonical_anchor_variants(anchor):
            if variant.lower() in corpus:
                return True
    return False


def _is_strict_legal_candidate(result: dict[str, str], anchors: list[str]) -> bool:
    hostname = urlsplit(result.get("link", "")).netloc.lower()
    if not _host_matches(hostname, TRUSTED_LEGAL_HOSTS):
        return False
    if not _result_matches_anchor(result, anchors):
        return False
    corpus = "\n".join(
        _clean_text(part).lower()
        for part in (result.get("title", ""), result.get("snippet", ""))
        if part
    )
    legal_markers = (
        "\u6cd5",
        "\u6761\u4f8b",
        "\u89c4\u5b9a",
        "\u529e\u6cd5",
        "\u89e3\u91ca",
        "\u4e3b\u5e2d\u4ee4",
        "\u4fee\u8ba2",
        "\u8349\u6848",
        "\u65bd\u884c",
        "\u751f\u6548",
    )
    return any(marker in corpus for marker in legal_markers)


def should_use_live_search(query: str) -> bool:
    normalized = (query or "").strip()
    return any(keyword in normalized for keyword in TIME_SENSITIVE_KEYWORDS)


def fetch_live_search_results(query: str, max_results: int = 5) -> list[dict[str, str]]:
    anchors = _extract_anchor_terms(query)
    candidates: list[dict[str, str]] = []
    seen_links: set[str] = set()

    for search_query in _build_live_search_queries(query):
        try:
            items = _fetch_bing_rss_items(search_query)
        except Exception:
            continue

        for item in items:
            link = item.get("link", "").strip()
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            item["search_query"] = search_query
            item["score"] = _score_live_search_result(item, anchors)
            if not _is_strict_legal_candidate(item, anchors):
                continue
            candidates.append(item)

    candidates.sort(
        key=lambda item: (
            item.get("score", 0),
            1 if _looks_like_legal_source(item) else 0,
        ),
        reverse=True,
    )
    return candidates[:max_results]


def enrich_live_search_result(result: dict[str, str]) -> dict[str, str]:
    title = result.get("title", "")
    link = result.get("link", "")
    snippet = result.get("snippet", "")
    enriched = dict(result)
    enriched["source_host"] = urlsplit(link).netloc

    if not link:
        return enriched

    try:
        html_text = _fetch_page_text(link)
        page_title = _extract_first([r"<title[^>]*>(.*?)</title>"], html_text)
        body_text = _strip_html(html_text)
        facts = _extract_fact_summary(body_text, page_title or title, snippet)
        if page_title:
            enriched["page_title"] = page_title
        enriched["page_excerpt"] = facts["excerpt"] or body_text[:180]
        enriched["published_at"] = facts["published_at"]
        enriched["effective_at"] = facts["effective_at"]
        enriched["status"] = facts["status"]
        enriched["authority"] = facts["authority"]
    except Exception as exc:
        enriched["fetch_error"] = str(exc)

    return enriched


def build_live_search_context(results: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        lines = [
            f"\u3010\u6700\u65b0\u4e8b\u5b9e {index}\u3011",
            result.get("page_title") or result.get("title") or "",
            f"\u6765\u6e90\uff1a{result['link']}" if result.get("link") else "",
            f"\u53d1\u5e03/\u5ba1\u8bae\u65f6\u95f4\uff1a{result['published_at']}" if result.get("published_at") else "",
            f"\u65bd\u884c\u65f6\u95f4\uff1a{result['effective_at']}" if result.get("effective_at") else "",
            f"\u5f53\u524d\u72b6\u6001\uff1a{result['status']}" if result.get("status") else "",
            f"\u673a\u5173\uff1a{result['authority']}" if result.get("authority") else "",
            f"\u6458\u8981\uff1a{result['snippet']}" if result.get("snippet") else "",
            f"\u6b63\u6587\u7247\u6bb5\uff1a{result['page_excerpt']}" if result.get("page_excerpt") else "",
        ]
        block = "\n".join(line for line in lines if line)
        if block:
            blocks.append(block)
    return "\n\n".join(blocks)


def _normalize_model_base_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _build_model_endpoints(base_url: str) -> list[str]:
    normalized = _normalize_model_base_url(base_url)
    if not normalized:
        return []
    if normalized.lower().endswith("/chat/completions"):
        return [normalized]
    if "xiaomimimo.com" in normalized.lower() and not re.search(r"/v\d+(?:\.\d+)?$", normalized, re.I):
        return [f"{normalized}/v1/chat/completions"]
    endpoints = [f"{normalized}/chat/completions"]
    if not re.search(r"/v\d+(?:\.\d+)?$", normalized, re.I):
        endpoints.append(f"{normalized}/v1/chat/completions")
    return list(dict.fromkeys(endpoints))


def _read_response_text(response) -> str:
    charset = response.headers.get_content_charset() or "utf-8"
    return response.read().decode(charset, errors="replace")


def _extract_upstream_error(body_text: str, fallback: str) -> str:
    if not body_text.strip():
        return fallback
    try:
        payload = json.loads(body_text)
        if isinstance(payload, dict):
            if isinstance(payload.get("error"), str):
                return payload["error"]
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                for key in ("message", "code", "type"):
                    value = error_obj.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
    except Exception:
        pass
    return body_text.strip()[:300]


def _extract_chat_message_content(response_payload: dict) -> str:
    choice = (response_payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if isinstance(value, str):
                    parts.append(value)
        joined = "\n".join(part.strip() for part in parts if part.strip())
        if joined:
            return joined
    for key in ("reasoning_content", "text"):
        value = message.get(key) or choice.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _request_openai_compatible(base_url: str, api_key: str, request_body: dict, timeout: int = 40) -> tuple[str, int, dict, str]:
    endpoints = _build_model_endpoints(base_url)
    if not endpoints:
        raise ValueError("Base URL 不能为空")

    payload_bytes = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    last_http_error: HTTPError | None = None
    last_error: Exception | None = None

    for index, endpoint in enumerate(endpoints):
        request_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": SEARCH_USER_AGENT,
        }
        if "xiaomimimo.com" in endpoint:
            request_headers["api-key"] = api_key

        request = Request(
            endpoint,
            data=payload_bytes,
            headers=request_headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body_text = _read_response_text(response)
                headers = {key: value for key, value in response.headers.items()}
                return endpoint, response.status, headers, body_text
        except HTTPError as exc:
            last_http_error = exc
            if index < len(endpoints) - 1 and exc.code in {400, 401, 403, 404, 405}:
                continue
        except socket.timeout:
            last_error = TimeoutError("模型接口响应超时，请稍后重试或减少输出范围")
        except Exception as exc:
            last_error = exc

    if last_http_error is not None:
        detail = _extract_upstream_error(_read_response_text(last_http_error), last_http_error.reason or "模型接口调用失败")
        raise RuntimeError(f"HTTP {last_http_error.code} {detail}".strip())
    if last_error is not None:
        if isinstance(last_error, TimeoutError):
            raise RuntimeError(str(last_error))
        if isinstance(last_error, URLError):
            raise RuntimeError(f"连接模型接口失败：{last_error.reason}")
        raise RuntimeError(f"连接模型接口失败：{last_error}")
    raise RuntimeError("模型接口调用失败")


def _validate_gateway_settings(payload: dict) -> tuple[str, str, str]:
    base_url = _normalize_model_base_url(str(payload.get("baseUrl") or payload.get("base_url") or ""))
    api_key = str(payload.get("apiKey") or payload.get("api_key") or "").strip()
    model = str(payload.get("model") or "").strip()
    if not base_url:
        raise ValueError("Base URL 不能为空")
    if not model:
        raise ValueError("模型名称不能为空")
    if not api_key:
        raise ValueError("API Key 不能为空")
    if "xiaomimimo.com" in base_url.lower():
        model = model.lower()
    return base_url, api_key, model


class SearchHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path == "/api/health":
            self._send_json({"ok": True})
            return

        if request_path == "/api/traffic-summary":
            query_params = parse_qs(urlsplit(self.path).query)
            requested_day = (query_params.get("date") or [None])[0]
            if requested_day and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", requested_day):
                self._send_json({"ok": False, "error": "date 必须是 YYYY-MM-DD 格式"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(get_traffic_summary(requested_day))
            return

        if request_path == "/":
            self.path = "/index.html"
        elif not request_path.startswith("/api/"):
            requested = STATIC_DIR / request_path.lstrip("/")
            if not requested.exists():
                self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        request_path = urlsplit(self.path).path
        if request_path not in {
            "/api/search",
            "/api/live-search",
            "/api/copy",
            "/api/model-test",
            "/api/chat",
            "/api/mindmap",
        }:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}

            if request_path == "/api/model-test":
                base_url, api_key, model = _validate_gateway_settings(payload)
                endpoint, status_code, _, _ = _request_openai_compatible(
                    base_url,
                    api_key,
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                        "temperature": 0,
                        "stream": False,
                    },
                    timeout=15,
                )
                self._send_json({"ok": True, "endpoint": endpoint, "status": status_code})
                return

            if request_path == "/api/chat":
                settings_payload = payload.get("settings") or {}
                request_body = payload.get("body")
                if not isinstance(settings_payload, dict):
                    raise ValueError("settings 格式不正确")
                if not isinstance(request_body, dict):
                    raise ValueError("body 格式不正确")
                base_url, api_key, model = _validate_gateway_settings(settings_payload)
                forward_body = dict(request_body)
                forward_body["model"] = model
                endpoint, status_code, headers, body_text = _request_openai_compatible(base_url, api_key, forward_body)
                content_type = headers.get("Content-Type", "application/json; charset=utf-8")
                body_bytes = body_text.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body_bytes)))
                self.end_headers()
                self.wfile.write(body_bytes)
                record_traffic_event("chat")
                return

            if request_path == "/api/mindmap":
                settings_payload = payload.get("settings") or {}
                request_body = payload.get("body")
                if not isinstance(settings_payload, dict):
                    raise ValueError("settings 格式不正确")
                if not isinstance(request_body, dict):
                    raise ValueError("body 格式不正确")
                base_url, api_key, model = _validate_gateway_settings(settings_payload)
                forward_body = dict(request_body)
                forward_body["model"] = model
                endpoint, _, _, body_text = _request_openai_compatible(base_url, api_key, forward_body, timeout=110)
                response_payload = json.loads(body_text)
                content = _extract_chat_message_content(response_payload)
                if not content:
                    raise RuntimeError("模型已响应，但没有返回可用于生成思维导图的正文内容")
                self._send_json({"ok": True, "endpoint": endpoint, "content": content})
                record_traffic_event("mindmap")
                return

            if request_path == "/api/copy":
                text = payload.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("text 不能为空")
                copy_text_to_windows_clipboard_native(text)
                self._send_json({"ok": True})
                return

            query = (payload.get("query") or "").strip()
            if not query:
                raise ValueError("query 不能为空")

            if request_path == "/api/live-search":
                requested_max_results = int(payload.get("max_results") or 5)
                max_results = max(1, min(requested_max_results, 8))
                auto = bool(payload.get("auto", True))
                enabled = should_use_live_search(query) if auto else True
                base_results = fetch_live_search_results(query, max_results=max_results) if enabled else []
                results = [enrich_live_search_result(result) for result in base_results]
                self._send_json(
                    {
                        "ok": True,
                        "query": query,
                        "enabled": enabled,
                        "results": results,
                        "context": build_live_search_context(results),
                    }
                )
                return

            top_k = int(payload.get("top_k") or 5)
            book_name = (payload.get("book_name") or "").strip() or None
            chapter = (payload.get("chapter") or "").strip() or None
            no_model_filter = bool(payload.get("no_model_filter"))

            db_config = load_db_config(self.server.db_env_path)
            embedding_config = load_embedding_config(self.server.embedding_env_path)
            if not embedding_config["api_key"]:
                raise ValueError("SILICONFLOW_API_KEY 未配置")

            vector, usage = create_query_embedding(embedding_config, query)
            embedding_model = None if no_model_filter else embedding_config["model"]

            connect, driver_name = get_db_driver()
            with connect(db_config) as conn:
                results = fetch_matches(
                    conn=conn,
                    query_vector=vector,
                    top_k=top_k,
                    book_name=book_name,
                    chapter=chapter,
                    embedding_model=embedding_model,
                )

            public_results = [_redact_search_result(row, index + 1) for index, row in enumerate(results)]

            self._send_json(
                {
                    "ok": True,
                    "query": query,
                    "top_k": top_k,
                    "driver": driver_name,
                    "usage": usage,
                    "embedding_model": embedding_model or "(no filter)",
                    "results": public_results,
                }
            )
            record_traffic_event("search")
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
    def log_message(self, fmt, *args):
        return super().log_message(fmt, *args)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


def copy_text_to_windows_clipboard(text: str) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    if not user32.OpenClipboard(None):
        raise RuntimeError("无法打开系统剪贴板")

    handle = None
    locked = None
    try:
        if not user32.EmptyClipboard():
            raise RuntimeError("无法清空系统剪贴板")

        data = text + "\0"
        buffer = data.encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(buffer))
        if not handle:
            raise RuntimeError("无法为剪贴板分配内存")

        locked = kernel32.GlobalLock(handle)
        if not locked:
            raise RuntimeError("无法锁定剪贴板内存")

        ctypes.memmove(locked, buffer, len(buffer))
        kernel32.GlobalUnlock(handle)
        locked = None

        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise RuntimeError("无法写入系统剪贴板")

        handle = None
    finally:
        if locked:
            kernel32.GlobalUnlock(handle)
        if handle:
            kernel32.GlobalFree(handle)
        user32.CloseClipboard()


def copy_text_to_windows_clipboard_native(text: str) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_bool
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool

    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_bool
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    if not user32.OpenClipboard(None):
        raise RuntimeError("无法打开系统剪贴板")

    handle = None
    locked = None
    try:
        if not user32.EmptyClipboard():
            raise RuntimeError("无法清空系统剪贴板")

        data = text + "\0"
        buffer = data.encode("utf-16-le")
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(buffer))
        if not handle:
            raise RuntimeError("无法为剪贴板分配内存")

        locked = kernel32.GlobalLock(handle)
        if not locked:
            raise RuntimeError("无法锁定剪贴板内存")

        ctypes.memmove(locked, buffer, len(buffer))
        kernel32.GlobalUnlock(handle)
        locked = None

        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise RuntimeError("无法写入系统剪贴板")

        handle = None
    finally:
        if locked and handle:
            kernel32.GlobalUnlock(handle)
        if handle:
            kernel32.GlobalFree(handle)
        user32.CloseClipboard()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动法考知识问答服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="监听端口，默认 8765")
    parser.add_argument("--db-env", default=str(SCRIPT_DIR / ".env.pg"), help="PostgreSQL 环境变量文件")
    parser.add_argument(
        "--embedding-env",
        default=str(SCRIPT_DIR / ".env.embedding"),
        help="embedding 环境变量文件",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not STATIC_DIR.exists():
        raise SystemExit(f"前端静态目录不存在：{STATIC_DIR}")

    server = ThreadingHTTPServer((args.host, args.port), SearchHandler)
    server.db_env_path = Path(args.db_env).resolve()
    server.embedding_env_path = Path(args.embedding_env).resolve()

    print(f"服务地址: http://{args.host}:{args.port}")
    print(f"前端目录: {STATIC_DIR}")
    print(f"数据库配置: {server.db_env_path}")
    print(f"embedding 配置: {server.embedding_env_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

