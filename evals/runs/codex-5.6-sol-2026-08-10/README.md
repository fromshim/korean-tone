# gpt-5.6-sol Korean Tone 산출물

`evals/raw-samples.md`의 13개 표본을 `default`, `easy`, `mz` 모드로 변환한 결과다.

## 실행 조건

- 실행일: 2026-08-10
- 모델: `gpt-5.6-sol`
- 추론 강도: `medium`
- Codex CLI: `0.147.0`
- 개인 Codex 설정과 프로젝트 실행 규칙: 제외
- 샌드박스: `read-only`
- 실행 단위: 모드별 새 세션 1개
- 대화 가정: 13개 표본은 서로 독립된 사용자 대화라고 명시

Claude 전용 `.claude-plugin` 훅을 Codex가 직접 실행한 것은 아니다. 훅이 넣는 것과 같은
규칙 파일을 모델에 읽혀 컨텍스트 주입을 재현했다.

- `default`: `rules/default.md` + `SKILL.md` + 필요한 `references/*`
- `easy`: 위 규칙 + `rules/easy.md`
- `mz`: 위 규칙 + `rules/mz.md`

## 결과

- [`default.md`](default.md)
- [`easy.md`](easy.md)
- [`mz.md`](mz.md)

각 Markdown 파일과 같은 이름의 JSONL 파일은 기존 `evaluate_quality.py`에 넣기 위한
기계 판독용 변환본이다.

## 기존 안전 게이트 결과

| 모드 | 통과 | 비율 |
|---|---:|---:|
| default | 172/179 | 96.1% |
| easy | 171/179 | 95.5% |
| mz | 174/179 | 97.2% |

이 점수는 자연스러움을 평가하지 않는다. 식별자·수량·의미 보존과 지양 표현 제거 같은
결정론적 조건만 확인한다.

배치 산출물을 기존 평가기에 맞추는 과정에서 생긴 거짓 실패도 있다. `두 단계` 대신
`2단계`를 쓴 경우, `재시도` 대신 `자동으로 다시 시도`라고 풀어 쓴 경우, 영어 문장의
줄바꿈만 원본 Markdown과 같게 유지한 경우가 대표적이다. 따라서 위 비율은 결과를 빠르게
살펴보기 위한 안전 게이트이며, 모델 간 품질 순위로 해석하면 안 된다.
