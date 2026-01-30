
Eternal Memory 사양서
# 1. 서론: 개인화 AI와 기억의 주권 (Sovereignty of Memory)
2026년 초, 인공지능 에이전트 시장은 거대한 패러다임의 전환을 맞이했습니다. 클라우드
기반의 거대 언어 모델(LLM)들이 제공하는 편리함 이면에는, 사용자 데이터의 외부 유출이라는
프라이버시 문제와 세션이 종료되면 사라지는 휘발성 문맥(Context)의 한계가 존재했습니다.
이러한 배경 속에서 등장한 OpenClaw (구 Moltbot, Clawdbot)는 단순한 오픈소스 프로젝트를
넘어 "로컬 우선(Local-First)"과 "영구적 기억(Eternal Memory)"이라는 두 가지 핵심 가치를
중심으로 AI 에이전트의 새로운 표준을 제시했습니다.1
OpenClaw가 단기간 내에 GitHub 스타 10만 개를 돌파하며 폭발적인 관심을 받은 것은 우연이
아닙니다. 이는 사용자가 자신의 기기에서 직접 구동하며, 모든 기억과 데이터를 로컬 파일
시스템에 저장하여 완벽하게 통제할 수 있다는 점에 기인합니다.3 특히 본 보고서가 집중적으로
분석할 영구적 기억 기술은 에이전트가 사용자의 선호도, 과거의 대화, 업무 패턴을 단순히
저장하는 것을 넘어, 이를 구조화하고 스스로 진화시키며 사용자의 의도를 선제적으로
파악하는 **능동적 지능(Proactive Intelligence)**의 기반이 됩니다.5
기존의 RAG(Retrieval-Augmented Generation) 시스템이 사용자의 질문에 대한 답변을 찾기
위해 수동적으로 데이터베이스를 검색했다면, OpenClaw의 기억 시스템은 사용자가 질문하기
전에 필요한 정보를 미리 예측하고 준비합니다. 이는 memU 프레임워크와 Markdown
Memory Vault라는 독창적인 아키텍처를 통해 구현되었습니다.5
본 연구 보고서는 OpenClaw의 기억 시스템이 어떻게 작동하는지 그 내부 메커니즘을 층위별로
해부하고, 이를 재현하기 위한 구체적인 기술 사양을 제시하는 것을 목적으로 합니다. 보고서의
후반부에는 코딩 에이전트가 즉시 구현에 착수할 수 있도록 작성된 상세 기술 사양서
eternal_memory_spec.md가 포함되어 있습니다.
# 2. OpenClaw 생태계와 아키텍처 개요

OpenClaw의 기억 시스템을 이해하기 위해서는 먼저 그가 속한 전체 생태계와 아키텍처의
철학을 파악해야 합니다. OpenClaw는 단일한 프로그램이 아니라, 여러 모듈이 유기적으로
결합된 복합 시스템입니다.

# 2. 1 로컬 우선 게이트웨이 (Local-First Gateway)

OpenClaw의 중추 신경계는 로컬 우선 게이트웨이입니다. Node.js 기반으로 구축된 이
게이트웨이는 사용자의 기기(Mac Mini, 로컬 서버 등)에서 백그라운드 데몬으로 실행되며, 세션
관리, 도구(Tool) 라우팅, 그리고 무엇보다 중요한 기억의 입출력을 통제하는 컨트롤
플레인(Control Plane) 역할을 수행합니다.4 게이트웨이는 외부 메신저(Telegram, Discord,
Slack 등)로부터 들어오는 인바운드 메시지를 "신뢰할 수 없는 입력(Untrusted Input)"으로
간주하고, 이를 격리된 샌드박스 환경에서 처리한 후 기억 시스템으로 전달합니다.6
이러한 구조는 기억의 보안성을 극대화합니다. 외부 통신 채널과 기억 저장소 사이에 강력한
게이트웨이가 존재함으로써, 해커나 악의적인 프롬프트 주입(Prompt Injection)이 기억
데이터베이스에 직접 접근하는 것을 원천적으로 차단합니다. 또한, 이 게이트웨이는 다중
에이전트 라우팅(Multi-agent Routing)을 지원하여, 사용자의 질문 유형에 따라 적절한 전문
에이전트(예: 코딩 에이전트, 스케줄러 에이전트)에게 문맥을 전달하고, 각 에이전트가 공유된
기억 저장소(Shared Memory)를 참조할 수 있게 합니다.7
# 2. 2 memU 프레임워크: 기억의 엔진

