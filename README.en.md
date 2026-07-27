<!-- tone-lint: off (지양 예문을 담고 있어 자기 검출 제외) -->

# korean-tone

[한국어](README.md) | [English](README.en.md)

<p align="center">
  <picture>
    <source media="(prefers-reduced-motion: reduce)" srcset="assets/korean-tone-hero/korean-tone-static.png">
    <img src="assets/korean-tone-hero/korean-tone.gif" width="960" alt="korean-tone removes stiff Korean phrasing while preserving client_id and other code identifiers">
  </picture>
</p>

<p align="center">
  <strong>Make Claude sound fluent in Korean — without translating away the things you need to grep.</strong><br>
  One writing skill. One non-blocking linter. Zero renamed identifiers.
</p>

<p align="center"><code>/plugin install korean-tone@fromshim</code></p>

---

## Edit the voice, not the coordinates

> The Korean is technically correct. It still sounds translated.

korean-tone strips that stiffness from plans, implementation notes, reviews, checklists,
ADRs, and user-facing choices — **while leaving code and precision alone.**

### What changes

**Jargon is interpreted, not deleted**

```diff
- handler가 stub이었다.
+ handler는 웹훅만 받고 저장하지 않았어요. 함수의 뼈대만 있고 실제 처리가 빠져 있었어요.
  ("the handler was a stub" → "the handler took the webhook and never stored it —
   just the shell of a function, with the actual work missing")
```

The term stays; a sentence explaining it gets added.

**Names you have to look up are left alone**

```diff
- client_id가 틀렸습니다.
+ client_id가 잘못됐어요. 인스타 전용 앱 ID가 들어갈 자리에 메타 앱 ID를 썼어요.
  ("client_id was wrong" → "client_id is wrong — a Meta app ID went where the
   Instagram-specific one belongs")
```

`client_id` stays `client_id` — **anything you can grep for in the repo (functions, files,
fields, commits) is a coordinate, not prose.** Translating it to "고객 식별자" would make it
unfindable.

**Claude's own working vocabulary is stripped from user-facing text**

```diff
- 수렴 제안 2건(인젝션 한 줄 제약 + 디자인 육안 승인 기준)을 적용할까요?
+ 추가 지침은 한 줄로 제한하고, 디자인은 결과물을 직접 본 뒤 승인하도록 할까요?
  ("Apply the 2 convergence proposals?" → "Should extra instructions be capped at one
   line, and design approved after looking at the result?")
```

Terms like `수렴 제안`, `AC7`, and `이터레이션` are how Claude tracks its own work. Nothing is
cut, though — the question above still asks exactly the same thing.

**Ordinary translationese goes too**

```diff
- 이 함수에 대해 리팩토링을 진행하겠습니다.   ("I will proceed with refactoring of this function")
+ 이 함수를 리팩토링할게요.                    ("I'll refactor this function")
```

### It works in two layers

Most style guides stop at "write it this way" — when the model drifts, nothing catches it.
korean-tone adds an enforcement layer on top.

| Layer | What | How |
|---|---|---|
| **Soft** — the skill | Shapes the writing | Rules apply whenever Claude speaks Korean |
| **Hard** — `tone-linter` hook | Catches the drift | Scans every Korean `.md` you save for translationese |

Patterns are sourced from National Institute of Korean Language papers, Toss's technical
writing guide, and 이오덕's *우리글 바로쓰기*. They're split into **error grade** (near-zero
false positives) and **warn grade** (judged by frequency). Code blocks, inline code, and
URLs are excluded; `<!-- tone-lint: off -->` skips a file entirely.

It never blocks a write — it just tells Claude what to fix next turn.

### Per-document rules

The common rules apply to every Korean answer. Documents get extra rules by type:

| Document | Rule file | The gist |
|---|---|---|
| Checklists, backlogs | [`references/checklists.md`](references/checklists.md) | Break concepts onto separate lines instead of packing one row |
| ADRs, research notes | [`references/research-note.md`](references/research-note.md) | Plain `~다` prose + standard ADR structure (status, alternatives, trade-offs) |
| User-facing choices | [`references/choices.md`](references/choices.md) | Ask the decision only; describe outcomes, not mechanisms |
| Full translationese catalog | [`references/translationese.md`](references/translationese.md) | Every pattern, with sources and auto-detect grade |

## Install

### As a plugin

Claude Code only. The `tone-linter` hook is registered alongside the writing rules, so
every Korean `.md` you save is scanned for translationese automatically. No extra setup.

```bash
/plugin marketplace add fromshim/korean-tone
/plugin install korean-tone@fromshim
```

### Via skills.sh

Installs to Codex, Cursor, Antigravity, Amp, Gemini CLI, and others besides Claude Code.
Only the writing rules take effect — the hook is not registered, so run
[`hooks/register-hook.py`](hooks/README.md) yourself to turn on the automatic check.

```bash
npx skills add fromshim/korean-tone
```

## When it runs

### The skill — mostly on its own

Claude applies it when explaining plans, implementations, and reviews in Korean, or when
writing Korean documents. You don't have to call it.

To invoke it explicitly, the name depends on how you installed it:

| Install method | Invocation |
|---|---|
| Plugin | `/korean-tone:korean-tone` |
| skills.sh | `/korean-tone` |

Phrases like "어투 교정", "말투 자연스럽게", "번역투 고쳐" trigger it too.

### The linter hook — only under these conditions

With the plugin install, the hook scans when **all** of these hold:

- Claude saved a file with `Write` or `Edit`
- The extension is `.md`, `.mdx`, or `.markdown`
- The saved text contains Hangul
- The file has no `<!-- tone-lint: off -->` marker

Excluded from scanning: code blocks, inline code, URLs, and link targets.
`Edit` scans only the changed text, and line numbers are reported against the file.

Chat replies are never scanned — only text written to disk.

## Evaluation

Rule changes are re-checked against the same cases each time.

- **Trigger regression** — 10 queries in [`evals/`](evals) verify the skill fires when it should and stays quiet when it shouldn't.
- **Correction quality** — 12 cases in [`evals/quality-cases.jsonl`](evals/quality-cases.jsonl), scored by [`evals/evaluate_quality.py`](evals/evaluate_quality.py) for coordinate preservation, translationese removal, and over-correction.
- **Human review** — naturalness, accuracy, register match, and over-correction are rated 1–5 by a person. The script's `--write-review` builds the sheet.

```bash
python3 evals/evaluate_quality.py --outputs <file>   # automated pass
python3 hooks/tone-linter.py --selftest              # linter self-check
```

## Related

- [shimmy-tone](https://github.com/seungboshim/skills) — a personal dev-blog writing voice
  that layers on top of korean-tone. Lives in the author's skills collection along with
  workflow skills (feature-flow, daily, worklog).

## License

MIT
