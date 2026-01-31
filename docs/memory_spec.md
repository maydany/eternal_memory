# Eternal Memory 시스템 사양서

**Document Version:** 2.0.0  
**Last Updated:** 2026-01-31  
**Status:** Implementation Complete

## 1. 서론

### 1.1 프로젝트 개요

**Eternal Memory**는 로컬 우선(Local-First) AI 에이전트를 위한 영구적 기억 시스템입니다. 이 시스템은 사용자와의 모든 상호작용을 구조화된 지식으로 변환하고, PostgreSQL + pgvector 기반의 벡터 데이터베이스와 인간이 읽을 수 있는 Markdown 파일 시스템을 하이브리드로 운용하여 지속성(Persistence)과 투명성(Transparency)을 동시에 제공합니다.

### 1.2 핵심 철학

Eternal Memory 시스템은 다음 세 가지 핵심 원칙을 기반으로 설계되었습니다:

1. **영구성 (Persistence)**: 세션이 종료되어도 모든 기억은 영구적으로 보존됩니다. 사용자와의 대화, 학습한 선호도, 맥락 정보가 데이터베이스와 Markdown 파일에 이중으로 저장됩니다.

2. **능동성 (Proactivity)**: 사용자가 요청하기 전에 상황에 맞는 문맥을 선제적으로 로딩합니다. 시간대, 최근 활동 패턴, 카테고리 접근 빈도를 분석하여 다음 의도를 예측합니다.

3. **투명성 (Transparency)**: 모든 기억 데이터는 사용자가 읽고 수정할 수 있는 Markdown 파일로 미러링됩니다. AI의 환각(Hallucination)을 사용자가 직접 교정할 수 있습니다.

### 1.3 기술 스택

- **Backend**: Python 3.11+ (AsyncIO 기반)
- **Database**: PostgreSQL 14+ with pgvector extension
- **Vector Search**: pgvector (HNSW indexing)
- **API Framework**: FastAPI 0.104+
- **LLM Integration**: OpenAI GPT-4o-mini (기본), text-embedding-ada-002
- **Storage**: Dual-layer (PostgreSQL + Markdown Vault)
- **Scheduling**: Custom AsyncIO Cron Scheduler

## 2. 시스템 아키텍처

### 2.1 전체 구조 개요

