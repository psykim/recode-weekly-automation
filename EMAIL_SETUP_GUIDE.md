# RECODE WEEKLY 이메일 발송 설정 가이드

## 🔧 Gmail 설정

### 1. Gmail 앱 비밀번호 생성

1. Google 계정 설정으로 이동: https://myaccount.google.com/
2. **보안** 탭 클릭
3. **2단계 인증** 활성화 (필수)
4. **앱 비밀번호** 생성
   - 앱 선택: "메일"
   - 기기 선택: "기타 (사용자 지정 이름)"
   - 이름 입력: "RECODE WEEKLY"
5. 생성된 **16자리 앱 비밀번호** 복사

### 2. GitHub Secrets 설정

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions**

다음 Secrets 추가:

```
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=generated-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=RECODE WEEKLY
```

## 📧 수신자 관리

### 1. 수신자 추가

1. 대시보드에서 **"👥 수신자 관리"** 클릭
2. **"새 수신자 추가"** 폼 작성:
   - 이름 (필수)
   - 이메일 (필수)
   - 소속, 부서 (선택)
   - 태그 (선택)

### 2. 수신자 관리

- **활성화/비활성화**: 일시적으로 발송 중단
- **삭제**: 영구 제거
- **검색**: 이름, 이메일, 소속으로 검색
- **내보내기/가져오기**: JSON 형태로 백업/복원

## 🚀 이메일 발송 방법

### 방법 1: 대시보드에서 발송

1. 대시보드 접속
2. **"📧 이메일 발송하기"** 버튼 클릭
3. 가장 최근 보고서가 자동으로 발송됨

### 방법 2: GitHub Actions에서 발송

1. GitHub 저장소 → **Actions** 탭
2. **"이메일 발송"** 워크플로우 선택
3. **"Run workflow"** 클릭

### 방법 3: 명령어로 발송

```bash
cd scripts
python send_email.py
```

## 📋 이메일 내용

발송되는 이메일에는 다음이 포함됩니다:

- **HTML 이메일**: 깔끔한 디자인의 안내 메일
- **텍스트 이메일**: HTML 미지원 클라이언트용
- **HTML 첨부파일**: 완전한 보고서
- **온라인 링크**: GitHub Pages 호스팅 버전

## 🔍 문제 해결

### 이메일 발송 실패

1. **Gmail 인증 실패**
   - 앱 비밀번호 재생성
   - 2단계 인증 확인
   - 계정 잠금 상태 확인

2. **수신자 없음**
   - recipients.json 파일 확인
   - 활성화된 수신자 존재 확인

3. **SMTP 연결 실패**
   - 네트워크 연결 확인
   - 방화벽 설정 확인

### 로그 확인

GitHub Actions에서 워크플로우 실행 로그를 확인하여 오류 원인 파악

## 🔒 보안 고려사항

1. **Gmail 앱 비밀번호**는 안전하게 보관
2. **GitHub Secrets**만 사용하여 인증 정보 관리
3. 개인 이메일은 절대 코드에 하드코딩하지 않음
4. 정기적으로 앱 비밀번호 갱신

## 📊 발송 통계

- 발송 성공/실패 개수
- 실패한 수신자 목록
- 발송 시간 기록

모든 정보는 GitHub Actions 로그에서 확인 가능합니다.