# Eternal Memory System

OpenClaw 스타일의 영구적 기억(Eternal Memory) 시스템 구현체입니다.

## Features

- **영구적 기억**: 세션 종료 후에도 데이터가 영구적으로 보존
- **능동적 예측**: 사용자 요청 전, 상황에 맞는 문맥을 선제적으로 로딩
- **투명성**: 모든 기억 데이터는 Markdown 파일로 미러링
- **이중 모드 검색**: RAG 기반 + LLM 기반 검색

## Installation

```bash
cd eternal_memory
pip install -e ".[dev]"
```

## Database Setup

PostgreSQL 16과 pgvector가 필요합니다:

```bash
brew install postgresql@16 pgvector
brew services start postgresql@16
createdb eternal_memory
```

## Running the Application

One command to run the entire system (Database + Backend + Frontend):

```bash
./scripts/run.sh
```

This script will:
1. Check if PostgreSQL is running (and start it if needed)
2. Start the Backend API (http://localhost:8000)
3. Start the Frontend UI (http://localhost:5173)

## Usage

```python
from eternal_memory import EternalMemorySystem

# Initialize
memory = EternalMemorySystem()

# Store a memory
await memory.memorize("사용자는 파이썬보다 타입스크립트를 선호한다")

# Retrieve memories
result = await memory.retrieve("프로그래밍 언어 선호도", mode="fast")
```

## License

MIT
