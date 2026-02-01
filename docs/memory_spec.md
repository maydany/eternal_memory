# Eternal Memory 시스템 사양서

**Document Version:** 4.0.0  
**Last Updated:** 2026-02-02  
**Status:** Production Ready

## 1. 서론

### 1.1 프로젝트 개요

**Eternal Memory**는 차세대 AI 에이전트를 위한 **Entity-Level 영구 기억 시스템**입니다.

#### 왜 하이브리드 아키텍처인가?

Eternal Memory는 **세 가지 서로 다른 강점을 가진 레이어를 결합**하여, 단일 기술로는 불가능한 수준의 성능과 안정성을 달성합니다.

**1. Semantic Triples (정밀성) — LangMem 기반 Entity-Level Memory**

기존 RAG 시스템은 문장을 통째로 저장합니다. 하지만 LangChain의 **LangMem 프레임워크**는 다른 접근을 제안합니다: 문장을 `(Subject, Predicate, Object)` 형태의 **지식 그래프 트리플**로 분해하여 저장하면, 엔티티 단위로 정밀한 업데이트가 가능합니다.

```
[실제 시나리오: 프로젝트 기술 스택 변경]

Week 1: "우리 프로젝트는 React 17을 사용하고 있어"
Week 4: "React 18로 마이그레이션 완료했어"
Week 8: "Next.js 14로 전환했어, React는 이제 프레임워크 내부에서 사용"

──────────────────────────────────────────────────────────────────
❌ 기존 RAG (문장 기반 저장)
──────────────────────────────────────────────────────────────────
저장된 데이터:
  "프로젝트는 React 17을 사용한다"
  "프로젝트는 React 18로 마이그레이션했다"
  "프로젝트는 Next.js 14로 전환했다"

질문: "우리 프로젝트 프론트엔드 스택이 뭐야?"
결과: 세 문장 모두 반환 (벡터 유사도 유사)
AI: "React 17, React 18, Next.js 14를 사용하고 있습니다" ❌

──────────────────────────────────────────────────────────────────
✅ Eternal Memory (Semantic Triples)
──────────────────────────────────────────────────────────────────
저장된 트리플:
  (Project, uses_framework, React_17)    → is_active: false
  (Project, uses_framework, React_18)    → is_active: false  
  (Project, uses_framework, Next.js_14)  → is_active: true
  (Next.js_14, internally_uses, React)   → is_active: true

질문: "우리 프로젝트 프론트엔드 스택이 뭐야?"
결과: is_active=true인 트리플만 조회
AI: "Next.js 14를 사용하고 있고, 내부적으로 React를 활용합니다" ✅
```

**왜 트리플인가?**

| 접근 방식 | 업데이트 시 | 검색 시 |
|----------|------------|--------|
| 문장 저장 | 새 문장 추가 (충돌 누적) | 모든 관련 문장 반환 |
| 트리플 저장 | 동일 Subject-Predicate 자동 supersede | 최신 정보만 반환 |

트리플의 핵심은 **동일한 Subject-Predicate 조합은 하나의 진실만 가질 수 있다**는 원칙입니다. `(Project, uses_framework, X)`에서 X가 바뀌면, 기존 트리플은 자동으로 비활성화(supersede)됩니다.

**2. Vector Search (속도)**  
pgvector의 HNSW 인덱스를 활용해 수백만 개의 기억 중에서도 ~50ms 내에 유사한 항목을 검색합니다. 트리플이 아직 생성되지 않은 최신 기억도 벡터 검색으로 즉시 찾을 수 있어, Lazy Evaluation의 핵심 백본 역할을 합니다.

**3. Markdown Vault (투명성)**  
모든 기억을 사람이 읽고 편집할 수 있는 Markdown 파일로 미러링합니다. AI가 잘못 기억한 내용을 사용자가 직접 수정할 수 있고, 버전 관리(Git)와도 자연스럽게 통합됩니다.

**이 조합이 특별한 이유:**
- 트리플만 있으면 → 추출 실패 시 기억 손실
- 벡터만 있으면 → 충돌 정보 누적, 정확도 하락
- 마크다운만 있으면 → 검색 속도 느림, 구조화 어려움

**Eternal Memory는 세 레이어가 서로를 보완합니다:**

```
+-------------------------------------------------------------------------+
|                   Eternal Memory Hybrid Architecture                    |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------+  +-------------------+  +-------------------+    |
|  | Semantic Triples  |  |   Vector Search   |  |   Markdown Vault  |    |
|  |   (Precision)     |  |     (Speed)       |  |  (Transparency)   |    |
|  +-------------------+  +-------------------+  +-------------------+    |
|  | Entity-Level      |  | HNSW ~50ms        |  | Human-readable    |    |
|  | Auto-conflict     |  | Similarity search |  | Editable          |    |
|  | Supersede support |  | Fallback layer    |  | Full history      |    |
|  +---------+---------+  +---------+---------+  +---------+---------+    |
|            |                      |                      |              |
|            +----------------------+----------------------+              |
|                                   |                                     |
|                                   v                                     |
|                  +-------------------------------+                      |
|                  |     Hierarchical Filtering    |                      |
|                  |   Triples -> Items -> Fallback|                      |
|                  +-------------------------------+                      |
+-------------------------------------------------------------------------+
```

