#!/usr/bin/env python3
"""tone-linter — korean-tone 스킬의 하드 검출 층.

Claude Code의 PostToolUse 훅으로 걸린다. Write/Edit 후 한국어 .md 파일에서 번역투
(translationese.md의 A 패턴)를 찾아 비차단 어드바이저리로 짚어준다. 저장은 그대로 두고,
Claude가 다음 턴에 고칠 수 있게 알려주는 방식.

- 규칙 전체: skills/korean-tone/references/translationese.md
- 끄기: 파일에 `<!-- tone-lint: off -->` 가 있으면 그 파일은 건너뛴다.
- 자체 점검: `python3 tone-linter.py --selftest`

어떤 예외가 나도 exit 0 으로 조용히 끝낸다 — 린터가 사용자의 Write/Edit 흐름을 막으면 안 된다.
"""
import json
import re
import sys

MD_EXT = (".md", ".mdx", ".markdown")
HANGUL = re.compile(r"[가-힣]")
OFF_MARKER = "tone-lint: off"
MAX_ERRORS = 10  # 리포트에 담을 error 발견 상한

# --- error 급: 오탐 거의 없음, 보이면 거의 항상 고칠 것 --------------------------
# (이름, 정규식, 제안)
ERROR = [
    ("~에 의해(수동 by)",   re.compile(r"에\s*의(?:해서?|하여|한)"),            "능동으로 — 행위 주체를 주어로"),
    ("~을 필요로 하다",     re.compile(r"[을를]\s*필요로\s*(?:하|한|해|합|했)"), "→ ~이 필요하다"),
    ("가지다(have 직역)",   re.compile(r"(?:회의|미팅|모임|세션|논의|시간)[을를]\s*(?:가진|가지|가졌|갖)"), "→ 회의하다 / ~이 있다"),
    ("~에 있어서",          re.compile(r"에\s*있어서"),                          "→ ~할 때 / ~에서"),
    ("~에 다름 아니다",     re.compile(r"에\s*다름\s*아니"),                     "→ ~일 뿐이다"),
    ("~임에 틀림없다",      re.compile(r"(?:임에|음에|것임에|것에)\s*틀림\s*없"), "→ ~가 분명하다"),
    ("~에도 불구하고",      re.compile(r"불구하고"),                             "→ ~지만 / ~는데도"),
    ("~하지 않으면 안 된다", re.compile(r"지\s*않으면\s*안\s*(?:되|돼|될|됩)|않을\s*수\s*없"), "→ ~해야 한다"),
    ("~해도 지나치지 않다", re.compile(r"지나치지\s*않"),                        "→ 꼭 ~해야 한다"),
    ("~에 위치하다",        re.compile(r"에\s*위치(?:하|한|해|합)"),             "→ ~에 있다"),
    ("이중피동",            re.compile(r"(?:되어|보여|쓰여|씌어|잊혀|나뉘어|모여|불려|갈려)(?:지|진|졌|질|집|져)"), "→ 홑피동/능동: 보인다·되다·했다"),
    ("그녀",                re.compile(r"그녀"),                                 "→ 그 / 이름 반복"),
    ("당신",                re.compile(r"당신"),                                 "→ 대개 생략"),
    ("본(本) ~ (일본식)",   re.compile(r"(?:^|[\s(])본\s*(?:문서|기능|프로젝트|시스템|장|절|가이드|글|보고서|연구|모듈|함수|절차|API)"), "→ 이 문서/기능"),
    ("가장 ~ 중 하나",      re.compile(r"가장\s+.{0,20}?중\s*하나|것\s*중\s*하나"), "→ 대표적인 ~이다"),
]

# --- warn 급: 정당한 용례 있음, 빈도가 높을 때만 -------------------------------
# (이름, 정규식, 임계값, 제안)
WARN = [
    ("~에 대해/관해",  re.compile(r"에\s*(?:대|관)(?:해서?|하여|한)"), 3, "대부분 뺄 수 있어"),
    ("~를 통해",       re.compile(r"[를을]\s*통(?:해서?|하여|한)"),    3, "→ ~하면 / ~로"),
    ("~하기 위해",     re.compile(r"기\s*위(?:해서?|하여|한)"),        4, "→ ~하려고"),
    ("~의 경우",       re.compile(r"의\s*경우"),                       2, "→ ~는 / ~일 때"),
    ("것이다/것입니다", re.compile(r"것(?:이다|입니다)"),               4, "절반은 동사 종결로"),
    ("할 수 있다",     re.compile(r"할\s*수\s*있(?:다|습니다)"),        4, "될 것 같아 / 하면 돼 로 갈아"),
    ("메타 담화",      re.compile(r"다음과\s*같(?:다|습니다|은|이)|살펴보(?:겠|도록|자)|결론적으로|아시다시피|앞서\s*(?:설명|언급)"), 2, "대개 통째로 삭제"),
    ("이루어지다/요구되다", re.compile(r"이루어(?:진다|집니다|졌|지)|(?:이|가)\s*요구(?:된다|됩니다|되)"), 2, "→ 능동 동사로"),
]

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_INLINE_CODE = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://\S+")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")


