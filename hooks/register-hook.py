#!/usr/bin/env python3
"""tone-linter 훅을 Claude Code settings.json 에 등록한다.

기본은 전역(~/.claude/settings.json). `--project <dir>` 로 프로젝트 스코프에도 등록 가능.
멱등(이미 있으면 스킵) + 실행 전 .bak 백업 + 등록 후 기존 설정 보존 검증.
tone-linter.py 경로는 이 스크립트 위치로 계산하므로, 레포를 옮겼으면 그냥 다시 실행하면 된다.

    python3 register-hook.py              # 전역 등록
    python3 register-hook.py --project .  # 현재 프로젝트에도 등록
    python3 register-hook.py --remove     # 전역에서 제거
"""
import argparse
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
LINTER = os.path.join(HERE, "tone-linter.py")
HOOK_CMD = f"python3 {LINTER}"


def load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(path, cfg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def register(path):
    cfg = load(path)
    before = json.dumps(cfg, ensure_ascii=False, sort_keys=True)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")

    post = cfg.setdefault("hooks", {}).setdefault("PostToolUse", [])
    if any(h.get("command") == HOOK_CMD
           for entry in post for h in entry.get("hooks", [])):
        print(f"이미 등록됨 — 변경 없음: {path}")
        return
    post.append({
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 10}],
    })
    save(path, cfg)

    # 검증: 우리가 더한 것 말고 다른 최상위 키는 그대로여야
    after = load(path)
    old = json.loads(before) if before != "{}" else {}
    for k, v in old.items():
        if k != "hooks":
            assert after.get(k) == v, f"기존 키 손상: {k}"
    print(f"등록 완료: {path}\n  command: {HOOK_CMD}")


def remove(path):
    cfg = load(path)
    post = cfg.get("hooks", {}).get("PostToolUse", [])
    kept = [e for e in post
            if not any(h.get("command") == HOOK_CMD for h in e.get("hooks", []))]
    if len(kept) == len(post):
        print(f"등록돼 있지 않음: {path}")
        return
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    cfg["hooks"]["PostToolUse"] = kept
    save(path, cfg)
    print(f"제거 완료: {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", metavar="DIR", help="프로젝트 .claude/settings.json 에 등록")
    ap.add_argument("--remove", action="store_true", help="전역에서 제거")
    args = ap.parse_args()

    target = (os.path.join(os.path.abspath(args.project), ".claude", "settings.json")
              if args.project
              else os.path.expanduser("~/.claude/settings.json"))
    remove(target) if args.remove else register(target)
