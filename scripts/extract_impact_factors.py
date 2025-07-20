#!/usr/bin/env python3
"""
PDF 파일에서 Impact Factor 정보를 추출하는 스크립트
"""

import json
import re
import sys

def extract_if_from_text(text):
    """텍스트에서 저널명과 IF 정보 추출"""
    impact_factors = {}
    
    # 일반적인 패턴: Journal Name ... 숫자.숫자
    # 예: Nature Medicine 58.7
    # 예: The Lancet 202.731
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # IF 값 찾기 (소수점이 있는 숫자)
        if_match = re.search(r'\b(\d+\.\d+)\b', line)
        if if_match:
            if_value = float(if_match.group(1))
            
            # IF 값 앞의 텍스트를 저널명으로 추정
            journal_part = line[:if_match.start()].strip()
            
            # 저널명 정리
            journal_name = re.sub(r'[\s\-]+', ' ', journal_part)
            journal_name = journal_name.strip(' -.,;:')
            
            if journal_name and if_value > 1.0:  # IF가 1.0 이상인 것만
                impact_factors[journal_name] = if_value
    
    return impact_factors

def process_pdf_text(pdf_text_file):
    """PDF에서 추출한 텍스트 파일 처리"""
    with open(pdf_text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    impact_factors = extract_if_from_text(text)
    
    # 결과를 JSON 파일로 저장
    output = {
        "impact_factors": impact_factors,
        "last_updated": "2025-07-20",
        "notes": "Extracted from PDF file"
    }
    
    output_file = 'data/impact_factors_extracted.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"추출된 저널 수: {len(impact_factors)}")
    print(f"저장 위치: {output_file}")
    
    # 상위 10개 출력
    sorted_ifs = sorted(impact_factors.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n상위 10개 저널:")
    for journal, if_value in sorted_ifs:
        print(f"  {journal}: {if_value}")

def manual_input():
    """수동으로 IF 정보 입력"""
    print("Impact Factor 정보를 수동으로 입력합니다.")
    print("형식: 저널명,IF값 (예: Nature Medicine,58.7)")
    print("입력을 마치려면 빈 줄을 입력하세요.\n")
    
    impact_factors = {}
    
    while True:
        line = input("저널명,IF값: ").strip()
        if not line:
            break
            
        try:
            parts = line.split(',')
            if len(parts) == 2:
                journal_name = parts[0].strip()
                if_value = float(parts[1].strip())
                impact_factors[journal_name] = if_value
                print(f"  추가됨: {journal_name} = {if_value}")
            else:
                print("  오류: 올바른 형식이 아닙니다.")
        except ValueError:
            print("  오류: IF 값은 숫자여야 합니다.")
    
    if impact_factors:
        # 기존 데이터 로드
        existing_file = 'data/impact_factors.json'
        try:
            with open(existing_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['impact_factors'].update(impact_factors)
        except:
            data = {
                "impact_factors": impact_factors,
                "last_updated": "2025-07-20",
                "notes": "Manually entered data"
            }
        
        # 저장
        with open(existing_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n{len(impact_factors)}개 저널 정보가 추가되었습니다.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # PDF 텍스트 파일 경로가 제공된 경우
        process_pdf_text(sys.argv[1])
    else:
        # 수동 입력 모드
        manual_input()