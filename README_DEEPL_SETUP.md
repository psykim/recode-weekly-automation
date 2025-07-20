# DeepL API 설정 가이드

## 1. DeepL API 키 발급

1. [DeepL Pro API](https://www.deepl.com/pro-api) 페이지 방문
2. **"무료로 가입"** 클릭
3. 계정 정보 입력 (신용카드 불필요)
4. 이메일 인증 완료
5. 로그인 후 계정 설정에서 **Authentication Key** 복사

## 2. API 키 설정

### 방법 1: .env 파일 사용 (권장)
```bash
# 프로젝트 루트에 .env 파일 생성
cp .env.example .env

# .env 파일 편집
# DEEPL_API_KEY=YOUR_API_KEY를 실제 키로 변경
```

### 방법 2: 환경 변수 설정
```bash
# macOS/Linux
export DEEPL_API_KEY="your-api-key-here"

# Windows
set DEEPL_API_KEY=your-api-key-here
```

### 방법 3: GitHub Actions 시크릿 설정
1. GitHub 저장소 → Settings → Secrets and variables → Actions
2. **New repository secret** 클릭
3. Name: `DEEPL_API_KEY`
4. Value: DeepL API 키 입력

## 3. 무료 플랜 제한사항

- **월 500,000 문자** (약 53개 보고서)
- 초당 3개 요청
- 문서당 최대 1MB

## 4. 사용량 확인

DeepL 계정 페이지에서 월별 사용량 확인 가능:
- https://www.deepl.com/account/usage

## 5. 번역 품질 개선

생성된 보고서의 번역 품질이 이제 대폭 개선됩니다:
- 전문 의학 용어의 정확한 번역
- 자연스러운 한국어 문장 구성
- 문맥을 고려한 번역

## 주의사항

- API 키를 GitHub에 직접 커밋하지 마세요
- .env 파일은 .gitignore에 포함되어 있습니다
- 무료 한도 초과 시 자동으로 기본 번역으로 전환됩니다