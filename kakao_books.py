#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


API_URL = "https://dapi.kakao.com/v3/search/book"
ENV_API_KEY = "KAKAO_REST_API_KEY"


@dataclass
class KakaoBookRequest:
    query: str
    target: str = "title"
    sort: str = "accuracy"
    size: int = 50
    max_pages: int = 20
    out_dir: Path = Path("./out")
    sleep_between: float = 0.2


def get_rest_api_key() -> str:
    """Read Kakao REST API key from environment variable."""
    api_key = os.getenv(ENV_API_KEY)
    if not api_key:
        raise RuntimeError(
            f"환경변수 {ENV_API_KEY}가 설정되어 있지 않습니다.\n"
            "예시 (zsh/bash):\n"
            f"  export {ENV_API_KEY}='YOUR_REST_API_KEY'\n"
        )
    return api_key


def build_headers(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"KakaoAK {api_key}"}


def fetch_page(
    session: requests.Session,
    req: KakaoBookRequest,
    page: int,
    headers: Dict[str, str],
    retries: int = 3,
    backoff_base: float = 0.5,
) -> Dict[str, Any]:
    """
    Fetch a single page from Kakao Book Search API with retry and exponential backoff.
    """
    params = {
        "query": req.query,
        "target": req.target,
        "sort": req.sort,
        "page": page,
        "size": req.size,
    }

    attempt = 0
    while True:
        try:
            resp = session.get(API_URL, headers=headers, params=params, timeout=10)

            # Retry only for 429 and 5xx
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                attempt += 1
                if attempt > retries:
                    resp.raise_for_status()
                wait = backoff_base * (2 ** (attempt - 1))
                print(
                    f"[경고] 상태코드 {resp.status_code} (page={page}) - "
                    f"{wait:.1f}초 후 재시도 ({attempt}/{retries})"
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt > retries:
                raise RuntimeError(
                    f"[에러] 페이지 {page} 요청 실패 (재시도 {retries}회 초과): {e}"
                ) from e
            wait = backoff_base * (2 ** (attempt - 1))
            print(
                f"[경고] 네트워크 에러 발생 (page={page}): {e} - "
                f"{wait:.1f}초 후 재시도 ({attempt}/{retries})"
            )
            time.sleep(wait)


def fetch_all(req: KakaoBookRequest) -> List[Dict[str, Any]]:
    """Fetch all pages until is_end or max_pages."""
    api_key = get_rest_api_key()
    headers = build_headers(api_key)

    documents: List[Dict[str, Any]] = []

    with requests.Session() as session:
        for page in range(1, req.max_pages + 1):
            print(f"[정보] 페이지 {page} 요청 중...")
            data = fetch_page(session, req, page, headers=headers)

            docs = data.get("documents", [])
            meta = data.get("meta", {})
            is_end = bool(meta.get("is_end", False))

            documents.extend(docs)
            print(
                f"[정보] 페이지 {page} 수신 - 이번 페이지 {len(docs)}건, "
                f"누적 {len(documents)}건, is_end={is_end}"
            )

            if is_end:
                print("[정보] meta.is_end = true, 수집을 종료합니다.")
                break

            if page < req.max_pages:
                time.sleep(req.sleep_between)

    return documents


def _normalize_isbn(isbn_raw: str) -> Optional[str]:
    """
    Normalize Kakao's isbn field.

    Kakao returns "ISBN10 ISBN13" or multiple separated by spaces.
    We split by whitespace and common delimiters and pick the first non-empty part.
    """
    if not isbn_raw:
        return None

    # Split by whitespace or common separators
    parts = re.split(r"[\s,;|/]+", isbn_raw.strip())
    parts = [p for p in parts if p]
    if not parts:
        return None

    return parts[0]


def _authors_to_string(authors: Any) -> str:
    if isinstance(authors, list):
        return ", ".join(str(a) for a in authors)
    if authors is None:
        return ""
    return str(authors)


def _fallback_key(doc: Dict[str, Any]) -> str:
    title = str(doc.get("title", "")).strip()
    publisher = str(doc.get("publisher", "")).strip()
    authors_str = _authors_to_string(doc.get("authors", [])).strip()
    if not any([title, publisher, authors_str]):
        return "unknown"
    return f"{title}||{publisher}||{authors_str}"


def dedup_documents(docs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate documents by isbn. If isbn is empty, use title+publisher+authors.
    """
    seen: Dict[str, Dict[str, Any]] = {}

    for doc in docs:
        raw_isbn = str(doc.get("isbn", "")).strip()
        isbn_key = _normalize_isbn(raw_isbn)

        if isbn_key:
            key = f"isbn:{isbn_key}"
        else:
            key = f"fallback:{_fallback_key(doc)}"

        if key in seen:
            continue
        seen[key] = doc

    return list(seen.values())


def sanitize_query_for_filename(query: str) -> str:
    """
    Sanitize query string for safe filename.
    Keeps alphanumerics and Korean characters, replaces others with '_'.
    """
    # Allow Korean, English letters, numbers
    sanitized = re.sub(r"[^0-9A-Za-z가-힣]+", "_", query)
    sanitized = sanitized.strip("_")
    if not sanitized:
        sanitized = "query"
    return sanitized


def ensure_out_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, docs: List[Dict[str, Any]]) -> None:
    ensure_out_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print(f"[정보] JSON 저장 완료: {path}")


CSV_COLUMNS: Tuple[str, ...] = (
    "title",
    "authors",
    "publisher",
    "isbn",
    "datetime",
    "price",
    "sale_price",
    "url",
    "thumbnail",
    "status",
    "contents",
)


def save_csv(path: Path, docs: List[Dict[str, Any]]) -> None:
    ensure_out_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for doc in docs:
            row = {
                "title": doc.get("title", ""),
                "authors": _authors_to_string(doc.get("authors", [])),
                "publisher": doc.get("publisher", ""),
                "isbn": _normalize_isbn(str(doc.get("isbn", "")).strip()) or "",
                "datetime": doc.get("datetime", ""),
                "price": doc.get("price", ""),
                "sale_price": doc.get("sale_price", ""),
                "url": doc.get("url", ""),
                "thumbnail": doc.get("thumbnail", ""),
                "status": doc.get("status", ""),
                "contents": doc.get("contents", ""),
            }
            writer.writerow(row)
    print(f"[정보] CSV 저장 완료: {path}")


def parse_args(argv: Optional[List[str]] = None) -> KakaoBookRequest:
    parser = argparse.ArgumentParser(
        description="Kakao Daum Book Search API를 사용하여 도서 데이터를 수집하는 CLI 도구",
    )

    parser.add_argument(
        "--query",
        required=True,
        help="검색어 (필수)",
    )
    parser.add_argument(
        "--target",
        choices=["title", "isbn", "publisher", "person"],
        default="title",
        help="검색 대상 필드 (기본값: title)",
    )
    parser.add_argument(
        "--sort",
        choices=["accuracy", "latest"],
        default="accuracy",
        help="정렬 기준 (accuracy|latest, 기본값: accuracy)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=50,
        help="페이지당 결과 수 1~50 (기본값: 50)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="최대 페이지 수 (기본값: 20)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="./out",
        help="결과 저장 폴더 (기본값: ./out)",
    )

    args = parser.parse_args(argv)

    if not (1 <= args.size <= 50):
        parser.error("--size 값은 1~50 사이여야 합니다.")

    if args.max_pages <= 0:
        parser.error("--max-pages 값은 1 이상이어야 합니다.")

    out_dir = Path(args.out_dir)

    return KakaoBookRequest(
        query=args.query,
        target=args.target,
        sort=args.sort,
        size=args.size,
        max_pages=args.max_pages,
        out_dir=out_dir,
    )


def main(argv: Optional[List[str]] = None) -> None:
    try:
        req = parse_args(argv)
    except SystemExit:
        # argparse already printed message
        raise

    print(
        "[정보] 검색 시작 - "
        f"query='{req.query}', target={req.target}, sort={req.sort}, "
        f"size={req.size}, max_pages={req.max_pages}"
    )

    try:
        all_docs = fetch_all(req)
    except RuntimeError as e:
        print(str(e))
        raise SystemExit(1)

    print(f"[정보] 총 수집 건수: {len(all_docs)}")
    deduped_docs = dedup_documents(all_docs)
    print(f"[정보] 중복 제거 후 건수: {len(deduped_docs)}")

    query_sanitized = sanitize_query_for_filename(req.query)
    json_path = req.out_dir / f"books_{query_sanitized}.json"
    csv_path = req.out_dir / f"books_{query_sanitized}.csv"

    save_json(json_path, deduped_docs)
    save_csv(csv_path, deduped_docs)

    print("[정보] 작업이 완료되었습니다.")


if __name__ == "__main__":
    main()