OpenClaw의 기억 능력은 memU (NevaMind-AI 개발)라는 특수 목적의 기억 프레임워크에
전적으로 의존합니다. memU는 일반적인 데이터베이스 라이브러리가 아니라, "24/7 구동되는
능동적 에이전트"를 위해 설계된 기억 운영체제(Memory OS)에 가깝습니다.5
memU의 핵심 철학은 **"저장(Storage)이 아닌 이해(Understanding)"**입니다. 단순히
텍스트를 벡터로 변환하여 저장하는 것을 넘어, 입력된 정보의 의미를 해석하고, 이를 기존의
지식 그래프와 연결하며, 시간이 지남에 따라 중요도가 낮은 기억은 망각하고 중요한 기억은
강화하는 수명 주기(Lifecycle) 관리를 수행합니다. 이는 에이전트가 마치 인간처럼 단기
기억을 장기 기억으로 전환하고, 필요할 때 이를 회상(Recall)하는 인지적 과정을 모방한
것입니다.
# 2. 3 데이터 주권과 Markdown Memory Vault

OpenClaw 아키텍처에서 가장 독창적이고 사용자 친화적인 부분은 Markdown Memory
Vault입니다.6 대부분의 AI 에이전트가 효율성을 이유로 JSON이나 이진(Binary) 포맷의
데이터베이스를 사용하는 것과 달리, OpenClaw는 사용자의 기억을 사람이 읽을 수 있는
Markdown 파일(.md) 형태로 로컬 파일 시스템에 저장합니다.
이러한 설계는 다음과 같은 결정적인 이점을 제공합니다:
# 1. 투명성(Transparency): 사용자는 언제든지 폴더를 열어 에이전트가 자신에 대해 무엇을

기억하고 있는지 확인할 수 있습니다.
# 2. 수정 가능성(Editability): 에이전트가 잘못된 정보를 기억했다면, 사용자는 텍스트

에디터로 파일을 열어 직접 수정할 수 있습니다. 이는 AI의 환각(Hallucination)을 교정하는
가장 확실한 방법입니다.
# 3. 이식성(Portability): 특정 데이터베이스 벤더에 종속되지 않으므로, 기기를 변경하거나

다른 에이전트 소프트웨어로 이주할 때도 기억 파일을 그대로 복사하여 가져갈 수

있습니다.
이 Markdown 파일들은 단순히 텍스트 덩어리가 아니라, memU 프레임워크에 의해 정교하게
관리되는 구조화된 지식 베이스입니다. 백그라운드에서는 이 파일들의 내용이 벡터 임베딩과
동기화되어 검색 효율성을 보장합니다.
# 3. 심층 분석: memU의 계층적 기억 구조

OpenClaw의 기억 시스템은 인간의 인지 모델을 차용하여 3단계의 계층적 구조(Hierarchical
Architecture)로 설계되어 있습니다. 이 구조는 원시 데이터가 정제된 지식으로 변환되는 과정을
체계화합니다.5
# 3. 1 1계층: 리소스 (Resource) - 원천의 보존

