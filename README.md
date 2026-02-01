# Eternal Memory System

**Next-Generation Entity-Level Persistent Memory for AI Agents**

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

Eternal Memory는 차세대 AI 에이전트를 위한 **Entity-Level 영구 기억 시스템**입니다. 검증된 학술 연구와 업계 표준을 기반으로, 기존 RAG 시스템의 한계를 극복하는 하이브리드 아키텍처를 구현했습니다.

### 🎓 Built on Validated Research

| Foundation | Source | Application |
|------------|--------|-------------|
| **Memory Supersede** | MemGPT (Packer et al., 2023) | 삭제 대신 비활성화로 히스토리 보존, 컨텍스트 관리 |
| **Semantic Triples** | LangMem (LangChain) | Subject-Predicate-Object 분해로 Entity-Level 정밀 업데이트 |
| **Salience Scoring** | Generative Agents (Stanford, 2023) | 중요도 기반 기억 평가, Reflection을 통한 장기 기억 구조화 |
| **Matryoshka Embeddings** | MRL (Kusupati et al., 2022) | 유연한 차원 축소로 다국어 정밀도 최적화 |

### Why Hybrid Architecture?

기존 RAG 시스템은 문장을 통째로 저장하여 정보 충돌 시 모든 버전을 반환합니다. Eternal Memory는 세 가지 레이어를 결합하여 이 문제를 해결합니다:

| Layer | Role | Benefit |
|-------|------|---------|
| **Semantic Triples** | Subject-Predicate-Object 분해 | Entity-Level 정밀 업데이트, 자동 충돌 해결 |
| **Vector Search** | pgvector HNSW 인덱스 | ~50ms 고속 검색, Fallback 레이어 |
| **Markdown Vault** | 인간 친화적 파일 | 사람이 읽기 쉬운 형식, 기억 내용 확인용 |

```
❌ 기존 RAG: "React 17 사용" + "React 18로 마이그레이션" → 모든 버전 반환
✅ Eternal Memory: (Project, uses_framework, React_17) → is_active: false
                   (Project, uses_framework, React_18) → is_active: true  → 최신 정보만 반환
```

## ✨ Key Features

- **🧠 Semantic Triples**: LangMem 스타일 (Subject, Predicate, Object) 지식 그래프
- **♻️ Memory Supersede**: MemGPT 논문 기반 - 삭제 대신 비활성화로 히스토리 보존
- **🔍 Hierarchical Retrieval**: Triple → MemoryItem → Fallback 계층적 검색
- **⚡ Lazy Evaluation**: 즉시 저장 → 백그라운드 Triple 추출 (80% 비용 절감)
- **🌐 Multilingual Precision**: text-embedding-3-large (1536d, Matryoshka) 기반
- **📁 Markdown Vault**: 모든 기억을 사람이 읽기 쉬운 Markdown으로 미러링 (읽기 전용)
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
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What programming languages do I prefer?"}'

# Get memory statistics
curl http://localhost:8000/stats

# List all memories
curl http://localhost:8000/memories
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
