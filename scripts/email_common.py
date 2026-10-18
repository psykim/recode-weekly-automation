#!/usr/bin/env python3
"""RECODE WEEKLY 메일 — send_email.py(정기)·send_email_selected.py(골라 보내기)가 함께 쓴다.

본문 = 고정 소개 + 이번 호 에디터 노트(Gemini, 보고서 생성 때 만들어 보고서 HTML 의
<script id="recode-meta"> 에 넣어 둔다) + 하이라이트 3편 + 온라인 보기 단추. 보고서는 HTML 파일로 첨부.

수신자: GitHub Secret RECIPIENTS_JSON(비공개)이 있으면 그것만 쓴다. 저장소는 공개라
멤버 이메일을 database/recipients.json 에 넣으면 안 된다(2026-10-18).
형식: [{"name": "홍길동", "email": "a@b.c"}, ...] 또는 {"recipients": [...]}
"""

import json
import os
import re
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

PAGES = "https://psykim.github.io/recode-weekly-automation/reports/"
HOMEPAGE = "https://recode.re.kr"

INTRO = ("RECODE WEEKLY는 분당서울대학교병원 치매극복연구센터(RECODE)가 매주 금요일 보내드리는 논문 브리핑입니다. "
         "지난 한 주 PubMed에 실린 치매·인지·신경퇴행 연구 가운데 영향력지수(IF) 10 이상 학술지의 논문을 골라, "
         "주요 논문은 한글 번역·요약과 함께, 나머지는 목록으로 소개합니다.")


def mask(email: str) -> str:
    """Actions 로그는 공개 — 주소를 그대로 찍지 않는다 (ab***@gmail.com)"""
    user, _, dom = email.partition('@')
    return f"{user[:2]}***@{dom}"


def report_meta(report_path: str) -> dict:
    """보고서 HTML 안의 메타(에디터 노트·하이라이트). 예전 보고서에는 없다 → 빈 dict."""
    try:
        s = open(report_path, encoding="utf-8").read()
        m = re.search(r'<script type="application/json" id="recode-meta">(.*?)</script>', s, re.S)
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def report_date_of(report_path: str) -> str:
    m = re.search(r"recode_weekly_(\d{4})(\d{2})(\d{2})_", os.path.basename(report_path))
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else ""


