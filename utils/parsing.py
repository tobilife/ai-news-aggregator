# ai_news_aggregator/utils/parsing.py

"""
뉴스 항목 파싱 및 처리를 위한 유틸리티
"""

import hashlib
import logging
import re
import json
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from collections import Counter
import time
from functools import lru_cache
import aiohttp
import asyncio

# 상대 경로 임포트 사용
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.feeds import SOURCE_NAME_MAPPING, AI_KEYWORDS, EXCLUDE_KEYWORDS

# 로깅 설정
logger = logging.getLogger(__name__)

# 번역 및 요약을 위한 API 키 설정 (실제 사용시 환경변수나 설정 파일로 관리 권장)
OPENAI_API_KEY = "" # 필요시 여기에 API 키 입력

# 번역 및 요약 모델 선택
MODEL_NAME = "gpt-3.5-turbo"
MAX_TOKENS = 150  # 요약 최대 길이

async def translate_and_summarize(text: str, session: Optional[aiohttp.ClientSession] = None) -> str:
    """
    텍스트를 한국어로 번역하고 요약
    
    Args:
        text: 요약할 원문 텍스트
        session: 재사용할 세션 (선택적)
    
    Returns:
        str: 한국어로 번역된 요약 또는 오류 메시지
    """
    if not text or len(text) < 50:
        return "요약할 충분한 내용이 없습니다."
    
    # API 키가 없는 경우 간단한 메시지 반환
    if not OPENAI_API_KEY:
        # 키가 없는 경우 단순히 길이를 줄여서 반환
        return f"이 기사는 약 {len(text)} 단어 분량입니다. API 키가 필요한 번역 요약 기능을 사용하려면 OPENAI_API_KEY를 설정하세요."
    
    # 너무 긴 텍스트는 잘라서 사용 (API 토큰 제한 고려)
    text = text[:4000] if len(text) > 4000 else text
    
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
    
    try:
        # OpenAI API 호출
        api_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "너는 영어 텍스트를 한국어로 번역하고 요약하는 전문가야. 핵심 내용을 놓치지 말고 3-4줄로 간결하게 요약해줘."},
                {"role": "user", "content": text}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3
        }
        
        async with session.post(api_url, headers=headers, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"API 호출 오류: {response.status}, {error_text}")
                return "API 오류로 요약을 생성할 수 없습니다."
            
            response_data = await response.json()
            summary = response_data["choices"][0]["message"]["content"].strip()
            return summary
            
    except Exception as e:
        logger.error(f"요약 생성 중 오류 발생: {e}")
        return "요약 생성 중 오류가 발생했습니다."
        
    finally:
        if close_session:
            await session.close()

def get_source_display_name(url: str) -> str:
    """URL에서 알아보기 쉬운 출처 이름을 반환합니다."""
    try:
        hostname = urlparse(url).hostname
        if hostname:
            for key, name in SOURCE_NAME_MAPPING.items():
                if key in hostname:
                    return name
            # 매핑에 없으면 호스트 이름에서 www. 등을 제거하고 반환
            return hostname.replace("www.", "").split('.')[0].capitalize()
    except Exception as e:
        logger.error(f"Error determining source name for {url}: {e}")
    return "Unknown Source"

async def fetch_article_content(url: str, session: aiohttp.ClientSession) -> str:
    """
    기사 URL에서 본문 내용 가져오기
    
    Args:
        url: 기사 URL
        session: HTTP 세션
        
    Returns:
        str: 추출된 기사 본문 또는 빈 문자열
    """
    try:
        # 타임아웃 설정
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        async with session.get(url, timeout=timeout, headers=headers) as response:
            if response.status != 200:
                return ""
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 필요없는 요소 제거
            for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                tag.decompose()
            
            # 본문 콘텐츠를 찾기 위한 일반적인 패턴 시도
            article_content = ""
            
            # 1. article 태그 시도
            article = soup.find('article')
            if article:
                article_content = article.get_text(strip=True)
            
            # 2. 메인 콘텐츠 영역 시도
            if not article_content or len(article_content) < 100:
                main = soup.find('main')
                if main:
                    article_content = main.get_text(strip=True)
            
            # 3. content, container 클래스 시도
            if not article_content or len(article_content) < 100:
                for div in soup.find_all('div', class_=lambda c: c and ('content' in c.lower() or 'article' in c.lower())):
                    text = div.get_text(strip=True)
                    if len(text) > len(article_content):
                        article_content = text
            
            # 4. 대안: 문단에서 가장 긴 텍스트 추출
            if not article_content or len(article_content) < 100:
                paragraphs = []
                for p in soup.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 40:  # 의미 있는 문단만 고려
                        paragraphs.append(text)
                
                if paragraphs:
                    article_content = ' '.join(paragraphs[:10])  # 처음 10개 문단만 사용
            
            # 5. 정리: 필수 공백만 남기기
            article_content = re.sub(r'\s+', ' ', article_content).strip()
            
            # 너무 짧으면 원문 요약 변환이 어려움
            if len(article_content) < 50:
                return ""
                
            return article_content[:8000]  # 최대 길이 제한
            
    except Exception as e:
        logger.error(f"기사 내용 가져오기 실패 ({url}): {e}")
        return ""

