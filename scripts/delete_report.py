#!/usr/bin/env python3
"""
보고서 삭제 스크립트
"""

import os
import sys
import json

def delete_report(filename):
    """보고서 파일 삭제 및 reports.json 업데이트"""
    # reports 디렉토리 경로
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    report_path = os.path.join(reports_dir, filename)
    
    # 파일 삭제
    if os.path.exists(report_path):
        os.remove(report_path)
        print(f"삭제됨: {report_path}")
    else:
        print(f"파일을 찾을 수 없음: {report_path}")
        return False
    
    # reports.json 업데이트
    json_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'reports.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 삭제된 파일 제거
        data['reports'] = [r for r in data['reports'] if r['filename'] != filename]
        
        # JSON 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"reports.json 업데이트 완료")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python delete_report.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    if delete_report(filename):
        print(f"보고서 '{filename}' 삭제 완료")
    else:
        print(f"보고서 '{filename}' 삭제 실패")
        sys.exit(1)