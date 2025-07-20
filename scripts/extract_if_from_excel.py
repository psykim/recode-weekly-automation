#!/usr/bin/env python3
"""
엑셀 파일에서 2024_IF 컬럼을 읽어 Impact Factor 정보를 추출하는 스크립트
"""

import json
import pandas as pd
import os
import sys

def clean_journal_name(name):
    """저널명 정규화"""
    if pd.isna(name):
        return None
    
    # 문자열로 변환하고 공백 정리
    name = str(name).strip()
    
    # 여러 공백을 하나로
    import re
    name = re.sub(r'\s+', ' ', name)
    
    # 특수문자 주변 공백 정리
    name = re.sub(r'\s*&\s*', ' & ', name)
    name = re.sub(r'\s*-\s*', '-', name)
    
    return name

def extract_if_from_excel(excel_file):
    """엑셀 파일에서 IF 정보 추출"""
    try:
        # 파일 확장자에 따라 다르게 읽기
        file_ext = os.path.splitext(excel_file)[1].lower()
        
        if file_ext == '.csv':
            print(f"CSV 파일 읽는 중: {excel_file}")
            df = pd.read_csv(excel_file)
        else:
            print(f"엑셀 파일 읽는 중: {excel_file}")
            # 먼저 시트 이름들을 확인
            excel = pd.ExcelFile(excel_file)
            print(f"시트 목록: {excel.sheet_names}")
            
            # 첫 번째 시트 읽기 (또는 특정 시트 지정 가능)
            df = pd.read_excel(excel_file, sheet_name=0)
        
        print(f"\n데이터 크기: {df.shape}")
        print(f"컬럼 목록: {list(df.columns)}")
        
        # 2024_IF 컬럼 찾기
        if_column = None
        journal_column = None
        
        # 가능한 IF 컬럼명들
        if_column_names = ['2024_IF', '2024 IF', 'IF_2024', 'IF 2024', 'Impact Factor 2024', 'IF', 'Impact Factor']
        # 가능한 저널명 컬럼들
        journal_column_names = ['Journal', 'Journal Name', 'Journal name', 'Title', 'Name', 'Abbreviation', 'Full Name']
        
        # IF 컬럼 찾기
        for col in df.columns:
            if any(name.lower() in col.lower() for name in if_column_names):
                if_column = col
                print(f"\nIF 컬럼 찾음: {col}")
                break
        
        # 저널명 컬럼 찾기
        for col in df.columns:
            if any(name.lower() in col.lower() for name in journal_column_names):
                journal_column = col
                print(f"저널명 컬럼 찾음: {col}")
                break
        
        if not if_column:
            print("\n❌ 오류: 2024_IF 또는 유사한 IF 컬럼을 찾을 수 없습니다.")
            print("첫 5행 미리보기:")
            print(df.head())
            return None
            
        if not journal_column:
            print("\n❌ 오류: 저널명 컬럼을 찾을 수 없습니다.")
            print("첫 5행 미리보기:")
            print(df.head())
            return None
        
        # IF 데이터 추출
        impact_factors = {}
        
        for idx, row in df.iterrows():
            journal_name = clean_journal_name(row[journal_column])
            if_value = row[if_column]
            
            # 유효한 데이터만 처리
            if journal_name and pd.notna(if_value):
                try:
                    if_value = float(if_value)
                    if if_value > 0:
                        impact_factors[journal_name] = if_value
                        
                        # 다양한 변형 추가
                        # The 추가/제거
                        if journal_name.startswith("The "):
                            impact_factors[journal_name[4:]] = if_value
                        else:
                            impact_factors[f"The {journal_name}"] = if_value
                        
                        # 약어가 있는 경우 처리
                        if 'Abbreviation' in df.columns:
                            abbrev = clean_journal_name(row.get('Abbreviation'))
                            if abbrev and abbrev != journal_name:
                                impact_factors[abbrev] = if_value
                except (ValueError, TypeError):
                    continue
        
        print(f"\n추출된 저널 수: {len(impact_factors)}")
        
        # 상위 10개 출력
        sorted_ifs = sorted(impact_factors.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n상위 10개 저널:")
        for journal, if_value in sorted_ifs:
            print(f"  {journal}: {if_value}")
        
        return impact_factors
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return None

def merge_with_existing(new_factors, existing_file):
    """기존 데이터와 병합"""
    try:
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_factors = existing_data.get('impact_factors', {})
    except:
        existing_data = {
            "impact_factors": {},
            "last_updated": "",
            "notes": ""
        }
        existing_factors = {}
    
    # 병합 (새 데이터가 우선)
    merged = existing_factors.copy()
    merged.update(new_factors)
    
    return merged, existing_data

def main():
    if len(sys.argv) < 2:
        print("사용법: python extract_if_from_excel.py <엑셀파일경로>")
        print("예시: python extract_if_from_excel.py data/journals_2024.xlsx")
        return
    
    excel_file = sys.argv[1]
    
    if not os.path.exists(excel_file):
        print(f"❌ 오류: 파일을 찾을 수 없습니다: {excel_file}")
        return
    
    # IF 정보 추출
    impact_factors = extract_if_from_excel(excel_file)
    
    if impact_factors:
        # 기존 데이터와 병합
        output_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'impact_factors.json')
        merged_factors, existing_data = merge_with_existing(impact_factors, output_file)
        
        # 업데이트된 데이터 저장
        from datetime import datetime
        output_data = {
            "impact_factors": merged_factors,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "notes": f"Updated from Excel file: {os.path.basename(excel_file)}"
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, sort_keys=False)
        
        print(f"\n✅ 업데이트 완료: {output_file}")
        print(f"전체 저널 수: {len(merged_factors)}")
        
        # 새로 추가된 저널 수 계산
        new_count = len(set(impact_factors.keys()) - set(existing_data.get('impact_factors', {}).keys()))
        print(f"새로 추가된 저널 수: {new_count}")

if __name__ == "__main__":
    main()