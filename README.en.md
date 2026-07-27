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

```diff
- 이 함수에 대해 리팩토링을 진행하겠습니다.   ("I will proceed with refactoring of this function")
+ 이 함수를 리팩토링할게.                      ("I'll refactor this function")

- handler 가 stub 이었다.
+ 웹훅을 받아놓고 저장을 안 했어. 껍데기만 있고 안이 비어 있던 거지.
  (jargon isn't deleted — it's interpreted: "it took the webhook and never stored it")
```

Identifiers survive. `client_id` stays `client_id` — **anything you can grep for in the
repo (functions, files, fields, commits) is a coordinate, not prose.** Translating it to
"고객 식별자" would make it unfindable.

Claude's own working vocabulary gets stripped from user-facing text:

```diff
- [충돌 A] OCR 품질 게이트를 어떻게 처리할까요?
+ AI 가 손글씨를 잘 읽는지 언제 확인할까요?
  ("How should we handle conflict A's OCR quality gate?" → "When should we check
   whether the AI reads handwriting well?")
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