Eternal Memory 시스템은 계층화된 아키텍처로 구성되어 있습니다:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│                  /memories, /stats, /jobs                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Memory Engine (EternalMemorySystem)            │
│  Orchestrates all components, manages lifecycle, buffer     │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌──────▼──────┐  ┌───────▼────────┐
│  4 Pipelines  │  │  Repository │  │ Markdown Vault │
│               │  │   (CRUD)    │  │ (Human Layer)  │
│ - Memorize    │  │             │  │                │
│ - Retrieve    │  │             │  │                │
│ - Predict     │  │             │  │                │
│ - Consolidate │  │             │  │                │
└───────┬───────┘  └──────┬──────┘  └───────┬────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│   PostgreSQL   │  │ LLM Client  │  │  Cron Jobs     │
│   + pgvector   │  │   (OpenAI)  │  │  (Scheduler)   │
└────────────────┘  └─────────────┘  └────────────────┘
```

### 2.2 핵심 컴포넌트

#### 2.2.1 메모리 엔진 (EternalMemorySystem)

시스템의 중앙 컨트롤러로, 모든 파이프라인과 컴포넌트를 통합합니다.

**주요 기능:**
- 초기화 및 연결 관리
- 대화 버퍼 관리 (in-memory buffer)
- 파이프라인 오케스트레이션
- 데이터베이스 및 Vault 동기화

#### 2.2.2 계층적 데이터 모델

시스템은 3계층 구조로 데이터를 관리합니다:

1. **Resource (리소스)**: 원시 데이터 소스
   - 대화 로그, PDF 문서 등 원본 자료
   - 출처 추적(Traceability) 제공

2. **MemoryItem (메모리 아이템)**: 추출된 사실
   - LLM이 리소스에서 추출한 구조화된 정보
   - 벡터 임베딩, 중요도, 신뢰도 포함

3. **Category (카테고리)**: 의미적 클러스터
   - 아이템들을 주제별로 그룹화
   - 계층적 경로 (예: `knowledge/coding/python`)
   - 자동 요약 생성

#### 2.2.3 이중 저장 레이어

모든 기억은 두 곳에 동시 저장됩니다:

**Machine Layer (PostgreSQL + pgvector)**
- 고속 벡터 검색 (HNSW 인덱스)
- 하이브리드 검색 (벡터 + 키워드)
- 트랜잭션 지원

**Human Layer (Markdown Vault)**
- `user_memory/markdown/` 디렉토리
- 사람이 읽고 편집 가능
- Timeline (시간순) + Knowledge (주제별) 구조

## 3. 프로젝트 구조

### 3.1 디렉토리 레이아웃

```
eternal_memory/
├── docs/                             # 설계 문서
│   ├── memory_spec.md                # 본 문서
│   └── ui_spec.md
│
├── scripts/                          # 유틸리티 스크립트
│   ├── install.sh
│   └── setup_db.sh
│
├── setting/                          # 프로젝트 설정
│   └── .env                          # OPENAI_API_KEY (gitignore)
│
├── src/eternal_memory/              # 소스 코드
│   ├── __init__.py
│   ├── config.py                     # 설정 관리
│   │
│   ├── api/                          # FastAPI 라우트
│   │   ├── main.py
│   │   └── routes/
│   │       ├── memories.py
│   │       ├── stats.py
│   │       ├── jobs.py
│   │       └── ...
│   │
│   ├── database/                     # 데이터베이스 레이어
│   │   ├── schema.py                 # PostgreSQL 스키마
│   │   └── repository.py             # CRUD 연산
│   │
│   ├── engine/                       # 메모리 엔진
│   │   ├── base.py                   # 추상 인터페이스
│   │   ├── memory_engine.py          # 메인 구현
│   │   └── context_pruner.py         # 버퍼 관리
│   │
│   ├── llm/                          # LLM 통합
│   │   └── client.py                 # OpenAI 클라이언트
│   │
│   ├── models/                       # 데이터 모델
│   │   ├── memory_item.py            # MemoryItem, Resource, Category
│   │   └── retrieval.py              # RetrievalResult
│   │
│   ├── pipelines/                    # 핵심 파이프라인
│   │   ├── memorize.py               # 저장
│   │   ├── retrieve.py               # 검색
│   │   ├── predict.py                # 예측
│   │   ├── consolidate.py            # 정리
│   │   └── flush.py                  # 버퍼 플러시
│   │
│   ├── scheduling/                   # 스케줄링
│   │   ├── scheduler.py              # Cron 스케줄러
│   │   └── jobs.py                   # 작업 정의
│   │
│   ├── security/                     # 보안
│   │   └── sanitizer.py              # 입력 검증
│   │
│   └── vault/                        # Markdown Vault
│       └── markdown_vault.py
│
├── tests/                            # 테스트 스위트
│   ├── test_engine.py
│   ├── test_pipelines.py
│   └── ...
│
├── user_memory/                      # 사용자 데이터 (gitignore)
│   ├── config/
│   │   └── memory_config.yaml        # 사용자 설정
│   ├── db_data/                      # PostgreSQL 데이터 (옵션)
│   └── markdown/                     # Markdown Vault
│       ├── profile.md
│       ├── timeline/                 # 시간순 로그
│       │   ├── 2026-01.md
│       │   └── 2026-02.md
│       └── knowledge/                # 주제별 지식
│           ├── coding/
│           │   ├── python.md
│           │   └── typescript.md
│           └── personal/
│
├── pyproject.toml                    # Python 프로젝트 설정
└── README.md
```

### 3.2 핵심 디렉토리 설명

#### 3.2.1 `src/eternal_memory/`

모든 비즈니스 로직이 포함된 메인 소스 코드 디렉토리입니다.

**주요 모듈:**
- `engine/`: 시스템의 중앙 오케스트레이터
- `pipelines/`: 4개의 핵심 파이프라인 (memorize, retrieve, predict, consolidate)
- `database/`: PostgreSQL 스키마 및 저장소 패턴
- `vault/`: Markdown 파일 시스템 관리
- `scheduling/`: 백그라운드 작업 스케줄러

#### 3.2.2 `user_memory/`

모든 사용자별 데이터가 저장되는 디렉토리로, **git에서 제외**됩니다.

**구조:**
- `config/`: 사용자별 설정 (YAML)
- `markdown/`: 인간이 읽을 수 있는 기억 파일
  - `timeline/`: 월별 시간순 로그
  - `knowledge/`: 주제별 계층 구조

#### 3.2.3 `setting/`

프로젝트 레벨 부트스트랩 설정입니다.

**내용:**
- `.env`: 오직 `OPENAI_API_KEY`만 저장
- `.env.example`: 사용자용 템플릿

## 4. 데이터 모델

### 4.1 MemoryItem (메모리 아이템)

`MemoryItem`은 시스템의 핵심 데이터 구조로, 추출된 사실(Fact)을 표현합니다.

```python
from pydantic import BaseModel
from enum import Enum
from uuid import UUID
from datetime import datetime

class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    PLAN = "plan"

