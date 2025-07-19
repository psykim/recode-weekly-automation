# GitHub 저장소 생성 및 설정 가이드

## 1. GitHub에서 새 저장소 생성

1. https://github.com/new 접속
2. 다음 정보 입력:
   - Repository name: `recode-weekly-automation`
   - Description: "RECODE WEEKLY 자동 생성 및 이메일 발송 시스템"
   - Public 선택
   - **중요**: "Initialize this repository with:" 섹션의 모든 체크박스는 **비워두기**
3. "Create repository" 클릭

## 2. 로컬 저장소를 GitHub에 연결

터미널에서 다음 명령어 실행:

```bash
cd /Users/kwk/development/recode-weekly-automation
git remote add origin https://github.com/psykim/recode-weekly-automation.git
git push -u origin main
```

## 3. GitHub Secrets 설정

1. 저장소 페이지에서 Settings 탭 클릭
2. 왼쪽 메뉴에서 "Secrets and variables" → "Actions" 클릭
3. "New repository secret" 버튼 클릭
4. 다음 시크릿들을 하나씩 추가:

### 필수 시크릿:
- **SMTP_SERVER**: `smtp.gmail.com` (Gmail 사용 시)
- **SMTP_PORT**: `587`
- **SMTP_USERNAME**: 본인의 Gmail 주소
- **SMTP_PASSWORD**: Gmail 앱 비밀번호 (아래 참조)
- **SENDER_EMAIL**: 발신자 이메일 (SMTP_USERNAME과 동일)

### Gmail 앱 비밀번호 생성:
1. https://myaccount.google.com/security 접속
2. "2단계 인증" 활성화 (필수)
3. https://myaccount.google.com/apppasswords 접속
4. "앱 선택" → "기타(맞춤 이름)" 선택
5. "RECODE WEEKLY" 입력
6. 생성된 16자리 비밀번호를 **SMTP_PASSWORD**에 사용

## 4. GitHub Pages 설정

1. Settings → Pages
2. Source: "Deploy from a branch" 선택
3. Branch: "gh-pages" 선택 (없으면 "None" 그대로 둠)
4. Save 클릭

## 5. 첫 실행

1. Actions 탭으로 이동
2. "RECODE WEEKLY 자동 생성 및 발송" 워크플로우 선택
3. "Run workflow" 버튼 클릭
4. "Run workflow" 확인

## 6. 확인사항

- Actions 탭에서 워크플로우 실행 상태 확인
- 이메일 수신 확인 (스팸함도 확인)
- gh-pages 브랜치 생성 확인

## 문제 해결

### "gh-pages" 브랜치가 없을 때:
첫 워크플로우 실행 시 자동 생성됩니다.

### 이메일이 오지 않을 때:
1. Actions 로그에서 오류 확인
2. Gmail 설정에서 "보안 수준이 낮은 앱" 허용 확인
3. 2단계 인증 및 앱 비밀번호 확인

### Permission 오류:
Settings → Actions → General → Workflow permissions에서
"Read and write permissions" 선택