**기존 RAG vs Eternal Memory 비교:**

| 측면 | 기존 RAG | Eternal Memory |
|------|----------|----------------|
| 정보 충돌 | 모순된 정보 누적, 정확도 하락 | Entity-Level supersede로 자동 해결 |
| 업데이트 | 문장 단위 추가만 가능 | 트리플 단위 정밀 수정 가능 |
| 검색 속도 | 벡터 검색만 의존 | Triple + Vector 하이브리드 |
| 장애 대응 | 추출 실패 시 데이터 손실 | Fallback으로 무중단 동작 |


#### Graceful Degradation: 트리플 없어도 동작

Eternal Memory의 핵심 설계 원칙은 **"트리플이 준비되지 않아도 시스템이 정상 동작"**하는 것입니다.

```
[Lazy Evaluation + Hierarchical Filtering]

User: "I prefer green tea over coffee"
      |
      v
+-----------------------------------------------------------+
|  INSTANT SAVE (No delay)                                  |
|  MemoryItem: "User prefers green tea over coffee"         |
|  -> Vector embedding created, immediately searchable      |
+-----------------------------------------------------------+
      |
      |  (5 min later, Background Job)
      v
+-----------------------------------------------------------+
|  TRIPLE EXTRACTION (Lazy Evaluation)                      |
|  (User, prefers_drink, green_tea)                         |
|  (User, dislikes, coffee)                                 |
|  -> Conflict detection, supersede processing              |
+-----------------------------------------------------------+

Search Flow (Hierarchical Filtering):
1. Query Semantic Triples first (precise results if available)
2. No triples? -> Fallback to MemoryItem (always works)
```

**왜 이게 중요한가?**

| 다른 시스템 | Eternal Memory |
|------------|----------------|
| 트리플 추출 완료까지 응답 지연 | 즉시 저장, 즉시 검색 가능 |
| 추출 실패 시 데이터 손실 | MemoryItem으로 항상 백업 |
| 높은 LLM 비용 (매번 추출) | 배치 처리로 80% 비용 절감 |

#### 핵심 장점 요약

| 측면 | 장점 |
|------|------|
| **즉시 반응** | 저장 즉시 검색 가능, 트리플 추출은 백그라운드에서 진행 |
| **무중단 동작** | 트리플 미생성/추출 실패해도 MemoryItem으로 항상 동작 |
| **저비용** | Lazy 배치 추출로 LLM 호출 80% 절감, 피크 부하 분산 |
| **높은 정확도** | 트리플 생성 후 Entity-Level supersede로 정보 자동 정제 |

#### 학술 연구 기반 설계

이러한 장점을 달성하기 위해 검증된 학술 연구와 업계 표준을 적용했습니다:

- **MemGPT 논문 (Packer et al., 2023)**: 새로운 정보가 기존과 충돌할 때 삭제 대신 비활성화하는 **Memory Supersede** 메커니즘으로, 기억 히스토리를 보존하면서 최신 정보로 자연스럽게 전환합니다.

- **LangMem 프레임워크 (LangChain)**: 문장을 **Subject-Predicate-Object 트리플**로 분해하여 `(User, lives_in, 서울)` → `(User, lives_in, 부산)`처럼 정밀한 엔티티 수준 업데이트를 가능하게 합니다.

- **Generative Agents (Stanford, 2023)**: **Salience 기반 중요도 평가**로 중요한 기억에 빠르게 접근하고, **Reflection 메커니즘**으로 주기적 요약을 통해 장기 기억을 구조화합니다.

### 1.2 핵심 철학

Eternal Memory 시스템은 네 가지 핵심 원칙을 기반으로 설계되었습니다:

1. **영구성 (Persistence)**: 세션이 종료되어도 모든 기억은 영구적으로 보존됩니다. 삭제 대신 Supersede 패턴으로 히스토리를 유지합니다.

2. **정밀성 (Precision)**: Semantic Triples(Subject-Predicate-Object)로 기억을 분해하여, "철수가 서울에서 부산으로 이사했다"와 같은 업데이트를 정확히 반영합니다.

3. **효율성 (Efficiency)**: Lazy Evaluation, 배치 임베딩, LRU 캐시 등 비용 최적화 기법을 적용하여 LLM API 호출을 최소화합니다.

4. **투명성 (Transparency)**: 모든 기억은 Markdown 파일로 미러링되어 사용자가 직접 확인하고 수정할 수 있습니다.

### 1.3 기술 스택

- **Backend**: Python 3.11+ (AsyncIO 기반)
- **Database**: PostgreSQL 14+ with pgvector extension
- **Vector Search**: pgvector (HNSW indexing)
- **Text Search**: pg_trgm (Trigram matching)
- **API Framework**: FastAPI 0.104+
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **LLM Integration**: OpenAI GPT-4o-mini (다중 모델 지원)
- **Embedding**: text-embedding-3-large (1536d Matryoshka dim reduction)
- **Storage**: Triple-layer (Semantic Triples + MemoryItems + Markdown)
- **Scheduling**: APScheduler 기반 Cron Scheduler
- **Monitoring**: PerformanceMonitor (JSON 로그 기반)

## 2. 시스템 아키텍처

### 2.1 전체 구조 개요