class MemoryItem(BaseModel):
    id: UUID                           # 고유 식별자
    content: str                       # 실제 기억 내용
    category_path: str                 # 예: "knowledge/coding/python"
    type: MemoryType                   # fact, preference, event, plan
    confidence: float                  # 0.0 ~ 1.0 (신뢰도)
    importance: float                  # 0.0 ~ 1.0 (중요도, Salience)
    mention_count: int                 # 강화 카운터 (반복 언급)
    source_resource_id: Optional[UUID] # 원본 리소스 참조
    created_at: datetime
    last_accessed: datetime
```

**필드 설명:**
- `content`: LLM이 추출한 사실 또는 선호도
- `category_path`: 계층적 분류 경로 (슬래시 구분)
- `type`: 기억 유형 (사실/선호/이벤트/계획)
- `importance`: LLM이 평가한 기억의 중요도
- `mention_count`: 시간이 지남에 따라 반복 언급될 때마다 증가
- `confidence`: 정보의 확실성 (모호한 정보는 낮은 값)

### 4.2 Resource (리소스)

원시 데이터 소스를 표현하며, 출처 추적(Traceability)을 제공합니다.

```python
class Resource(BaseModel):
    id: UUID
    uri: str                  # 파일 경로 또는 URL
    modality: str             # 'text', 'image', 'conversation'
    content: Optional[str]    # 전체 텍스트 내용
    created_at: datetime
    metadata: dict            # 추가 정보 (sender, context 등)
```

**사용 사례:**
- 대화 로그: `uri="conversation://2026-01-31"`
- PDF 문서: `uri="file:///path/to/doc.pdf"`
- 웹페이지: `uri="https://example.com/article"`

### 4.3 Category (카테고리)

의미적 클러스터로, 여러 MemoryItem을 그룹화합니다.

```python
class Category(BaseModel):
    id: UUID
    name: str                    # 카테고리 이름 (예: "python")
    description: Optional[str]   # 설명
    parent_id: Optional[UUID]    # 부모 카테고리 (계층 구조)
    summary: Optional[str]       # LLM 생성 요약
    path: str                    # 전체 경로 (예: "knowledge/coding/python")
    last_accessed: datetime
```

**계층 구조 예시:**
```
knowledge/                      # Root
├── coding/                     # Parent
│   ├── python/                 # Child
│   └── typescript/
└── personal/
    └── relationships/
```

## 5. 데이터베이스 스키마

### 5.1 PostgreSQL + pgvector 구조

시스템은 PostgreSQL 14+ with pgvector extension을 사용합니다.

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Resources Table
CREATE TABLE IF NOT EXISTS resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uri TEXT NOT NULL,
    modality VARCHAR(50) NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- 2. Categories Table  
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id),
    summary TEXT,
    path TEXT NOT NULL UNIQUE,
    embedding vector(1536),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Memory Items Table
CREATE TABLE IF NOT EXISTS memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES categories(id),
    resource_id UUID REFERENCES resources(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    type VARCHAR(20) DEFAULT 'fact',
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    mention_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 인덱스 전략

```sql
-- HNSW 벡터 인덱스 (고속 ANN 검색)
CREATE INDEX idx_memory_embedding 
    ON memory_items USING hnsw (embedding vector_cosine_ops);

-- Trigram 키워드 인덱스
CREATE INDEX idx_memory_trgm 
    ON memory_items USING gin (content gin_trgm_ops);

-- B-Tree 인덱스
CREATE INDEX idx_category_path ON categories(path);
CREATE INDEX idx_memory_importance ON memory_items(importance DESC);
```

## 6. 마크다운 볼트 시스템

### 6.1 MarkdownVault 클래스

`vault/markdown_vault.py`는 인간이 읽을 수 있는 파일 시스템을 관리합니다.

**주요 메서드:**

```python
class MarkdownVault:
    def __init__(self, base_path: str = None):
        # Default: user_memory/markdown/
        
    async def initialize(self):
        # 디렉토리 구조 생성, 권한 설정 (chmod 700)
        
    async def append_to_timeline(self, content, timestamp):
        # timeline/2026-01.md에 추가
        
    async def append_to_category(self, category_path, content, memory_type, timestamp):
        # knowledge/coding/python.md에 추가
        
    async def update_category_summary(self, category_path, summary):
        # 카테고리 상단 요약 섹션 업데이트
        
    async def archive_items(self, category_path, summary, original_count):
        # archived/ 디렉토리로 이동
```

### 6.2 디렉토리 구조

```
user_memory/markdown/
├── profile.md                 # 사용자 프로필
├── timeline/                  # 시간순 로그
│   ├── 2026-01.md
│   └── 2026-02.md
└── knowledge/                 # 주제별 지식
    ├── coding/
    │   ├── python.md
    │   └── typescript.md
    └── personal/
        └── relationships.md