def extract_title_from_html(html_content: str) -> Optional[str]:
    """HTML 콘텐츠에서 제목을 추출합니다."""
    if not html_content:
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. OpenGraph 태그 확인
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        
        # 2. title 태그 확인
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        
        # 3. 가장 큰 h1 찾기
        h1 = soup.find('h1')
        if h1 and h1.get_text():
            return h1.get_text().strip()
    
    except Exception as e:
        logger.error(f"Error extracting title from HTML: {e}")
    
    return None

def get_article_relevance_score(title: str, content: Optional[str] = None) -> Tuple[bool, float]:
    """
    제목과 콘텐츠의 관련성을 점수로 분석하여 반환
    
    Args:
        title: 기사 제목
        content: 기사 콘텐츠 (선택적)
    
    Returns:
        Tuple[bool, float]: (관련성 여부, 관련성 점수 0.0-1.0)
    """
    if not title:
        return False, 0.0
    
    title_lower = title.lower()
    score = 0.0
    
    # 1. 제외 키워드 체크 (브레이크)
    if any(keyword.lower() in title_lower for keyword in EXCLUDE_KEYWORDS):
        return False, 0.0
    
    # 2. 제목에서 AI 키워드 체크
    title_keywords = [keyword for keyword in AI_KEYWORDS if keyword.lower() in title_lower]
    if title_keywords:
        # 최소한 하나의 키워드가 있으면 관련성 있음
        score += min(0.6, len(title_keywords) * 0.2)  # 최대 0.6
    
    # 3. 콘텐츠 분석 (제공된 경우)
    if content and len(content) > 100:  # 너무 짧은 콘텐츠는 무시
        content_lower = content.lower()
        content_keywords = [keyword for keyword in AI_KEYWORDS if keyword.lower() in content_lower]
        if content_keywords:
            # 콘텐츠에서도 키워드가 발견되면 추가 점수
            score += min(0.4, len(content_keywords) * 0.1)  # 최대 0.4
    
    # 제목에 키워드가 없지만 콘텐츠에 있는 경우 약한 관련성 인정
    is_relevant = score > 0.1  # 10% 이상의 관련성이 있어야 함
    
    return is_relevant, min(1.0, score)

def is_relevant_article(title: str, content: Optional[str] = None) -> bool:
    """제목이 AI 관련 키워드를 포함하고 있고 제외 키워드를 포함하지 않는지 확인"""
    is_relevant, _ = get_article_relevance_score(title, content)
    return is_relevant

@lru_cache(maxsize=1000)
def clean_title(title: str) -> str:
    """제목 정리: 불필요한 접두사, 접미사 제거 및 일반적인 문제 해결"""
    if not title:
        return ""
    
    # HTML 태그 제거
    title = re.sub(r'<[^>]+>', '', title)
    
    # 자주 보이는 접두어 제거 (예: "Breaking: ", "[Update] ")
    title = re.sub(r'^(Breaking|Update|News|Exclusive|Just In|Watch|Read)[:\s\-\[\]\|]+', '', title, flags=re.IGNORECASE)
    
    # 관련 없는 접미사 제거 (예: " - Read More")
    title = re.sub(r'\s*[\-\|]\s*(Read More|Subscribe|Full Article).*$', '', title, flags=re.IGNORECASE)
    
    # 공통 접미사 제거
    title = re.sub(r'\s*[\-\|]\s*(\w+\.com|\w+\.org)$', '', title, flags=re.IGNORECASE)
    
    # 특수 문자 및 프로그래밍 관련 문자 정리
    title = re.sub(r'\s*\{\{.*?\}\}\s*', ' ', title)  # Handlebars/template 문법 제거
    title = re.sub(r'\s*\$\{.*?\}\s*', ' ', title)      # JavaScript 템플릿 문법 제거
    
    # URL 기호 정리
    title = re.sub(r'%20', ' ', title)  # URL 인코딩 된 공백 치환
    title = re.sub(r'%\w{2}', '', title)  # 그 외 URL 인코딩 제거
    
    # 중복 공백 제거 및 앞뒤 공백 제거
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title

def extract_published_datetime(entry: Dict) -> Optional[datetime]:
    """
    피드 항목에서 게시 날짜/시간을 추출하여 datetime 객체로 반환
    """
    # 가능한 모든 게시 시간 필드 정의
    date_fields = [
        "published", "pubDate", "date", "updated", "created", 
        "lastBuildDate", "dc:date", "updatedDate"
    ]
    
    # 각 피드 순회하며 날짜 찾기
    for field in date_fields:
        date_str = entry.get(field, "")
        if date_str:
            try:
                # feedparser에서 이미 datetime 또는 struct_time으로 변환된 경우
                if hasattr(date_str, 'timetuple'):
                    return datetime.fromtimestamp(time.mktime(date_str.timetuple()))
                
                # 두 가지 일반적인 형식 시도
                for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"]:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        pass
                        
                # feedparser의 dateutil 사용
                try:
                    import dateutil.parser
                    return dateutil.parser.parse(date_str)
                except (ImportError, ValueError):
                    pass
                    
            except Exception as e:
                logger.debug(f"Failed to parse date {date_str}: {e}")
    
    # 날짜를 찾지 못한 경우 None 반환
    return None

