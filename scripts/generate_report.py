#!/usr/bin/env python3
"""
RECODE WEEKLY 보고서 생성 스크립트
매주 금요일 새벽 0시에 실행되어 최신 논문 정보를 수집하고 HTML 보고서를 생성합니다.
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict
import time
import deepl
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class RecodeWeeklyGenerator:
    def __init__(self):
        self.current_date = datetime.now()
        self.report_date = self.current_date.strftime("%Y.%m.%d")
        self.file_timestamp = self.current_date.strftime("%Y%m%d_%H%M%S")
        self.impact_factors = self._load_impact_factors()
        
        # DeepL 번역기 초기화
        api_key = os.getenv('DEEPL_API_KEY')
        if api_key and api_key != 'YOUR_API_KEY':
            try:
                self.translator = deepl.Translator(api_key)
                print("DeepL API 초기화 성공")
            except Exception as e:
                print(f"DeepL API 초기화 실패: {e}")
                self.translator = None
        else:
            print("DeepL API 키가 설정되지 않았습니다. 기본 번역을 사용합니다.")
            self.translator = None
    
    def _load_impact_factors(self) -> Dict[str, float]:
        """Impact Factor 데이터 로드"""
        if_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'impact_factors.json')
        
        if os.path.exists(if_file):
            try:
                with open(if_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('impact_factors', {})
            except Exception as e:
                print(f"Impact Factor 파일 로드 오류: {e}")
        
        # 파일이 없거나 오류 발생 시 기본값 반환
        return {
            "Nature": 64.8,
            "Science": 56.9,
            "Cell": 64.5,
            "Nature Medicine": 58.7,
            "Nature Neuroscience": 28.0,
            "Lancet": 202.7,
            "The Lancet Neurology": 44.2,
            "JAMA": 120.7,
            "JAMA Neurology": 29.9,
            "New England Journal of Medicine": 176.1,
            "Neuron": 18.7,
            "Brain": 15.3,
            "Alzheimer's & Dementia": 14.0
        }
        
    def fetch_papers(self) -> List[Dict]:
        """
        PubMed API를 사용하여 최근 1주일간의 치매 관련 논문 검색
        """
        import urllib.parse
        from datetime import timedelta
        
        # 검색 기간 설정 (지난 7일)
        end_date = self.current_date
        start_date = end_date - timedelta(days=7)
        
        # 날짜 포맷
        date_start = start_date.strftime("%Y/%m/%d")
        date_end = end_date.strftime("%Y/%m/%d")
        
        # 검색어 설정 - 치매 관련 주요 키워드
        search_terms = [
            "dementia",
            "Alzheimer's disease", 
            "cognitive impairment",
            "neurodegeneration",
            "tau protein",
            "amyloid beta",
            "cognitive decline",
            "frontotemporal dementia",
            "vascular dementia",
            "Lewy body dementia"
        ]
        
        # 주요 저널 필터
        major_journals = [
            "Nature",
            "Science", 
            "Cell",
            "Nature Medicine",
            "Nature Neuroscience",
            "Lancet",
            "Lancet Neurology",
            "JAMA",
            "JAMA Neurology",
            "New England Journal of Medicine",
            "Neuron",
            "Brain",
            "Alzheimer's & Dementia"
        ]
        
        # 검색 쿼리 구성 - 저널 필터 없이 더 넓게 검색
        search_query = f'({" OR ".join(search_terms)}) AND ("{date_start}"[PDAT]:"{date_end}"[PDAT])'
        
        # PubMed API 호출
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        # 1. 검색하여 논문 ID 목록 가져오기
        search_url = f"{base_url}esearch.fcgi?db=pubmed&term={urllib.parse.quote(search_query)}&retmax=100&retmode=json"
        
        try:
            response = requests.get(search_url)
            search_results = response.json()
            
            id_list = search_results.get('esearchresult', {}).get('idlist', [])
            
            if not id_list:
                print(f"검색 결과가 없습니다. 검색어: {search_query}")
                return []
            
            print(f"검색된 논문 수: {len(id_list)}")
            
            # 2. 논문 상세 정보 가져오기
            fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
            response = requests.get(fetch_url)
            
            # XML 파싱
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            papers = []
            for i, article in enumerate(root.findall('.//PubmedArticle')):
                try:
                    # PubMed ID
                    pmid = id_list[i] if i < len(id_list) else None
                    
                    # 제목
                    title = article.find('.//ArticleTitle').text or "제목 없음"
                    
                    # 저널명
                    journal = article.find('.//Journal/Title').text or "Unknown Journal"
                    
                    # 저자
                    authors = []
                    for author in article.findall('.//Author'):
                        last_name = author.find('LastName')
                        fore_name = author.find('ForeName')
                        if last_name is not None:
                            name = last_name.text
                            if fore_name is not None:
                                name = f"{fore_name.text} {name}"
                            authors.append(name)
                    authors_str = ", ".join(authors[:3])
                    if len(authors) > 3:
                        authors_str += " et al."
                    
                    # 출판일
                    pub_date = article.find('.//PubDate')
                    year = pub_date.find('Year').text if pub_date.find('Year') is not None else "2025"
                    
                    # 초록
                    abstract_parts = []
                    for abstract in article.findall('.//AbstractText'):
                        if abstract.text:
                            abstract_parts.append(abstract.text)
                    abstract_text = " ".join(abstract_parts) if abstract_parts else "No abstract available"
                    
                    # 저널명에서 IF 찾기
                    impact_factor = self._get_impact_factor(journal)
                    
                    # 한글 제목 (간단한 번역 - 실제로는 번역 API 사용)
                    korean_title = self._translate_title(title)
                    
                    # 한글 초록 (간단한 요약 - 실제로는 번역 API 사용)
                    korean_abstract = self._summarize_abstract(abstract_text)
                    
                    # 주요 저널만 포함 (Impact Factor 10 이상)
                    if impact_factor >= 10.0:
                        papers.append({
                            "title": title,
                            "korean_title": korean_title,
                            "journal": journal,
                            "impact_factor": impact_factor,
                            "authors": authors_str,
                            "date": year,
                            "korean_abstract": korean_abstract,
                            "english_abstract": abstract_text[:500] + "..." if len(abstract_text) > 500 else abstract_text,
                            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
                        })
                    
                except Exception as e:
                    print(f"논문 파싱 오류: {e}")
                    continue
            
            return papers
            
        except Exception as e:
            print(f"PubMed API 오류: {e}")
            # 오류 시 예시 데이터 반환
            return [
                {
                    "title": "Recent advances in Alzheimer's disease research",
                    "korean_title": "알츠하이머병 연구의 최근 진전",
                    "journal": "Nature Medicine",
                    "impact_factor": 58.7,
                    "authors": "Kim et al.",
                    "date": "2025",
                    "korean_abstract": "이 연구는 알츠하이머병의 새로운 치료 타겟을 발견했습니다...",
                    "english_abstract": "This study discovered new therapeutic targets for Alzheimer's disease..."
                }
            ]
    
    def _translate_title(self, title: str) -> str:
        """논문 제목의 한글 번역"""
        if self.translator:
            try:
                # DeepL API로 번역
                result = self.translator.translate_text(
                    title, 
                    source_lang="EN",
                    target_lang="KO"
                )
                translated_title = result.text
                
                # 번역 후처리 - 의학 용어 개선
                medical_terms = {
                    "알츠하이머 병": "알츠하이머병",
                    "치매 증": "치매",
                    "신경 퇴행성": "신경퇴행성",
                    "인지 기능": "인지기능",
                    "베타 아밀로이드": "베타-아밀로이드",
                    "타우 단백질": "타우 단백질",
                    "바이오 마커": "바이오마커"
                }
                
                for wrong_term, correct_term in medical_terms.items():
                    translated_title = translated_title.replace(wrong_term, correct_term)
                
                return translated_title
                
            except Exception as e:
                print(f"DeepL 제목 번역 오류: {e}")
        
        # DeepL 사용 불가 시 기본 키워드 번역
        translations = {
            "Alzheimer's disease": "알츠하이머병",
            "dementia": "치매",
            "cognitive": "인지",
            "impairment": "손상",
            "neurodegeneration": "신경퇴행",
            "tau": "타우",
            "amyloid": "아밀로이드",
            "treatment": "치료",
            "therapy": "치료법",
            "diagnosis": "진단",
            "biomarker": "바이오마커",
            "prevention": "예방"
        }
        
        korean_title = title
        for eng, kor in translations.items():
            korean_title = korean_title.replace(eng, kor)
        
        return korean_title
    
    def _get_impact_factor(self, journal_name: str) -> float:
        """저널명으로 Impact Factor 찾기"""
        # 1. 정확한 매칭 먼저 시도
        if journal_name in self.impact_factors:
            return self.impact_factors[journal_name]
        
        # 2. 대소문자 무시한 정확한 매칭
        journal_lower = journal_name.lower()
        for stored_journal, if_value in self.impact_factors.items():
            if stored_journal.lower() == journal_lower:
                return if_value
        
        # 3. The 추가/제거한 매칭
        if journal_name.startswith("The "):
            alt_name = journal_name[4:]
            if alt_name in self.impact_factors:
                return self.impact_factors[alt_name]
        else:
            alt_name = "The " + journal_name
            if alt_name in self.impact_factors:
                return self.impact_factors[alt_name]
        
        # 4. 약어 확장 매칭 (예: Nat Commun -> Nature Communications)
        abbreviation_map = {
            "Nat Commun": "Nature Communications",
            "Nat Med": "Nature Medicine", 
            "Nat Neurosci": "Nature Neuroscience",
            "Nat Genet": "Nature Genetics",
            "Nat Aging": "Nature Aging",
            "Sci Transl Med": "Science Translational Medicine",
            "Mol Psychiatry": "Molecular Psychiatry",
            "Biol Psychiatry": "Biological Psychiatry",
            "J Clin Invest": "Journal of Clinical Investigation",
            "Ann Neurol": "Annals of Neurology",
            "Mov Disord": "Movement Disorders",
            "J Neurosci": "Journal of Neuroscience",
            "Neurobiol Aging": "Neurobiology of Aging",
            "J Alzheimers Dis": "Journal of Alzheimer's Disease",
            "Front Aging Neurosci": "Frontiers in Aging Neuroscience",
            "Acta Neuropathol": "Acta Neuropathologica",
            "Proc Natl Acad Sci": "Proceedings of the National Academy of Sciences",
            "N Engl J Med": "New England Journal of Medicine",
            "Alzheimers Dement": "Alzheimer's & Dementia"
        }
        
        # 약어로 검색
        for abbrev, full_name in abbreviation_map.items():
            if abbrev.lower() in journal_lower:
                if full_name in self.impact_factors:
                    return self.impact_factors[full_name]
        
        # 5. 특수 케이스 처리 (더 구체적인 매칭)
        if "lancet" in journal_lower:
            if "neurology" in journal_lower:
                return self.impact_factors.get("The Lancet Neurology", self.impact_factors.get("Lancet Neurology", 44.2))
            elif "psychiatry" in journal_lower:
                return self.impact_factors.get("The Lancet Psychiatry", 30.0)  # 예시값
            else:
                return self.impact_factors.get("The Lancet", self.impact_factors.get("Lancet", 202.7))
        
        if ("new england" in journal_lower and "medicine" in journal_lower) or "nejm" in journal_lower:
            return self.impact_factors.get("New England Journal of Medicine", 176.1)
        
        if "alzheimer" in journal_lower and "dementia" in journal_lower:
            return self.impact_factors.get("Alzheimer's & Dementia", 14.0)
        
        # 6. 최후의 부분 매칭 (길이가 긴 것부터 매칭하여 더 구체적인 저널명 우선)
        matches = []
        for stored_journal, if_value in self.impact_factors.items():
            stored_lower = stored_journal.lower()
            # 전체 단어 단위로 매칭 (부분 문자열이 아닌)
            if all(word in journal_lower.split() for word in stored_lower.split()):
                matches.append((stored_journal, if_value, len(stored_journal)))
        
        # 가장 긴 매칭 선택
        if matches:
            matches.sort(key=lambda x: x[2], reverse=True)
            return matches[0][1]
        
        # 기본값 반환 (IF가 없는 저널)
        return 0.0  # 5.0 대신 0.0으로 변경하여 IF가 없는 저널 명확히 표시
    
    def _summarize_abstract(self, abstract: str) -> str:
        """초록의 한글 번역"""
        if len(abstract) < 100:
            return "초록이 제공되지 않았습니다."
        
        if self.translator:
            try:
                # 초록이 너무 길면 처음 500자만 번역 (비용 절약)
                text_to_translate = abstract[:500] if len(abstract) > 500 else abstract
                
                # DeepL API로 번역
                result = self.translator.translate_text(
                    text_to_translate,
                    source_lang="EN",
                    target_lang="KO"
                )
                translated_text = result.text
                
                # 번역 후처리 - 의학 용어 개선
                medical_terms = {
                    "알츠하이머 병": "알츠하이머병",
                    "치매 증": "치매",
                    "신경 퇴행성": "신경퇴행성",
                    "단일 클론": "단클론",
                    "베타 아밀로이드": "베타-아밀로이드",
                    "타우 단백질": "타우 단백질",
                    "인지 기능": "인지기능",
                    "신경 세포": "신경세포",
                    "미세 아교": "미세아교",
                    "혈액 뇌 장벽": "혈액-뇌 장벽",
                    "시냅스 가소성": "시냅스 가소성"
                }
                
                for wrong_term, correct_term in medical_terms.items():
                    translated_text = translated_text.replace(wrong_term, correct_term)
                
                # 길이 조정
                if len(abstract) > 500:
                    translated_text += "..."
                
                return translated_text
                
            except Exception as e:
                print(f"DeepL 초록 번역 오류: {e}")
        
        # DeepL 사용 불가 시 기본 키워드 번역
        sentences = abstract.split('. ')[:3]
        summary = ". ".join(sentences) + "..."
        
        basic_translations = {
            "Alzheimer's disease": "알츠하이머병",
            "dementia": "치매",
            "patients": "환자",
            "treatment": "치료",
            "cognitive": "인지",
            "memory": "기억력",
            "brain": "뇌",
            "study": "연구"
        }
        
        for eng, kor in basic_translations.items():
            summary = summary.replace(eng, kor)
        
        return summary
    
    def generate_html(self, papers: List[Dict]) -> str:
        """HTML 보고서 생성"""
        html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RECODE WEEKLY - {date}</title>
    <style>
        body {{
            font-family: -apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            line-height: 1.8;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            padding: 50px 40px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            position: relative;
            overflow: hidden;
            min-height: 220px;
        }}
        .logo-bg {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 650px;
            height: 240px;
            opacity: 0.15;
            pointer-events: none;
            z-index: 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 3.5em;
            font-weight: 900;
            letter-spacing: 3px;
            position: relative;
            z-index: 1;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            font-family: 'Arial Black', sans-serif;
        }}
        .header .subtitle {{
            font-size: 1.2em;
            margin-top: 10px;
            position: relative;
            z-index: 1;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .stat:hover {{
            transform: translateY(-5px);
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2a5298;
        }}
        .section {{
            margin: 40px 0;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #1e3c72;
            border-bottom: 3px solid #2a5298;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .paper {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .paper-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        .paper-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #1e3c72;
            margin: 0 0 10px 0;
        }}
        .korean-title {{
            color: #666;
            font-size: 1.1em;
            margin-bottom: 10px;
        }}
        .badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            white-space: nowrap;
        }}
        .if-badge {{
            background: #f0f8ff;
            color: #2a5298;
        }}
        .journal-badge {{
            background: #fff0f5;
            color: #d1208a;
        }}
        .meta-info {{
            font-size: 0.9em;
            color: #666;
            margin: 10px 0;
        }}
        .korean-abstract {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .korean-abstract h4 {{
            margin: 0 0 10px 0;
            color: #2a5298;
        }}
        .english-abstract {{
            background: #f0f4f8;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            font-size: 0.95em;
            line-height: 1.6;
        }}
        details {{
            margin-top: 15px;
        }}
        summary {{
            cursor: pointer;
            color: #2a5298;
            font-weight: bold;
            padding: 5px 0;
        }}
        summary:hover {{
            text-decoration: underline;
        }}
        .high-if {{
            border-left: 4px solid #ff6b6b;
        }}
        .mid-if {{
            border-left: 4px solid #4ecdc4;
        }}
        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #666;
            font-size: 0.9em;
            line-height: 1.6;
        }}
        .footer a {{
            color: #2a5298;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <svg class="logo-bg" viewBox="0 0 800 240" xmlns="http://www.w3.org/2000/svg">
            <!-- RECODE 로고 SVG -->
            <g transform="translate(0, -30)">
                <circle cx="80" cy="120" r="45" fill="white" opacity="0.3"/>
                <rect x="45" y="90" width="70" height="60" rx="10" fill="white" opacity="0.3"/>
                <circle cx="80" cy="100" r="15" fill="white" opacity="0.5"/>
                <circle cx="65" cy="125" r="8" fill="white" opacity="0.5"/>
                <circle cx="95" cy="125" r="8" fill="white" opacity="0.5"/>
                <path d="M60 140 Q80 150 100 140" stroke="white" stroke-width="3" fill="none" opacity="0.5"/>
            </g>
            
            <text x="400" y="170" font-family="Arial Black, sans-serif" font-size="85" font-weight="900" text-anchor="middle" fill="white" letter-spacing="-2">
                <tspan opacity="0.35">RE</tspan><tspan opacity="1">CO</tspan><tspan opacity="0.35">DE</tspan>
            </text>
            
            <g transform="translate(700, -30)">
                <rect x="0" y="85" width="50" height="70" rx="8" fill="white" opacity="0.3"/>
                <circle cx="25" cy="95" r="4" fill="white" opacity="0.5"/>
                <rect x="10" y="105" width="30" height="3" rx="1.5" fill="white" opacity="0.5"/>
                <rect x="10" y="115" width="30" height="3" rx="1.5" fill="white" opacity="0.5"/>
                <rect x="10" y="125" width="20" height="3" rx="1.5" fill="white" opacity="0.5"/>
                <rect x="10" y="135" width="25" height="3" rx="1.5" fill="white" opacity="0.5"/>
                <rect x="10" y="145" width="15" height="3" rx="1.5" fill="white" opacity="0.5"/>
            </g>
            
            <text x="400" y="250" font-family="Arial, sans-serif" font-size="20" text-anchor="middle" fill="white" letter-spacing="3" opacity="0.5" font-weight="600">
                RESEARCH CENTER FOR OVERCOMING DEMENTIA
            </text>
        </svg>
        <h1>RECODE WEEKLY</h1>
        <div class="subtitle">분당서울대학교병원 치매극복연구센터 | {date}</div>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="stat-number">{total_papers}</div>
            <div>이번 주 논문</div>
        </div>
        <div class="stat">
            <div class="stat-number">{high_impact}</div>
            <div>High Impact</div>
        </div>
        <div class="stat">
            <div class="stat-number">{mid_impact}</div>
            <div>주목할 논문</div>
        </div>
    </div>

    <section class="section">
        <h2 class="section-title">🔥 High Impact Papers (IF > 30)</h2>
        {high_impact_papers}
    </section>

    <section class="section">
        <h2 class="section-title">📊 주목할 만한 논문들</h2>
        {mid_impact_papers}
    </section>

    <div class="footer">
        <p>
            <strong>RECODE WEEKLY</strong><br>
            분당서울대학교병원 치매극복연구센터 주간 논문 리뷰<br>
            Research Center for Overcoming Dementia, Seoul National University Bundang Hospital<br>
            <br>
            📧 문의: recode@snubh.org | 🌐 https://recode.snubh.org<br>
            <br>
            <em>이 뉴스레터는 매주 금요일 발행됩니다.</em>
        </p>
    </div>
</body>
</html>"""
        
        # 논문 통계 계산
        high_impact_papers = [p for p in papers if p.get('impact_factor', 0) > 30]
        mid_impact_papers = [p for p in papers if 10 <= p.get('impact_factor', 0) <= 30]
        
        # IF 순으로 정렬 (높은 순)
        high_impact_papers.sort(key=lambda x: x.get('impact_factor', 0), reverse=True)
        mid_impact_papers.sort(key=lambda x: x.get('impact_factor', 0), reverse=True)
        
        # HTML 생성
        html = html_template.format(
            date=self.report_date,
            total_papers=len(papers),
            high_impact=len(high_impact_papers),
            mid_impact=len(mid_impact_papers),
            high_impact_papers=self._format_papers(high_impact_papers, 'high'),
            mid_impact_papers=self._format_papers(mid_impact_papers, 'mid')
        )
        
        return html
    
    def _format_papers(self, papers: List[Dict], category: str) -> str:
        """논문 목록을 HTML로 변환"""
        if not papers:
            return '<p>이번 주에는 해당하는 논문이 없습니다.</p>'
        
        html = ''
        for idx, paper in enumerate(papers, 1):
            # PubMed 링크 생성
            pubmed_link = ''
            if paper.get('pubmed_url'):
                pubmed_link = f' | <a href="{paper["pubmed_url"]}" target="_blank" style="color: #2a5298; text-decoration: none;">📄 PubMed 원문 보기</a>'
            
            html += f"""
            <div class="paper {category}-if">
                <div class="paper-header">
                    <div style="flex: 1;">
                        <h3 class="paper-title">{idx}. {paper['title']}</h3>
                        <div class="korean-title">→ {paper['korean_title']}</div>
                    </div>
                    <div class="badges">
                        <span class="badge if-badge">IF {paper['impact_factor']}</span>
                        <span class="badge journal-badge">{paper['journal']}</span>
                    </div>
                </div>
                <div class="meta-info">
                    {paper['authors']} ({paper['date']}){pubmed_link}
                </div>
                <div class="korean-abstract">
                    <h4>📝 한글 번역</h4>
                    <p>{paper['korean_abstract']}</p>
                </div>
                <details>
                    <summary>영문 초록 원문 보기 ▼</summary>
                    <div class="english-abstract">
                        <p>{paper['english_abstract']}</p>
                    </div>
                </details>
            </div>
            """
        
        return html
    
    def save_report(self, html: str) -> str:
        """보고서를 파일로 저장"""
        filename = f"recode_weekly_{self.file_timestamp}.html"
        filepath = os.path.join("reports", filename)
        
        os.makedirs("reports", exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return filepath
    
    def run(self):
        """메인 실행 함수"""
        print(f"RECODE WEEKLY 보고서 생성 시작 - {self.report_date}")
        
        # 1. 논문 데이터 수집
        print("논문 데이터 수집 중...")
        papers = self.fetch_papers()
        
        # 2. HTML 보고서 생성
        print("HTML 보고서 생성 중...")
        html = self.generate_html(papers)
        
        # 3. 파일 저장
        filepath = self.save_report(html)
        print(f"보고서 저장 완료: {filepath}")
        
        return filepath


if __name__ == "__main__":
    generator = RecodeWeeklyGenerator()
    report_path = generator.run()
    
    # 생성된 보고서 경로를 출력 (이메일 발송 스크립트에서 사용)
    print(f"REPORT_PATH={report_path}")