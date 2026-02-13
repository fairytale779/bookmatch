from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import upsert_book, get_books
from app.kakao_client import search_books, KakaoAPIError
from app.models import Book

app = FastAPI(title="Book Match API")


@app.get("/import")
async def import_books(
    query: str = Query(..., description="검색어"),
    db: Session = Depends(get_db)
):
    """
    Kakao API를 호출하여 책을 검색하고 데이터베이스에 저장합니다.
    
    Args:
        query: 검색어
        db: 데이터베이스 세션
    
    Returns:
        저장된 책의 개수
    """
    try:
        # Kakao API 호출
        books_data = search_books(keyword=query, size=10)
        
        if not books_data:
            return {"count": 0, "message": "검색 결과가 없습니다."}
        
        # 각 책을 DB에 저장
        saved_count = 0
        for book_data in books_data:
            try:
                upsert_book(db, book_data)
                saved_count += 1
            except ValueError as e:
                # ISBN이 없는 경우 등 스킵
                continue
        
        return {"count": saved_count, "message": f"{saved_count}권의 책이 저장되었습니다."}
        
    except KakaoAPIError as e:
        raise HTTPException(status_code=500, detail=f"Kakao API 호출 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 에러: {str(e)}")


@app.get("/books")
async def list_books(
    limit: int = Query(10, ge=1, le=100, description="반환할 책의 개수"),
    db: Session = Depends(get_db)
):
    """
    데이터베이스에서 책 목록을 조회합니다.
    
    Args:
        limit: 반환할 책의 개수 (기본값: 10, 최대 100)
        db: 데이터베이스 세션
    
    Returns:
        책 목록
    """
    books = get_books(db, limit=limit)
    
    # Pydantic 모델로 변환하여 반환
    return {
        "count": len(books),
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "isbn": book.isbn,
                "authors": book.authors,
                "publisher": book.publisher,
                "price": book.price,
                "sale_price": book.sale_price,
                "thumbnail": book.thumbnail,
                "url": book.url,
                "created_at": book.created_at.isoformat() if book.created_at else None,
            }
            for book in books
        ]
    }


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Book Match API",
        "endpoints": {
            "import": "GET /import?query=xxx - Kakao API에서 책을 검색하고 저장",
            "books": "GET /books?limit=10 - 저장된 책 목록 조회",
        }
    }