```

### 6.3 Markdown 파일 형식

각 카테고리 파일은 다음 구조를 따릅니다:

```markdown
# Python 프로그래밍

## Summary
[LLM이 생성한 카테고리 요약]

## Memories

- [2026-01-31 14:30] **[Preference]** 사용자는 타입 힌트를 선호한다. (importance: 0.7, mentions: 3)
- [2026-01-30 09:15] **[Fact]** FastAPI는 async/await를 네이티브로 지원한다.
- [2026-01-29 16:45] **[Event]** pytest로 첫 번째 테스트 작성 완료
```

## 7. 메모리 엔진 (EternalMemorySystem)

### 7.1 클래스 구조

`engine/memory_engine.py`는 시스템의 중앙 오케스트레이터입니다.

```python
class EternalMemorySystem(EternalMemoryEngine):
    def __init__(self, config: MemoryConfig, vault_path: str):
        self.config = config
        self.repository = MemoryRepository(config.database.connection_string)
        self.vault = MarkdownVault(vault_path)
        self.llm = LLMClient(config.llm)
        
        # 4개의 파이프라인 초기화
        self.memorize_pipeline = MemorizePipeline(...)
        self.retrieve_pipeline = RetrievePipeline(...)
        self.predict_pipeline = PredictPipeline(...)
        self.consolidate_pipeline = ConsolidatePipeline(...)
        
        # 대화 버퍼 (in-memory)
        self.conversation_buffer = []
        self.buffer_size_limit = 10
        
        # 스케줄러
        self.scheduler = CronScheduler()
    
    async def initialize(self):
        # DB 스키마 생성
        # Vault 디렉토리 생성
        # 스케줄러 작업 등록
        
    async def memorize(self, text: str, metadata: dict = None):
        return await self.memorize_pipeline.execute(text, metadata)
        
    async def retrieve(self, query: str, mode: Literal["fast", "deep"] = "fast"):
        return await self.retrieve_pipeline.execute(query, mode)
    
    async def predict_context(self, current_context: dict):
        return await self.predict_pipeline.execute(current_context)
        
    async def consolidate(self):
        return await self.consolidate_pipeline.execute()
```

### 7.2 대화 버퍼 관리

짧은 대화는 메모리에 유지되다가 일정 크기를 초과하면 DB로 플러시됩니다:

```python
async def add_to_buffer(self, role: str, content: str):
    self.conversation_buffer.append({"role": role, "content": content, "timestamp": datetime.now()})
    await self._save_buffer_to_file()  # 영속성 보장
    
async def check_and_flush(self):
    if len(self.conversation_buffer) >= self.buffer_size_limit:
        await self.flush_buffer()
        
async def flush_buffer(self):
    # 버퍼 내용을 memorize_pipeline으로 전송
    # 버퍼 초기화
    # 파일 삭제
```

## 8. Memorize 파이프라인

### 8.1 파이프라인 흐름

```
Input Text
    ↓
[LLM Extraction]  ← Salience Detection
    ↓
구조화된 Facts (JSON)
    ↓
[Category Assignment]  ← Semantic Similarity
    ↓
[Embedding Generation]  ← OpenAI API
    ↓
┌─────────────────┬─────────────────┐
│   PostgreSQL    │  Markdown Vault │
│  + Embedding    │    + Timeline   │
└─────────────────┴─────────────────┘
```

### 8.2 LLM 추출 프롬프트

```python
EXTRACTION_PROMPT = """
Analyze the following conversation and extract memory items.
Focus on FACTS, PREFERENCES, EVENTS, and PLANS.
Ignore trivial chit-chat.

Conversation:
{text}

Output Format (JSON):
[
  {
    "content": "User prefers TypeScript over Python",
    "type": "preference",
    "category_path": "knowledge/coding/languages",
    "importance": 0.6
  }
]
"""
```

### 8.3 카테고리 자동 할당

새로운 기억이 생성될 때:

1. **기존 카테고리 검색**: 벡터 유사도로 가장 가까운 카테고리 찾기
2. **임계값 확인**: 유사도 > 0.7이면 해당 카테고리 사용
3. **신규 생성**: 임계값 미만이면 새 카테고리 생성

```python
async def _assign_category(self, content: str):
    embedding = await self.llm.generate_embedding(content)
    similar_categories = await self.repository.vector_search_categories(
        embedding, limit=1, threshold=0.7
    )
    
    if similar_categories:
        return similar_categories[0].path
    else:
        # LLM에게 새 카테고리 경로 제안 요청
        suggested_path = await self.llm.suggest_category_path(content)
        await self._ensure_category(suggested_path)
        return suggested_path
