#!/usr/bin/env python3
"""
PDF 파일에서 직접 Impact Factor 정보를 추출하는 스크립트
"""

import json
import re
import PyPDF2
import os

def extract_text_from_pdf(pdf_path):
    """PDF 파일에서 텍스트 추출"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
                print(f"페이지 {page_num + 1} 처리 중...")
    except Exception as e:
        print(f"PDF 읽기 오류: {e}")
        return None
    return text

def extract_impact_factors(text):
    """텍스트에서 저널명과 IF 정보 추출"""
    impact_factors = {}
    
    # 다양한 패턴으로 IF 정보 찾기
    patterns = [
        # 패턴 1: Journal Name ... 숫자.숫자
        r'([A-Za-z][A-Za-z\s&\-\.]+?)\s+(\d{1,3}\.\d{1,3})',
        # 패턴 2: Journal Name (IF: 숫자.숫자)
        r'([A-Za-z][A-Za-z\s&\-\.]+?)\s*\(IF:\s*(\d{1,3}\.\d{1,3})\)',
        # 패턴 3: Journal Name Impact Factor: 숫자.숫자
        r'([A-Za-z][A-Za-z\s&\-\.]+?)\s*Impact Factor:\s*(\d{1,3}\.\d{1,3})',
    ]
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        for pattern in patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                journal_name = match[0].strip()
                try:
                    if_value = float(match[1])
                    
                    # 저널명 정리
                    journal_name = re.sub(r'\s+', ' ', journal_name)
                    journal_name = journal_name.strip(' -.,;:')
                    
                    # 유효한 저널명과 IF 값인지 확인
                    if (journal_name and 
                        len(journal_name) > 3 and 
                        if_value > 1.0 and 
                        if_value < 500 and  # 비정상적으로 높은 값 제외
                        not any(word in journal_name.lower() for word in ['page', 'table', 'figure', 'volume', 'issue', 'doi'])):
                        
                        # 기존 값이 없거나 더 높은 값인 경우 업데이트
                        if journal_name not in impact_factors or impact_factors[journal_name] < if_value:
                            impact_factors[journal_name] = if_value
                            print(f"찾음: {journal_name} = {if_value}")
                except ValueError:
                    continue
    
    return impact_factors

def merge_with_existing(new_factors, existing_file):
    """기존 데이터와 병합"""
    try:
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_factors = existing_data.get('impact_factors', {})
    except:
        existing_factors = {}
    
    # 병합 (새 데이터가 우선)
    merged = existing_factors.copy()
    
    # 저널명 정규화를 위한 매핑
    name_mappings = {
        'Lancet': ['The Lancet', 'Lancet'],
        'Nature Med': ['Nature Medicine'],
        'Nat Med': ['Nature Medicine'],
        'NEJM': ['New England Journal of Medicine', 'The New England Journal of Medicine'],
        'N Engl J Med': ['New England Journal of Medicine', 'The New England Journal of Medicine'],
        'Alzheimers Dement': ['Alzheimer\'s & Dementia', 'Alzheimers & Dementia'],
        'Proc Natl Acad Sci': ['Proceedings of the National Academy of Sciences', 'PNAS'],
        'Nat Neurosci': ['Nature Neuroscience'],
        'Nat Commun': ['Nature Communications'],
        'Sci Transl Med': ['Science Translational Medicine'],
        'Mol Psychiatry': ['Molecular Psychiatry'],
        'Biol Psychiatry': ['Biological Psychiatry'],
        'J Clin Invest': ['Journal of Clinical Investigation'],
        'Ann Neurol': ['Annals of Neurology'],
        'Mov Disord': ['Movement Disorders'],
        'J Neurosci': ['Journal of Neuroscience'],
        'Neurobiol Aging': ['Neurobiology of Aging'],
        'J Alzheimers Dis': ['Journal of Alzheimer\'s Disease'],
        'Front Aging Neurosci': ['Frontiers in Aging Neuroscience'],
        'Acta Neuropathol': ['Acta Neuropathologica'],
        'Nat Genet': ['Nature Genetics'],
        'Nat Aging': ['Nature Aging']
    }
    
    # 새로운 데이터 추가
    for journal, if_value in new_factors.items():
        # 약어 확장
        expanded = False
        for abbrev, full_names in name_mappings.items():
            if abbrev.lower() in journal.lower():
                for full_name in full_names:
                    merged[full_name] = if_value
                expanded = True
                break
        
        if not expanded:
            merged[journal] = if_value
            # 일반적인 변형도 추가
            if journal.startswith('The '):
                merged[journal[4:]] = if_value
            elif not journal.startswith('The '):
                merged[f'The {journal}'] = if_value
    
    return merged

def main():
    pdf_path = '/Users/kwk/development/recode-weekly-automation/data/JCR2025_202506.pdf'
    output_file = '/Users/kwk/development/recode-weekly-automation/data/impact_factors.json'
    
    print(f"PDF 파일 처리 중: {pdf_path}")
    
    # PDF에서 텍스트 추출
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("PDF에서 텍스트를 추출할 수 없습니다.")
        return
    
    print(f"\n추출된 텍스트 길이: {len(text)} 문자")
    
    # 샘플 출력
    print("\n--- 텍스트 샘플 (첫 500자) ---")
    print(text[:500])
    print("--- 샘플 끝 ---\n")
    
    # IF 정보 추출
    impact_factors = extract_impact_factors(text)
    print(f"\n추출된 저널 수: {len(impact_factors)}")
    
    if impact_factors:
        # 기존 데이터와 병합
        merged_factors = merge_with_existing(impact_factors, output_file)
        
        # 저장
        output_data = {
            "impact_factors": merged_factors,
            "last_updated": "2025-07-20",
            "notes": "Updated with data from JCR2025_202506.pdf"
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, sort_keys=True)
        
        print(f"\n업데이트 완료: {output_file}")
        print(f"전체 저널 수: {len(merged_factors)}")
        
        # 상위 20개 출력
        sorted_ifs = sorted(impact_factors.items(), key=lambda x: x[1], reverse=True)[:20]
        print("\n추출된 상위 20개 저널:")
        for journal, if_value in sorted_ifs:
            print(f"  {journal}: {if_value}")
    else:
        print("IF 정보를 찾을 수 없습니다.")
        print("PDF 파일 형식을 확인해주세요.")

if __name__ == "__main__":
    main()