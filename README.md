# Eternal Memory System

**Next-Generation Entity-Level Persistent Memory for AI Agents**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

Eternal Memory는 차세대 AI 에이전트를 위한 **Entity-Level 영구 기억 시스템**입니다. 검증된 학술 연구(MemGPT, LangMem, Generative Agents)를 기반으로, AI 에이전트의 장기 기억 관리에서 직면하는 핵심 과제들을 해결합니다:

| Challenge | Our Solution |
|-----------|--------------|
| **정보 충돌** — 업데이트된 정보와 기존 정보가 혼재 | Semantic Triples로 엔티티 단위 자동 충돌 해결 |
| **검색 지연** — 대규모 기억에서의 응답 속도 저하 | HNSW 벡터 인덱스로 수백만 기억 중 ~50ms 검색 |
| **컨텍스트 비용** — 긴 대화의 토큰 폭증 | Multi-Tier Context로 일관된 토큰 예산 유지 |

### 🎓 Built on Validated Research

| Foundation | Source | Application |
|------------|--------|-------------|
| **Memory Supersede** | MemGPT (Packer et al., 2023) | 삭제 대신 비활성화로 히스토리 보존, 컨텍스트 관리 |
| **Semantic Triples** | LangMem (LangChain) | Subject-Predicate-Object 분해로 Entity-Level 정밀 업데이트 |
| **Salience Scoring** | Generative Agents (Stanford, 2023) | 중요도 기반 기억 평가, Reflection을 통한 장기 기억 구조화 |
| **Matryoshka Embeddings** | MRL (Kusupati et al., 2022) | text-embedding-3-large로 한국어↔영어 0.90+ 유사도 달성 |

### Hybrid Memory Architecture

Eternal Memory는 세 가지 레이어가 **상호 보완**하는 하이브리드 구조로 정밀성, 속도, 투명성을 동시에 달성합니다.

| Layer | Strength | Role |
|-------|----------|------|
| **Semantic Triples** | 정밀성 | `(Subject, Predicate, Object)` 분해로 엔티티 단위 충돌 해결 |
| **Vector Search** | 속도 | HNSW 인덱스로 수백만 기억 중 ~50ms 내 검색 |
| **Markdown Vault** | 투명성 | 사람이 읽고 편집 가능한 형태로 기억 미러링 |

**상호 보완 설계**: Triple 추출 지연 시 Vector가 즉시 검색을 제공하고, 복잡한 쿼리에서는 Triple이 정밀 결과를 Vector가 Fallback을 담당합니다.

### Multi-Tier Context Management

긴 대화에서도 효율적인 토큰 관리를 위해 **계층적 컨텍스트 압축**을 적용합니다.

| Tier | Content | Strategy |
|------|---------|----------|
| **Tier 1** | 최근 N턴 | 원본 유지 (Verbatim) |
| **Tier 2** | 이전 대화 | Rolling Summary로 압축 |
| **Tier 3** | 장기 기억 | Semantic Search로 필요 시 로드 |

→ 수백 턴의 대화도 일관된 토큰 예산 내에서 컨텍스트 유지

## ✨ Key Features

### Core Intelligence
- **🧠 Semantic Triples**: LangMem 스타일 (Subject, Predicate, Object) 지식 그래프
- **♻️ Memory Supersede**: MemGPT 논문 기반 - 삭제 대신 비활성화로 히스토리 보존
- **🔍 Hierarchical Retrieval**: Triple → MemoryItem → Fallback 계층적 검색
- **⚡ Lazy Evaluation**: 즉시 저장 → 백그라운드 Triple 추출 (80% 비용 절감)
- **🌐 Multilingual Precision**: text-embedding-3-large (1536d, Matryoshka) 기반

### Reliability & Persistence
- **☁️ Server-Side Sessions**: PostgreSQL 기반 세션 영속성 (멀티 디바이스 지원)
- **🛡️ Buffer Reliability**: `beforeunload`, `visibilitychange`, `pagehide`, 세션 전환 시 자동 플러시
- **🔄 Graceful Degradation**: Triple 추출 실패해도 MemoryItem으로 무중단 동작
- **📜 Rolling Summary**: Multi-Tier Context (Verbatim + Summary + Memory) 관리

### Developer Experience
- **📁 Markdown Vault**: 모든 기억을 사람이 읽기 쉬운 Markdown으로 미러링
- **🖥️ Modern UI**: React + TailwindCSS 기반 Chat/Settings/Database 인터페이스
- **🔄 Real-time Tracing**: Process Tab에서 AI 추론 과정 실시간 관찰

## 🚀 Quick Start

### 1. Install Everything

```bash
./scripts/install.sh
```