```

## 9. Retrieve 파이프라인

### 9.1 이중 모드 검색

**Fast Mode (하이브리드 검색)**
- 벡터 검색 (pgvector HNSW) + 키워드 검색 (Trigram)
- RRF(Reciprocal Rank Fusion)로 결과 병합
- 응답 시간: ~50-200ms

**Deep Mode (LLM 추론)**
- 하이브리드 검색으로 높은 recall 확보 (20개 아이템)
- LLM이 컨텍스트를 읽고 질문에 대한 답변 합성
- 응답 시간: ~2-5초

### 9.2 쿼리 진화 (Query Evolution)

모호한 질문을 대화 문맥을 바탕으로 구체화:

```python
# 원본: "그때 뭐라고 했지?"
# 진화: "지난주 Python 프로젝트 논의할 때 성능 최적화에 대해 뭐라고 조언했는지?"

async def evolve_query(self, query: str, conversation_context: str):
    prompt = f"""
    Original vague query: {query}
    Recent conversation: {conversation_context}
    
    Rewrite the query to be specific and searchable.
    """
    return await self.llm.complete(prompt)
```

### 9.3 RetrievalResult 구조

```python
class RetrievalResult(BaseModel):
    items: List[MemoryItem]           # 검색된 아이템들
    related_categories: List[str]      # 관련 카테고리
    suggested_context: str             # 컨텍스트 요약
    query_evolved: Optional[str]       # 진화된 쿼리
    retrieval_mode: str                # "fast" or "deep"
    confidence_score: float            # 0.0 ~ 1.0
```
    retrieval_mode: str                # "fast" or "deep"
    confidence_score: float            # 0.0 ~ 1.0
```

## 10. Predict 파이프라인

### 10.1 컨텍스트 예측 메커니즘

시스템은 현재 상황을 분석하여 사용자가 필요로 할 기억을 선제적으로 로딩합니다.

```python
async def execute(self, current_context: dict) -> str:
    # 1. 현재 상황 분석
    time_of_day = current_context.get("time")
    recent_files = current_context.get("recent_files", [])
    open_apps = current_context.get("open_apps", [])
    
    # 2. 최근 접근 패턴 분석
    recent_memories = await self.repository.get_memories_since(
        since=datetime.now() - timedelta(hours=24)
    )
    
    # 3. 카테고리 접근 빈도 계산
    category_freq = self._calculate_category_frequency(recent_memories)
    top_categories = sorted(category_freq.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # 4. LLM에게 예측 요청
    prediction_prompt = f"""
    Current context:
    - Time: {time_of_day}
    - Recently accessed categories: {top_categories}
    - Open files: {recent_files}
    
    Predict what the user might need next and suggest relevant memories to preload.
    """
    
    predicted_context = await self.llm.complete(prediction_prompt)
    return predicted_context
```

### 10.2 시스템 프롬프트 주입

예측된 컨텍스트는 시스템 프롬프트에 자동으로 추가됩니다:

```python
# API Gateway에서 사용
predicted_context = await memory_system.predict_context({
    "time": datetime.now(),
    "recent_files": get_recent_files(),
    "open_apps": get_open_applications()
})

system_prompt = f"""
You are a helpful AI assistant with access to the user's memory.

{predicted_context}

Use this context to provide more personalized and relevant responses.
"""
```

## 11. Consolidate 파이프라인

### 11.1 메모리 정리 작업

시스템은 주기적으로 기억을 정리하고 최적화합니다:

```python
async def execute(self):
    # 1. Stale 아이템 찾기
    stale_items = await self.repository.get_stale_items(days_threshold=90)
    
    if len(stale_items) > 100:
        # 2. LLM으로 요약 생성 (현재는 비활성화)
        # summary = await self.llm.summarize_items(stale_items)
        # await self.vault.archive_items(category_path, summary, len(stale_items))
        pass  # Eternal Memory 철학: 삭제하지 않음
    
    # 3. 카테고리 요약 업데이트
    categories = await self.repository.get_all_categories()
    for category in categories:
        items = await self.repository.get_items_by_category(category.path)
        if len(items) > 0:
            summary = await self.llm.summarize_category(items)
            await self.repository.update_category_summary(category.id, summary)
            await self.vault.update_category_summary(category.path, summary)
    
    # 4. 대형 카테고리 재구성
    for category in categories:
        if await self._category_is_too_large(category):
            await self._split_category(category)
```

### 11.2 카테고리 분할 로직

카테고리가 너무 커지면 자동으로 하위 카테고리로 분리:

```python
async def _split_category(self, category: Category):
    items = await self.repository.get_items_by_category(category.path)
    
    # LLM에게 클러스터링 요청
    subcategories = await self.llm.suggest_subcategories(
        category_name=category.name,
        items=items,
        target_clusters=3
    )
    
    for subcat_name, assigned_items in subcategories.items():
        new_path = f"{category.path}/{subcat_name}"
        await self._ensure_category(new_path, parent_id=category.id)
        
        for item in assigned_items:
            await self.repository.update_item_category(item.id, new_path)
```

