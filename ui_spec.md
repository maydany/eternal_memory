요청하신 내용을 개발자가 즉시 참고할 수 있는 **Markdown(.md)** 파일 형식으로 작성했습니다.

아래 내용을 복사하여 `openclaw_ui_spec.md` 등의 파일로 저장해 사용하시면 됩니다.

---

```markdown
# OpenClaw Eternal Memory UI/UX Specification

- **Project:** OpenClaw Desktop Client (with Eternal Memory)
- **Version:** 1.0.0
- **Status:** Draft
- **Target Platform:** Electron (React + TypeScript)
- **Reference Doc:** OpenClaw 영구 기억 시스템 설계 (OpenClaw Eternal Memory Architecture)

---

## 1. 프로젝트 개요 (Overview)

[cite_start]본 문서는 로컬 우선(Local-First) AI 에이전트인 **OpenClaw**의 데스크톱 애플리케이션 UI 명세서입니다[cite: 6].
[cite_start]본 프로젝트의 핵심 목표는 사용자가 자신의 데이터 주권을 유지하면서, AI가 과거의 맥락을 스스로 기억하고 활용하는 과정을 **투명하게(Transparency)** 시각화하고 제어할 수 있는 인터페이스를 제공하는 것입니다[cite: 8, 33].

## 2. 핵심 기능 요구사항 (Core Requirements)

1.  **LLM 연동 관리:** API Key 및 모델(Provider) 설정 관리.
2.  [cite_start]**기억 기반 대화 (Memory-Augmented Chat):** RAG(검색)와 Reasoning(추론)이 결합된 하이브리드 대화 인터페이스[cite: 68].
3.  [cite_start]**맥락 시각화 (Context Visualization):** AI가 답변 생성 시 참조한 로컬 마크다운 파일 출처 표시[cite: 46].
4.  [cite_start]**Memory Vault 탐색기:** `~/.openclaw/memory` 디렉토리 내의 기억 데이터를 직접 열람하고 수정하는 기능[cite: 34, 124].

---

## 3. 상세 UI 명세 (Detailed UI Specifications)

### 3.1 화면 1: 초기 설정 및 API 키 관리 (Settings)

애플리케이션 구동을 위한 필수 설정을 관리합니다.

#### 3.1.1 UI 구성 요소

- **LLM Provider Selector:**
  - 지원 목록: OpenAI, Anthropic, Google Gemini, Ollama (Local)
- **API Key Input:**
  - Type: Password (Masked)
  - Validation: 입력 후 연결 테스트 버튼 제공.
  - _Note:_ 보안을 위해 시스템 Keychain에 저장 권장.
- **System Prompt Editor:**
  - 사용자의 페르소나 및 기본 지시사항 설정.
  - [cite_start]설정 파일 경로: `~/.openclaw/config/memory_config.yaml` 참조[cite: 144].

---

### 3.2 화면 2: 메인 채팅 인터페이스 (Main Chat)

사용자와 AI의 상호작용 및 기억 활용 프로세스를 시각화합니다.

#### 3.2.1 레이아웃 구조

- **Left Panel:** 세션 기록 (History)
- **Center Panel:** 채팅 스트림 (Chat Stream)
- **Right Panel (Collapsible):** 컨텍스트 인스펙터 (Context Inspector)

#### 3.2.2 Center Panel: 채팅 기능

- **Message Bubble:**
  - **User:** 우측 정렬.
  - **AI:** 좌측 정렬.
- [cite_start]**Processing Indicators (이중 모드 지능 시각화):** [cite: 68]
  1.  [cite_start]`Searching Memory...` (Vector Search - Fast Context) [cite: 70]
  2.  [cite_start]`Reading Files...` (Markdown Analysis - Deep Reasoning) [cite: 76]
  3.  `Thinking...` (Response Generation)

#### 3.2.3 Right Panel: 컨텍스트 인스펙터 (핵심 기능)

[cite_start]"출처 추적(Traceability)"을 위한 패널입니다[cite: 46].

- **Active References (참조된 기억):**
  - AI가 현재 답변을 생성하기 위해 읽어들인 파일 목록 표시.
  - UI 예시:
    > 📂 `knowledge/coding/python.md` (유사도: 0.92)
    > 📂 `personal/schedule.md` (관련 일정)
- **Real-time Log:**
  - 대화 중 새로운 기억이 저장될 때 실시간 피드백 제공.
  - [cite_start]예: _"New fact extracted -> Saved to `projects/new_app.md`"_[cite: 94].

---

### 3.3 화면 3: 메모리 볼트 탐색기 (Memory Vault Explorer)

[cite_start]사용자가 AI의 기억을 직접 검증하고 수정할 수 있는 "투명성(Transparency)" 및 "수정 가능성(Editability)" 구현 화면입니다[cite: 33, 34].

#### 3.3.1 UI 구성 요소

- **File Tree View:**
  - [cite_start]Root: `~/.openclaw/memory/` [cite: 124]
  - Directories:
    - [cite_start]`timeline/`: 시간순 로그 [cite: 128]
    - [cite_start]`knowledge/`: 주제별 지식 [cite: 131]
    - [cite_start]`personal/`: 개인 정보 [cite: 138]
- **Markdown Editor:**
  - 선택된 `.md` 파일의 내용을 렌더링 및 편집.
  - 사용자가 내용을 수정하고 저장하면, 백그라운드에서 Vector Index 재조정 트리거.
- **Search Bar:**
  - 기억 저장소 전체에 대한 Full-text 검색 지원.

---

## 4. 인터랙션 흐름 (Interaction Flows)

### 4.1 기억 회상 (Retrieval Flow)

1.  **User Input:** 사용자가 질문 입력.
2.  **State Change:** UI 상태가 'Retrieving'으로 변경.
3.  **Process:**
    - [cite_start]Gateway가 벡터 DB 검색 및 관련 Markdown 요약본 로드[cite: 262, 264].
4.  **Display:**
    - Right Panel에 참조된 파일 목록 업데이트.
    - AI 답변 출력.

### 4.2 기억 저장 (Memorize Flow)

1.  **User Input:** 정보성 발언 (예: "내 프로젝트 마감일은 3월 1일이야.")
2.  **Process:**
    - [cite_start]LLM이 중요 정보(Salience) 감지 및 추출[cite: 94].
    - [cite_start]적절한 카테고리 파일(`schedule.md`)에 내용 Append[cite: 257].
3.  **Feedback:**
    - UI 상단 또는 하단에 _"Memory Updated"_ 토스트 메시지 출력.

---

## 5. 기술 스택 제안 (Tech Stack Recommendation)

- **Frontend:** React, TypeScript, Tailwind CSS
- [cite_start]**Runtime:** Electron (Node.js Gateway와의 통합 용이성) [cite: 19]
- **Markdown:** `react-markdown` (GitHub Style Rendering)
- **State Management:** TanStack Query (파일 시스템 I/O 동기화)

---

## 6. 개발 마일스톤 (Milestones)

1.  **Phase 1 (Setup):** LLM API 연동 및 기본 채팅 UI, `~/.openclaw` 디렉토리 스캔 기능.
2.  **Phase 2 (Visualization):** 채팅 시 참조(Reference) 파일 표시 기능 구현.
3.  **Phase 3 (Management):** Markdown 에디터 통합 및 실시간 기억 수정 기능 구현.
```

---

**다음 단계:**
이 UI 명세서를 바탕으로 **"Phase 1: 설정 및 기본 채팅 UI"** 구현을 위한 **React 컴포넌트 구조(폴더 구조 및 컴포넌트 명세)**를 잡아드릴까요?
