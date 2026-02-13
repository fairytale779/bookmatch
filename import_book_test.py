import os
import json
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ------------------------
# 환경 변수 로드
# ------------------------
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("KAKAO_REST_API_KEY")

if not DB_URL:
    raise RuntimeError("DATABASE_URL missing in .env")
if not API_KEY:
    raise RuntimeError("KAKAO_REST_API_KEY missing in .env")


# ------------------------
# Kakao API 호출
# ------------------------
def fetch_books(query: str, size: int = 10):
    url = "https://dapi.kakao.com/v3/search/book"
    headers = {"Authorization": f"KakaoAK {API_KEY}"}
    params = {"query": query, "size": size}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    return data.get("documents", [])


# ------------------------
# DB 저장 (Upsert)
# ------------------------
def upsert_books(engine, docs):
    sql = text("""
    INSERT INTO books
    (title, contents, url, isbn, datetime, authors, publisher, translators,
     price, sale_price, thumbnail, status, raw_json, created_at, updated_at)
    VALUES
    (:title, :contents, :url, :isbn, :datetime,
     CAST(:authors AS jsonb),
     :publisher,
     CAST(:translators AS jsonb),
     :price, :sale_price, :thumbnail, :status,
     CAST(:raw_json AS jsonb),
     now(), now())
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


# ------------------------
# 메인 실행
# ------------------------
def main():
    engine = create_engine(DB_URL, pool_pre_ping=True)

    query = input("검색어 입력 (예: 해리포터): ").strip() or "해리포터"

    docs = fetch_books(query, size=10)

    print("가져온 권수:", len(docs))
    if docs:
        print("첫 번째 제목:", docs[0].get("title"))

    if not docs:
        print("검색 결과가 없습니다.")
        return

    upsert_books(engine, docs)

    print(f"{len(docs)}권 저장 완료!")


if __name__ == "__main__":
    main()