class EmailSender:
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.sender_email = os.environ.get('SENDER_EMAIL')
        self.sender_name = os.environ.get('SENDER_NAME', 'RECODE WEEKLY')
        if not all([self.smtp_username, self.smtp_password, self.sender_email]):
            raise ValueError("이메일 설정이 누락되었습니다. 환경 변수를 확인해주세요.")

    def load_recipients(self) -> list:
        raw = os.environ.get('RECIPIENTS_JSON', '').strip()
        if raw:
            data = json.loads(raw)
            source = "RECIPIENTS_JSON(Secret)"
        else:
            path = os.path.join(os.path.dirname(__file__), '..', 'database', 'recipients.json')
            if not os.path.exists(path):
                return []
            data = json.load(open(path, encoding='utf-8'))
            source = "database/recipients.json"
        people = data.get('recipients', []) if isinstance(data, dict) else data
        people = [r for r in people if r.get('email') and r.get('active', True)]
        print(f"수신자 {len(people)}명 ({source})")
        return people

    def create_email_message(self, recipient: dict, report_path: str) -> MIMEMultipart:
        meta = report_meta(report_path)
        date = meta.get("date") or report_date_of(report_path)
        online = PAGES + os.path.basename(report_path)
        name = recipient.get('name') or '선생'
        note = meta.get("editor_note") or ""
        highlights = meta.get("highlights") or []

        msg = MIMEMultipart('mixed')
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = recipient['email']
        msg['Subject'] = f"RECODE WEEKLY {date} — 이번 주 치매·인지 연구 {meta.get('total', '')}{'편' if meta.get('total') else ''}".rstrip(" —")

        a = 'style="color:#2a5298;text-decoration:none;"'
        note_html = "".join(f'<p style="margin:0 0 12px;">{escape(p)}</p>' for p in note.split("\n") if p.strip())
        hl_html = "".join(
            f'<li style="margin:0 0 10px;"><strong>{escape(h.get("title_ko") or h["title"])}</strong><br>'
            f'<span style="color:#666;font-size:13px;">{escape(h["journal"])} · IF {h["if"]:g}'
            + (f' · <a href="{escape(h["pubmed"])}" {a}>PubMed</a>' if h.get("pubmed") else "")
            + (f' · <a href="{escape(h["fulltext"])}" {a}>{"무료 원문" if h.get("is_oa") else "출판사 원문"}</a>' if h.get("fulltext") else "")
            + '</span></li>' for h in highlights[:3])

        html_body = f"""<html><body style="margin:0;background:#f4f5f7;">
<div style="max-width:620px;margin:0 auto;padding:24px 16px;font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;color:#222;line-height:1.7;font-size:15px;">
  <div style="background:#1e3c72;color:#fff;padding:26px 24px;border-radius:10px;">
    <div style="font-size:12px;letter-spacing:2px;opacity:.8;">RESEARCH CENTER FOR OVERCOMING DEMENTIA</div>
    <div style="font-size:26px;font-weight:800;margin-top:4px;">RECODE WEEKLY</div>
    <div style="font-size:14px;opacity:.9;">{escape(date)} · 주간 논문 브리핑</div>
  </div>
  <div style="background:#fff;padding:24px;border-radius:10px;margin-top:12px;">
    <p style="margin:0 0 14px;">{escape(name)}님, 안녕하세요.</p>
    <p style="margin:0 0 14px;color:#555;font-size:14px;">{escape(INTRO)}</p>
    {f'<h3 style="margin:22px 0 10px;font-size:16px;color:#1e3c72;">✍️ 이번 호 에디터 노트</h3>{note_html}' if note_html else ''}
    {f'<h3 style="margin:22px 0 10px;font-size:16px;color:#1e3c72;">📌 이번 주 하이라이트</h3><ol style="padding-left:20px;margin:0;">{hl_html}</ol>' if hl_html else ''}
    <div style="text-align:center;margin:26px 0 8px;">
      <a href="{online}" style="display:inline-block;padding:12px 28px;background:#2a5298;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">이번 호 전체 보기</a>
    </div>
    <p style="margin:6px 0 0;text-align:center;color:#888;font-size:13px;">같은 내용을 첨부한 HTML 파일로도 보실 수 있습니다.</p>
  </div>
  <p style="text-align:center;color:#888;font-size:12px;margin:16px 0 0;">
    분당서울대학교병원 치매극복연구센터 · <a href="{HOMEPAGE}" style="color:#888;">recode.re.kr</a><br>
    수신을 원하지 않으시면 이 메일에 회신해 주세요.
  </p>
</div></body></html>"""

        text_body = "\n".join([
            f"RECODE WEEKLY {date}", "", f"{name}님, 안녕하세요.", "", INTRO, "",
            *(["[이번 호 에디터 노트]", note, ""] if note else []),
            *(["[이번 주 하이라이트]"] + [f"- {h.get('title_ko') or h['title']} ({h['journal']}, IF {h['if']:g})" for h in highlights[:3]] + [""] if highlights else []),
            f"이번 호 전체 보기: {online}", "", "분당서울대학교병원 치매극복연구센터 · recode.re.kr",
            "수신을 원하지 않으시면 이 메일에 회신해 주세요.",
        ])

        alt = MIMEMultipart('alternative')
        alt.attach(MIMEText(text_body, 'plain', 'utf-8'))
        alt.attach(MIMEText(html_body, 'html', 'utf-8'))
        msg.attach(alt)

        if os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                part = MIMEBase('text', 'html')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="RECODE_WEEKLY_{date.replace(".", "")}.html"')
            msg.attach(part)
        return msg

    def send_email(self, recipient: dict, report_path: str) -> bool:
        try:
            msg = self.create_email_message(recipient, report_path)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            print(f"✅ 이메일 발송 성공: {mask(recipient['email'])}")
            return True
        except Exception as e:
            print(f"❌ 이메일 발송 실패 ({mask(recipient['email'])}): {str(e).replace(recipient['email'], mask(recipient['email']))}")
            return False

    def send_to_all(self, report_path: str):
        recipients = self.load_recipients()
        if not recipients:
            print("수신자가 없습니다.")
            return 0, 0
        print(f"총 {len(recipients)}명의 수신자에게 이메일을 발송합니다.")
        ok = sum(self.send_email(r, report_path) for r in recipients)
        print(f"\n발송 완료: {ok}/{len(recipients)} 성공")
        return ok, len(recipients)


def finish(ok: int, total: int) -> None:
    """한 명이라도 못 받으면 Actions 단계를 실패로 끝낸다(2026-10-18)."""
    if ok < total:
        print(f"::error::이메일 발송 실패 {total - ok}/{total}건 — SMTP 설정(앱 비밀번호)을 확인하세요.")
        sys.exit(1)
