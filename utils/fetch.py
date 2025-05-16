# ai_news_aggregator/utils/fetch.py

"""
비동기 HTTP 요청 및 RSS 피드 처리를 위한 유틸리티
"""

import asyncio
import aiohttp
import feedparser
import logging
import json
import os
from io import BytesIO
from typing import Dict, List, Optional, Set, Any, Tuple
from urllib.parse import urlparse
import hashlib
import time
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 캐시 설정
_cache: Dict[str, Dict[str, Any]] = {}
_cache_expiry: Dict[str, float] = {}
CACHE_DURATION = 1800  # 30분 (초 단위)

# 파일 캐시 디렉토리
CACHE_DIR = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache'))

# 최대 동시 요청 수 제한
MAX_CONCURRENT_REQUESTS = 10

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 1  # 재시도 사이의 대기 시간(초)

def _get_cache_key(url: str) -> str:
    """URL에 대한 캐시 키 생성"""
    return hashlib.md5(url.encode()).hexdigest()

def get_cached_response(url: str) -> Optional[Dict[str, Any]]:
    """캐시에서 응답 가져오기 (메모리 및 파일 캐시)"""
    key = _get_cache_key(url)
    now = time.time()
    
    # 1. 메모리 캐시 확인
    if key in _cache and _cache_expiry.get(key, 0) > now:
        logger.debug(f"Memory cache hit for {url}")
        return _cache[key]
    
    # 2. 파일 캐시 확인
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                if cache_data.get('expiry', 0) > now:
                    logger.debug(f"File cache hit for {url}")
                    # 메모리 캐시 업데이트
                    _cache[key] = cache_data['data']
                    _cache_expiry[key] = cache_data['expiry']
                    return cache_data['data']
        except Exception as e:
            logger.error(f"Error reading cache file for {url}: {e}")
    
    return None

def cache_response(url: str, data: Dict[str, Any]) -> None:
    """응답을 메모리 및 파일 캐시에 저장"""
    key = _get_cache_key(url)
    expiry = time.time() + CACHE_DURATION
    
    # 1. 메모리 캐시 업데이트
    _cache[key] = data
    _cache_expiry[key] = expiry
    
    # 2. 파일 캐시 업데이트
    try:
        # 캐시 디렉토리 확인 및 생성
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        cache_file = CACHE_DIR / f"{key}.json"
        cache_data = {
            'data': data,
            'expiry': expiry,
            'url': url
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, default=str)
            
        logger.debug(f"Cached response for {url} to file {cache_file}")
    except Exception as e:
        logger.error(f"Error writing cache file for {url}: {e}")

async def fetch_rss_feed(session: aiohttp.ClientSession, feed_url: str, feed_name: str, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """
    단일 RSS 피드를 비동기적으로 가져옴
    """
    # 캐시 확인
    cached_data = get_cached_response(feed_url)
    if cached_data:
        return cached_data
    
    try:
        # 세마포어를 사용하여 동시 요청 수 제한
        async with semaphore:
            retries = 0
            last_exception = None
            
            while retries <= MAX_RETRIES:
                try:
                    logger.info(f"Fetching feed: {feed_name} ({feed_url}) - Attempt {retries+1}/{MAX_RETRIES+1}")
                    
                    # TCP 연결 타임아웃과 전체 요청 타임아웃 설정
                    timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_connect=5, sock_read=10)
                    
                    async with session.get(feed_url, timeout=timeout, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }) as response:
                        if response.status != 200:
                            logger.warning(f"Error fetching {feed_name}: HTTP {response.status}")
                            last_exception = Exception(f"HTTP {response.status}")
                            retries += 1
                            if retries <= MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY * retries)  # 지수 백오프
                                continue
                            break
                        
                        content = await response.read()
                        
                        # BytesIO를 사용하여 feedparser에 전달
                        feed_data = feedparser.parse(BytesIO(content))
                        
                        # 비어있는 피드인지 확인
                        if not feed_data.entries and not getattr(feed_data, 'feed', None):
                            logger.warning(f"Empty or invalid feed: {feed_name}")
                            last_exception = Exception("Empty or invalid feed")
                            retries += 1
                            if retries <= MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY * retries)
                                continue
                            break
                        
                        result = {
                            "entries": feed_data.entries,
                            "name": feed_name,
                            "url": feed_url,
                            "feed_info": getattr(feed_data, 'feed', {})
                        }
                        
                        # 결과 캐싱
                        cache_response(feed_url, result)
                        
                        logger.info(f"Successfully fetched {feed_name}: {len(feed_data.entries)} entries")
                        return result
                        
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"Attempt {retries+1}/{MAX_RETRIES+1} failed for {feed_name}: {e}")
                    last_exception = e
                    retries += 1
                    if retries <= MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * retries)  # 지수 백오프
                    else:
                        break
                except Exception as e:
                    logger.error(f"Unexpected error fetching {feed_name}: {e}")
                    last_exception = e
                    break
            
            # 모든 시도 실패 시 빈 결과 반환
            logger.error(f"All attempts failed for {feed_name}, last error: {last_exception}")
            return {"entries": [], "name": feed_name, "url": feed_url}
            
    except Exception as e:
        logger.error(f"Exception fetching {feed_name} ({feed_url}): {e}")
        return {"entries": [], "name": feed_name, "url": feed_url}

async def fetch_all_feeds(feed_urls: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    모든 RSS 피드를 병렬로 가져옴 (동시 요청 수 제한 적용)
    """
    # 세마포어 생성 - 동시 요청 수 제한
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # TCP 커넥션 풀링과 DNS 캐싱 최적화된 세션 생성
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS,
        ttl_dns_cache=300,  # DNS 캐시 5분 유지
        ssl=False  # 필요한 경우 SSL 확인 비활성화
    )
    
    timeout = aiohttp.ClientTimeout(total=60)  # 전체 타임아웃 60초
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            fetch_rss_feed(session, url, name, semaphore) 
            for name, url in feed_urls.items()
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

async def fetch_page_content(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore = None) -> Optional[str]:
    """
    웹 페이지 컨텐츠를 비동기적으로 가져옴 (재시도 및 타임아웃 처리)
    """
    # 세마포어가 제공되지 않은 경우 새로 생성
    if semaphore is None:
        semaphore = asyncio.Semaphore(1)
    
    async with semaphore:
        retries = 0
        while retries <= MAX_RETRIES:
            try:
                timeout = aiohttp.ClientTimeout(total=15, connect=5)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
                
                async with session.get(url, timeout=timeout, headers=headers) as response:
                    if response.status != 200:
                        retries += 1
                        if retries <= MAX_RETRIES:
                            await asyncio.sleep(RETRY_DELAY * retries)
                            continue
                        return None
                    
                    # 먼저 인코딩 확인 시도
                    content_type = response.headers.get('Content-Type', '')
                    if 'charset=' in content_type:
                        encoding = content_type.split('charset=')[-1].strip()
                        try:
                            return await response.text(encoding=encoding)
                        except UnicodeDecodeError:
                            # 인코딩 실패 시 기본 인코딩 시도
                            pass
                    
                    # 기본 인코딩으로 시도
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Attempt {retries+1} failed for {url}: {e}")
                retries += 1
                if retries <= MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * retries)
                else:
                    logger.error(f"Failed to fetch page content from {url} after {MAX_RETRIES} retries: {e}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error fetching page content from {url}: {e}")
                return None
        
        return None