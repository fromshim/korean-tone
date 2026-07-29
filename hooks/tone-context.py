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
        "KOREAN TONE ACTIVE: mz. default와 정보·순서·설명량·구조를 똑같이 유지하고 말투만 "
        "인스타 댓글체로 바꾼다. 마침표보다 줄바꿈을 쓰고 ~함/~임 계열을 연속 사용하지 "
        "않는다. 고정 문구를 반복하지 말고 [관점]+[사실]+[선택적 강조]+[의미에 맞는 핵심 "
        "반응과 어미]+[선택적 꼬리]로 매번 새로 조합한다. 모든 칸을 채우지 말고 강한 반응은 "
        "보통 한두 개만 쓴다. ㄹㅇ·ㅋㅋ·아자스!는 자동으로 붙이지 않는다. 나같경은 내 "
        "선택을 여는 말, 야르·개좋·멘헤라·늙크크·밤티·샤갈은 각 의미가 맞을 때만 쓴다. "
        "코드 좌표와 정확성은 그대로 둔다."
    ),
}


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

    default_rule = _read_rule("default")
    assert len(default_rule) < 9000, "SessionStart 규칙은 10,000자 제한보다 여유 있게 작아야 한다"
    assert "대시" in default_rule and "seam" in default_rule and "유/무" in default_rule
    assert "default" in REMINDERS["mz"] and "정보·순서·설명량·구조" in REMINDERS["mz"]
    assert "마침표보다 줄바꿈" in REMINDERS["mz"] and "~함/~임 계열을 연속" in REMINDERS["mz"]
    assert "고정 문구를 반복하지" in REMINDERS["mz"] and "선택적 강조" in REMINDERS["mz"]
    assert "ㄹㅇ야르" not in REMINDERS["mz"] and "이러면ㄹㅇ멘헤라옴ㅋㅋ" not in REMINDERS["mz"]

    mz_rule = _read_rule("mz")
    assert len(mz_rule) < 9000, "MZ 상세 규칙은 세션 컨텍스트를 과하게 차지하지 않아야 한다"
    assert "조합 호환표" in mz_rule and "관점·도입" in mz_rule and "어미와 꼬리" in mz_rule
    assert "[구체적인 실패 사실]" in mz_rule and "또 터지면 ㄹㅇ멘헤라 올듯" not in mz_rule

    plugin_root = _plugin_root()
    for expected in VALID_MODES:
        skill = (plugin_root / "skills" / expected / "SKILL.md").read_text(encoding="utf-8")
        body = re.sub(r"^---[\s\S]*?---\s*", "", skill)
        assert _detect_mode(body) == expected, f"{expected} 스킬의 모드 표식을 읽지 못함"
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
    except Exception:
        pass


if __name__ == "__main__":
    main()