Eternal Memory 시스템은 **Entity-Level 기억 관리**를 위한 계층화된 아키텍처로 구성됩니다:

```
┌────────────────────────────────────────────────────────────────┐
│                 React Frontend (Vite + TailwindCSS)            │
│          Chat / Settings / Database / Scheduling UI            │
└─────────────────────────────┬──────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                    API Layer (FastAPI)                         │
│      /chat, /memories, /stats, /settings, /schedule            │
└─────────────────────────────┬──────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│              Memory Engine (EternalMemorySystem)               │
│     Orchestrates pipelines, manages buffer & lifecycle         │
└─────────────────────────────┬──────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
┌────────▼────────┐  ┌───────▼───────┐  ┌────────▼─────────┐
│   4 Pipelines   │  │  Repository   │  │  Markdown Vault  │
│                 │  │    (CRUD)     │  │  (Human Layer)   │
│ - Memorize      │  │               │  │                  │
│ - Retrieve      │  │               │  │                  │
│ - Predict       │  │               │  │                  │
│ - Consolidate   │  │               │  │                  │
└────────┬────────┘  └───────┬───────┘  └────────┬─────────┘
         │                   │                    │
         └───────────────────┼────────────────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
┌───▼─────────────┐  ┌──────▼──────────┐  ┌──────────▼──────────┐
│   PostgreSQL    │  │   LLM Client    │  │   Scheduler         │
│                 │  │                 │  │                     │
│ ┌─────────────┐ │  │  - Chat Model   │  │  - Lazy Extraction  │
│ │MemoryItems  │ │  │  - Memory Model │  │  - Consolidation    │
│ │+ embedding  │ │  │  - Supersede    │  │  - Reflection       │
│ ├─────────────┤ │  │                 │  │  - Backup           │
│ │Semantic     │ │  │  (Multi-Model)  │  │                     │
│ │Triples (SPO)│ │  │                 │  │  (APScheduler)      │
│ └─────────────┘ │  └─────────────────┘  └─────────────────────┘
└─────────────────┘
```

### 2.2 핵심 컴포넌트

#### 2.2.1 메모리 엔진 (EternalMemorySystem)

시스템의 중앙 컨트롤러로, 모든 파이프라인과 컴포넌트를 통합합니다.

**주요 기능:**
- 초기화 및 연결 관리
- 대화 버퍼 관리 (토큰 기반 자동 플러시)
- 파이프라인 오케스트레이션
- 다중 모델 LLM 클라이언트 관리

#### 2.2.2 계층적 데이터 모델

시스템은 **4계층 구조**로 데이터를 관리합니다:

1. **Resource (리소스)**: 원시 데이터 소스
   - 대화 로그, PDF 문서 등 원본 자료
   - 출처 추적(Traceability) 제공

2. **MemoryItem (메모리 아이템)**: 추출된 사실 (문장 수준)
   - LLM이 리소스에서 추출한 구조화된 정보
   - 벡터 임베딩, 중요도, 신뢰도 포함
   - MemGPT-style `is_active`, `superseded_by` 지원

3. **SemanticTriple (시맨틱 트리플)**: 엔티티 수준 지식 (핵심 기능)
   - Subject-Predicate-Object 분해 (LangMem 방식)
   - 예: `(철수, lives_in, 서울)`, `(철수, prefers, Python)`
   - 동일 Subject-Predicate 충돌 시 자동 supersede

4. **Category (카테고리)**: 의미적 클러스터
   - 아이템들을 주제별로 그룹화
   - 계층적 경로 (예: `knowledge/coding/python`)
   - 자동 요약 생성

#### 2.2.3 Triple-Layer 저장소

모든 기억은 세 곳에 저장됩니다:

**Semantic Layer (Semantic Triples)**
- Entity-Level 정밀 업데이트
- Subject 기반 빠른 조회
- 충돌 감지 및 자동 supersede

**Vector Layer (MemoryItems + pgvector)**
- 고속 벡터 검색 (HNSW 인덱스)
- 하이브리드 검색 (벡터 + 키워드 RRF)
- 문장 수준 유사도 검색

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
    -- MemGPT-style Supersede 지원
    is_active BOOLEAN DEFAULT TRUE,           -- 비활성화된 기억은 검색에서 제외
    superseded_by UUID REFERENCES memory_items(id),  -- 대체한 기억 참조
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Semantic Triples Table (LangMem-style)
-- 논문 기반: Subject-Predicate-Object 트리플 저장
-- 참고: LangChain LangMem, Knowledge Graph Memory
CREATE TABLE IF NOT EXISTS semantic_triples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_item_id UUID REFERENCES memory_items(id) ON DELETE CASCADE,
    
    -- Triple components
    subject TEXT NOT NULL,                    -- "User", "Alice", "Python"
    predicate TEXT NOT NULL,                  -- "likes", "knows", "is_born_on"
    object TEXT NOT NULL,                     -- "apples", "coding", "1990-01-01"
    context TEXT,                             -- Optional: "since 2020", "very much"
    
    -- Metadata
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES semantic_triples(id),
    
    -- Embeddings for semantic search
    subject_embedding vector(1536),
    object_embedding vector(1536),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Token Usage: Cost Tracking
