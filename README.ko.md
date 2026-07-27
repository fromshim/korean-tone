<!-- tone-lint: off (지양 예문을 담고 있어 자기 검출 제외) -->

# korean-tone

[English](README.md) | [한국어](README.ko.md)

<p align="center">
  <picture>
    <source media="(prefers-reduced-motion: reduce)" srcset="assets/korean-tone-hero/korean-tone-static.png">
    <img src="assets/korean-tone-hero/korean-tone.gif" width="960" alt="korean-tone이 딱딱한 번역투는 걷어내고 client_id 같은 코드 좌표는 그대로 두는 모습">
  </picture>
</p>

<p align="center">
  <strong>Claude Code가 쓰는 한국어를 자연스럽게 다듬습니다.</strong><br>
  스킬은 문장을 다듬고, 린터는 놓친 번역투를 알려줍니다. 코드 식별자는 바꾸지 않습니다.
</p>

<p align="center"><code>/plugin install korean-tone@fromshim</code></p>

---

## 문장은 다듬고 코드 좌표는 남깁니다

Claude Code와 오래 작업하다 보니, 틀린 한국어보다 맞지만 어색한 한국어를 더 자주 고치게
됐습니다. 그렇다고 문장을 다듬다가 `client_id` 같은 이름까지 바뀌면 실제 코드를 찾기
어렵습니다. korean-tone은 이 둘을 구분하려고 만든 스킬입니다.

계획·구현 설명, 리뷰, 체크리스트, 연구노트, 선택지의 딱딱한 번역투를 걷어내되 코드와
정확성은 그대로 둡니다.

### 이렇게 바뀝니다

**계획·구현 설명**

```diff
- 이 함수에 대해 리팩토링을 진행하겠습니다.
+ 이 함수를 리팩토링할게요.

- 캐싱을 통해 성능 향상을 도모할 수 있습니다.
+ 캐싱을 넣으면 성능이 올라가요.

- 입력값 검증이 수행되며, 수정이 이루어졌습니다.
+ 여기서 입력값을 검증했고, 문제도 고쳤어요.
```

**필요한 기술 용어는 남기고 뜻을 풀어 씁니다**

```diff
- handler가 stub이었다.
+ handler는 웹훅만 받고 저장하지 않았어요. 함수의 뼈대만 있고 실제 처리가 빠져 있었어요.

- client_id가 틀렸습니다.
+ client_id가 잘못됐어요. 인스타 전용 앱 ID가 들어갈 자리에 메타 앱 ID를 썼어요.
```

`client_id`는 그대로 남습니다. **저장소에서 다시 찾아야 할 이름(함수·파일·필드·커밋)은
좌표이므로 바꾸지 않습니다.** 이를 "고객 식별자"로 옮기면 사용자가 실제 코드를 찾기
어려워집니다.

**내부 작업 용어는 답변에서 걷어냅니다**

```diff
- [충돌 A] OCR 품질 게이트를 어떻게 처리할까요?
-   (현재: 'acceptable verbatim quality' — 측정 불가 지적)
+ AI가 손글씨를 잘 읽는지 언제 확인할까요?

- 온톨로지를 어떻게 고칠까요? (QA: auth_provider 누락 지적)
+ 데이터 구조를 정리할까요?
```

`AC7`, `이터레이션`, `수렴 제안` 같은 말은 Claude가 작업을 관리하려고 쓰는 표현입니다.
사용자의 결정에 필요하지 않다면 답변에 드러내지 않습니다.

### 스킬과 린터가 함께 작동합니다

스타일 규칙만으로는 모델이 놓친 표현을 모두 잡기 어렵습니다. korean-tone은 작성 규칙과
자동 린터를 함께 제공합니다.

| 구성 | 역할 | 작동 방식 |
|---|---|---|
| **작성 규칙(스킬)** | 문장을 쓰는 기준을 정합니다 | 한국어 답변과 문서에 규칙을 적용합니다 |
| **자동 점검(`tone-linter` 훅)** | 놓친 표현을 알려줍니다 | 한국어 `.md`를 저장할 때 번역투를 검사합니다 |

린터 규칙은 국립국어원의 번역투 연구, 토스 테크니컬 라이팅 가이드, 이오덕의
『우리글 바로쓰기』를 참고해 정리했습니다. 비교적 기계적으로 판별할 수 있는 규칙은
`error`(`~에 의해`, 이중 피동, `~에 있어서`, `그녀`)로, 문맥과 빈도를 함께 봐야 하는 규칙은
`warn`(`~를 통해`, `것이다`, 메타 담화)으로 나눕니다. 코드 블록, 인라인 코드, URL은 검사하지
않으며, 파일에 `<!-- tone-lint: off -->`를 넣으면 해당 파일을 건너뜁니다.

린터는 파일 저장을 막지 않습니다. 저장이 끝난 뒤 다듬을 표현만 알려줍니다.

### 문서 종류별 규칙

공통 규칙은 모든 한국어 답변에 적용하고, 문서를 쓸 때는 형식에 맞는 규칙을 더 사용합니다.

| 문서 | 규칙 파일 | 핵심 |
|---|---|---|
| 체크리스트·백로그 | [`references/checklists.md`](references/checklists.md) | 여러 개념을 한 줄에 몰아넣지 않고 나눠 씁니다 |
| 설계 결정 기록·연구노트 | [`references/research-note.md`](references/research-note.md) | 담백한 `~다` 문어체 + 표준 ADR 구조(상태·검토한 대안·트레이드오프) |
| 선택지 제시 | [`references/choices.md`](references/choices.md) | 결정할 내용과 각 선택의 결과만 담습니다 |
| 번역투 전체 목록 | [`references/translationese.md`](references/translationese.md) | 모든 패턴과 근거, 자동 검출 등급 |

## 설치

```bash
/plugin marketplace add fromshim/korean-tone
/plugin install korean-tone@fromshim
```

`tone-linter` 훅도 함께 설치됩니다. 따로 설정할 것이 없습니다.

<details>
<summary>다른 설치 방법</summary>

**skills.sh로 설치하기 (여러 에이전트에서 사용):**

```bash
npx skills add fromshim/korean-tone
```

Claude Code 밖에서도 쓸 수 있지만, 훅은 [따로 등록](hooks/README.md)해야 합니다.

</details>

## 평가

규칙을 바꾼 뒤에는 같은 사례로 다시 확인합니다.

- **호출 여부** — [`evals/`](evals)의 질의 10개로 스킬이 필요할 때 호출되고 불필요할 때 조용한지 봅니다.
- **교정 품질** — [`evals/quality-cases.jsonl`](evals/quality-cases.jsonl)의 사례 12개를 [`evals/evaluate_quality.py`](evals/evaluate_quality.py)로 채점해 좌표 보존, 번역투 제거, 과교정을 먼저 거릅니다.
- **사람 검수** — 자연스러움, 정확성, 말투 일치, 과교정 여부는 사람이 1~5점으로 매깁니다. 같은 스크립트의 `--write-review`로 검수표를 만듭니다.

```bash
python3 evals/evaluate_quality.py --outputs <파일>   # 자동 채점
python3 hooks/tone-linter.py --selftest              # 린터 자체 점검
```

## 관련 스킬

- [shimmy-tone](https://github.com/seungboshim/skills) — korean-tone 위에 얹히는 개발 블로그
  저술 보이스입니다. 워크플로 스킬(feature-flow, daily, worklog)과 함께 스킬 모음 저장소에
  있습니다.

## 라이선스

MIT
