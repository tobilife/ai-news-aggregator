# ai_news_aggregator/main.py

"""
AI 뉴스 수집기 메인 실행 파일
"""

import asyncio
import argparse
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from config.feeds import AI_NEWS_RSS_FEEDS
from utils.fetch import fetch_all_feeds
from utils.parsing import process_feed_entries

# 로깅 설정
def setup_logging(log_level: str = "INFO") -> None:
    """
    로깅 설정 초기화
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 로그 디렉토리 생성
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # 로그 파일 경로
    log_file = os.path.join(logs_dir, f"ai_news_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # 본해쭈 3딹쫴 로그 설정(사용자가 지정한 수준으로)
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.WARNING)  # urllib3 로그는 언제나 WARNING 이상만 출력
    
    aiohttp_logger = logging.getLogger('aiohttp')
    aiohttp_logger.setLevel(logging.WARNING)  # aiohttp 로그는 언제나 WARNING 이상만 출력
    
    return logger

# 기본 로거 초기화
logger = setup_logging()

async def get_ai_news(max_items_per_feed: int = 5, total_max_items: int = 30, feed_urls: Optional[Dict[str, str]] = None) -> List[Dict]:
    """
    AI 관련 뉴스를 여러 RSS 피드에서 비동기적으로 가져옴
    
    Args:
        max_items_per_feed: 각 피드당 최대 항목 수
        total_max_items: 가져올 총 항목 수
        feed_urls: 사용할 피드 URL 목록 (지정하지 않으면 기본값 사용)
    
    Returns:
        List[Dict]: 가공된 뉴스 항목 목록
    """
    # 사용할 피드 URL 선택
    feeds_to_use = feed_urls if feed_urls is not None else AI_NEWS_RSS_FEEDS
    
    start_time = datetime.now()
    logger.info(f"Starting to fetch news from {len(feeds_to_use)} RSS feeds")
    
    # 모든 피드를 병렬로 가져오기
    feed_results = await fetch_all_feeds(feeds_to_use)
    
    # 요청 성공/실패 통계
    success_count = sum(1 for result in feed_results if not isinstance(result, Exception))
    logger.info(f"Successfully fetched {success_count}/{len(feeds_to_use)} feeds")
    
    # 피드 항목 처리 및 필터링
    news_items = await process_feed_entries(feed_results, max_items_per_feed, total_max_items)
    
    # 완료 시간 기록
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Fetched {len(news_items)} AI news items in {elapsed:.2f} seconds")
    
    return news_items

def format_news_output(news_items: List[Dict], output_format: str = "console", output_file: Optional[str] = None) -> str:
    """
    가져온 뉴스 항목을 지정된 형식으로 출력
    
    Args:
        news_items: 가공된 뉴스 항목 목록
        output_format: 출력 형식 (console, json, markdown)
        output_file: 출력을 저장할 파일 경로 (선택적)
    
    Returns:
        str: 포맷팅된 출력 내용
    """
    today = datetime.now().strftime("%Y년 %m월 %d일")
    
    if not news_items:
        output = f"{today} - 새로운 AI 뉴스를 가져오지 못했습니다."
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
        return output
    
    # 형식에 따른 출력 생성
    if output_format == "json":
        # JSON 형식으로 변환
        formatted_data = {
            "date": today,
            "count": len(news_items),
            "news": [{
                **item,
                # datetime 객체는 JSON으로 직접 직렬화할 수 없으므로 문자열로 변환
                "published_datetime": item["published_datetime"].isoformat() if item.get("published_datetime") else None
            } for item in news_items]
        }
        output = json.dumps(formatted_data, ensure_ascii=False, indent=2)
        
    elif output_format == "markdown":
        # 마크다운 형식으로 변환
        output = f"# {today} AI 뉴스 모음\n\n"
        output += f"총 {len(news_items)}개의 AI 뉴스\n\n"
        
        for idx, news in enumerate(news_items, 1):
            output += f"## {idx}. {news['title']}\n\n"
            
            # 한국어 요약이 있는 경우 포함
            if news.get("korean_summary"):
                output += f"> **한국어 요약:** {news['korean_summary']}\n\n"
                
            output += f"- **출처:** {news['source_name']}\n"
            output += f"- **원문 링크:** [{news['original_link']}]({news['original_link']})\n"
            
            # 게시일이 있는 경우 포함
            if news.get("published"):
                output += f"- **게시일:** {news.get('published')}\n"
                
            output += "\n---\n\n"
    
    else:  # 기본 콘솔 출력
        output = f"{today} AI 뉴스\n"
        output += "-" * 30 + "\n\n"
        output += f"총 {len(news_items)}개의 AI 뉴스를 가져왔습니다.\n\n"
        
        for idx, news in enumerate(news_items, 1):
            output += f"{idx}. {news['title']}\n"
            if news.get("korean_summary"):
                output += f"   한국어 요약: {news['korean_summary']}\n"
            output += f"   원문: {news['source_name']} - {news['original_link']}\n\n"
    
    # 파일로 출력
    if output_file:
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        logger.info(f"Output saved to {output_file}")
    
    # 콘솔에 출력
    if output_format == "console":
        print(output)
        
    return output

async def main():
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description="AI 뉴스 수집기")
    parser.add_argument("--max-per-feed", type=int, default=5, 
                        help="각 피드당 최대 뉴스 항목 수 (기본값: 5)")
    parser.add_argument("--max-total", type=int, default=30, 
                        help="가져올 총 뉴스 항목 수 (기본값: 30)")
    parser.add_argument("--output", type=str, choices=["console", "json", "markdown"], 
                        default="console", help="출력 형식 (기본값: console)")
    parser.add_argument("--file", type=str, 
                        help="출력을 저장할 파일 경로 (기본값: stdout)")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        default="INFO", help="로깅 레벨 (기본값: INFO)")
    parser.add_argument("--cache-dir", type=str,
                        help="캐시 디렉토리의 경로 (기본값: ./cache)")
    parser.add_argument("--feeds-file", type=str,
                        help="추가 RSS 피드를 포함한 JSON 파일")
    
    args = parser.parse_args()
    
    # 로깅 설정 초기화
    global logger
    logger = setup_logging(args.log_level)
    
    # 추가 RSS 피드 처리
    custom_feeds = {}
    if args.feeds_file and os.path.exists(args.feeds_file):
        try:
            with open(args.feeds_file, 'r', encoding='utf-8') as f:
                custom_feeds = json.load(f)
                logger.info(f"Loaded {len(custom_feeds)} custom feeds from {args.feeds_file}")
        except Exception as e:
            logger.error(f"Error loading feeds file: {e}")
    
    # 캐시 디렉토리 설정
    if args.cache_dir:
        from utils.fetch import CACHE_DIR
        CACHE_DIR = Path(args.cache_dir)
        logger.info(f"Set cache directory to {CACHE_DIR}")
    
    # 수집 시작 시간 기록
    start_time = datetime.now()
    
    # AI 뉴스 가져오기
    news_items = await get_ai_news(
        max_items_per_feed=args.max_per_feed,
        total_max_items=args.max_total,
        feed_urls={**AI_NEWS_RSS_FEEDS, **custom_feeds} if custom_feeds else None
    )
    
    # 실행 시간 기록
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Total execution time: {elapsed:.2f} seconds")
    
    # 뉴스 출력
    format_news_output(news_items, args.output, args.file)

if __name__ == "__main__":
    # Windows에서 실행할 때 이벤트 루프 정책 설정
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 비동기 메인 함수 실행
    asyncio.run(main())