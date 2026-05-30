#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import html
import json
import re
import ssl
import urllib.parse
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from docx import Document
from pypdf import PdfReader


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
MANIFEST_PATH = SCRIPT_DIR / "法条库清单.json"
PROJECT_TEXT_ROOT_DIR = PROJECT_ROOT / "整理后文本" / "法条库"
PROJECT_TEXT_DIR = PROJECT_TEXT_ROOT_DIR / "正文"
PROJECT_META_DIR = PROJECT_TEXT_ROOT_DIR / "来源元数据"
OBSIDIAN_RAW_DIR = Path(r"D:\Onedrive\Obsidian\法考知识点\300_LawText\官方法条下载")

FLK_SEARCH_URL = "https://flk.npc.gov.cn/law-search/search/list"
FLK_DETAIL_URL = "https://flk.npc.gov.cn/law-search/search/flfgDetails"
FLK_DOWNLOAD_BATCH_URL = "https://flk.npc.gov.cn/law-search/download/batch"

SSL_CONTEXT = ssl.create_default_context()
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
HTML_TAG_RE = re.compile(r"<[^>]+>")
INVALID_WIN_NAME_RE = re.compile(r'[<>:"/\\\\|?*]')


def sanitize_filename(name: str) -> str:
    return INVALID_WIN_NAME_RE.sub("_", name).strip()