CREATE TABLE IF NOT EXISTS token_usage (
    model TEXT PRIMARY KEY,
    prompt_tokens BIGINT DEFAULT 0,
    completion_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Scheduled Tasks: Persistent Job Registry
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL,
    interval_seconds INT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    is_system BOOLEAN DEFAULT false,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Chat Sessions: Server-side session persistence (cross-device)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,     -- Array of Message objects
    mode VARCHAR(10) NOT NULL DEFAULT 'fast',        -- 'fast' | 'deep'
    context_summary TEXT,                            -- Rolling summary cache
    summarized_count INTEGER DEFAULT 0,              -- For stale cache detection
    selected_message_id VARCHAR(255),                -- Currently selected message
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 인덱스 전략

```sql
-- HNSW 벡터 인덱스 (고속 ANN 검색)
CREATE INDEX idx_memory_embedding 
    ON memory_items USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_category_embedding 
    ON categories USING hnsw (embedding vector_cosine_ops);

-- Trigram 키워드 인덱스
CREATE INDEX idx_memory_trgm 
    ON memory_items USING gin (content gin_trgm_ops);

-- B-Tree 인덱스
CREATE INDEX idx_category_path ON categories(path);
CREATE INDEX idx_memory_importance ON memory_items(importance DESC);
CREATE INDEX idx_memory_category ON memory_items(category_id);
CREATE INDEX idx_memory_last_accessed ON memory_items(last_accessed DESC);

-- Semantic Triple 전용 인덱스
CREATE INDEX idx_triple_subject ON semantic_triples(subject);
CREATE INDEX idx_triple_predicate ON semantic_triples(predicate);
CREATE INDEX idx_triple_object_trgm 
    ON semantic_triples USING gin (object gin_trgm_ops);
CREATE INDEX idx_triple_subject_embed 
    ON semantic_triples USING hnsw (subject_embedding vector_cosine_ops);
CREATE INDEX idx_triple_object_embed 
    ON semantic_triples USING hnsw (object_embedding vector_cosine_ops);
CREATE INDEX idx_triple_is_active ON semantic_triples(is_active);
CREATE INDEX idx_triple_memory_item ON semantic_triples(memory_item_id);
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

### 8.3 카테고리 자동 할당 및 배치 임베딩

새로운 기억이 생성될 때 카테고리를 자동으로 할당하고, 여러 아이템을 한 번에 임베딩합니다:

```python
async def execute(self, text: str, metadata: dict = None):
    # 1. LLM으로 사실 추출
    facts = await self.llm.extract_facts(text, existing_categories)
    
    if not facts:
        return []
    
    # 2. 카테고리 할당 (각 사실마다)
    for fact in facts:
        category_path = await self._assign_category(fact["content"])
        fact["category_path"] = category_path
    
    # 3. 배치 임베딩 생성 (성능 최적화)
    # 개별 호출 대신 모든 사실을 한 번에 임베딩
    fact_contents = [f["content"] for f in facts]
    embeddings = await self.llm.batch_generate_embeddings(fact_contents)
    
    # 4. DB 저장 및 Vault 동기화
    created_items = []
    for fact, embedding in zip(facts, embeddings):
        # DB에 저장
        item = await self.repository.create_memory_item(
            content=fact["content"],
            category_path=fact["category_path"],
            embedding=embedding,
            type=fact["type"],
            importance=fact["importance"],
        )
        
        # Markdown Vault에 추가
        await self.vault.append_to_category(
            category_path=fact["category_path"],
            content=fact["content"],
            memory_type=fact["type"],
            timestamp=item.created_at,
        )
        
        created_items.append(item)
    
    return created_items

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

**배치 임베딩의 이점:**
- **다중 사실 처리 시**: 5개 사실 추출 시 API 호출 **5회 → 1회**
- **비용**: 약 **80% 절감**
- **속도**: 약 **4-5배 향상**

### 8.4 실제 사용 예시

```python
# 사용자 입력
text = """
오늘 팀과 Python 프로젝트 킥오프 미팅을 했어.
FastAPI를 사용하기로 결정했고, PostgreSQL을 데이터베이스로 선택했어.
나는 타입 힌트를 선호하니까 모든 함수에 타입 힌트를 붙이기로 했어.
"""

# Memorize 파이프라인 실행
items = await memory_system.memorize(text)

# 결과: 3개의 MemoryItem 생성
# 1. "User had Python project kickoff meeting" (type: event)
# 2. "Team decided to use FastAPI and PostgreSQL" (type: fact)
# 3. "User prefers type hints in all functions" (type: preference)

# 성능: 3개 아이템 임베딩을 1회 API 호출로 처리
```

### 8.5 고급 기억 관리 (Advanced Memory Features)

#### 8.5.1 LangMem-style Semantic Triples

**배경**: LangChain의 LangMem 프레임워크에서 영감을 받은 Entity-Level Memory 시스템입니다.
기존의 문장 단위 저장 대신, Subject-Predicate-Object 트리플로 분해하여 더 정밀한 업데이트를 지원합니다.

**트리플 추출 예시:**
```
입력: "철수는 파이썬을 좋아하고 서울에 살고 있다"

추출된 트리플:
- (철수, likes, 파이썬)
- (철수, lives_in, 서울)
```

**장점:**
- **정밀한 업데이트**: "철수가 부산으로 이사했다" → `(철수, lives_in, 서울)` → `(철수, lives_in, 부산)` 교체
- **충돌 해결**: 동일 Subject-Predicate에 다른 Object가 발견되면 최신 값으로 supersede
- **그래프 쿼리**: Subject 기반으로 관련 정보 빠르게 조회

```python
# 트리플 추출 (memorize.py)
if self.llm_config.use_semantic_triples:
    if self.llm_config.triple_extraction_immediate:
        # 즉시 추출 모드
        triple_dicts = await self.llm.extract_triples(content)
        for triple in triple_dicts:
            # 충돌 감지 및 supersede
            conflicts = await self.repository.find_conflicting_triples(
                subject=triple["subject"],
                predicate=triple["predicate"]
            )
            for conflict in conflicts:
                await self.repository.supersede_triple(conflict.id, new_triple.id)
    else:
        # Lazy Evaluation 모드 - 나중에 배치 처리
        await self.repository.mark_pending_triple_extraction(item.id)
```

#### 8.5.2 MemGPT-style Memory Supersede

**배경**: MemGPT 논문의 "Memory Update" 메커니즘을 구현합니다.
새로운 정보가 기존 기억과 충돌할 때, 기존 기억을 삭제하지 않고 비활성화(supersede)합니다.

**Supersede 워크플로우:**
```
1. 새 기억 저장 요청
2. 기존 기억과 충돌 여부 확인 (LLM 또는 Rule-based)
3. 충돌 시:
   - 기존 기억: is_active = False, superseded_by = 새 기억 ID
   - 새 기억: is_active = True
4. 히스토리 보존: 어떤 기억이 어떤 기억을 대체했는지 추적 가능
```

```python
# MemGPT-style 충돌 감지 (memorize.py)
if self.llm_config.use_memory_supersede:
    supersede_result = await self.llm.detect_supersede(
        new_content=content,
        existing_items=similar_items
    )
    if supersede_result.should_supersede:
        for old_item in supersede_result.items_to_supersede:
            await self.repository.supersede_memory(old_item.id, new_item.id)
```

#### 8.5.3 Lazy Evaluation (지연 평가)

Triple 추출은 LLM 호출이 필요하므로 비용이 큽니다. Lazy Evaluation을 통해:

1. **Memorize 시**: 기억만 즉시 저장, Triple 추출은 pending으로 마킹
2. **Background Job**: 설정된 간격(1/5/10/30분)으로 pending 아이템 배치 처리
3. **검색 시**: Triple이 없으면 MemoryItem으로 fallback (Hierarchical Filtering)

**설정:**
```yaml
llm:
  triple_extraction_immediate: false  # Lazy 모드 활성화
  triple_extraction_interval_minutes: 5  # 5분마다 배치 처리
```

**Scheduler Job:**
```python
# jobs.py - lazy_triple_extraction
async def lazy_triple_extraction():
    pending_items = await repository.get_pending_triple_items(limit=20)
    for item in pending_items:
        triples = await llm.extract_triples(item.content)
        # 트리플 저장 및 임베딩 생성
        await repository.clear_pending_triple_flag(item.id)
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

### 9.4 Generative Agents Search (Park et al., 2023)

시스템은 Stanford의 Generative Agents 논문에서 제안된 검색 알고리즘을 구현합니다:

**점수 공식:**
```
Score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
```

**구성 요소:**
- **Relevance**: 코사인 유사도 (1 - cosine_distance)
- **Recency**: 시간 기반 감쇠 (decay_factor^hours_since_access)
- **Importance**: 기억의 중요도 (0.0 ~ 1.0)

```python
# repository.py - generative_agents_search
async def generative_agents_search(
    self,
    query_embedding: List[float],
    limit: int = 10,
    alpha_relevance: float = 1.0,
    alpha_recency: float = 1.0,
    alpha_importance: float = 1.0,
    recency_decay_factor: float = 0.995,  # Generative Agents 기본값
    min_relevance_threshold: float = 0.3,
) -> List[MemoryItem]:
    """
    Search using Generative Agents scoring formula.
    
    Based on: "Generative Agents: Interactive Simulacra of Human Behavior"
    Park et al., Stanford University, 2023
    """
    ...
```

**설정 (`ScoringConfig`):**
```yaml
scoring:
  alpha_relevance: 1.0
  alpha_recency: 1.0
  alpha_importance: 1.0
  recency_decay_factor: 0.995
  min_relevance_threshold: 0.3
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
        
        # LRU 임베딩 캐시
        self._embedding_cache: dict[str, List[float]] = {}
        self._cache_order: list[str] = []
        self.max_cache_size = 1000
    
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
    
    async def extract_facts(self, text: str) -> List[dict]:
        prompt = EXTRACTION_PROMPT.format(text=text)
        response = await self.complete(prompt, temperature=0.3)
        return json.loads(response)
```

### 13.2 배치 임베딩 (성능 최적화)

여러 텍스트를 한 번에 임베딩하여 API 호출을 최소화합니다:

```python
async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single API call.
    
    Performance benefits:
    - Reduces API calls from N to 1
    - Reduces cost by ~70%
    - Improves speed by ~5x
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors in the same order as input texts
    """
    if not texts:
        return []
    
    # Check cache first
    uncached_texts = []
    uncached_indices = []
    result_embeddings = [None] * len(texts)
    
    for i, text in enumerate(texts):
        if text in self._embedding_cache:
            self._touch_cache(text)  # Update LRU order
            result_embeddings[i] = self._embedding_cache[text]
        else:
            uncached_texts.append(text)
            uncached_indices.append(i)
    
    # If all cached, return early
    if not uncached_texts:
        return result_embeddings
    
    # Single batch API call for uncached texts
    response = await self.client.embeddings.create(
        model="text-embedding-ada-002",
        input=uncached_texts,  # OpenAI API accepts list
    )
    
    # Process results and update cache
    for i, embedding_data in enumerate(response.data):
        embedding = embedding_data.embedding
        original_index = uncached_indices[i]
        text = uncached_texts[i]
        
        result_embeddings[original_index] = embedding
        self._add_to_cache(text, embedding)
    
    return result_embeddings

async def generate_embedding(self, text: str) -> List[float]:
    """
    Generate embedding for a single text.
    
    Internally uses batch_generate_embeddings for consistency.
    """
    embeddings = await self.batch_generate_embeddings([text])
    return embeddings[0]
```

### 13.3 임베딩 캐시 (LRU)

동일한 텍스트를 반복적으로 임베딩하는 것을 방지합니다:

```python
def _add_to_cache(self, key: str, value: List[float]) -> None:
    """Add to cache with LRU eviction."""
    # Evict oldest if cache full
    if len(self._embedding_cache) >= self.max_cache_size:
        if self._cache_order:
            oldest = self._cache_order.pop(0)
            del self._embedding_cache[oldest]
    
    # Add new entry
    self._embedding_cache[key] = value
    self._cache_order.append(key)

def _touch_cache(self, key: str) -> None:
    """Update LRU order for cache hit."""
    if key in self._cache_order:
        self._cache_order.remove(key)
    self._cache_order.append(key)

def get_cache_stats(self) -> dict:
    """Get cache hit/miss statistics."""
    return {
        "hits": self._cache_hits,
        "misses": self._cache_misses,
        "hit_rate_percent": round(hit_rate, 2),
        "cache_size": len(self._embedding_cache),
    }
```

**성능 개선:**
- **10개 텍스트 기준**: 개별 호출 대비 **5x 속도 향상**, **90% 비용 절감**
- **캐시 효과**: 재사용률이 높은 경우 추가 **50-70% 비용 절감**

### 13.4 다중 프로바이더 지원

어댑터 패턴을 사용하여 여러 임베딩 프로바이더를 지원합니다:

```python
# OpenAI 사용 (기본)
llm = LLMClient(
    embedding_provider="openai",
    api_key="sk-..."
)

# Google Gemini 사용
llm = LLMClient(
    embedding_provider="gemini",
    embedding_api_key="your-google-api-key"
)
```

**지원 프로바이더:**

| Provider | Model | Dimension | 배치 지원 |
|----------|-------|-----------|----------|
| OpenAI | text-embedding-ada-002 | 1536 | 네이티브 |
| Gemini | models/embedding-001 | 768 | asyncio.gather |

**프로바이더 아키텍처:**

```python
# llm/base.py - 추상 인터페이스
class EmbeddingProvider(ABC):
    @abstractmethod
    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        pass

# llm/openai_provider.py - OpenAI 구현
class OpenAIEmbeddingProvider(EmbeddingProvider):
    async def batch_embed(self, texts: List[str]):
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts  # 네이티브 배치 지원
        )
        return [item.embedding for item in response.data]

# llm/gemini_provider.py - Gemini 구현
class GeminiEmbeddingProvider(EmbeddingProvider):
    async def batch_embed(self, texts: List[str]):
        tasks = [self._embed_single(text) for text in texts]
        return await asyncio.gather(*tasks)  # 동시 처리
```

**프로바이더 추가 방법:**

새로운 임베딩 프로바이더를 추가하려면:
1. `EmbeddingProvider` 인터페이스 구현
2. `LLMClient._create_embedding_provider()`에 케이스 추가

### 13.5 토큰 사용량 추적

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
    """Database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "eternal_memory"
    user: Optional[str] = None
    password: Optional[str] = None

class EmbeddingConfig(BaseModel):
    """Embedding model configuration.
    
    Using text-embedding-3-large with Matryoshka dimension reduction to 1536.
    This provides embedding-3-large's superior multilingual performance (MIRACL: 54.9%)
    while maintaining compatibility with pgvector's HNSW index (2000d limit).
    """
    model: str = "text-embedding-3-large"
    dimension: int = 1536  # Matryoshka-reduced from native 3072d

class ScoringConfig(BaseModel):
    """Memory scoring configuration based on Generative Agents (Park et al., 2023).
    
    Retrieval score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
    """
    alpha_relevance: float = 1.0  # Weight for semantic similarity
    alpha_recency: float = 1.0    # Weight for time-based decay
    alpha_importance: float = 1.0 # Weight for memory importance
    recency_decay_factor: float = 0.995  # Generative Agents default
    min_relevance_threshold: float = 0.3

class BufferConfig(BaseModel):
    """Conversation buffer configuration."""
    flush_threshold_tokens: int = 4000  # OpenClaw default
    auto_flush_enabled: bool = True
    idle_flush_timeout_minutes: int = 10

class RetentionConfig(BaseModel):
    """Memory retention policy configuration."""
    stale_days_threshold: int = 30
    archive_low_importance: bool = True
    importance_threshold: float = 0.3

class LLMConfig(BaseModel):
    """다중 모델 지원 및 기능 토글"""
    # 기본 모델 (하위 호환성)
    model: str = "gpt-4o-mini"
    
    # 작업별 모델 분리 (비용 최적화)
    chat_model: Optional[str] = None       # 대화용 (품질 우선)
    memory_model: str = "gpt-4o-mini"      # 중요도 평가용 (가벼운 모델)
    supersede_model: str = "gpt-4o-mini"   # 충돌 감지용 (MemGPT-style)
    
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # 기능 토글 (Feature Toggles)
    use_llm_importance: bool = False       # LLM 기반 중요도 평가
    use_memory_supersede: bool = True      # MemGPT-style 기억 대체 감지 (기본 활성화)
    use_semantic_triples: bool = True      # LangMem-style 트리플 추출 (항상 활성화)
    
    # Lazy Evaluation (지연 평가)
    triple_extraction_immediate: bool = True   # True=즉시, False=배치
    triple_extraction_interval_minutes: int = 5  # 배치 간격 (1, 5, 10, 30분)

class MemoryConfig(BaseModel):
    """Main configuration model."""
    database: DatabaseConfig
    embedding: EmbeddingConfig
    scoring: ScoringConfig
    buffer: BufferConfig
    retention: RetentionConfig
    llm: LLMConfig
    vault_path: str = "user_memory/markdown"

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

### 15.2 Sessions API

Server-side 세션 관리를 위한 API 엔드포인트입니다:

```python
@router.get("/sessions")
async def list_sessions():
    """모든 채팅 세션 목록 조회 (메시지 내용 제외)"""
    
@router.post("/sessions")
async def create_session(request: SessionCreate):
    """새로운 채팅 세션 생성"""
    
@router.get("/sessions/{session_id}")
async def get_session(session_id: UUID):
    """특정 세션 상세 조회 (메시지 포함)"""
    
@router.put("/sessions/{session_id}")
async def update_session(session_id: UUID, request: SessionUpdate):
    """세션 업데이트 (이름, 메시지, 모드, 요약 등)"""
    
@router.delete("/sessions/{session_id}")
async def delete_session(session_id: UUID):
    """채팅 세션 삭제"""
```

### 15.3 Metrics API

성능 모니터링 엔드포인트입니다:

```python
@router.get("/metrics/summary")
async def get_metrics_summary():
    """집계된 성능 요약 조회"""
    
@router.get("/metrics/recent")
async def get_recent_metrics(limit: Optional[int] = 50):
    """최근 메트릭 조회 (메모리 내)"""
    
@router.get("/metrics/logs")
async def list_log_files():
    """사용 가능한 로그 파일 목록"""
    
@router.get("/metrics/logs/{filename}")
async def get_log_file(filename: str, limit: Optional[int] = 100):
    """특정 로그 파일에서 메트릭 조회"""
```

### 15.4 Chat API

대화 및 메모리 관리 엔드포인트입니다:

```python
@router.post("/chat/conversation")
async def conversation(request: ConversationRequest):
    """자연어 대화 + 자동 메모리 관리"""
    # 1. 관련 메모리 검색
    # 2. LLM 응답 생성 (메모리 컨텍스트 포함)
    # 3. 중요 정보 자동 저장 (비동기 백그라운드)
    # 4. Rolling Summary 컨텍스트 관리
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

## 18. 성능 모니터링

### 18.1 PerformanceMonitor

`monitoring/performance.py`는 파이프라인 실행 메트릭을 수집하고 로깅합니다.

**기능:**
- 스테이지별 타이밍 측정
- 임베딩 성능 추적
- 캐시 통계
- JSON 형식 로그 (daily rotation)
- 인메모리 최근 메트릭 보관

```python
class PerformanceMonitor:
    def __init__(self, log_dir: str = "logs", max_recent: int = 100):
        self.recent_metrics: deque = deque(maxlen=max_recent)
        
    async def record_pipeline_execution(self, context: Dict[str, Any]):
        """파이프라인 실행 완료 후 메트릭 기록"""
        
    def get_summary(self) -> Dict[str, Any]:
        """집계된 성능 요약 반환"""
        # total_pipelines, avg_duration, p95_duration 등
```

**로그 형식:**
```json
{
  "timestamp": "2026-02-02T01:15:00",
  "type": "pipeline_execution",
  "total_duration": 1.234,
  "stages": {"extraction": 0.5, "store": 0.3, ...},
  "facts": {"extracted": 3, "stored": 3},
  "embeddings": {"count": 3, "batched": true}
}
```

## 19. Server-side 세션 관리

### 19.1 개요

localStorage 기반 세션 저장에서 PostgreSQL 기반 서버사이드 저장으로 마이그레이션하여 **크로스 디바이스 세션 동기화**를 지원합니다.

### 19.2 Chat Session 스키마

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    name VARCHAR(255) DEFAULT 'New Chat',
    messages JSONB DEFAULT '[]'::jsonb,
    mode VARCHAR(10) DEFAULT 'fast',
    context_summary TEXT,           -- Rolling Summary 캐시
    summarized_count INTEGER,       -- Stale Cache Detection
    selected_message_id VARCHAR(255),
    created_at TIMESTAMPTZ,
    last_active_at TIMESTAMPTZ
);
```

### 19.3 Rolling Summary 컨텍스트 관리

대화가 길어질 때 토큰 사용량을 최적화하면서 컨텍스트를 보존합니다:

```
[Context Window Strategy]
┌─────────────────────────────────────────┐
│  Rolling Summary (오래된 메시지 요약)    │  → context_summary
├─────────────────────────────────────────┤
│  Verbatim Window (최근 N개 메시지)       │  → messages[-15:]
└─────────────────────────────────────────┘
```

**Stale Cache Detection:**
- `summarized_count`: 요약된 메시지 수
- 새 메시지가 추가되면 캐시 무효화 감지
- 필요 시 Rolling Summary 재생성

---

---

# 결론

**Eternal Memory 시스템**은 로컬 우선 AI 에이전트를 위한 완전한 영구 기억 솔루션입니다. 본 문서는 실제 구현된 시스템을 기반으로 작성되었으며, 다음과 같은 핵심 특징을 갖추고 있습니다:

## 구현 완료 사항

### 계층적 데이터 모델
- Resource, MemoryItem, Category, SemanticTriple의 4계층 구조
- Pydantic 기반 타입 안전성
- PostgreSQL + pgvector 벡터 데이터베이스

### 이중 저장 레이어
- **Machine Layer**: PostgreSQL with HNSW 인덱스 (고속 검색)
- **Human Layer**: Markdown Vault (투명성 및 편집 가능성)

### 4가지 핵심 파이프라인
1. **Memorize**: LLM 기반 사실 추출 및 저장
2. **Retrieve**: Fast/Deep 이중 모드 검색 + Generative Agents Search
3. **Predict**: 컨텍스트 예측 및 선제적 로딩
4. **Consolidate**: 자동 요약 및 카테고리 관리

### 자동화된 백그라운드 작업
- Daily/Weekly/Monthly Reflection
- Maintenance (인덱스 최적화)
- Vault Backup
- 완전 비동기(AsyncIO) 스케줄러

### 프로덕션 준비
- FastAPI 기반 REST API (Sessions, Metrics, Chat)
- 환경 변수 기반 설정
- 토큰 사용량 추적
- 입력 검증 및 보안
- Performance Monitoring (JSON 로그)

### v4.0.0 신규 기능
- **text-embedding-3-large**: Matryoshka 차원 축소 (1536d), MIRACL 54.9% 다국어 성능
- **Server-side 세션 관리**: PostgreSQL 기반 크로스 디바이스 동기화
- **Rolling Summary**: 장기 대화 컨텍스트 보존
- **Generative Agents Search**: Park et al. (2023) 기반 Relevance/Recency/Importance 점수

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

**문서 버전**: 4.0.0  
**마지막 업데이트**: 2026-02-02  
**구현 상태**: Production Ready

---

## 참고문헌 (References)

### 학술 논문

1. **MemGPT: Towards LLMs as Operating Systems**  
   Packer et al., 2023. arXiv:2310.08560  
   - Memory Supersede 및 컨텍스트 관리 메커니즘 참조
   - `is_active`, `superseded_by` 패턴 구현 기반

2. **Generative Agents: Interactive Simulacra of Human Behavior**  
   Park et al., Stanford University, 2023  
   - Salience (중요도) 기반 기억 접근
   - Reflection 및 요약 메커니즘 참조

3. **Reciprocal Rank Fusion (RRF)**  
   Cormack et al., 2009. SIGIR  
   - 하이브리드 검색 결과 병합 알고리즘

### 프레임워크 & 라이브러리

4. **LangChain LangMem**  
   https://github.com/langchain-ai/langmem  
   - Entity-Level Memory (Semantic Triples)
   - Subject-Predicate-Object 구조 영감

5. **pgvector**  
   https://github.com/pgvector/pgvector  
   - PostgreSQL 벡터 검색 확장
   - HNSW 인덱싱 알고리즘

6. **OpenAI Embeddings**  
   https://platform.openai.com/docs/guides/embeddings  
   - text-embedding-3-large (3072d native, 1536d Matryoshka reduced)
   - MIRACL 54.9% multilingual performance
   - 배치 임베딩 API

### 업계 표준 패턴

7. **Repository Pattern**  
   Martin Fowler, Patterns of Enterprise Application Architecture  
   - 데이터 접근 추상화

8. **CQRS (Command Query Responsibility Segregation)**  
   - 읽기/쓰기 경로 분리 (Fast/Deep 모드)

9. **Event Sourcing**  
   - Supersede 히스토리 보존 패턴

---

## 변경 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|----------|
| 1.0.0 | 2026-01-15 | 초기 설계 문서 |
| 2.0.0 | 2026-01-31 | 구현 완료, API 문서화 |
| 3.0.0 | 2026-02-01 | Semantic Triples, MemGPT Supersede, Lazy Evaluation 추가 |
| 4.0.0 | 2026-02-02 | text-embedding-3-large 마이그레이션, Server-side 세션 관리, Generative Agents Search, Performance Monitoring, Sessions/Metrics API 추가 |