This will automatically:
- ✅ Install PostgreSQL 16 + pgvector extension
- ✅ Create and configure the database
- ✅ Set up Python virtual environment
- ✅ Install all Python dependencies
- ✅ Install UI dependencies (npm)
- ✅ Create configuration files

### 2. Add Your API Key

```bash
# Edit setting/.env and add:
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Application

```bash
./scripts/run.sh
```

This will start:
- 📡 **Backend API**: http://localhost:8000
- 💻 **Frontend UI**: http://localhost:5173

## 💻 System Requirements

- **Python**: 3.11+
- **PostgreSQL**: 14+ with pgvector extension
- **Node.js**: 18+ (for UI)
- **OS**: macOS, Linux, or WSL2

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                 React Frontend (Vite + TailwindCSS)            │
│              Chat / Settings / Database / Scheduling           │
└─────────────────────────────┬──────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                    API Layer (FastAPI)                         │
│        /chat, /memories, /stats, /settings, /schedule          │
└─────────────────────────────┬──────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│              Memory Engine (EternalMemorySystem)               │
│       Orchestrates pipelines, manages buffer & lifecycle       │
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

## 📂 Project Structure

```
eternal_memory/
├── docs/                             # Documentation
│   └── memory_spec.md                # Detailed specification
│
├── scripts/                          # Utility scripts
│   ├── install.sh                    # Full installation
│   ├── run.sh                        # Start application
│   ├── migrate_embeddings.py         # Embedding migration tool
│   └── migrate_triples.py            # Triple extraction migration
│
├── setting/                          # Project settings
│   └── .env                          # OPENAI_API_KEY (gitignored)
│
├── src/eternal_memory/               # Source code
│   ├── api/                          # FastAPI routes
│   ├── database/                     # PostgreSQL + pgvector
│   ├── engine/                       # Memory engine core
│   ├── llm/                          # LLM integration
│   ├── models/                       # Data models
│   ├── pipelines/                    # Core pipelines
│   ├── scheduling/                   # Background jobs
│   └── vault/                        # Markdown vault
│
├── ui/                               # React frontend
│   └── src/
│       ├── pages/                    # Chat, Settings, Database
│       └── components/               # UI components
│
├── tests/                            # Test suite
│
└── user_memory/                      # User data (gitignored)
    ├── config/                       # User settings
    └── markdown/                     # Human-readable memories
        ├── timeline/                 # Chronological logs
        └── knowledge/                # Topic-based knowledge
```

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11+, FastAPI 0.109+, AsyncIO |
| **Database** | PostgreSQL 14+, pgvector (HNSW) |
| **Search** | Hybrid (Vector + pg_trgm Trigram) |
| **Embedding** | OpenAI text-embedding-3-large (1536d) |
| **LLM** | OpenAI GPT-4o-mini (Multi-Model Config) |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **Scheduling** | APScheduler (AsyncIO Cron) |

## 📖 Usage

### Python API

```python
from eternal_memory import EternalMemorySystem

# Initialize
memory = EternalMemorySystem()

# Store a memory (instantly searchable, triple extraction in background)
await memory.memorize("사용자는 파이썬보다 타입스크립트를 선호한다")

# Retrieve memories (hierarchical: Triples → MemoryItems → Fallback)
result = await memory.retrieve("프로그래밍 언어 선호도", mode="fast")

# Predict context (proactive loading)
context = await memory.predict_context({"topic": "coding"})

# Consolidate memories (reflection)
await memory.consolidate()
```

### REST API

```bash
# Chat with memory context
curl -X POST http://localhost:8000/api/chat/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "What programming languages do I prefer?", "mode": "fast"}'

# Get memory statistics
curl http://localhost:8000/api/stats

# List all memories
curl http://localhost:8000/api/memories

# Session management (cross-device persistence)
curl http://localhost:8000/api/sessions                    # List sessions
curl http://localhost:8000/api/sessions/{id}               # Get session
curl -X POST http://localhost:8000/api/sessions            # Create session

# Buffer control
curl http://localhost:8000/api/buffer/status               # Buffer status
curl -X POST http://localhost:8000/api/buffer/flush        # Manual flush

# Semantic triples
curl http://localhost:8000/api/triples                     # List triples
curl http://localhost:8000/api/triples/search?query=Python # Search triples
```

## 📚 Documentation

- [Memory Specification](docs/memory_spec.md) - Detailed system specification (Korean)
- [UI README](ui/README.md) - Frontend documentation

## 🧪 Development

```bash
# Run tests
python -m pytest tests/

# Lint code
ruff check src/

# Migration scripts
python scripts/migrate_embeddings.py --dry-run
python scripts/migrate_triples.py --batch-size 50
```

## 📄 License

MIT
