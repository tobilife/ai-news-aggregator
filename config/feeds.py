# ai_news_aggregator/config/feeds.py

"""
AI 뉴스 RSS 피드 소스 및 관련 설정
"""

# AI 관련 뉴스 RSS 피드 URL 목록
AI_NEWS_RSS_FEEDS = {
    "Google AI Blog": "https://blog.research.google/feeds/posts/default/-/artificial%20intelligence",
    "MIT Technology Review (AI)": "https://www.technologyreview.com/c/artificial-intelligence/feed/",
    "VentureBeat AI": "https://feeds.feedburner.com/venturebeat/SZYF",
    "Ars Technica (AI)": "https://arstechnica.com/tag/ai/feed/",
    "IEEE Spectrum AI": "https://spectrum.ieee.org/topic/artificial-intelligence/feed/",
    "AI Trends": "https://aitrends.com/feed/",
    "Unite.AI": "https://www.unite.ai/feed/",
    "The AI Journal": "https://aijourn.com/feed/",
    "AI Business": "https://aibusiness.com/feed/",
    "Analytics Insight": "https://www.analyticsinsight.net/category/latest-news/artificial-intelligence/feed/",
    "KDnuggets": "https://www.kdnuggets.com/feed",
    "Towards Data Science": "https://towardsdatascience.com/feed",
    "Analytics Vidhya": "https://medium.com/feed/analytics-vidhya",
    "OpenAI Blog": "https://openai.com/blog/rss/",
    "DeepMind Blog": "https://deepmind.com/blog/feed/basic/",
}

# 특정 웹사이트의 짧은 이름 매핑 (원문 출처 표기용)
SOURCE_NAME_MAPPING = {
    "blog.research.google": "Google AI Blog",
    "www.technologyreview.com": "MIT Tech Review",
    "venturebeat.com": "VentureBeat",
    "arstechnica.com": "Ars Technica",
    "www.zdnet.com": "ZDNet",
    "www.anthropic.com": "Anthropic",
    "stability.ai": "Stability AI",
    "blog.google": "Google Blog",
    "spectrum.ieee.org": "IEEE Spectrum",
    "aitrends.com": "AI Trends",
    "www.unite.ai": "Unite.AI",
    "aijourn.com": "The AI Journal",
    "aibusiness.com": "AI Business",
    "www.analyticsinsight.net": "Analytics Insight",
    "www.kdnuggets.com": "KDnuggets",
    "towardsdatascience.com": "Towards Data Science",
    "medium.com": "Medium",
    "openai.com": "OpenAI",
    "deepmind.com": "DeepMind",
}

# 필터링할 키워드 목록 (제목에 이 키워드가 있는 뉴스만 포함)
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning", 
    "neural network", "nlp", "natural language", "computer vision",
    "ml", "generative ai", "llm", "gpt", "chatgpt", "gemini", "claude",
    "stable diffusion", "dall-e", "midjourney", "anthropic", "openai",
    "ml ops", "mlops", "rag", "retrieval", "embedding", "transformer",
    "fine-tuning", "fine tune", "inference", "data science", "prompt",
]

# 특정 단어를 포함하는 제목은 제외 (광고성 뉴스 등)
EXCLUDE_KEYWORDS = [
    "sponsor", "sponsored", "advertisement", "promoción", 
    "webinar", "register now", "limited time", "discount",
]