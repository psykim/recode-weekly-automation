#!/usr/bin/env python3
"""
Impact Factor 정보를 수동으로 추가하는 간단한 도구
"""

import json
import os

def load_existing_factors():
    """기존 IF 데이터 로드"""
    if_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'impact_factors.json')
    if os.path.exists(if_file):
        with open(if_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    return {"impact_factors": {}, "last_updated": "", "notes": ""}

def save_factors(data):
    """IF 데이터 저장"""
    if_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'impact_factors.json')
    with open(if_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
    print(f"\n저장 완료: {if_file}")

def add_journal_variations(factors, journal_name, if_value):
    """저널명의 다양한 변형 추가"""
    # 기본 저널명
    factors[journal_name] = if_value
    
    # The 추가/제거
    if journal_name.startswith("The "):
        factors[journal_name[4:]] = if_value
    else:
        factors[f"The {journal_name}"] = if_value
    
    # 특별한 경우 처리
    if "Journal of" in journal_name:
        # J 약어 버전 추가
        abbreviated = journal_name.replace("Journal of", "J")
        factors[abbreviated] = if_value
    
    if "&" in journal_name:
        # & -> and 변환
        factors[journal_name.replace("&", "and")] = if_value
        factors[journal_name.replace(" & ", " and ")] = if_value

def main():
    print("=== Impact Factor 추가 도구 ===")
    print("PDF에서 확인한 IF 정보를 입력하세요.")
    print("형식: 저널명,IF값 (예: Nature Biotechnology,46.9)")
    print("종료하려면 빈 줄을 입력하세요.\n")
    
    # 기존 데이터 로드
    data = load_existing_factors()
    factors = data['impact_factors']
    
    print(f"현재 등록된 저널 수: {len(factors)}\n")
    
    added_count = 0
    
    while True:
        line = input("저널명,IF값: ").strip()
        if not line:
            break
        
        try:
            parts = line.split(',')
            if len(parts) >= 2:
                journal_name = ','.join(parts[:-1]).strip()  # 저널명에 쉼표가 있을 수 있음
                if_value = float(parts[-1].strip())
                
                # 다양한 변형 추가
                add_journal_variations(factors, journal_name, if_value)
                
                print(f"✓ 추가됨: {journal_name} = {if_value}")
                added_count += 1
            else:
                print("❌ 오류: 올바른 형식이 아닙니다.")
        except ValueError:
            print("❌ 오류: IF 값은 숫자여야 합니다.")
    
    if added_count > 0:
        # 날짜 업데이트
        from datetime import datetime
        data['last_updated'] = datetime.now().strftime("%Y-%m-%d")
        data['notes'] = f"Updated with {added_count} new journal(s) from PDF"
        
        # 저장
        save_factors(data)
        print(f"\n총 {added_count}개 저널이 추가되었습니다.")
        print(f"전체 저널 수: {len(factors)}")
        
        # 상위 10개 출력
        sorted_ifs = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n상위 10개 저널:")
        for journal, if_value in sorted_ifs:
            print(f"  {journal}: {if_value}")
    else:
        print("\n추가된 저널이 없습니다.")

if __name__ == "__main__":
    main()