가장 하위 계층인 **리소스(Resource)**는 에이전트가 접한 모든 원시 데이터(Raw Data)를
의미합니다. 여기에는 사용자와의 대화 로그 전체, 공유된 PDF 문서, 분석한 이미지, 웹페이지의
스크랩 데이터 등이 포함됩니다.
- 역할: 기억의 "진실성(Truth)"을 보증하는 근거 자료입니다. 에이전트가 특정 사실을
기억해냈을 때, "이 정보가 어디서 왔는가?"에 대한 출처 추적(Traceability)을 가능하게
합니다.
- 저장 방식: 원본 파일의 경로나 URL, 그리고 텍스트로 변환된 스냅샷 형태로 저장됩니다.
- 능동적 활용: 리소스 계층은 수동적으로 저장만 되는 것이 아닙니다. memU는
백그라운드에서 리소스 계층을 지속적으로 모니터링하며 새로운 패턴이나 연관성을
찾아냅니다.5
# 3. 2 2계층: 아이템 (Item) - 사실의 추출

아이템(Item) 계층은 리소스에서 추출된 구체적이고 독립적인 사실(Fact) 단위입니다. LLM은
리소스의 방대한 텍스트를 분석하여 "무엇이 중요한 정보인가?"를 판단하고, 이를 구조화된
데이터로 추출합니다.
- 구조: 각 아이템은 고유 ID, 내용 요약, 생성 시간, 그리고 원본 리소스에 대한 참조 링크를
가집니다.
- 예시: "대화 로그 2026-01-31.txt"라는 리소스에서 "사용자는 파이썬보다 타입스크립트를
선호한다"는 사실을 추출하여 하나의 아이템으로 저장합니다.
- 검색: 사용자의 질문에 대한 직접적인 답변을 구성할 때 가장 빈번하게 조회되는
계층입니다. RAG 시스템에서 주로 검색되는 '청크(Chunk)'와 유사하지만, 단순한 텍스트
조각이 아니라 의미 단위로 정제된 정보라는 점에서 차이가 있습니다.
# 3. 3 3계층: 카테고리 (Category) - 맥락의 형성

최상위 계층인 **카테고리(Category)**는 개별 아이템들이 모여 형성된 주제(Topic) 또는
**맥락(Context)**입니다. 이는 사전에 정의된 고정된 분류가 아니라, 기억이 축적됨에 따라

