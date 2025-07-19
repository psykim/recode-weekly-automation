# RECODE WEEKLY 자동화 시스템 설정 가이드

## 1. GitHub 저장소 설정

1. GitHub에서 새 저장소 생성 (`recode-weekly-automation`)
2. 로컬 프로젝트를 GitHub에 푸시:
```bash
cd recode-weekly-automation
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/psykim/recode-weekly-automation.git
git push -u origin main
```

## 2. GitHub Secrets 설정

GitHub 저장소의 Settings → Secrets and variables → Actions에서 다음 시크릿 추가:

- `SMTP_SERVER`: SMTP 서버 주소 (예: smtp.gmail.com)
- `SMTP_PORT`: SMTP 포트 번호 (예: 587)
- `SMTP_USERNAME`: 이메일 계정
- `SMTP_PASSWORD`: 이메일 비밀번호 또는 앱 비밀번호
- `SENDER_EMAIL`: 발신자 이메일 주소

### Gmail 사용 시:
1. Google 계정에서 2단계 인증 활성화
2. 앱 비밀번호 생성: https://myaccount.google.com/apppasswords
3. 생성된 앱 비밀번호를 `SMTP_PASSWORD`로 사용

## 3. GitHub Pages 설정

1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: gh-pages / (root)
4. Save

## 4. 수신자 관리

### 방법 1: GitHub에서 직접 수정
1. `database/recipients.json` 파일 편집
2. 새 수신자 추가 또는 기존 수신자 수정

### 방법 2: 웹 인터페이스 사용
1. `web/manage_recipients.html` 파일을 브라우저에서 열기
2. 웹 UI를 통해 수신자 추가/삭제/수정
3. 내보내기 기능으로 JSON 파일 다운로드
4. GitHub에 업로드

## 5. 수동 실행

GitHub Actions 탭에서:
1. "RECODE WEEKLY 자동 생성 및 발송" 워크플로우 선택
2. "Run workflow" 버튼 클릭
3. "Run workflow" 확인

## 6. 스케줄 변경

`.github/workflows/weekly_report.yml` 파일에서 cron 표현식 수정:

```yaml
schedule:
  - cron: '0 15 * * 4'  # 매주 목요일 15:00 UTC (금요일 0:00 KST)
```

### Cron 표현식 예시:
- `0 15 * * 4`: 매주 금요일 0시 (KST)
- `0 0 * * 5`: 매주 금요일 9시 (KST)
- `0 15 * * 1-5`: 평일 매일 0시 (KST)

## 7. 보고서 커스터마이징

`scripts/generate_report.py`에서:
- `fetch_papers()`: 실제 API 연동 구현
- HTML 템플릿 수정
- 새로운 섹션 추가

## 8. 문제 해결

### 이메일이 발송되지 않을 때:
1. GitHub Secrets 확인
2. SMTP 설정 확인
3. 스팸 폴더 확인

### 보고서가 생성되지 않을 때:
1. Actions 로그 확인
2. Python 스크립트 오류 확인

### 수신자 목록이 업데이트되지 않을 때:
1. `database/recipients.json` 형식 확인
2. JSON 문법 오류 확인