def request_json(url: str, *, method: str = "GET", payload=None) -> dict:
    data = None
    headers = {"User-Agent": USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json;charset=UTF-8"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=120, context=SSL_CONTEXT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=180, context=SSL_CONTEXT) as resp:
        return resp.read()


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(records: list[dict]) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def find_record(records: list[dict], book_name: str) -> dict:
    record = next((item for item in records if item["book_name"] == book_name), None)
    if not record:
        raise SystemExit(f"未在清单中找到书目: {book_name}")
    return record


def strip_markup(text: str | None) -> str:
    if not text:
        return ""
    return html.unescape(HTML_TAG_RE.sub("", text)).strip()


def normalize_title(text: str | None) -> str:
    cleaned = strip_markup(text)
    return re.sub(r"\s+", "", cleaned)


def effective_status_text(status_code: int | None) -> str:
    mapping = {
        3: "现行有效",
        2: "已被修改",
        1: "已失效",
        0: "历史版本",
    }
    return mapping.get(status_code, "未知")


def exact_match_score(row: dict, law_name: str, doc_type: str) -> tuple:
    normalized_target = normalize_title(law_name)
    normalized_row = normalize_title(row.get("title"))
    law_kind = row.get("flxz") or ""
    expected_kind = "司法解释" if doc_type == "司法解释" else "法律"
    alt_exact = normalized_row.startswith(normalized_target)
    effective_code = int(row.get("sxx") or 0)
    return (
        1 if normalized_row == normalized_target else 0,
        1 if alt_exact else 0,
        1 if law_kind == expected_kind else 0,
        1 if effective_code == 3 else 0,
        row.get("sxrq") or "",
        row.get("gbrq") or "",
    )


def search_best_bbbs(law_name: str, doc_type: str) -> str:
    payload = {
        "searchContent": law_name,
        "searchType": 1,
        "searchRange": 1,
        "page": 1,
        "size": 20,
    }
    result = request_json(FLK_SEARCH_URL, method="POST", payload=payload)
    rows = result.get("rows") or []
    if not rows:
        raise RuntimeError(f"官方检索未找到: {law_name}")
    ranked = sorted(
        rows,
        key=lambda row: exact_match_score(row, law_name, doc_type),
        reverse=True,
    )
    best = ranked[0]
    score = exact_match_score(best, law_name, doc_type)
    if score[0] != 1 and score[1] != 1:
        raise RuntimeError(f"官方检索未找到精确标题: {law_name}")
    return best["bbbs"]


def fetch_details(detail_id: str) -> dict:
    query = urllib.parse.urlencode({"bbbs": detail_id})
    result = request_json(f"{FLK_DETAIL_URL}?{query}")
    if result.get("code") != 200 or not result.get("data"):
        raise RuntimeError(f"获取官方详情失败: {detail_id}")
    return result["data"]


def ensure_current_effective(details: dict, law_name: str) -> None:
    status_code = int(details.get("sxx") or 0)
    if status_code != 3:
        raise RuntimeError(
            f"{law_name} 当前不是现行有效版本，状态={effective_status_text(status_code)}"
        )


def enrich_record(record: dict) -> dict:
    detail_id = record.get("detail_id") or search_best_bbbs(record["law_name"], record["doc_type"])
    details = fetch_details(detail_id)
    ensure_current_effective(details, record["law_name"])

    enriched = dict(record)
    enriched.update(
        {
            "detail_id": detail_id,
            "source_url": f"{FLK_DETAIL_URL}?bbbs={detail_id}",
            "source_site": "flk.npc.gov.cn",
            "issued_authority": details.get("zdjgName") or record.get("issued_authority"),
            "effective_status": effective_status_text(int(details.get("sxx") or 0)),
            "issued_date": details.get("gbrq") or record.get("issued_date"),
            "effective_date": details.get("sxrq") or record.get("effective_date"),
            "law_kind": details.get("flxz") or record.get("law_kind"),
            "official_title": details.get("title") or record["law_name"],
        }
    )
    return enriched


def persist_record_update(updated_record: dict) -> None:
    records = load_manifest()
    changed = False
    for index, item in enumerate(records):
        if item["book_name"] == updated_record["book_name"]:
            records[index] = updated_record
            changed = True
            break
    if changed:
        save_manifest(records)


def get_presigned_download(detail_id: str, file_format: str) -> str | None:
    result = request_json(
        FLK_DOWNLOAD_BATCH_URL,
        method="POST",
        payload=[{"bbbs": detail_id, "format": file_format}],
    )
    if result.get("code") != 200:
        return None
    items = result.get("data") or []
    if not items:
        return None
    return items[0].get("url")


def choose_download_formats(details: dict) -> list[str]:
    oss = details.get("ossFile") or {}
    formats: list[str] = []
    if oss.get("ossWordPath"):
        formats.append("docx")
    if oss.get("ossPdfPath"):
        formats.append("pdf")
    return formats or ["pdf"]


def obsidian_record_dir(law_name: str) -> Path:
    return OBSIDIAN_RAW_DIR / sanitize_filename(law_name)


def get_raw_source_path(record: dict) -> Path | None:
    raw_dir = obsidian_record_dir(record["law_name"])
    for ext in (".docx", ".pdf"):
        candidate = raw_dir / f"{sanitize_filename(record['law_name'])}{ext}"
        if candidate.exists():
            return candidate
    return None


def get_project_text_path(file_name: str) -> Path:
    return PROJECT_TEXT_DIR / file_name


def get_project_meta_path(file_name: str) -> Path:
    return PROJECT_META_DIR / Path(file_name).with_suffix(".source.json").name


def write_obsidian_index_note() -> None:
    OBSIDIAN_RAW_DIR.mkdir(parents=True, exist_ok=True)
    note_path = OBSIDIAN_RAW_DIR / "README.md"
    if note_path.exists():
        return
    note_path.write_text(
        "# 官方法条下载\n\n"
        "本目录保存从国家法律法规数据库等官方来源下载的法条原始文件。\n\n"
        "- 每部法律单独一个子目录\n"
        "- 原始文件优先保存官方 docx，缺失时保存官方 pdf\n"
        "- `来源信息.json` 记录来源链接、发布日期、施行日期和现行状态\n",
        encoding="utf-8",
    )


def download_official_source(record: dict) -> tuple[dict, Path]:
    write_obsidian_index_note()
    enriched = enrich_record(record)
    details = fetch_details(enriched["detail_id"])
    formats = choose_download_formats(details)
    raw_dir = obsidian_record_dir(enriched["law_name"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    selected_format = None
    download_url = None
    for file_format in formats:
        download_url = get_presigned_download(enriched["detail_id"], file_format)
        if download_url:
            selected_format = file_format
            break
    if not selected_format or not download_url:
        raise RuntimeError(f"未拿到官方原始文件下载链接: {enriched['law_name']}")

    raw_path = raw_dir / f"{sanitize_filename(enriched['law_name'])}.{selected_format}"
    raw_path.write_bytes(download_bytes(download_url))

    source_meta = {
        "book_name": enriched["book_name"],
        "law_name": enriched["law_name"],
        "source_url": enriched["source_url"],
        "source_site": enriched["source_site"],
        "detail_id": enriched["detail_id"],
        "issued_authority": enriched.get("issued_authority"),
        "issued_date": enriched.get("issued_date"),
        "effective_date": enriched.get("effective_date"),
        "effective_status": enriched.get("effective_status"),
        "law_kind": enriched.get("law_kind"),
        "download_format": selected_format,
        "download_url": download_url,
        "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        "raw_file": str(raw_path),
    }
    (raw_dir / "来源信息.json").write_text(
        json.dumps(source_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "来源说明.md").write_text(
        f"# {enriched['law_name']}\n\n"
        f"- 来源站点：{enriched['source_site']}\n"
        f"- 详情接口：{enriched['source_url']}\n"
        f"- 发布机关：{enriched.get('issued_authority') or ''}\n"
        f"- 公布日期：{enriched.get('issued_date') or ''}\n"
        f"- 施行日期：{enriched.get('effective_date') or ''}\n"
        f"- 效力状态：{enriched.get('effective_status') or ''}\n"
        f"- 原件格式：{selected_format}\n",
        encoding="utf-8",
    )

    persist_record_update(enriched)
    return enriched, raw_path


def normalize_text_content(text: str, law_name: str) -> str:
    cleaned = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned.startswith("# "):
        cleaned = f"# {law_name}\n\n{cleaned}"
    return cleaned.strip() + "\n"


def extract_docx_text(path: Path) -> str:
    document = Document(str(path))
    parts: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
        else:
            parts.append("")
    return "\n".join(parts)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if page_text:
            parts.append(page_text)
    return "\n\n".join(parts)


def extract_raw_file(raw_path: Path) -> str:
    suffix = raw_path.suffix.lower()
    if suffix == ".docx":
        return extract_docx_text(raw_path)
    if suffix == ".pdf":
        return extract_pdf_text(raw_path)
    raise RuntimeError(f"暂不支持的官方原件格式: {raw_path}")


def build_project_text(record: dict, *, output_path: Path | None = None) -> tuple[dict, Path, Path]:
    current_record = enrich_record(record)
    persist_record_update(current_record)
    raw_path = get_raw_source_path(current_record)
    if raw_path is None:
        current_record, raw_path = download_official_source(current_record)
    text = normalize_text_content(extract_raw_file(raw_path), current_record["law_name"])
    PROJECT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    PROJECT_META_DIR.mkdir(parents=True, exist_ok=True)
    final_output = output_path or get_project_text_path(current_record["file_name"])
    final_output.write_text(text, encoding="utf-8")
    meta_output = get_project_meta_path(current_record["file_name"])
    meta_output.write_text(
        json.dumps(
            {
                "book_name": current_record["book_name"],
                "law_name": current_record["law_name"],
                "source_url": current_record.get("source_url"),
                "source_site": current_record.get("source_site"),
                "detail_id": current_record.get("detail_id"),
                "issued_authority": current_record.get("issued_authority"),
                "issued_date": current_record.get("issued_date"),
                "effective_date": current_record.get("effective_date"),
                "effective_status": current_record.get("effective_status"),
                "raw_file": str(raw_path),
                "text_file": str(final_output),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return current_record, raw_path, final_output