## 12. 스케줄링 시스템

### 12.1 CronScheduler

`scheduling/scheduler.py`는 백그라운드 작업을 관리합니다:

```python
class CronScheduler:
    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._running = False
    
    def add_job(
        self,
        name: str,
        interval_seconds: int,
        func: Callable[[], Coroutine],
        job_type: str = "custom",
        is_system: bool = False
    ):
        self._jobs[name] = JobInfo(
            name=name,
            func=func,
            interval=interval_seconds,
            next_run=datetime.now() + timedelta(seconds=interval_seconds),
            job_type=job_type,
            is_system=is_system
        )
    
    async def start(self):
        self._running = True
        asyncio.create_task(self._loop())
    
    async def _loop(self):
        while self._running:
            now = datetime.now()
            for job in self._jobs.values():
                if job.enabled and now >= job.next_run:
                    try:
                        await job.func()
                        job.last_run = now
                        job.next_run = now + timedelta(seconds=job.interval)
                    except Exception as e:
                        logger.error(f"Job {job.name} failed: {e}")
            
            await asyncio.sleep(1)
```

### 12.2 주요 백그라운드 작업

**Daily Reflection** (매일 자정)
```python
@register_job(name="daily_reflection")
def job_daily_reflection(system: EternalMemorySystem):
    async def run():
        yesterday = datetime.now() - timedelta(days=1)
        memories = await system.repository.get_memories_since(yesterday)
        
        summary = await system.llm.complete(f"""
        Summarize the following memories from yesterday:
        {[m.content for m in memories]}
        
        Extract:
        - Key events
        - Important insights
        - Overall sentiment
        """)
        
        await system.memorize(
            f"Daily Reflection ({yesterday.date()}): {summary}",
            metadata={"type": "reflection", "period": "daily"}
        )
    return run
```

**Weekly Summary** (매주 일요일)
```python
@register_job(name="weekly_summary")
def job_weekly_summary(system: EternalMemorySystem):
    async def run():
        week_ago = datetime.now() - timedelta(days=7)
        memories = await system.repository.get_memories_since(week_ago)
        
        summary = await system.llm.complete(f"""
        Create a weekly summary synthesizing these memories:
        - Major accomplishments
        - Recurring themes
        - Changes in preferences or behavior
        """)
        
        await system.memorize(
            f"Weekly Summary: {summary}",
            metadata={"type": "reflection", "period": "weekly"}
        )
    return run
```

**Maintenance** (매일 03:00)
```python
@register_job(name="maintenance")
def job_maintenance(system: EternalMemorySystem):
    async def run():
        await system.consolidate()
        # 임베딩 인덱스 최적화
        await system.repository.refresh_indexes()
    return run
```

## 13. LLM 클라이언트 통합

### 13.1 LLMClient 클래스

`llm/client.py`는 OpenAI API를 래핑합니다:

```python
class LLMClient:
    def __init__(self, model: str, api_key: str, base_url: str = None):
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.embedding_model = "text-embedding-ada-002"
    
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def extract_facts(self, text: str) -> List[dict]:
        prompt = EXTRACTION_PROMPT.format(text=text)
        response = await self.complete(prompt, temperature=0.3)  # 낮은 온도
        return json.loads(response)
```

### 13.2 토큰 사용량 추적

모든 LLM 호출은 토큰 사용량을 기록합니다:

```python
async def _track_usage(self, usage: openai.types.CompletionUsage):
    await self.repository.increment_token_usage(
        model=self.model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens
    )
```

## 14. 설정 관리

### 14.1 MemoryConfig

`config.py`는 설정을 관리합니다:

```python
class DatabaseConfig(BaseModel):
    connection_string: str = "postgresql://localhost/eternal_memory"
    pool_size: int = 10

class LLMConfig(BaseModel):
    model: str = "gpt-4o-mini"
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7

class RetentionConfig(BaseModel):
    archive_after_days: int = 90
    consolidate_interval_hours: int = 24

class MemoryConfig(BaseModel):
    database: DatabaseConfig
    llm: LLMConfig
    retention: RetentionConfig
    vault_path: str = "user_memory/markdown"
    buffer_size: int = 10

def load_config(config_path: str = "user_memory/config/memory_config.yaml") -> MemoryConfig:
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    
    # 환경 변수 오버라이드
    if "OPENAI_API_KEY" in os.environ:
        config_dict.setdefault("llm", {})["api_key"] = os.environ["OPENAI_API_KEY"]
    
    if "DATABASE_URL" in os.environ:
        config_dict.setdefault("database", {})["connection_string"] = os.environ["DATABASE_URL"]
    
    return MemoryConfig(**config_dict)
```

