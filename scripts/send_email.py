#!/usr/bin/env python3
"""
이메일 발송 스크립트
생성된 RECODE WEEKLY 보고서를 수신자들에게 이메일로 발송합니다.
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import sys

class EmailSender:
    def __init__(self):
        # 환경 변수에서 이메일 설정 읽기
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.sender_email = os.environ.get('SENDER_EMAIL')
        self.sender_name = os.environ.get('SENDER_NAME', 'RECODE WEEKLY')
        
        if not all([self.smtp_username, self.smtp_password, self.sender_email]):
            raise ValueError("이메일 설정이 누락되었습니다. 환경 변수를 확인해주세요.")
    
    def load_recipients(self) -> list:
        """수신자 목록 로드"""
        recipients_file = os.path.join(os.path.dirname(__file__), '..', 'database', 'recipients.json')
        
        if not os.path.exists(recipients_file):
            return []
        
        with open(recipients_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 활성화된 수신자만 반환
            return [r for r in data.get('recipients', []) if r.get('active', True)]
    
    def create_email_message(self, recipient: dict, report_path: str) -> MIMEMultipart:
        """이메일 메시지 생성"""
        msg = MIMEMultipart('alternative')
        
        # 이메일 헤더 설정
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = recipient['email']
        msg['Subject'] = f"RECODE WEEKLY - {datetime.now().strftime('%Y.%m.%d')} 주간 논문 리뷰"
        
        # 이메일 본문 (HTML)
        html_body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #1e3c72, #2a5298);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px;
                }}
                .content {{
                    padding: 30px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #2a5298;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    padding: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>RECODE WEEKLY</h1>
                    <p>분당서울대학교병원 치매극복연구센터 주간 논문 리뷰</p>
                </div>
                
                <div class="content">
                    <p>안녕하세요, {recipient.get('name', '구독자')}님</p>
                    
                    <p>이번 주 RECODE WEEKLY가 도착했습니다.</p>
                    
                    <p>최신 치매 연구 동향과 주요 논문들을 한눈에 확인하실 수 있습니다.</p>
                    
                    <center>
                        <a href="https://psykim.github.io/recode-weekly-web/" class="button">
                            온라인에서 보기
                        </a>
                    </center>
                    
                    <p>첨부된 HTML 파일로도 확인하실 수 있습니다.</p>
                    
                    <p>더 나은 서비스를 위해 항상 노력하겠습니다.</p>
                    
                    <p>감사합니다.</p>
                    
                    <p>
                    RECODE WEEKLY 팀 드림<br>
                    분당서울대학교병원 치매극복연구센터
                    </p>
                </div>
                
                <div class="footer">
                    <p>
                        이 이메일은 RECODE WEEKLY 구독자에게 발송되었습니다.<br>
                        구독 해지를 원하시면 <a href="mailto:recode@snubh.org">recode@snubh.org</a>로 문의해주세요.<br>
                        © 2025 분당서울대학교병원 치매극복연구센터
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 이메일 본문 (텍스트 - HTML을 지원하지 않는 클라이언트용)
        text_body = f"""
RECODE WEEKLY - {datetime.now().strftime('%Y.%m.%d')}

안녕하세요, {recipient.get('name', '구독자')}님

이번 주 RECODE WEEKLY가 도착했습니다.

최신 치매 연구 동향과 주요 논문들을 확인하시려면 
첨부된 HTML 파일을 열어보시거나 아래 링크를 방문해주세요:

https://psykim.github.io/recode-weekly-web/

감사합니다.

RECODE WEEKLY 팀 드림
분당서울대학교병원 치매극복연구센터

---
구독 해지: recode@snubh.org
"""
        
        # 본문 추가
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # HTML 보고서 파일 첨부
        if os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                attachment = MIMEBase('text', 'html')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="RECODE_WEEKLY_{datetime.now().strftime("%Y%m%d")}.html"'
                )
                msg.attach(attachment)
        
        return msg
    
    def send_email(self, recipient: dict, report_path: str) -> bool:
        """이메일 발송"""
        try:
            # 이메일 메시지 생성
            msg = self.create_email_message(recipient, report_path)
            
            # SMTP 서버 연결 및 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ 이메일 발송 성공: {recipient['email']}")
            return True
            
        except Exception as e:
            print(f"❌ 이메일 발송 실패 ({recipient['email']}): {str(e)}")
            return False
    
    def send_to_all(self, report_path: str):
        """모든 수신자에게 이메일 발송"""
        recipients = self.load_recipients()
        
        if not recipients:
            print("수신자가 없습니다.")
            return
        
        print(f"총 {len(recipients)}명의 수신자에게 이메일을 발송합니다.")
        
        success_count = 0
        for recipient in recipients:
            if self.send_email(recipient, report_path):
                success_count += 1
        
        print(f"\n발송 완료: {success_count}/{len(recipients)} 성공")


def main():
    if len(sys.argv) < 2:
        print("사용법: python send_email.py <report_file_path>")
        sys.exit(1)
    
    report_path = sys.argv[1]
    
    if not os.path.exists(report_path):
        print(f"보고서 파일을 찾을 수 없습니다: {report_path}")
        sys.exit(1)
    
    sender = EmailSender()
    sender.send_to_all(report_path)


if __name__ == "__main__":
    main()