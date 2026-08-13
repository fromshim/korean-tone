<!-- tone-lint: off -->

# korean-tone 훅

플러그인 설치 시 네 가지 시점에 자동으로 동작한다.

| 시점 | 파일 | 하는 일 |
|---|---|---|
| 세션 시작 | `tone-context.py` | 기본 Korean Tone 규칙을 대화 맥락에 넣는다. |
| 질문 전송 | `tone-context.py` | 현재 `default`·`easy`·`mz` 모드를 짧게 다시 알려준다. |
| 서브에이전트 시작 | `tone-context.py` | 서브에이전트가 파일에 쓸 글을 위해 규칙을 두 줄로 줄여 넣는다. |
| Markdown 저장 | `tone-linter.py` | 놓친 번역투를 찾아 다음 응답에서 고칠 수 있게 알려준다. |

## 말투는 설치 직후부터 계속 적용된다

`SessionStart` 훅이 `rules/default.md`를 읽어 Claude의 대화 맥락에 넣는다. 사용자가 스킬을
따로 부르지 않아도 모든 한국어 답변에 기본 말투가 적용된다.

`UserPromptSubmit` 훅은 질문을 보낼 때마다 현재 모드를 짧게 다시 알려준다. 긴 대화나 다른
플러그인의 지침 때문에 말투가 흐트러지는 것을 막는다.

모드는 세션별로 저장한다. 새 세션은 `default`로 시작하고, `/clear`·대화 압축·세션 재개 뒤에는
그 세션의 모드를 유지한다.

```text
/korean-tone:default  자연스럽고 정확한 기본 말투
/korean-tone:easy     초등학생도 따라올 수 있게 쉽게 설명
/korean-tone:mz       내용은 그대로 두고 인스타 댓글체로 변경
```

`easy`와 `mz`는 한 답변만 바꾸는 명령이 아니다. 다른 모드를 고르거나 새 세션을 시작할 때까지
유지된다.

## 서브에이전트에는 줄인 규칙만 내려간다

`SessionStart` 맥락은 메인 세션에만 남고 서브에이전트에는 닿지 않는다. 그래서 `SubagentStart`
훅이 규칙을 두 줄로 줄여 따로 넣는다. 서브에이전트는 여럿 뜨니 전문을 넣으면 프롬프트마다
분량이 곱해진다.

대상은 서브에이전트가 **파일로 저장하는 글**이다. 문서, README, 주석, 커밋 메시지처럼 메인
에이전트를 거치지 않고 저장소에 그대로 남는 것들이다. 메인에 올리는 보고문은 대상이 아니다.
보고문은 어차피 메인이 자기 말로 다시 쓰고, 이 범위를 그어둬야 출력을 압축하는 다른
스킬과 부딪히지 않는다.

세션 모드는 물려주지 않고 항상 `default`로 넣는다. `easy`와 `mz`는 대화용 말투인데
서브에이전트가 만드는 파일은 세션이 끝나도 남기 때문이다.

## `tone-linter`는 저장한 문서를 검사한다

Claude Code의 `PostToolUse` 훅으로 걸려서 한국어 `.md` 파일을 `Write`나 `Edit`로 저장할
때마다 번역투를 찾는다. 저장을 막지는 않고, Claude가 다음 응답에서 고칠 수 있게 알려준다.

- 검출 규칙: `../references/translationese.md`
- 코드 블록·인라인 코드·URL은 검사에서 제외
- `<!-- tone-lint: off -->`가 있는 파일은 건너뜀
- 대시(`—`)는 산문에 한 번만 나와도 알려줌. 표의 구분자는 제외

## 설치

### 플러그인으로 설치: 모두 자동

```bash
/plugin marketplace add fromshim/korean-tone
/plugin install korean-tone@fromshim
```

`hooks/hooks.json`이 네 훅을 함께 연결한다. 추가 등록은 필요 없다. 설치하거나 업데이트한 뒤
새 세션을 시작해야 `SessionStart` 훅이 적용된다.

### `npx skills` 또는 직접 설치: 린터만 수동 등록

```bash
python3 skills/korean-tone/hooks/register-hook.py
```

`register-hook.py`는 `tone-linter.py`만 `~/.claude/settings.json`에 등록한다. 항상 적용되는
말투와 모드 전환은 Claude 플러그인 설치에서만 제공한다.

프로젝트에만 린터를 걸려면 `--project .`, 끄려면 `--remove`를 쓴다. 설정을 바꾸기 전에
`.bak` 백업을 만든다.

## 점검

```bash
python3 hooks/tone-context.py --selftest
python3 hooks/tone-linter.py --selftest
claude plugin validate . --strict
```
