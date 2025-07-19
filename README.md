# RECODE WEEKLY 자동화 시스템

매주 금요일 새벽 0시에 자동으로 RECODE WEEKLY 보고서를 생성하고 이메일로 발송하는 시스템입니다.

## 기능

- 매주 자동 보고서 생성
- 수신자 관리 (추가/삭제/수정)
- 이메일 자동 발송
- 웹 인터페이스를 통한 수신자 관리

## 구조

```
recode-weekly-automation/
├── scripts/
│   ├── generate_report.py      # 보고서 생성 스크립트
│   └── send_email.py           # 이메일 발송 스크립트
├── database/
│   └── recipients.json         # 수신자 데이터베이스
├── reports/                    # 생성된 보고서 저장
├── web/
│   └── manage_recipients.html  # 수신자 관리 페이지
└── .github/
    └── workflows/
        └── weekly_report.yml   # GitHub Actions 워크플로우
```

## 설정

1. GitHub Secrets에 이메일 인증 정보 추가
2. 수신자 정보 관리
3. GitHub Actions 활성화