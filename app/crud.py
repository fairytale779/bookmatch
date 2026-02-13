from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Book


def upsert_book(db: Session, book_data: Dict[str, Any]) -> Book:
    """
    ISBN 기준으로 책 정보를 upsert합니다.
    
    - ISBN이 존재하면 해당 레코드를 업데이트
    - ISBN이 없으면 새 레코드를 생성
    - raw_json에 전체 book_data를 저장
    
    Args:
        db: SQLAlchemy 세션
        book_data: Kakao API에서 받은 책 데이터 딕셔너리
    
    Returns:
        생성 또는 업데이트된 Book 인스턴스
    """
    # ISBN 추출 (Kakao API는 "ISBN10 ISBN13" 형식일 수 있음)
    isbn_raw = book_data.get("isbn", "").strip()
    if not isbn_raw:
        raise ValueError("book_data에 isbn이 없습니다.")
    
    # ISBN 정규화 (첫 번째 ISBN만 사용)
    isbn = isbn_raw.split()[0] if isbn_raw else None
    if not isbn:
        raise ValueError("유효한 ISBN을 찾을 수 없습니다.")
    
    # 기존 책 조회
    stmt = select(Book).where(Book.isbn == isbn)
    existing_book = db.scalar(stmt)
    
    # authors와 translators를 리스트에서 적절한 형식으로 변환
    authors = book_data.get("authors")
    if isinstance(authors, list):
        authors = authors  # JSONB로 저장 가능
    elif isinstance(authors, str):
        authors = [authors]
    
    translators = book_data.get("translators")
    if isinstance(translators, list):
        translators = translators
    elif isinstance(translators, str):
        translators = [translators]
    
    # datetime 문자열 파싱
    datetime_str = book_data.get("datetime")
    book_datetime = None
    if datetime_str:
        try:
            # ISO 형식 문자열을 datetime으로 변환
            if isinstance(datetime_str, str):
                book_datetime = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            elif isinstance(datetime_str, datetime):
                book_datetime = datetime_str
        except (ValueError, AttributeError):
            pass
    
    if existing_book:
        # 업데이트
        existing_book.title = book_data.get("title", existing_book.title)
        existing_book.contents = book_data.get("contents")
        existing_book.url = book_data.get("url")
        existing_book.datetime = book_datetime
        existing_book.authors = authors
        existing_book.publisher = book_data.get("publisher")
        existing_book.translators = translators
        existing_book.price = book_data.get("price")
        existing_book.sale_price = book_data.get("sale_price")
        existing_book.thumbnail = book_data.get("thumbnail")
        existing_book.status = book_data.get("status")
        existing_book.raw_json = book_data  # 전체 원본 데이터 저장
        
        db.commit()
        db.refresh(existing_book)
        return existing_book
    else:
        # 새로 생성
        new_book = Book(
            title=book_data.get("title", ""),
            contents=book_data.get("contents"),
            url=book_data.get("url"),
            isbn=isbn,
            datetime=book_datetime,
            authors=authors,
            publisher=book_data.get("publisher"),
            translators=translators,
            price=book_data.get("price"),
            sale_price=book_data.get("sale_price"),
            thumbnail=book_data.get("thumbnail"),
            status=book_data.get("status"),
            raw_json=book_data,  # 전체 원본 데이터 저장
        )
        
        db.add(new_book)
        db.commit()
        db.refresh(new_book)
        return new_book


def get_books(db: Session, limit: int = 10) -> list[Book]:
    """
    데이터베이스에서 책 목록을 조회합니다.
    
    Args:
        db: SQLAlchemy 세션
        limit: 반환할 최대 개수 (기본값: 10)
    
    Returns:
        Book 인스턴스 리스트
    """
    stmt = select(Book).limit(limit)
    return list(db.scalars(stmt).all())
