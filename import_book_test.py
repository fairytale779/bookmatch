import os
import json
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("KAKAO_REST_API_KEY")

if not DB_URL:
    raise RuntimeError("DATABASE_URL missing")
if not API_KEY:
    raise RuntimeError("KAKAO_REST_API_KEY missing")


def fetch_books(query: str, size: int = 10):
    url = "https://dapi.kakao.com/v3/search/book"
    headers = {"Authorization": f"KakaoAK {API_KEY}"}
    params = {"query": query, "size": size}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()["documents"]


def upsert_books(engine, docs):
    sql = text("""
    INSERT INTO books
    (title, contents, url, isbn, datetime, authors, publisher, translators,
     price, sale_price, thumbnail, status, raw_json, created_at, updated_at)
    VALUES
    (:title, :contents, :url, :isbn, :datetime, :authors::jsonb, :publisher, :translators::jsonb,
     :price, :sale_price, :thumbnail, :status, :raw_json::jsonb, now(), now())
    ON CONFLICT (isbn)
    DO UPDATE SET
      title=EXCLUDED.title,
      contents=EXCLUDED.contents,
      url=EXCLUDED.url,
      datetime=EXCLUDED.datetime,
      authors=EXCLUDED.authors,
      publisher=EXCLUDED.publisher,
      translators=EXCLUDED.translators,
      price=EXCLUDED.price,
      sale_price=EXCLUDED.sale_price,
      thumbnail=EXCLUDED.thumbnail,
      status=EXCLUDED.status,
      raw_json=EXCLUDED.raw_json,
      updated_at=now();
    """)

    with engine.begin() as conn:
        for d in docs:
            conn.execute(sql, {
                "title": d.get("title") or "",
                "contents": d.get("contents"),
                "url": d.get("url"),
                "isbn": d.get("isbn") or "",
                "datetime": d.get("datetime"),
                "authors": json.dumps(d.get("authors") or [], ensure_ascii=False),
                "publisher": d.get("publisher"),
                "translators": json.dumps(d.get("translators") or [], ensure_ascii=False),
                "price": d.get("price"),
                "sale_price": d.get("sale_price"),
                "thumbnail": d.get("thumbnail"),
                "status": d.get("status"),
                "raw_json": json.dumps(d, ensure_ascii=False),
            })


def main():
    engine = create_engine(DB_URL, pool_pre_ping=True)

    query = input("검색어 입력: ").strip() or "해리포터"

    docs = fetch_books(query, size=10)

    if not docs:
        print("검색 결과 없음")
        return

    upsert_books(engine, docs)

    print(f"{len(docs)}권 저장 완료")


if __name__ == "__main__":
    main()