스스로 조직화(Self-organizing)되는 동적인 구조입니다.
- 자동 분류(Auto-categorization): 새로운 기억 아이템이 생성되면, 시스템은 기존
카테고리와의 의미적 유사성을 분석하여 적절한 그룹에 배치하거나, 새로운 카테고리를
생성합니다.5
- 요약(Summarization): 각 카테고리는 포함된 아이템들의 내용을 종합한 '상위 요약본'을
유지합니다. 이는 사용자가 광범위한 질문(예: "내가 최근에 무슨 프로젝트를
고민했지?")을 던졌을 때, 수백 개의 아이템을 일일이 검색하는 대신 카테고리의 요약본을
통해 신속하게 답변할 수 있게 합니다.
- 예측(Prediction): 카테고리 계층은 에이전트가 사용자의 다음 행동을 예측하는 기반이
됩니다. 특정 카테고리(예: '여행 계획')가 활성화되면, 관련된 하위 아이템들이 미리
로딩되어 대기 상태에 들어갑니다.
계층 (Layer) 데이터 성격 처리 방식 주요 역할 (Primary
(Nature) (Processing) Role)
Resource 비정형 원시 데이터 전체 저장 및 인덱싱 출처 보존,
백그라운드 패턴
분석
Item 정형화된 사실 단위 LLM 추출 및 벡터화 구체적 사실 회상,
질의응답
Category 구조화된 주제/맥락 클러스터링 및 요약 문맥 파악, 행동
예측, 자동 분류
# 4. 이중 모드 지능: 검색과 추론의 결합

OpenClaw 기억 시스템의 또 다른 기술적 혁신은 **이중 모드 지능(Dual-Mode
Intelligence)**이라 불리는 하이브리드 검색 전략입니다.5 이는 속도와 깊이 사이의
트레이드오프를 해결하기 위해 고안되었습니다.
# 4. 1 RAG 기반 검색 (Fast Context)

첫 번째 모드는 전통적인 RAG(Retrieval-Augmented Generation) 방식입니다.
- 메커니즘: pgvector와 같은 벡터 데이터베이스를 사용하여, 사용자의 쿼리를 임베딩
벡터로 변환하고, 저장된 기억 아이템 중 코사인 유사도가 높은 것들을 밀리초(ms) 단위로
찾아냅니다.5
- 장점: 매우 빠르고 비용 효율적입니다. 대화가 끊기지 않고 실시간으로 반응해야 하는
상황에 적합합니다.
- 한계: 키워드 매칭이나 단순 유사성에 의존하기 때문에, 복합적인 추론이 필요한 질문이나

시간적 맥락이 중요한 질문에는 취약할 수 있습니다.
# 4. 2 LLM 기반 검색 (Deep Reasoning)

두 번째 모드는 LLM 기반 검색 또는 **비-임베딩 검색(Non-embedding search)**입니다.8
- 메커니즘: LLM이 Markdown 파일로 저장된 기억의 구조(카테고리 및 요약)를 직접
'읽고(Read)' 판단합니다. 임베딩에 의존하지 않고, LLM의 추론 능력을 활용하여 파일
시스템을 탐색합니다.
- 심층적 추론: "지난달에 내가 힘들다고 했을 때 네가 뭐라고 조언했지?"와 같은 질문은
단순한 키워드 검색으로는 찾기 어렵습니다. LLM 기반 검색은 '힘들다'는 감정적 맥락과
'조언'이라는 행위적 맥락을 연결하여, 관련된 카테고리 파일을 열어보고 정확한 답변을
찾아냅니다.
- 쿼리 진화(Query Evolution): 사용자의 질문이 모호할 경우, 시스템은 현재까지의 대화
문맥을 바탕으로 질문을 재구성(Rewrite)하여 검색 정확도를 높입니다.5
OpenClaw는 상황에 따라 이 두 가지 모드를 동적으로 전환하거나 병합하여 사용합니다.
일상적인 대화에서는 RAG 모드로 빠르게 반응하고, 사용자가 복잡한 업무 지시를 내리거나
과거의 프로젝트 맥락을 물을 때는 LLM 모드로 전환하여 깊이 있는 기억을 불러옵니다.
# 5. 능동적 기억의 수명 주기 (Proactive Memory

Lifecycle)
OpenClaw가 "살아있는 기억"을 가진 것처럼 느껴지는 이유는 기억 데이터가 정적이지 않고
끊임없이 순환하며 갱신되기 때문입니다. 이를 **능동적 기억 수명 주기(Proactive Memory
Lifecycle)**라고 합니다.5
# 5. 1 모니터링 (Monitor)

에이전트는 사용자의 명시적인 명령어뿐만 아니라, 열려 있는 창, 수정된 파일, 시간대 등 환경
변수를 지속적으로 모니터링합니다. 이는 memU의 백그라운드 프로세스로 동작하며, 사용자의
작업 흐름을 방해하지 않습니다.
# 5. 2 기억 및 추출 (Memorize & Extract)

유의미한 정보가 감지되면 memorize() 함수가 트리거됩니다. 이 과정에서 LLM은 입력된
데이터에서 '일회성 잡담'과 '장기 기억 가치가 있는 정보'를 구분합니다(Salience Detection).
선별된 정보는 즉시 MemoryItem으로 구조화되어 저장됩니다.
# 5. 3 예측 (Predict)

이 단계가 OpenClaw의 차별점입니다. 시스템은 현재 상황과 과거의 패턴을 분석하여 사용자의
**다음 의도(Next Step Intent)**를 예측합니다. 예를 들어, 사용자가 "서버 로그 확인해줘"라고

말하면, 시스템은 과거의 패턴을 바탕으로 "이 사용자는 로그 확인 후 보통 에러 리포트를
작성하라고 지시한다"는 것을 예측합니다.
# 5. 4 주입 (Inject)

