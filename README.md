# AI 뉴스 수집기 (AI News Aggregator)

AI 관련 최신 뉴스를 다양한 소스에서 자동으로 수집하고, 한국어로 번역 및 요약해주는 도구입니다.

## 주요 기능

- **다양한 소스에서 AI 뉴스 수집**: 15개 이상의 주요 AI 관련 뉴스 소스에서 최신 정보 수집
- **비동기 처리**: 빠른 처리 속도를 위한 `asyncio` 기반 병렬 수집
- **지능형 필터링**: AI 관련 컨텐츠 자동 필터링 및 우선순위 지정
- **한국어 번역 및 요약**: 영문 기사를 한국어로 번역하고 요약 (OpenAI API 사용)
- **다양한 출력 형식**: 콘솔, 마크다운, JSON 형식 지원
- **캐싱**: 중복 요청 방지를 위한 메모리 및 파일 기반 캐싱
- **사용자 정의 피드**: 추가 RSS 피드 설정 가능

## 설치 방법

### 필수 요구사항
- Python 3.8 이상
- 인터넷 연결

### 설치 과정

1. 저장소 복제:
```bash
git clone https://github.com/tobilife/ai-news-aggregator.git
cd ai-news-aggregator
```

2. 가상 환경 생성 및 활성화:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 사용 방법

### 기본 실행

```bash
python main.py
```

### 번역 및 요약 기능 설정

OpenAI API 키를 설정하여 번역 및 요약 기능을 활성화할 수 있습니다.
`utils/parsing.py` 파일에서 API 키를 설정하세요:

```python
# 번역 및 요약을 위한 API 키 설정
OPENAI_API_KEY = "your-api-key-here"
```

또는 환경 변수를 통해 설정할 수도 있습니다:

```bash
# Windows
set OPENAI_API_KEY=your-api-key-here
# macOS/Linux
export OPENAI_API_KEY=your-api-key-here
```

### 명령행 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--max-per-feed` | 각 피드당 최대 뉴스 항목 수 | 5 |
| `--max-total` | 가져올 총 뉴스 항목 수 | 30 |
| `--output` | 출력 형식 (console, json, markdown) | console |
| `--file` | 출력을 저장할 파일 경로 | - |
| `--log-level` | 로깅 레벨 (DEBUG, INFO, WARNING, ERROR) | INFO |
| `--cache-dir` | 캐시 디렉토리 경로 | ./cache |
| `--feeds-file` | 추가 RSS 피드를 포함한 JSON 파일 | - |

### 예제

```bash
# 피드당 3개, 총 20개 뉴스 가져오기
python main.py --max-per-feed 3 --max-total 20

# 마크다운 형식으로 파일 저장
python main.py --output markdown --file results/news.md

# JSON 형식으로 파일 저장
python main.py --output json --file results/news.json

# 디버그 모드로 실행
python main.py --log-level DEBUG

# 사용자 정의 피드 사용
python main.py --feeds-file custom_feeds.json
```

## 사용자 정의 RSS 피드

추가 RSS 피드를 사용하려면 JSON 형식 파일을 생성하세요:

```json
{
  "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
  "NVIDIA AI Blog": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
  "NAVER AI": "https://www.navercorp.com/navercorp/taxonomy/feed?tag=AI",
  "Samsung Research": "https://research.samsung.com/feed/blog",
  "AWS Machine Learning Blog": "https://aws.amazon.com/blogs/machine-learning/feed/"
}
```

## 프로젝트 구조

```
ai_news_aggregator/
├── config/
│   └── feeds.py        # RSS 피드 URL 및 설정
├── utils/
│   ├── __init__.py
│   ├── fetch.py        # 비동기 HTTP 요청 처리
│   └── parsing.py      # 데이터 파싱 및 번역/요약
├── cache/              # 캐시 디렉토리
├── logs/               # 로그 디렉토리
├── custom_feeds.json   # 사용자 정의 피드 예시
├── main.py             # 메인 실행 파일
├── README.md           # 이 문서
└── requirements.txt    # 의존성 패키지
```

## 성능 및 최적화

- **비동기 처리**: 여러 RSS 피드를 동시에 요청하여 처리 시간 단축
- **캐싱 메커니즘**: 중복 요청 방지를 위한 메모리 및 파일 기반 2단계 캐싱
- **오류 처리**: 개별 피드 실패가 전체 프로세스에 영향을 주지 않음
- **재시도 메커니즘**: 일시적인 네트워크 오류에 대처하기 위한 지수 백오프 재시도

## 의존성 패키지

- feedparser: RSS 피드 파싱
- aiohttp: 비동기 HTTP 요청
- beautifulsoup4: HTML 파싱
- python-dateutil: 날짜 파싱
- lxml: XML/HTML 파서

## 추가 개발 계획

- [ ] 웹 인터페이스 구현
- [ ] 주제별 뉴스 분류
- [ ] 이메일/메신저 알림 기능
- [ ] NLP 텍스트 분석 기능 강화
- [ ] 태그 클라우드 및 트렌드 분석

## 라이센스

MIT

## 기여 방법

1. 이 저장소를 포크합니다.
2. 기능 브랜치를 생성합니다: `git checkout -b new-feature`
3. 변경사항을 커밋합니다: `git commit -am 'Add new feature'`
4. 브랜치에 푸시합니다: `git push origin new-feature`
5. Pull Request를 제출합니다.

## 버그 신고 및 기능 요청
이슈 트래커를 통해 버그를 신고하거나 새로운 기능을 요청할 수 있습니다.
