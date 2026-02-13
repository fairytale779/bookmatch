from dotenv import load_dotenv
import os, requests

load_dotenv()  # .env 읽기

key = os.getenv("KAKAO_REST_API_KEY")
if not key:
    print("❌ .env에서 KAKAO_REST_API_KEY를 못 찾았어요. .env 위치/이름/내용 확인!")
    raise SystemExit

url = "https://dapi.kakao.com/v3/search/book"
headers = {"Authorization": f"KakaoAK {key}"}
params = {"query": "파이썬", "size": 5, "target": "title"}

r = requests.get(url, headers=headers, params=params, timeout=15)

print("HTTP status:", r.status_code)
if r.status_code != 200:
    print("응답 내용:", r.text)  # 실패 이유 출력
    raise SystemExit

data = r.json()
print("✅ total_count:", data["meta"]["total_count"])
print("✅ is_end:", data["meta"]["is_end"])
print("---- 책 제목 5개 ----")
for i, doc in enumerate(data["documents"], 1):
    print(f"{i}. {doc.get('title')}")
