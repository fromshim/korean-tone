<!-- tone-lint: off -->

# tone-linter 훅

korean-tone 스킬의 **하드 검출 층**. Claude Code의 `PostToolUse` 훅으로 걸려서,
한국어 `.md` 파일을 Write/Edit 할 때마다 저장된 내용에서 번역투(A 패턴)를 찾아
**비차단 어드바이저리**로 짚어준다. 저장은 그대로 두고, Claude가 다음 턴에 고칠 수 있게
알려주는 방식이다. 소프트 규칙(스킬)이 shape하고, 이 훅이 drift를 잡는다.

- 검출 규칙: `../references/translationese.md` (A급만 자동 검출, error/warn 2단)
- 코드블록·인라인코드·URL은 검사에서 제외
- 파일에 `<!-- tone-lint: off -->` 가 있으면 그 파일은 건너뜀

## 설치

### 플러그인으로 설치했다면 — 자동

```bash
/plugin marketplace add seungboshim/skills
/plugin install korean-tone@seungboshim-skills
```

`hooks.json`이 함께 설치돼서 훅이 **자동으로 걸린다.** 아래 수동 등록은 필요 없다.

### `npx skills`로 설치했거나 직접 쓸 때 — 수동 등록

```bash
python3 skills/korean-tone/hooks/register-hook.py
```

`~/.claude/settings.json` 의 `PostToolUse` 에 아래를 멱등하게 추가한다 (실행 전 `.bak` 백업):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command",
            "command": "python3 /경로/skills/korean-tone/hooks/tone-linter.py",
            "timeout": 10 }
        ]
      }
    ]
  }
}
```

전역으로 걸면 어느 프로젝트에서든 한국어 `.md`를 쓸 때 동작한다.
프로젝트 한정으로 걸고 싶으면 `--project .`, 끄려면 `--remove`.

레포를 다른 위치로 옮겼으면 `register-hook.py`를 다시 실행하면 경로가 갱신된다
(스크립트가 자기 위치로 tone-linter.py 경로를 계산한다).

## 점검

```bash
python3 skills/korean-tone/hooks/tone-linter.py --selftest
```
