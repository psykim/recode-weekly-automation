#!/usr/bin/env python3
"""정기 발송 — 가장 최근 보고서(또는 REPORT_PATH / 인자)를 수신자 전원에게. 본문·수신자는 email_common.py."""

import os
import sys

from email_common import EmailSender, finish


def main():
    report_path = os.environ.get('REPORT_PATH') or (sys.argv[1] if len(sys.argv) >= 2 else None)
    if not report_path:
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        files = sorted((f for f in os.listdir(reports_dir) if f.endswith('.html')), reverse=True) \
            if os.path.exists(reports_dir) else []
        if files:
            report_path = os.path.join(reports_dir, files[0])
            print(f"최신 보고서 파일 사용: {report_path}")
    if not report_path or not os.path.exists(report_path):
        print(f"보고서 파일을 찾을 수 없습니다: {report_path}")
        sys.exit(1)
    finish(*EmailSender().send_to_all(report_path))


if __name__ == "__main__":
    main()
