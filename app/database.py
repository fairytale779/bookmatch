import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from app.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경변수가 설정되어 있지 않습니다.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    데이터베이스 세션을 생성하고 반환하는 의존성 함수.
    FastAPI의 Depends에서 사용됩니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