예측된 정보와 관련 기억들은 사용자가 요청하기 전에 미리 시스템 프롬프트(System
Prompt)에 **주입(Injection)**됩니다. 따라서 사용자가 후속 질문을 했을 때, 에이전트는
별도의 검색 과정 없이 즉각적으로, 그리고 맥락에 완벽하게 부합하는 답변을 내놓을 수
있습니다.
# 5. 5 자기 진화 (Self-Evolution)

시간이 지남에 따라 기억 저장소는 비대해질 수 있습니다. OpenClaw는 사용
빈도(Frequency)와 최신성(Recency)을 기반으로 기억을 재구성합니다. 자주 조회되는 기억은
'활성 메모리'로 승격되어 검색 우선순위가 높아지고, 오랫동안 사용되지 않은 기억은 요약되어
아카이브되거나(망각 곡선 적용), 더 상위 카테고리로 통합됩니다.8
# 6. 구현 사양서: eternal_memory_spec.md

다음은 위에서 분석한 OpenClaw의 영구적 기억 시스템을 코딩 에이전트가 재현할 수 있도록
작성된 상세 기술 사양서입니다. 이 문서는 파일 구조, 데이터베이스 스키마, API 인터페이스,
그리고 핵심 알고리즘의 의사 코드(Pseudo-code)를 포함합니다.
Technical Specification: OpenClaw-style
Eternal Memory System
Document Version: 1.0.0
Target Framework: Python (Backend) / Node.js (Gateway Bridge)
Reference Architecture: memU, Markdown Memory Vault
# 1. System Overview (시스템 개요)

본 사양서는 로컬 우선(Local-First) AI 에이전트를 위한 영구적 기억 시스템인 Eternal
Memory의 구현을 정의합니다. 본 시스템은 **PostgreSQL (pgvector)**를 활용한 고속 벡터
검색과 Markdown Filesystem을 활용한 인간 가독성(Human-Readability) 저장소를
하이브리드로 운용합니다.

# 1. 1 Core Objectives (핵심 목표)

# 1. Persistence: 세션 종료 후에도 데이터가 영구적으로 보존되어야 한다.

# 2. Proactivity: 사용자 요청 전, 상황에 맞는 문맥을 선제적으로 로딩해야 한다.

# 3. Transparency: 모든 기억 데이터는 사용자가 읽을 수 있는 Markdown 파일로

미러링되어야 한다.
# 4. Hybrid Retrieval: 임베딩 기반 검색(RAG)과 LLM 기반 파일 분석(Reasoning)을 지원해야

한다.
# 2. Directory & File Structure (디렉토리 및 파일 구조)

사용자의 홈 디렉토리에 위치한 .openclaw 폴더 내에 기억 저장소를 구축합니다.
~/.openclaw/
├── memory/ # Markdown Memory Vault (Human Layer)
│ ├── profile.md # 사용자 기본 프로필 (이름, 선호도, 핵심 설정)
│ ├── index.json # 카테고리-파일 매핑 인덱스 (System Layer)
│ ├── timeline/ # 시간순 로그 (Raw Resources)
│ │ ├── 2026-01.md
│ │ └── 2026-02.md
│ └── knowledge/ # 주제별로 분류된 지식 (Categories)
│ ├── coding/
│ │ ├── python.md
│ │ └── typescript.md
│ ├── projects/
│ │ ├── openclaw_bot.md
│ │ └── personal_blog.md
│ └── personal/
│ └── relationships.md

├── storage/ # Vector Database & Blobs (Machine Layer)
│ ├── vector_store/ # ChromaDB or SQLite-vss files (if not using Postgres)
│ └── blobs/ # Images, PDF extracts
└── config/
└── memory_config.yaml # 설정 파일 (Retention policy, Embedding model)
# 3. Database Schema (데이터베이스 스키마)

