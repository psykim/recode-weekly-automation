# Google Translate API 설정 가이드

## 1. Google Cloud Console 접속
1. [Google Cloud Console](https://console.cloud.google.com) 방문
2. Google 계정으로 로그인

## 2. 프로젝트 생성 (처음 사용하는 경우)
1. 상단의 프로젝트 선택 드롭다운 클릭
2. "새 프로젝트" 클릭
3. 프로젝트 이름 입력 (예: "RECODE Weekly")
4. "만들기" 클릭

## 3. Cloud Translation API 활성화
1. 좌측 메뉴에서 "API 및 서비스" → "라이브러리"
2. 검색창에 "Cloud Translation API" 입력
3. "Cloud Translation API" 선택
4. "사용 설정" 버튼 클릭

## 4. API 키 생성
1. 좌측 메뉴에서 "API 및 서비스" → "사용자 인증 정보"
2. "사용자 인증 정보 만들기" → "API 키" 클릭
3. 생성된 API 키 복사
4. (선택사항) "키 제한" 클릭하여 보안 설정:
   - 애플리케이션 제한사항: IP 주소 (선택사항)
   - API 제한사항: Cloud Translation API 선택

## 5. API 키 설정
```bash
# .env 파일 편집
nano .env
```

다음과 같이 수정:
```
GOOGLE_API_KEY=여기에_복사한_API_키_붙여넣기
```

## 6. 번역 테스트
```bash
# 번역 기능 테스트
python3 test_translation.py

# 실제 보고서 생성 테스트
python3 scripts/generate_report.py
```

## 무료 사용량
- **월 500,000 문자 무료**
- 약 50개의 주간 보고서 생성 가능
- 초과 시: $20 / 1백만 문자

## 사용량 확인
1. [Google Cloud Console](https://console.cloud.google.com)
2. "API 및 서비스" → "대시보드"
3. Cloud Translation API 사용량 확인

## 문제 해결

### "API key not valid" 오류
1. API 키가 정확히 복사되었는지 확인
2. Cloud Translation API가 활성화되었는지 확인
3. 프로젝트가 올바르게 선택되었는지 확인

### 번역이 되지 않을 때
1. `python3 test_translation.py` 실행하여 상태 확인
2. Google Cloud Console에서 API 상태 확인
3. 무료 사용량 초과 여부 확인

## 장점
- 무료 사용량이 충분함 (월 50만 문자)
- 설정이 간단함
- 안정적인 서비스
- 다양한 언어 지원

## GitHub Actions 설정
저장소 Settings → Secrets → New repository secret:
- Name: `GOOGLE_API_KEY`
- Value: API 키 붙여넣기