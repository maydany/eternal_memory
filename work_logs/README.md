# 작업 로그 (Work Logs)

이 디렉토리에는 Eternal Memory 프로젝트의 개발 작업 로그가 날짜별로 정리되어 있습니다.

## 📁 파일 구조

```
work_logs/
├── README.md                    # 이 파일
├── 2026-01-31_work_log.md       # 1월 31일 작업 기록
└── 2026-02-01_work_log.md       # 2월 1일 작업 기록
```

## 📋 작업 로그 요약

### 2026-01-31
- **시맨틱 트리플 시스템 구현**: MemGPT 스타일 바이너리 대체에서 LangMem 스타일 엔티티 레벨 SPO 트리플로 전환
- **Memory Spec 문서 업데이트**: 4계층 인지 모델 및 이중 저장소 아키텍처 문서화
- **트리플 마이그레이션 스크립트**: 기존 메모리를 트리플로 변환하는 `migrate_triples.py` 작성
- **채팅 세션 Persistence**: Zustand + localStorage 기반 세션 관리 구현

### 2026-02-01
- **임베딩 모델 마이그레이션**: `text-embedding-ada-002` → `text-embedding-3-large` (다국어 정밀도 향상)
- **서버 측 세션 구현**: localStorage에서 PostgreSQL `chat_sessions` 테이블로 전환
- **버퍼 플러시 트리거 확장**: `visibilitychange`, `pagehide`, 세션 전환 이벤트 추가
- **LLM 컨텍스트 테스트 기능**: 메모리 검색 비활성화 토글 구현

## 🔒 보안 참고사항

- 모든 작업 로그에서 API 키, 환경 변수, 개인정보는 제외됨
- GitHub에 안전하게 커밋 가능

## 📝 로그 작성 규칙

1. 파일명: `YYYY-MM-DD_work_log.md` 형식
2. 구조: 작업 개요 → 상세 작업 내용 → 변경 파일 → 체크리스트
3. 코드 블록: 핵심 구현 및 명령어만 포함
4. 민감 정보: 절대 포함 금지
