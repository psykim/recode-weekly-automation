#!/usr/bin/env python3
"""
대시보드에 보고서 목록을 자동으로 업데이트하는 스크립트
"""

import os
import json
from datetime import datetime

def get_report_files():
    """reports 폴더의 모든 보고서 파일 목록 가져오기"""
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    report_files = []
    
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.startswith('recode_weekly_') and filename.endswith('.html'):
                report_files.append(filename)
    
    return sorted(report_files, reverse=True)

def generate_reports_json():
    """보고서 목록을 JSON 파일로 생성"""
    report_files = get_report_files()
    reports = []
    
    for filename in report_files:
        # 파일명에서 날짜 추출
        try:
            date_str = filename.replace('recode_weekly_', '').replace('.html', '')
            date_part = date_str.split('_')[0]
            year = date_part[:4]
            month = date_part[4:6]
            day = date_part[6:8]
            
            reports.append({
                'filename': filename,
                'date': f"{year}-{month}-{day}",
                'title': f"RECODE WEEKLY {year}.{month}.{day}"
            })
        except:
            continue
    
    # JSON 파일로 저장
    json_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'reports.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'reports': reports}, f, ensure_ascii=False, indent=2)
    
    print(f"보고서 목록 생성 완료: {len(reports)}개")
    print(f"저장 위치: {json_path}")

if __name__ == "__main__":
    generate_reports_json()