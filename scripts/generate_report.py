#!/usr/bin/env python3
"""
RECODE WEEKLY 보고서 생성 스크립트
매주 금요일 새벽 0시에 실행되어 최신 논문 정보를 수집하고 HTML 보고서를 생성합니다.
"""

import os
import re
from html import escape
import json
import requests
from datetime import datetime
from typing import List, Dict
import time
# from google.cloud import translate_v2 as translate  # Removed - using requests directly
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class RecodeWeeklyGenerator:
    def __init__(self):
        self.current_date = datetime.now()
        self.report_date = self.current_date.strftime("%Y.%m.%d")
        self.file_timestamp = self.current_date.strftime("%Y%m%d_%H%M%S")
        self.impact_factors = self._load_impact_factors()   # 옛 이름 기반 표 — 이제 선별에는 쓰지 않는다
        self.jcr_issn = self._load_jcr_issn()
        
        # Google Translate API 초기화
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        if self.google_api_key:
            print("Google Translate API 키가 설정되었습니다.")
        else:
            print("Google API 키가 설정되지 않았습니다. 기본 번역을 사용합니다.")
    
    def _load_jcr_issn(self) -> Dict[str, float]:
        """JCR ISSN·eISSN → JIF 표 (scripts/build_jcr_issn.py 가 엑셀에서 만든다)"""
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'jcr2025_issn.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"JCR IF 표: {data.get('source')} · {len(data['issn'])}개 ISSN")
        return data['issn']

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
        
    # ── 검색·선별 기준 (2026-10-18 개정) ──────────────────────────────────────
    # 예전에는 꼬리표 없는 검색어(소속·초록 한 줄 언급까지 걸림) + 새로 들어온 순 100편만 + 저널 이름
    # 부분 일치 IF 라서 metalloprotease·spatial transcriptomics 같은 무관한 논문이 실렸다.
    SEARCH_TIAB = ['dementia', 'alzheimer*', '"cognitive impairment"', '"cognitive decline"',
                   '"cognitive dysfunction"', 'neurodegenerat*', 'frontotemporal', '"lewy body"',
                   'tauopath*', '"amyloid beta"', '"amyloid-beta"', '"mild cognitive"']
    SEARCH_MESH = ['"Dementia"[Mesh]', '"Cognitive Dysfunction"[Mesh]', '"Neurodegenerative Diseases"[Mesh]',
                   '"Amyloid beta-Peptides"[Mesh]', '"tau Proteins"[Mesh]']
    # 제목·저자 키워드·MeSH 중 하나에 있어야 싣는다(초록에서 지나가듯 언급한 논문은 뺀다). 범위: 치매·인지·신경퇴행
    RELEVANT = re.compile(r"dementi|alzheimer|cognit|neurodegenerat|amyloid[- ]?(beta|β)|\bAβ|\btau\b|tauopath|"
                          r"lewy|frontotemporal|mild cognitive|delirium|brain ag(e|ing)|synuclein|parkinson", re.I)
    MIN_IF = 10.0
    DETAILED = 20          # IF 상위 20편만 번역·요약, 나머지는 목록

    def _is_relevant(self, title: str, keywords: List[str], mesh: List[str]) -> bool:
        return any(self.RELEVANT.search(t) for t in [title, *keywords, *mesh])

    def _if_by_issn(self, issns: List[str]) -> float:
        return max([self.jcr_issn.get(x.strip().upper(), 0.0) for x in issns if x] + [0.0])

    def fetch_papers(self) -> List[Dict]:
        """
        PubMed 에서 최근 7일 치매·인지·신경퇴행 논문을 모두 찾아, 관련성·IF(JCR, ISSN 일치)로 거른다.
        IF 순 상위 DETAILED 편은 detailed=True(번역·요약), 나머지는 목록용.
        """
        from datetime import timedelta
        import xml.etree.ElementTree as ET

        end_date = self.current_date
        start_date = end_date - timedelta(days=7)
        window = f'("{start_date:%Y/%m/%d}"[PDAT]:"{end_date:%Y/%m/%d}"[PDAT])'
        query = '(' + ' OR '.join([t + '[tiab]' for t in self.SEARCH_TIAB] + self.SEARCH_MESH) + ') AND ' + window
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

        try:
            r = requests.get(base_url + "esearch.fcgi", timeout=60,
                             params=dict(db="pubmed", term=query, retmax=10000, retmode="json"))
            r.raise_for_status()
            id_list = r.json().get('esearchresult', {}).get('idlist', [])
        except Exception as e:
            raise RuntimeError(f"PubMed 검색 실패: {e}")      # 예전처럼 가짜 예시 논문으로 보고서를 만들지 않는다
        print(f"검색된 논문 수: {len(id_list)}")
        if not id_list:
            return []

        candidates = []
        n_irrelevant = n_low_if = 0
        for i in range(0, len(id_list), 200):
            r = requests.post(base_url + "efetch.fcgi", timeout=120,
                              data=dict(db="pubmed", id=",".join(id_list[i:i + 200]), retmode="xml"))
            r.raise_for_status()
            for article in ET.fromstring(r.content).findall('.//PubmedArticle'):
                try:
                    text = lambda el: "".join(el.itertext()).strip() if el is not None else ""
                    pmid = text(article.find('.//MedlineCitation/PMID'))
                    title = text(article.find('.//ArticleTitle')) or "제목 없음"
                    journal = text(article.find('.//Journal/Title')) or "Unknown Journal"
                    keywords = [text(k) for k in article.findall('.//KeywordList/Keyword')]
                    mesh = [text(m) for m in article.findall('.//MeshHeading/DescriptorName')]
                    ids = {x.get('IdType'): text(x) for x in article.findall('./PubmedData/ArticleIdList/ArticleId')}
                    # PMC 공개 예정일(엠바고면 미래 날짜) — 'YYYY-MM-DD'
                    rel = next((d for d in article.findall('./PubmedData/History/PubMedPubDate')
                                if d.get('PubStatus') == 'pmc-release'), None)
                    pmc_release = "-".join(f"{int(text(rel.find(k)) or 1):02d}" for k in ('Year', 'Month', 'Day')) if rel is not None else None
                    issns = [text(x) for x in article.findall('.//Journal/ISSN')] + \
                            [text(x) for x in article.findall('.//MedlineJournalInfo/ISSNLinking')]

                    if not self._is_relevant(title, keywords, mesh):
                        n_irrelevant += 1
                        continue
                    impact_factor = self._if_by_issn(issns)
                    if impact_factor < self.MIN_IF:
                        n_low_if += 1
                        continue

                    authors = []
                    for author in article.findall('.//AuthorList/Author'):
                        last, fore = author.find('LastName'), author.find('ForeName')
                        if last is not None:
                            authors.append(f"{fore.text} {last.text}" if fore is not None else last.text)
                    authors_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")

                    pub_date = article.find('.//Journal/JournalIssue/PubDate')
                    year = text(pub_date.find('Year')) if pub_date is not None and pub_date.find('Year') is not None \
                        else (text(pub_date.find('MedlineDate'))[:4] if pub_date is not None and pub_date.find('MedlineDate') is not None
                              else str(self.current_date.year))
                    abstract_text = " ".join(text(a) for a in article.findall('.//AbstractText') if text(a)) \
                        or "No abstract available"

                    candidates.append({
                        "title": title, "journal": journal, "impact_factor": impact_factor,
                        "authors": authors_str, "date": year, "abstract": abstract_text,
                        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
                        "pmid": pmid, "doi": ids.get('doi'), "pmcid": ids.get('pmc'), "pmc_release": pmc_release,
                    })
                except Exception as e:
                    print(f"논문 파싱 오류: {e}")
            time.sleep(0.4)   # NCBI: 키 없이 초당 3회 이하

        candidates.sort(key=lambda p: p['impact_factor'], reverse=True)
        print(f"관련 없음 {n_irrelevant}편 · IF {self.MIN_IF:g} 미만 {n_low_if}편 제외 → 게재 {len(candidates)}편 "
              f"(자세히 {min(len(candidates), self.DETAILED)} + 목록 {max(0, len(candidates) - self.DETAILED)})")

        self._attach_fulltext(candidates)

        # 번역은 자세히 볼 논문에만(번역 사용량을 예전 수준으로 유지)
        for idx, p in enumerate(candidates):
            p["detailed"] = idx < self.DETAILED
            if p["detailed"]:
                p["korean_title"] = self._translate_title(p["title"])
                p["korean_abstract"] = self._summarize_abstract(p["abstract"], p["impact_factor"])
        return candidates
    
    def _attach_fulltext(self, papers: List[Dict]) -> None:
        """원문 링크 — 무료(PMC 또는 OpenAlex oa_url)면 fulltext_url+is_oa, 아니면 출판사 DOI 페이지.

        OpenAlex 는 키 없이도 되지만 같은 IP 와 하루 예산을 나눠 쓰므로, OPENALEX_API_KEY(선택, GitHub Secret)가
        있으면 붙인다. 조회가 실패해도 보고서는 만들고 DOI 링크로 대신한다.
        """
        # PMC 번호가 있어도 엠바고(PubMed 의 pmc-release 가 미래)면 아직 못 연다
        today = self.current_date.strftime("%Y-%m-%d")
        embargoed = [p for p in papers if p.get("pmcid") and (p.get("pmc_release") or "") > today]
        for p in embargoed:
            p["pmcid"] = None
        if embargoed:
            print(f"PMC 엠바고 {len(embargoed)}편 — 공개 전이라 PMC 링크를 쓰지 않음")
        for p in papers:
            p["is_oa"] = bool(p.get("pmcid"))
            p["fulltext_url"] = (f"https://pmc.ncbi.nlm.nih.gov/articles/{p['pmcid']}/" if p.get("pmcid")
                                 else (f"https://doi.org/{p['doi']}" if p.get("doi") else None))
        todo = [p for p in papers if not p["is_oa"] and p.get("pmid")]
        found = 0
        for i in range(0, len(todo), 50):
            chunk = {p["pmid"]: p for p in todo[i:i + 50]}
            params = {"filter": "pmid:" + "|".join(chunk), "per-page": 50, "select": "ids,open_access"}
            if os.getenv("OPENALEX_API_KEY"):
                params["api_key"] = os.getenv("OPENALEX_API_KEY")
            try:
                r = requests.get("https://api.openalex.org/works", params=params, timeout=60)
                r.raise_for_status()
                for w in r.json().get("results", []):
                    pmid = (w.get("ids", {}).get("pmid") or "").rstrip("/").split("/")[-1]
                    oa = w.get("open_access") or {}
                    url = oa.get("oa_url") or ""
                    # PubMed 초록 페이지를 '무료 원문'으로 주는 경우가 있어 제외
                    if pmid in chunk and oa.get("is_oa") and url and "pubmed.ncbi.nlm.nih.gov" not in url:
                        chunk[pmid]["is_oa"], chunk[pmid]["fulltext_url"] = True, url
                        found += 1
            except Exception as e:
                print(f"OpenAlex 조회 실패 — 출판사 링크로 대신: {e}")
        print(f"무료 원문: {sum(p['is_oa'] for p in papers)}/{len(papers)}편 (PMC {sum(bool(p.get('pmcid')) for p in papers)}, OpenAlex {found})")

    def _links_html(self, p: Dict) -> str:
        """PubMed · 원문 링크를 나란히 (메일에서도 보이게 인라인 스타일)"""
        style = 'style="color: #2a5298; text-decoration: none;"'
        links = []
        if p.get("pubmed_url"):
            links.append(f'<a href="{p["pubmed_url"]}" target="_blank" {style}>📄 PubMed</a>')
        if p.get("fulltext_url"):
            label = "🔓 무료 원문" if p.get("is_oa") else "🔗 출판사 원문"
            links.append(f'<a href="{escape(p["fulltext_url"])}" target="_blank" {style}>{label}</a>')
        return " · ".join(links)

    def _translate_title(self, title: str) -> str:
        """논문 제목의 한글 번역"""
        if self.google_api_key:
            try:
                # Google Translate API v2 직접 호출
                url = f"https://translation.googleapis.com/language/translate/v2?key={self.google_api_key}"
                data = {
                    'q': title,
                    'target': 'ko',
                    'source': 'en',
                    'format': 'text'
                }
                
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    result = response.json()
                    translated_title = result['data']['translations'][0]['translatedText']
                    return translated_title
                else:
                    print(f"Google 제목 번역 오류: {response.status_code} - {response.text}")
                
            except Exception as e:
                print(f"Google 제목 번역 오류: {e}")
        
        # Google Translate 사용 불가 시 기본 키워드 번역
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
    
    def _summarize_abstract(self, abstract: str, impact_factor: float = 0.0) -> str:
        """초록의 한글 번역 - IF에 따라 전체/요약 번역"""
        if len(abstract) < 100:
            return "초록이 제공되지 않았습니다."
        
        if self.google_api_key:
            try:
                # High Impact 논문(IF > 30)은 전체 초록 번역
                if impact_factor > 30:
                    text_to_translate = abstract
                else:
                    # 나머지 논문들은 핵심 문장 요약 후 번역
                    sentences = abstract.split('. ')
                    # 첫 번째, 마지막, 그리고 "conclusion", "result" 등이 포함된 문장 선택
                    key_sentences = []
                    
                    # 첫 번째 문장 (연구 목적)
                    if sentences:
                        key_sentences.append(sentences[0])
                    
                    # 결과/결론 관련 문장 찾기
                    for sentence in sentences[1:]:
                        if any(keyword in sentence.lower() for keyword in 
                               ['result', 'conclusion', 'found', 'showed', 'demonstrated', 'significant']):
                            key_sentences.append(sentence)
                            break
                    
                    # 마지막 문장 (결론)
                    if len(sentences) > 1 and sentences[-1] not in key_sentences:
                        key_sentences.append(sentences[-1])
                    
                    text_to_translate = '. '.join(key_sentences[:3]) + '.'
                
                # Google Translate API v2 직접 호출
                url = f"https://translation.googleapis.com/language/translate/v2?key={self.google_api_key}"
                data = {
                    'q': text_to_translate,
                    'target': 'ko',
                    'source': 'en',
                    'format': 'text'
                }
                
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    result = response.json()
                    translated_text = result['data']['translations'][0]['translatedText']
                    
                    # High Impact가 아닌 논문에는 요약 표시 추가
                    if impact_factor <= 30:
                        translated_text += " (핵심 내용 요약)"
                    
                    return translated_text
                else:
                    print(f"Google 초록 번역 오류: {response.status_code} - {response.text}")
                
            except Exception as e:
                print(f"Google 초록 번역 오류: {e}")
        
        # Google Translate 사용 불가 시 기본 키워드 번역
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

    <section class="section">
        <h2 class="section-title">📚 그 밖의 논문 (IF 10 이상)</h2>
        {other_papers}
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
        # 자세히 볼 논문(IF 상위 DETAILED 편)만 High/주목 섹션에, 나머지는 '그 밖의 논문' 목록에
        detailed = [p for p in papers if p.get('detailed', True)]
        others = [p for p in papers if not p.get('detailed', True)]
        high_impact_papers = [p for p in detailed if p.get('impact_factor', 0) > 30]
        mid_impact_papers = [p for p in detailed if p.get('impact_factor', 0) <= 30]
        
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
            mid_impact_papers=self._format_papers(mid_impact_papers, 'mid'),
            other_papers=self._format_brief(others)
        )
        
        return html
    
    def _format_papers(self, papers: List[Dict], category: str) -> str:
        """논문 목록을 HTML로 변환"""
        if not papers:
            return '<p>이번 주에는 해당하는 논문이 없습니다.</p>'
        
        html = ''
        for idx, paper in enumerate(papers, 1):
            # PubMed 링크 생성
            links = self._links_html(paper)
            pubmed_link = f' | {links}' if links else ''
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
            </div>
            """
        
        return html
    
    def _format_brief(self, papers: List[Dict]) -> str:
        """'그 밖의 논문' — 번역 없이 제목·저널·IF·PubMed 링크만 (메일에서도 보이게 인라인 스타일)"""
        if not papers:
            return '<p>이번 주에는 해당하는 논문이 없습니다.</p>'
        items = []
        for p in papers:
            links = self._links_html(p)
            link = f' · {links}' if links else ''
            items.append(
                f'<li style="margin: 0 0 10px; line-height: 1.5;">{escape(p["title"])}<br>'
                f'<span style="color: #666; font-size: 13px;">{escape(p["journal"])} · IF {p["impact_factor"]:g}{link}</span></li>')
        return '<ol style="padding-left: 22px; margin: 0;">' + ''.join(items) + '</ol>'

    def save_report(self, html: str) -> str:
        """보고서를 파일로 저장"""
        filename = f"recode_weekly_{self.file_timestamp}.html"
        # 프로젝트 루트의 reports 폴더에 저장
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        filepath = os.path.join(reports_dir, filename)
        
        os.makedirs(reports_dir, exist_ok=True)
        
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