def prioritize_articles(articles: List[Dict], max_items: int) -> List[Dict]:
    """
    기사의 연관성, 날짜, 원본, 중복성 등을 고려하여 후보 정렬
    """
    # 각 기사마다 점수 계산
    for article in articles:
        # 기본 점수
        score = 0.0
        
        # 1. 관련성 점수 (제목 기반)
        _, relevance_score = get_article_relevance_score(article["title"])
        score += relevance_score * 40  # 최대 40점
        
        # 2. 날짜 점수 - 최근 기사에 더 높은 점수
        if article.get("published_datetime"):
            age_hours = (datetime.now(timezone.utc) - article["published_datetime"]).total_seconds() / 3600
            if age_hours < 24:  # 24시간 이내
                score += max(0, 30 - age_hours/24*30)  # 최대 30점 (신규 기사)
            elif age_hours < 72:  # 3일 이내
                score += max(0, 15 - (age_hours-24)/48*15)  # 최대 15점
        
        # 3. 원본 소스 점수 - 원본에 가중치 적용
        source_name = article.get("source_name", "").lower()
        if any(trusted in source_name for trusted in [
            "google", "openai", "anthropic", "deepmind", "microsoft", "mit", "ieee", "arxiv"
        ]):
            score += 15  # 신뢰할 수 있는 소스에 가중치
        
        # 4. 중복화 및 유사성 점수 적용 (이미 점수에 반영됨)
        # 최종 점수 추가
        article["relevance_score"] = score
    
    # 점수를 기준으로 정렬
    sorted_articles = sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    # 전체 개수 제한 적용
    return sorted_articles[:max_items]

async def process_feed_entries(feed_results: List[Dict], max_items_per_feed: int, total_max_items: int) -> List[Dict]:
    """
    모든 피드의 항목을 처리하고 지정된 제한에 따라 뉴스 항목을 반환
    """
    # 세션 생성
    async with aiohttp.ClientSession() as session:
        # 요청에 실패한 피드 처리 (예외 객체가 반환된 경우)
        valid_feed_results = []
        for result in feed_results:
            if isinstance(result, Exception):
                logger.error(f"Feed fetch error: {result}")
                continue
            valid_feed_results.append(result)
        
        all_news_items = []
        title_fingerprints = set()  # 제목 유사성 중복 방지를 위한 집합
        processed_links = set()  # 정확한 URL 중복 방지를 위한 집합
        
        # 각 피드에서 항목 처리
        for feed_result in valid_feed_results:
            feed_name = feed_result["name"]
            items_from_feed = 0
            
            for entry in feed_result.get("entries", []):
                if items_from_feed >= max_items_per_feed:
                    break
                    
                # 링크 추출 및 중복 검사
                original_link = entry.get("link", "")
                if not original_link or original_link in processed_links:
                    continue
                
                # 제목 추출 및 정리
                title = clean_title(entry.get("title", ""))
                if not title or len(title) < 10:  # 너무 짧은 제목 무시
                    continue
                
                # 제목 지문 생성 (중복 검사용)
                title_fingerprint = hashlib.md5(title.lower()[:50].encode()).hexdigest()
                
                # 유사한 제목이 이미 있는지 확인
                if title_fingerprint in title_fingerprints:
                    continue
                    
                # 관련성 검사 (AI 관련 뉴스인지)
                summary = entry.get("summary", "") or entry.get("description", "")
                if not is_relevant_article(title, summary):
                    continue
                    
                # 소스 이름 생성
                source_display = get_source_display_name(original_link)
                
                # 게시 날짜 처리
                published_datetime = extract_published_datetime(entry)
                
                # 기사 본문 내용 가져오기
                article_content = await fetch_article_content(original_link, session)
                
                # 원문이 없으면 요약 부분 사용
                if not article_content and summary:
                    article_content = summary
                
                # 한글 요약 생성
                korean_summary = "요약 정보가 없습니다."
                if article_content:
                    korean_summary = await translate_and_summarize(article_content, session)
                    
                # 뉴스 항목 추가
                all_news_items.append({
                    "title": title,
                    "original_link": original_link,
                    "source_name": source_display,
                    "published": entry.get("published", entry.get("pubDate", "")),
                    "published_datetime": published_datetime,
                    "feed_name": feed_name,
                    "summary": summary[:500] if summary else "",  # 원본 요약은 500자로 제한
                    "korean_summary": korean_summary  # 한국어 요약 추가
                })
                
                # 처리된 항목 추적
                processed_links.add(original_link)
                title_fingerprints.add(title_fingerprint)
                items_from_feed += 1
        
        # 연관성, 날짜, 소스 등을 기준으로 항목 우선순위 지정
        prioritized_items = prioritize_articles(all_news_items, total_max_items)
        
        return prioritized_items