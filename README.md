# Eternal Memory System

OpenClaw 스타일의 영구적 기억(Eternal Memory) 시스템 구현체입니다.

## Features

- **영구적 기억**: 세션 종료 후에도 데이터가 영구적으로 보존
- **능동적 예측**: 사용자 요청 전, 상황에 맞는 문맥을 선제적으로 로딩
- **투명성**: 모든 기억 데이터는 Markdown 파일로 미러링
- **이중 모드 검색**: RAG 기반 + LLM 기반 검색

## Quick Start

### 1. Install Everything

Run the installation script (installs all dependencies, sets up database, configures environment):

```bash
./scripts/install.sh
```

This will automatically:
- ✅ Install PostgreSQL 16 + pgvector
- ✅ Create and configure the database
- ✅ Set up Python virtual environment
- ✅ Install all Python dependencies
- ✅ Install UI dependencies
- ✅ Create configuration files

### 2. Add Your API Key

The installer will prompt you for your OpenAI API key, or you can add it manually:

```bash
# Edit setting/.env and add:
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Application

Start everything with one command:

```bash
./scripts/run.sh
```

This will start:
- 📡 Backend API (http://localhost:8000)
- 💻 Frontend UI (http://localhost:5173)

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
