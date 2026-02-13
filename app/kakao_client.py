import os
from typing import Dict, List, Any, Optional

import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

API_URL = "https://dapi.kakao.com/v3/search/book"


class KakaoAPIError(Exception):
    """Kakao API 호출 중 발생한 에러를 나타내는 커스텀 예외"""
    pass


def search_books(keyword: str, size: int = 10) -> List[Dict[str, Any]]:
    """
    Kakao 책검색 API를 사용하여 도서를 검색합니다.
    
    Args:
        keyword: 검색어
        size: 반환할 결과 수 (기본값: 10)
    
    Returns:
        검색된 도서 정보 리스트
    
    Raises:
        KakaoAPIError: API 호출 실패 시
    """
    # .env에서 API 키 읽기
    api_key = os.getenv("KAKAO_REST_API_KEY")
    if not api_key:
        raise KakaoAPIError(
            "KAKAO_REST_API_KEY가 .env 파일에 설정되어 있지 않습니다."
        )
    
    # 헤더 설정
    headers = {
        "Authorization": f"KakaoAK {api_key}"
    }
    
    # 요청 파라미터 설정
    params = {
        "query": keyword,
        "size": size,
    }
    
    try:
        # API 호출
        response = requests.get(
            API_URL,
            headers=headers,
            params=params,
            timeout=10
        )
        
        # HTTP 에러 처리
        response.raise_for_status()
        
        # JSON 파싱
        data = response.json()
        
        # 응답 구조 확인
        if "documents" not in data:
            raise KakaoAPIError(
                f"예상치 못한 API 응답 형식입니다. 응답: {data}"
            )
        
        return data.get("documents", [])
        
    except requests.exceptions.Timeout:
        raise KakaoAPIError("API 요청 시간 초과가 발생했습니다.")
    except requests.exceptions.ConnectionError:
        raise KakaoAPIError("네트워크 연결에 실패했습니다.")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        error_msg = f"HTTP 에러 발생 (상태 코드: {status_code})"
        if e.response:
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {e.response.text}"
        raise KakaoAPIError(error_msg) from e
    except requests.exceptions.RequestException as e:
        raise KakaoAPIError(f"API 요청 중 에러가 발생했습니다: {e}") from e
    except ValueError as e:
        raise KakaoAPIError(f"응답 JSON 파싱에 실패했습니다: {e}") from e
