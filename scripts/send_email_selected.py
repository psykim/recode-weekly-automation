#!/usr/bin/env python3
"""골라 보내기 — REPORT_FILENAME(또는 인자)로 지정한 보고서를 수신자 전원에게. 본문·수신자는 email_common.py."""

import os
import sys

from email_common import EmailSender, finish


def main():
    name = os.environ.get('REPORT_FILENAME') or (sys.argv[1] if len(sys.argv) >= 2 else None)
    if not name:
        print("보고서 파일명을 지정해주세요. 사용법: python send_email_selected.py <report_filename>")
        sys.exit(1)
    report_path = os.path.join(os.path.dirname(__file__), '..', 'reports', name)
    if not os.path.exists(report_path):
        print(f"보고서 파일을 찾을 수 없습니다: {name}")
        sys.exit(1)
    finish(*EmailSender().send_to_all(report_path))


if __name__ == "__main__":
    main()