PostgreSQL과 pgvector 확장을 사용한 스키마 정의입니다. 이는 검색 속도와 데이터 무결성을
위한 Machine Layer입니다.
```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;
-- 1. Resources: Raw Data Source
CREATE TABLE resources (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
uri TEXT NOT NULL, -- File path or URL
modality VARCHAR(50) NOT NULL, -- 'text', 'image', 'conversation'
content TEXT, -- Full text content
created_at TIMESTAMPTZ DEFAULT NOW(),
metadata JSONB -- Extra info (sender, app context)
);
-- 2. Memory Categories: Semantic Clusters
CREATE TABLE categories (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name TEXT NOT NULL,
description TEXT,
parent_id UUID REFERENCES categories(id),
summary TEXT, -- High-level summary of contained items
last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Memory Items: Extracted Facts
CREATE TABLE memory_items (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
category_id UUID REFERENCES categories(id),
resource_id UUID REFERENCES resources(id),
content TEXT NOT NULL, -- The actual fact/memory
embedding vector(1536), -- Vector for RAG (OpenAI ada-002 compatible)
importance FLOAT DEFAULT 0.5, -- 0.0 to 1.0 (Salience)
created_at TIMESTAMPTZ DEFAULT NOW(),
last_accessed TIMESTAMPTZ DEFAULT NOW(),
-- Full Text Search index
fts_content TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);
-- Indexes for performance
CREATE INDEX idx_memory_embedding ON memory_items USING hnsw (embedding
vector_cosine_ops);
CREATE INDEX idx_memory_fts ON memory_items USING GIN (fts_content);
CREATE INDEX idx_category_parent ON categories(parent_id);
```

# 4. API Interface Definitions (인터페이스 정의)

시스템 구현을 위한 핵심 클래스와 메서드 서명(Signature)입니다. Python (Pydantic) 스타일로
정의합니다.
# 4. 1 Data Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import uuid

class MemoryItem(BaseModel):
id: uuid.UUID = Field(default_factory=uuid.uuid4)
content: str
category_path: str # e.g., "knowledge/coding/python"
type: Literal["fact", "preference", "event", "plan"]
confidence: float = 1.0
source_resource_id: Optional[str] = None
created_at: datetime = Field(default_factory=datetime.now)
class RetrievalResult(BaseModel):
items: List[MemoryItem]
related_categories: List[str]
suggested_context: str # Proactive suggestion string
```

# 4. 2 Core Interface (Abstract Base Class)

```python
from abc import ABC, abstractmethod
class EternalMemoryEngine(ABC):
@abstractmethod
async def memorize(self, text: str, metadata: dict = None) -> MemoryItem:
"""
Input Pipeline:
```

# 1. Extract salient facts from text via LLM.

# 2. Assign to existing or new category.

# 3. Save to Vector DB.

# 4. Append to corresponding Markdown file.

"""
```python
pass
@abstractmethod
async def retrieve(self, query: str, mode: Literal["fast", "deep"] = "fast") -> RetrievalResult:
"""
Output Pipeline:
- Mode 'fast': Vector similarity search + Keyword search.
- Mode 'deep': LLM reads summary of categories -> Opens Markdown files -> Reasons answer.
"""
pass

@abstractmethod
async def consolidate(self):
"""
Maintenance Pipeline:
```

# 1. Scan for rarely accessed items.

# 2. Summarize them into 'archived' files.

# 3. Re-cluster categories if they become too large.