### 14.2 설정 파일 예시

`user_memory/config/memory_config.yaml`:

```yaml
database:
  connection_string: "postgresql://localhost:5432/eternal_memory"
  pool_size: 10

llm:
  model: "gpt-4o-mini"
  # api_key는 환경 변수에서 읽음 (OPENAI_API_KEY)
  temperature: 0.7

retention:
  archive_after_days: 90
  consolidate_interval_hours: 24

vault_path: "user_memory/markdown"
buffer_size: 10
```

## 15. API 구조

### 15.1 FastAPI 라우트

`api/main.py`의 주요 엔드포인트:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Eternal Memory API")

# 전역 인스턴스
memory_system: EternalMemorySystem = None

@app.on_event("startup")
async def startup():
    global memory_system
    config = load_config()
    memory_system = EternalMemorySystem(config)
    await memory_system.initialize()
    await memory_system.scheduler.start()

@app.post("/memorize")
async def memorize_endpoint(request: MemorizeRequest):
    """새로운 기억 저장"""
    item = await memory_system.memorize(request.text, request.metadata)
    return {"status": "success", "item_id": str(item.id)}

@app.get("/retrieve")
async def retrieve_endpoint(
    query: str,
    mode: Literal["fast", "deep"] = "fast",
    limit: int = 5
):
    """기억 검색"""
    result = await memory_system.retrieve(query, mode=mode)
    return result.dict()

@app.get("/stats")
async def stats_endpoint():
    """시스템 통계"""
    stats = await memory_system.repository.get_stats()
    return stats

@app.post("/jobs/{job_name}/trigger")
async def trigger_job(job_name: str):
    """수동으로 작업 실행"""
    await memory_system.scheduler.trigger_job(job_name)
    return {"status": "triggered"}
```

## 16. 보안 및 권한 관리

### 16.1 파일 시스템 보안

- **디렉토리 권한**: `chmod 700` (소유자만 읽기/쓰기/실행)
- **파일 권한**: `chmod 600` (소유자만 읽기/쓰기)

```python
async def initialize(self):
    os.makedirs(self.base_path, mode=0o700, exist_ok=True)
    os.makedirs(self.timeline_dir, mode=0o700, exist_ok=True)
    os.makedirs(self.knowledge_dir, mode=0o700, exist_ok=True)
```

### 16.2 입력 검증

`security/sanitizer.py`:

```python
def sanitize_input(text: str) -> str:
    # XSS 방지
    text = text.replace("<script>", "").replace("</script>", "")
    # 제어 문자 제거
    text = "".join(char for char in text if char.isprintable() or char.isspace())
    return text.strip()

def validate_category_path(path: str) -> bool:
    # 경로 주입 방지
    if ".." in path or path.startswith("/"):
        raise ValueError("Invalid category path")
    return True
```

## 17. 배포 및 운영

### 17.1 초기 설정

```bash
# 1. PostgreSQL 및 pgvector 설치
brew install postgresql@14
psql -c "CREATE EXTENSION vector"

# 2. Python 의존성 설치
pip install -e .

# 3. 환경 변수 설정
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="postgresql://localhost:5432/eternal_memory"

# 4. 데이터베이스 초기화
python scripts/setup_db.py

# 5. 서버 실행
uvicorn eternal_memory.api.main:app --reload
```

### 17.2 모니터링

```python
# 토큰 사용량 확인
GET /stats/tokens

# 메모리 통계
GET /stats/memory
{
  "total_items": 1523,
  "total_categories": 45,
  "total_resources": 89,
  "storage_mb": 12.4
}

