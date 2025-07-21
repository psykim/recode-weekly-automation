# Claude API 설정 가이드

## 1. Claude API 키 얻기

### 옵션 A: 이미 Claude 계정이 있는 경우
1. [Anthropic Console](https://console.anthropic.com)에 로그인
2. 좌측 메뉴에서 **"API Keys"** 클릭
3. **"Create Key"** 버튼 클릭
4. 키 이름 입력 (예: "RECODE Weekly")
5. 생성된 키 복사 (sk-ant-api03-로 시작하는 긴 문자열)

### 옵션 B: 새로운 API 계정 생성
1. [Anthropic Console](https://console.anthropic.com)에서 새 계정 생성
2. 이메일 인증 완료
3. 위의 단계 2-5 진행

## 2. API 키 설정

```bash
# .env 파일 편집
nano .env
# 또는
vi .env
```

다음과 같이 수정:
```
ANTHROPIC_API_KEY=sk-ant-api03-실제키입력
```

## 3. 번역 테스트

```bash
# 번역 기능 테스트
python3 test_translation.py

# 실제 보고서 생성 테스트 (--test 옵션 사용)
python3 scripts/generate_report.py --test
```

## 4. 요금 정보

Claude Haiku (사용 중인 모델) 요금:
- 입력: $0.25 / 1M 토큰 (약 75만 단어)
- 출력: $1.25 / 1M 토큰 (약 75만 단어)

예상 비용:
- 주간 보고서 1개: 약 $0.01 (10원)
- 월간 (4개 보고서): 약 $0.04 (40원)
- 연간 (52개 보고서): 약 $0.52 (520원)

## 5. API 키 보안

- API 키는 절대 GitHub에 커밋하지 마세요
- .env 파일은 .gitignore에 포함되어 있습니다
- GitHub Actions에서 사용하려면 Secrets에 추가하세요:
  1. GitHub 저장소 → Settings → Secrets and variables → Actions
  2. New repository secret
  3. Name: `ANTHROPIC_API_KEY`
  4. Value: API 키 붙여넣기

## 문제 해결

### "Authentication error" 발생 시
1. API 키가 정확히 입력되었는지 확인
2. 키가 'sk-ant-api03-'로 시작하는지 확인
3. .env 파일에 공백이나 따옴표가 없는지 확인

### 번역이 되지 않을 때
1. `python3 test_translation.py` 실행하여 상태 확인
2. API 키 상태 확인
3. 인터넷 연결 확인

## 참고 사항

- Claude API는 DeepL보다 더 자연스러운 의학 용어 번역을 제공합니다
- 실시간 번역이므로 인터넷 연결이 필요합니다
- API 사용량은 Anthropic Console에서 확인 가능합니다