"""
```python
pass
@abstractmethod
async def predict_context(self, current_context: dict) -> str:
"""
Proactive Pipeline:
Based on time, open apps, and recent logs, return a context string
to be injected into the System Prompt.
"""
pass
```

# 5. Implementation Logic & Prompts (구현 로직 및

프롬프트)
코딩 에이전트가 사용할 구체적인 로직 흐름입니다.
# 5. 1 The memorize Pipeline (기억 파이프라인)

# 1. Input: 사용자 메시지 수신 ("나 다음 주 월요일에 서울로 출장 가. 기차표 알아봐 줘.")

# 2. Extraction Prompt (LLM Call):

Analyze the following input and extract independent memory items.
Focus on FACTS, PREFERENCES, EVENTS, and GOALS.
Ignore trivial chit-chat.
Input: "나 다음 주 월요일에 서울로 출장 가. 기차표 알아봐 줘."
Output Format (JSON):
# 3. Storage Action:

  - JSON 파싱 후 memory_items 테이블에 INSERT (임베딩 포함).
  - ~/.openclaw/memory/personal/schedule.md 파일 열기.
  - 파일 끝에 - [2026-01-31] User has a business trip to Seoul next Monday. 추가.
  - 파일 저장 및 닫기.
# 5. 2 The retrieve Pipeline (회상 파이프라인)

# 1. Query Evolution: 사용자의 모호한 질문("그때 거기 어디였지?")을 문맥을 포함하여

구체화("지난달 출장 갔을 때 묵었던 호텔 이름이 무엇인가?")로 변환.
# 2. Hybrid Search:

  - pgvector로 코사인 유사도 0.8 이상의 아이템 Top 5 검색.
  - 검색된 아이템의 category 필드를 확인 (예: personal/travel).
  - 해당 카테고리의 Markdown 파일(personal/travel.md)의 요약(Summary) 섹션을 로드.
# 3. Reasoning: 검색된 벡터 아이템과 Markdown 요약을 종합하여 LLM에게 최종 답변 생성

요청.
# 5. 3 Security & Permissions (보안 로직)

- File Mode: ~/.openclaw/memory 폴더는 생성 시 chmod 700으로 설정하여 소유자 외 접근
차단.
- Sanitization: Markdown 파일에 기록하기 전, 모든 입력 텍스트에서 스크립트 태그나 제어
문자 제거.
- Isolation: 게이트웨이 프로세스는 기억 시스템에 접근할 때 별도의 MemoryService
클래스를 통해서만 통신하며, 직접적인 파일 I/O나 DB 쿼리는 캡슐화되어야 함.
# 7. 결론 및 향후 전망

본 보고서를 통해 OpenClaw의 영구적 기억이 단순한 데이터베이스가 아니라,
인식(Perception), 저장(Storage), 추론(Reasoning)이 유기적으로 결합된 인지 시스템임을
확인했습니다. 특히 Markdown을 활용한 투명한 저장 방식과 memU 프레임워크의 능동적 예측
기능은 개인화 AI 에이전트가 나아가야 할 방향을 명확히 보여줍니다.
제공된 eternal_memory_spec.md는 이러한 아키텍처를 재현하기 위한 설계도입니다. 이를
바탕으로 구현된 에이전트는 사용자와의 상호작용이 거듭될수록 더 똑똑해지고, 사용자의
의도를 더 깊이 이해하는 진정한 디지털 동반자(Digital Companion)로 진화할 것입니다. 이는
단순히 편의성을 높이는 기술을 넘어, 사용자가 자신의 데이터에 대한 주권을 유지하면서도
최첨단 AI의 혜택을 누릴 수 있는 '개인용 운영체제(Personal OS)'의 초석이 될 것입니다.
참고 문헌 및 출처 표기
본 보고서의 분석과 사양은 다음의 연구 자료들을 기반으로 작성되었습니다:
- OpenClaw 및 Moltbot 프로젝트 개요 및 역사 1
- memU 프레임워크 아키텍처 및 기능 명세 5
- Markdown Memory Vault 및 보안 아키텍처 6
- OpenClaw GitHub 저장소 구조 및 소스 코드 분석 7
- 로컬 우선(Local-First) AI 트렌드 및 기술적 특징 3
보고서 종료. 코딩 에이전트는 포함된 eternal_memory_spec.md 섹션을 참조하여 개발을

시작하십시오.
참고 자료
# 1. Moltbot Molts Again And Becomes OpenClaw, Pushback And Concerns Grow -

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