def _clean(line: str) -> str:
    """코드·URL·링크 타깃을 지운 검사용 라인."""
    line = _INLINE_CODE.sub(" ", line)
    line = _URL.sub(" ", line)
    line = _LINK_TARGET.sub("] ", line)
    return line


def scan(content: str):
    """(error_findings, warn_counts) 반환. 코드블록은 통째로 제외."""
    errors = []            # (lineno, name, suggestion, snippet)
    warn_counts = {}       # name -> count
    in_fence = False
    for i, raw in enumerate(content.splitlines(), start=1):
        if _FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = _clean(raw)
        if not HANGUL.search(line):
            continue
        for name, rx, hint in ERROR:
            if len(errors) < MAX_ERRORS and rx.search(line):
                snippet = re.sub(r"\s+", " ", line).strip()[:44]
                errors.append((i, name, hint, snippet))
        for name, rx, _thr, _hint in WARN:
            n = len(rx.findall(line))
            if n:
                warn_counts[name] = warn_counts.get(name, 0) + n
    return errors, warn_counts


def format_report(errors, warn_counts):
    """어드바이저리 텍스트. 아무것도 없으면 None."""
    warn_hits = [(name, warn_counts[name], hint)
                 for name, _rx, thr, hint in WARN
                 if warn_counts.get(name, 0) >= thr]
    if not errors and not warn_hits:
        return None

    out = ["[tone-linter] 번역투가 보여 (korean-tone). 저장은 됐고, 다듬을지 판단해줘:"]
    if errors:
        out.append("\nerror급 (거의 항상 고칠 것):")
        for lineno, name, hint, snippet in errors:
            out.append(f"- L{lineno}  {name} {hint}  「{snippet}」")
    if warn_hits:
        out.append("\nwarn급 (빈도 높음 → 줄이기):")
        for name, count, hint in warn_hits:
            out.append(f"- {name} {count}회 — {hint}")
    out.append("\n전체 규칙: korean-tone/references/translationese.md")
    return "\n".join(out)


def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {}) or {}
        path = (tool_input.get("file_path") or "").lower()
        if not path.endswith(MD_EXT):
            return
        content = tool_input.get("content") or tool_input.get("new_string") or ""
        if not content or OFF_MARKER in content or not HANGUL.search(content):
            return
        report = format_report(*scan(content))
        if report:
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": report,
            }}, sys.stdout, ensure_ascii=False)
    except Exception:
        pass  # 린터가 Write/Edit 흐름을 막으면 안 된다
    # 항상 exit 0


def _selftest():
    # error 검출
    errs, _ = scan("이 함수는 스케줄러에 의해 호출된다.")
    assert any(n == "~에 의해(수동 by)" for _, n, _, _ in errs), "에 의해 미검출"
    errs, _ = scan("코드가 개선되어졌다. 결과가 보여진다.")
    assert sum(1 for _, n, _, _ in errs if n == "이중피동") >= 1, "이중피동 미검출"
    errs, _ = scan("토큰을 필요로 한다.")
    assert any(n == "~을 필요로 하다" for _, n, _, _ in errs), "필요로 하다 미검출"

    # 홑피동/일반 표현 오탐 없어야
    errs, _ = scan("객체가 만들어진다. 합의가 이루어졌다. 그렇게 되지 않는다.")
    assert not any(n == "이중피동" for _, n, _, _ in errs), "이중피동 오탐"

    # 코드블록·인라인코드·URL 제외
    errs, _ = scan("```\n스케줄러에 의해 호출\n```\n정상 문장이야.")
    assert not errs, "코드블록이 검사됨"
    errs, _ = scan("`에 의해` 는 인라인코드라 제외돼야 한다.")
    assert not errs, "인라인코드가 검사됨"

    # off 마커
    r = format_report(*scan("에 의해 호출된다."))
    assert r is not None
    # main 경로의 off는 content 검사에서 처리 — 여기선 스캐너만 확인

    # warn 임계값: 2회면 '의 경우'(thr 2) 걸리고 1회면 안 걸림
    r1 = format_report(*scan("서버의 경우 그렇다."))
    assert r1 is None or "의 경우" not in r1, "warn 임계 미달인데 보고됨"
    r2 = format_report(*scan("서버의 경우 그렇고 클라의 경우 아니다."))
    assert r2 and "의 경우" in r2, "warn 임계 도달인데 미보고"

    print("tone-linter selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