# 스케줄러 상태
GET /jobs
[
  {"name": "daily_reflection", "last_run": "2026-01-31T00:00:00", "enabled": true},
  {"name": "maintenance", "last_run": "2026-01-31T03:00:00", "enabled": true}
]
```

---

---

# 결론

**Eternal Memory 시스템**은 로컬 우선 AI 에이전트를 위한 완전한 영구 기억 솔루션입니다. 본 문서는 실제 구현된 시스템을 기반으로 작성되었으며, 다음과 같은 핵심 특징을 갖추고 있습니다:

## 구현 완료 사항

### 계층적 데이터 모델
- Resource, MemoryItem, Category의 3계층 구조
- Pydantic 기반 타입 안전성
- PostgreSQL + pgvector 벡터 데이터베이스

### 이중 저장 레이어
- **Machine Layer**: PostgreSQL with HNSW 인덱스 (고속 검색)
- **Human Layer**: Markdown Vault (투명성 및 편집 가능성)

### 4가지 핵심 파이프라인
1. **Memorize**: LLM 기반 사실 추출 및 저장
2. **Retrieve**: Fast/Deep 이중 모드 검색
3. **Predict**: 컨텍스트 예측 및 선제적 로딩
4. **Consolidate**: 자동 요약 및 카테고리 관리

### 자동화된 백그라운드 작업
- Daily/Weekly/Monthly Reflection
- Maintenance (인덱스 최적화)
- Vault Backup
- 완전 비동기(AsyncIO) 스케줄러

### 프로덕션 준비
- FastAPI 기반 REST API
- 환경 변수 기반 설정
- 토큰 사용량 추적
- 입력 검증 및 보안

## 기술적 혁신

### 하이브리드 검색
Reciprocal Rank Fusion (RRF)을 통해 벡터 검색과 키워드 검색을 결합하여, 단일 방법보다 우수한 검색 품질을 제공합니다.

### 쿼리 진화
대화 컨텍스트를 활용하여 모호한 질문을 구체화함으로써, 사용자가 정확한 검색어를 제공하지 않아도 의도를 파악합니다.

### 선제적 컨텍스트 로딩
시간, 최근 파일, 카테고리 접근 패턴을 분석하여 사용자가 요청하기 전에 관련 기억을 미리 준비합니다.

## 설계 철학 구현

### 영구성 (Persistence)
- 모든 데이터는 PostgreSQL에 영구 저장
- 대화 버퍼도 파일로 백업하여 프로세스 재시작 시 복구
- "Eternal Memory" 철학: 삭제 대신 아카이빙

### 투명성 (Transparency)
- 모든 기억은 Markdown 파일로 미러링
- 사용자가 직접 편집 가능
- AI 환각(Hallucination) 교정 지원

### 능동성 (Proactivity)
- Predict 파이프라인을 통한 의도 예측
- 시스템 프롬프트 자동 주입
- Daily Reflection으로 지속적 학습

## 확장 가능성

현재 시스템은 다음과 같은 확장이 가능합니다:

- **Multi-modal 지원**: 이미지, 오디오 임베딩 추가
- **분산 검색**: 여러 인스턴스 간 기억 공유
- **Fine-tuning**: 사용자별 임베딩 모델 특화
- **Graph Memory**: 기억 간 관계 그래프 구축

## 다음 단계

시스템을 프로덕션 환경에 배포하려면:

1. PostgreSQL 및 pgvector 설치
2. `setting/.env`에 `OPENAI_API_KEY` 설정
3. `scripts/setup_db.py` 실행
4. `uvicorn eternal_memory.api.main:app` 시작

자세한 내용은 섹션 17 (배포 및 운영)을 참조하세요.

---

**문서 버전**: 2.0.0  
**마지막 업데이트**: 2026-01-31  
**구현 상태**: Production Ready



Forbes, 1월 30, 2026에 액세스,
https://www.forbes.com/sites/ronschmelzer/2026/01/30/moltbot-molts-again-and
-becomes-openclaw-pushback-and-concerns-grow/
# 2. From Moltbot to OpenClaw: When the Dust Settles, the Project Survived - DEV

Community, 1월 30, 2026에 액세스,
https://dev.to/sivarampg/from-moltbot-to-openclaw-when-the-dust-settles-the-
project-survived-5h6o
# 3. OpenClaw — Personal AI Assistant, 1월 30, 2026에 액세스, https://openclaw.ai/

# 4. What is Moltbot? How the local AI agent works - Hostinger, 1월 30, 2026에

액세스, https://www.hostinger.com/my/tutorials/what-is-openclaw
# 5. NevaMind-AI/memU: Memory for 24/7 proactive agents like .. - GitHub, 1월 31,

2026에 액세스, https://github.com/NevaMind-AI/memU
# 6. Clawdbot (Moltbot) (OpenClaw) Privacy & Security Explained - YouTube, 1월 30,

2026에 액세스, https://www.youtube.com/watch?v=04IoKjApkrs
# 7. openclaw/openclaw: Your own personal AI assistant. Any .. - GitHub, 1월 30,

2026에 액세스, https://github.com/openclaw/openclaw
# 8. We built an open source memory framework that doesn't rely on embeddings.

Just open-sourced it - Reddit, 1월 31, 2026에 액세스,
https://www.reddit.com/r/LocalLLaMA/comments/1q57txn/we_built_an_open_sou
rce_memory_framework_that/
# 9. OpenClaw: The viral “space lobster” agent testing the limits of vertical integration

| IBM, 1월 30, 2026에 액세스,
https://www.ibm.com/think/news/clawdbot-ai-agent-testing-limits-vertical-integr
ation
# 10. Releases · openclaw/openclaw · GitHub, 1월 31, 2026에 액세스,

https://github.com/openclaw/openclaw/releases
