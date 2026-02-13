## Kakao Book Search CLI (`kakao_books.py`)

Kakao Daum Search의 **Book Search API**를 사용하여 도서 데이터를 수집하고, JSON/CSV 파일로 저장하는 Python CLI 스크립트입니다.

Python 3.10+ 및 macOS 환경을 기준으로 작성되었습니다.

---

### 1. 요구사항

- **Python**: 3.10 이상
- **패키지**:
  - `requests`

패키지는 `requirements.txt`를 통해 설치할 수 있습니다.

```bash
pip install -r requirements.txt
```

---

### 2. Kakao REST API 키 설정 (환경변수)

이 스크립트는 Kakao REST API 키를 **환경변수**에서 읽어옵니다.

- 사용 환경변수 이름: **`KAKAO_REST_API_KEY`**

#### zsh/bash (macOS 기본 터미널)

```bash
export KAKAO_REST_API_KEY="YOUR_REST_API_KEY"
```

매번 입력하기 번거롭다면 `~/.zshrc` 또는 `~/.bashrc` 등에 추가한 뒤 터미널을 재시작하거나 아래처럼 적용합니다.

```bash
echo 'export KAKAO_REST_API_KEY="YOUR_REST_API_KEY"' >> ~/.zshrc
source ~/.zshrc
```

환경변수가 설정되어 있지 않으면 스크립트 실행 시 친절한 에러 메시지를 출력하고 종료합니다.

---

### 3. 실행 방법

프로젝트 디렉토리로 이동 후 아래와 같이 실행합니다.

```bash
python kakao_books.py --query "파이썬"
```

#### 전체 옵션

```bash
python kakao_books.py \
  --query "검색어" \
  --target title|isbn|publisher|person \
  --sort accuracy|latest \
  --size 1~50 \
  --max-pages N \
  --out-dir ./out
```

- **`--query` (필수)**: 검색어
- **`--target` (옵션)**:
  - `title` (기본값)
  - `isbn`
  - `publisher`
  - `person`
- **`--sort` (옵션)**:
  - `accuracy` (기본값, 정확도 순)
  - `latest` (최신순)
- **`--size` (옵션)**:
  - 페이지당 결과 수 (1~50, 기본값: 50)
- **`--max-pages` (옵션)**:
  - 최대 페이지 수 (기본값: 20)
- **`--out-dir` (옵션)**:
  - 결과 저장 폴더 경로 (기본값: `./out`)

---

### 4. 동작 방식

- Kakao Book Search API 엔드포인트:
  - `GET https://dapi.kakao.com/v3/search/book`
- 헤더:
  - `Authorization: KakaoAK {REST_API_KEY}`
- **페이지네이션**:
  - `page=1`부터 시작하여 `meta.is_end == true` 이거나 `max_pages`에 도달할 때까지 수집
- **요청 간 딜레이**:
  - 각 페이지 요청 사이에 기본 **0.2초** `sleep` (rate limit 예방)
- **에러/재시도 처리**:
  - 네트워크 에러, `429`, `5xx` 응답에 대해 **최대 3회 재시도**
  - 재시도 시 **exponential backoff** 적용: 0.5초, 1초, 2초 간격

---

### 5. 중복 제거 로직

API가 반환하는 `documents` 리스트에 대해 다음 기준으로 중복을 제거합니다.

- 1차 기준: **`isbn`**
  - Kakao의 `isbn` 필드는 `"ISBN10 ISBN13"`처럼 여러 값이 공백으로 들어올 수 있습니다.
  - 공백 및 `, ; | /` 등의 구분자로 분리 후, **첫 번째 유효한 값**을 대표 ISBN으로 사용합니다.
- 2차 기준 (ISBN이 비어있을 경우): **`title + publisher + authors` 조합**
  - `title`, `publisher`, `authors`를 합쳐 하나의 문자열 키로 사용
  - `authors`는 리스트인 경우 `", "`로 join한 문자열로 변환

이 키(ISBN 또는 fallback 키)를 기준으로 **가장 먼저 등장한 문서만 유지**하고 나머지는 제거합니다.

---

### 6. 출력 결과

결과 파일은 기본적으로 `./out` 디렉토리에 생성됩니다.  
`--out-dir` 옵션으로 다른 폴더를 지정할 수 있습니다.

- **JSON 파일**
  - 경로: `out/books_{query_sanitized}.json`
  - 내용: Kakao API에서 받은 `documents`를 중복 제거한 뒤 리스트 형태로 저장
  - 인코딩: UTF-8, `ensure_ascii=False`, `indent=2`

- **CSV 파일**
  - 경로: `out/books_{query_sanitized}.csv`
  - 컬럼:
    - `title`
    - `authors`
    - `publisher`
    - `isbn`
    - `datetime`
    - `price`
    - `sale_price`
    - `url`
    - `thumbnail`
    - `status`
    - `contents`
  - `authors`가 리스트인 경우: `"a, b"` 형식의 문자열로 저장
  - `isbn`은 정규화된 대표 ISBN (예: `"ISBN10 ISBN13"` → `ISBN10` 또는 유효한 첫 값)

`query_sanitized`는 검색어에서 한글/영문/숫자를 제외한 문자를 `_`로 치환한 문자열입니다.

예:  
- 검색어 `"파이썬"` → 파일명 접미사 `"파이썬"`  
- 검색어 `"python 3.10"` → 파일명 접미사 `"python_3_10"`

---

### 7. 실행 예시

#### 1) 제목 기준, 최신순 정렬, 최대 10페이지

```bash
python kakao_books.py --query "파이썬" --target title --sort latest --max-pages 10
```

#### 2) ISBN 기준, 정확도 순, 기본 옵션 사용

```bash
python kakao_books.py --query "9788966263158" --target isbn
```

#### 3) 특정 폴더에 결과 저장

```bash
python kakao_books.py --query "머신러닝" --out-dir "./results"
```

---

### 8. 로그/출력 메시지

스크립트는 진행 상황을 간단한 로그로 출력합니다.

- 현재 요청 중인 페이지 번호
- 각 페이지에서 받은 건수
- 누적 수집 건수
- `meta.is_end` 상태
- 네트워크/429/5xx 에러 발생 시 재시도 안내

예시:

```text
[정보] 검색 시작 - query='파이썬', target=title, sort=latest, size=50, max_pages=10
[정보] 페이지 1 요청 중...
[정보] 페이지 1 수신 - 이번 페이지 50건, 누적 50건, is_end=False
...
[정보] 총 수집 건수: 420
[정보] 중복 제거 후 건수: 380
[정보] JSON 저장 완료: out/books_파이썬.json
[정보] CSV 저장 완료: out/books_파이썬.csv
[정보] 작업이 완료되었습니다.
```

---

### 9. 참고

- Kakao Developers의 Book Search API 문서를 참고하여 쿼리/파라미터를 조정할 수 있습니다.
- API 쿼터 및 사용량 제한에 유의하세요. 요청 간 기본 0.2초의 딜레이가 포함되어 있지만, 대량 수집 시에는 추가적인 조정이 필요할 수 있습니다.


