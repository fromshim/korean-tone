#!/usr/bin/env python3
"""korean-tone의 항상 적용되는 말투와 세션별 모드를 Claude Code에 넣는다.

SessionStart에서는 기본 규칙 전체를 한 번 넣고, UserPromptSubmit에서는 현재 모드를 짧게
다시 알려준다. `/korean-tone:easy` 같은 플러그인 스킬은 본문에 MODE_MARKER를 담으며,
Claude Code가 확장한 스킬 본문을 이 훅이 읽어 세션 모드를 바꾼다.

어떤 예외가 나도 조용히 끝낸다. 말투 훅 때문에 세션이나 사용자 입력을 막으면 안 된다.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path


VALID_MODES = ("default", "easy", "mz")
MODE_MARKER = re.compile(r"KOREAN_TONE_MODE\s*:\s*(default|easy|mz)\b", re.I)
DIRECT_COMMAND = re.compile(r"(?:^|\s)/korean-tone:(default|easy|mz)\b", re.I)
SAFE_SESSION_ID = re.compile(r"[^A-Za-z0-9._-]+")

REMINDERS = {
    "default": (
        "KOREAN TONE ACTIVE: default. 한국어 답변마다 자연스러운 말투를 적용한다. "
        "대시·번역투·수동태·압축된 보고서 용어를 걷어내고 코드 좌표는 그대로 둔다."
    ),
    "easy": (
        "KOREAN TONE ACTIVE: easy. 초등학생도 따라오게 짧은 문장으로 중간 단계를 풀어 쓴다. "
        "아기 말투는 쓰지 않고 코드 좌표와 정확성은 그대로 둔다."
    ),
    "mz": (
        "KOREAN TONE ACTIVE: mz. default의 사실·순서·설명량·식별자·수량·조건을 유지하고 "
        "말투만 자연스러운 MZ 반말로 바꾼다. 일반 문장의 마침표와 줄바꿈을 제한하거나 "
        "일반 동사를 ~함·~됨·~있음으로 만들지 않는다. 임은 밤티임·에바임 같은 평가 조합에만 "
        "쓴다. 원문에 없는 근거·효과·경험을 만들지 않는다. MZ 표현으로 문장이 끝날 때만 "
        "산문 마침표를 붙이지 않는다. 표현은 [강조]+[정도]+[의미 코어]+[어미]+[꼬리]로 "
        "조합한다. "
        "ㄹㅇ개밤티임;;은 ㄹㅇ+개+밤티+임+;;이며 ㄹㅇ·개는 문제 개수가 아니라 말의 강도다. "
        "야르=한 변화가 여러 일을 해결, 개좋=한 장점의 호평, 멘헤라=반복 실패·방어선 부재, "
        "늙크크=deprecated·legacy, 밤티=못생기고 엉킨 디자인·코드, 에바=과하거나 선 넘은 "
        "비용·복잡도·상황, 샤갈=황당한 반응이다. 나같경은 추천 문장의 첫 토큰이며 맨 앞에 "
        "둘 수 없으면 생략한다. 아자스!는 안전한 "
        "실행 제안의 가벼운 마무리에만 쓴다. 모든 표현이나 고정 순서를 강제하지 않는다."
    ),
}

# 서브에이전트에는 규칙 전문 대신 이 두 줄만 넣는다. 서브에이전트는 여럿 뜨니 전문을 넣으면
# 프롬프트마다 곱해진다. 놓친 번역투는 tone-linter가 파일 저장 시점에 잡는다.
SUBAGENT_SCOPE = (
    "파일로 저장하는 한국어 문서(README·문서·주석·커밋 메시지)에 이 말투를 적용한다. "
    "메인 에이전트에 올리는 보고문은 대상이 아니니 형식은 호출한 쪽 지시를 따른다."
)


def _plugin_root() -> Path:
    configured = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(configured).resolve() if configured else Path(__file__).resolve().parent.parent


def _config_root() -> Path:
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".claude"


def _session_key(data: dict) -> str:
    raw = str(data.get("session_id") or "global")
    cleaned = SAFE_SESSION_ID.sub("-", raw).strip(".-")[:120]
    return cleaned or "global"


def _mode_path(data: dict, config_root: Path | None = None) -> Path:
    base = config_root or _config_root()
    return base / ".korean-tone" / "modes" / _session_key(data)


def _read_mode(data: dict, config_root: Path | None = None) -> str:
    try:
        value = _mode_path(data, config_root).read_text(encoding="utf-8").strip()
        return value if value in VALID_MODES else "default"
    except OSError:
        return "default"


def _write_mode(data: dict, mode: str, config_root: Path | None = None) -> None:
    if mode not in VALID_MODES:
        return
    target = _mode_path(data, config_root)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".mode-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(mode + "\n")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _detect_mode(prompt: str) -> str | None:
    marker = MODE_MARKER.search(prompt)
    if marker:
        return marker.group(1).lower()
    command = DIRECT_COMMAND.search(prompt)
    return command.group(1).lower() if command else None


def _read_rule(name: str, plugin_root: Path | None = None) -> str:
    root = plugin_root or _plugin_root()
    return (root / "rules" / f"{name}.md").read_text(encoding="utf-8").strip()


def _emit_context(event: str, context: str) -> None:
    json.dump(
        {
            "suppressOutput": True,
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": context,
            },
        },
        sys.stdout,
        ensure_ascii=False,
    )


def _session_start(data: dict) -> None:
    source = data.get("source") or "startup"
    if source == "startup":
        _write_mode(data, "default")
    mode = _read_mode(data)

    context = _read_rule("default")
    if mode != "default":
        context += "\n\n" + _read_rule(mode)
    context += f"\n\n현재 모드: {mode}. 이 말투를 모든 한국어 답변에 계속 적용한다."
    _emit_context("SessionStart", context)


def _prompt_submit(data: dict) -> None:
    prompt = str(data.get("prompt") or "")
    requested = _detect_mode(prompt)
    if requested:
        _write_mode(data, requested)
    mode = requested or _read_mode(data)
    context = REMINDERS[mode]
    if requested and requested != "default":
        context = _read_rule(requested) + "\n\n" + context
    _emit_context("UserPromptSubmit", context)


def _subagent_start() -> None:
    # 서브에이전트 산출물은 파일로 남는다. easy·mz는 대화용 모드라 물려주지 않고 default로 고정한다.
    _emit_context("SubagentStart", REMINDERS["default"] + "\n" + SUBAGENT_SCOPE)


def _selftest() -> None:
    assert _detect_mode("KOREAN_TONE_MODE: easy\n설명") == "easy"
    assert _detect_mode("/korean-tone:mz") == "mz"
    assert _detect_mode("그냥 한국어로 말해줘") is None
    assert _session_key({"session_id": "a/b c"}) == "a-b-c"

    with tempfile.TemporaryDirectory() as temp_dir:
        config_root = Path(temp_dir)
        data = {"session_id": "session-1"}
        assert _read_mode(data, config_root) == "default"
        _write_mode(data, "easy", config_root)
        assert _read_mode(data, config_root) == "easy"
        _write_mode(data, "mz", config_root)
        assert _read_mode(data, config_root) == "mz"

    subagent_context = REMINDERS["default"] + "\n" + SUBAGENT_SCOPE
    assert "보고문은 대상이 아니" in subagent_context, "보고문을 제외한다는 범위가 빠지면 압축 스킬과 부딪힌다"
    assert "코드 좌표는 그대로 둔다" in subagent_context
    assert len(subagent_context) < 400, "서브에이전트마다 곱해지니 지시문을 짧게 유지한다"

    default_rule = _read_rule("default")
    assert len(default_rule) < 9000, "SessionStart 규칙은 10,000자 제한보다 여유 있게 작아야 한다"
    assert "대시" in default_rule and "seam" in default_rule and "유/무" in default_rule
    assert "default의 사실·순서·설명량·식별자·수량·조건" in REMINDERS["mz"]
    assert "마침표와 줄바꿈을 제한" in REMINDERS["mz"] and "MZ 표현으로 문장이 끝날 때만" in REMINDERS["mz"]
    assert "ㄹㅇ+개+밤티+임+;;" in REMINDERS["mz"] and "문제 개수가 아니라 말의 강도" in REMINDERS["mz"]
    assert "에바=과하거나 선 넘은" in REMINDERS["mz"] and "나같경은 추천 문장의 첫 토큰" in REMINDERS["mz"]
    assert "일반 동사를 ~함·~됨·~있음으로 만들지 않는다" in REMINDERS["mz"]
    assert "원문에 없는 근거·효과·경험을 만들지 않는다" in REMINDERS["mz"]
    assert "모든 표현이나 고정 순서를 강제하지 않는다" in REMINDERS["mz"]
    assert "마침표보다 줄바꿈" not in REMINDERS["mz"] and "네 박자" not in REMINDERS["mz"]

    mz_rule = _read_rule("mz")
    assert len(mz_rule) < 9000, "MZ 상세 규칙은 세션 컨텍스트를 과하게 차지하지 않아야 한다"
    assert "먼저 자연스러운 문장을 쓴다" in mz_rule and "마침표와 줄바꿈을 제한하지 않는다" in mz_rule
    assert "MZ 표현이 문장을 끝내면" in mz_rule and "산문 마침표를 덧붙이지 않는다" in mz_rule
    assert "표현을 부품으로 조합한다" in mz_rule and "ㄹㅇ + 개 + 밤티 + 임 + ;;" in mz_rule
    assert "구조 문제가 여러 개여야 `개`를 붙이는 것은 아니다" in mz_rule
    assert "`야르`" in mz_rule and "`늙크크`" in mz_rule and "`밤티`" in mz_rule and "`에바`" in mz_rule
    assert "`나같경`을 쓰기로 했다면 문장의 첫 토큰" in mz_rule
    assert "정해진 박자나 표현 순서를 반복하지 않는다" in mz_rule
    assert "네 박자 기준 예시" not in mz_rule and "`resolveConfig()`" not in mz_rule

    plugin_root = _plugin_root()
    for expected in VALID_MODES:
        skill = (plugin_root / "skills" / expected / "SKILL.md").read_text(encoding="utf-8")
        body = re.sub(r"^---[\s\S]*?---\s*", "", skill)
        assert _detect_mode(body) == expected, f"{expected} 스킬의 모드 표식을 읽지 못함"
        if expected == "mz":
            assert "자연스러운 마침표와 줄바꿈" in body and "MZ 표현으로 문장이 끝날 때만" in body
            assert "`ㄹㅇ + 개 + 밤티 + 임 + ;;`" in body and "문제 개수가 아니라 말의 강도" in body
            assert "`에바`" in body and "모든 표현을 채우거나 고정된 박자로 배열하지 않는다" in body
    print("tone-context selftest OK")


def main() -> None:
    if "--selftest" in sys.argv:
        _selftest()
        return
    try:
        data = json.load(sys.stdin)
        action = sys.argv[1] if len(sys.argv) > 1 else ""
        if action == "session-start":
            _session_start(data)
        elif action == "prompt-submit":
            _prompt_submit(data)
        elif action == "subagent-start":
            _subagent_start()
    except Exception:
        pass


if __name__ == "__main__":
    main()
