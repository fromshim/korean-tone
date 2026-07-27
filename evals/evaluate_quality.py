#!/usr/bin/env python3
"""korean-tone 후보 출력을 결정론적 조건으로 1차 채점한다.

입력 JSONL 형식: {"id": "case-id", "output": "모델 출력"}
자연스러움 자체는 자동 점수로 확정하지 않는다. --write-review로 사람 검수표를 만든다.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_CASES = HERE / "quality-cases.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{lineno}: JSON 오류: {error}") from error
    return rows


def validate_cases(cases: list[dict]) -> None:
    required = {"id", "category", "prompt", "source", "reference"}
    ids = set()
    for index, case in enumerate(cases, start=1):
        missing = required - case.keys()
        if missing:
            raise ValueError(f"case {index}: 필수 키 누락: {', '.join(sorted(missing))}")
        if case["id"] in ids:
            raise ValueError(f"case id가 겹쳐: {case['id']}")
        ids.add(case["id"])
        for field in ("id", "category", "prompt", "source", "reference"):
            if not isinstance(case[field], str):
                raise ValueError(f"{case['id']}: {field}는 문자열이어야 해")
        for field in ("avoid", "must_match"):
            for pattern in case.get(field, []):
                re.compile(pattern)


def read_outputs(path: Path, valid_ids: set[str]) -> dict[str, str]:
    outputs = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        if not isinstance(row.get("id"), str) or not isinstance(row.get("output"), str):
            raise ValueError(f"{path}:{index}: id와 output 문자열이 필요해")
        case_id = row["id"]
        if case_id not in valid_ids:
            raise ValueError(f"{path}:{index}: 알 수 없는 case id: {case_id}")
        if case_id in outputs:
            raise ValueError(f"{path}:{index}: output id가 겹쳐: {case_id}")
        outputs[case_id] = row["output"]
    return outputs


def assertions(case: dict, output: str) -> list[tuple[str, bool]]:
    checks: list[tuple[str, bool]] = []

    for token in case.get("preserve", []):
        checks.append((f"좌표 유지: {token}", token in output))

    for pattern in case.get("avoid", []):
        checks.append((f"지양 표현 제거: /{pattern}/", re.search(pattern, output) is None))

    for pattern in case.get("must_match", []):
        checks.append((f"필수 의미 유지: /{pattern}/", re.search(pattern, output) is not None))

    for alternatives in case.get("include_any", []):
        label = " | ".join(alternatives)
        checks.append((f"뜻풀이 포함: {label}", any(word in output for word in alternatives)))

    if "min_lines" in case:
        nonempty = sum(1 for line in output.splitlines() if line.strip())
        checks.append((f"최소 {case['min_lines']}줄", nonempty >= case["min_lines"]))

    if "max_length_ratio" in case:
        source_len = max(len(case.get("source", "")), 1)
        checks.append((
            f"길이 비율 <= {case['max_length_ratio']}",
            len(output) / source_len <= case["max_length_ratio"],
        ))

    if "max_change_ratio" in case:
        source = case.get("source", "")
        similarity = difflib.SequenceMatcher(None, source, output).ratio()
        checks.append((
            f"변경 비율 <= {case['max_change_ratio']}",
            1 - similarity <= case["max_change_ratio"],
        ))

    if case.get("must_equal_source"):
        checks.append(("이미 자연스러운 원문 유지", output == case.get("source", "")))

    return checks


def write_review(path: Path, cases: list[dict], outputs: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "category",
        "prompt",
        "source",
        "reference",
        "candidate",
        "naturalness_1_5",
        "accuracy_1_5",
        "tone_match_1_5",
        "overcorrection_1_5",
        "notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            writer.writerow({
                "id": case["id"],
                "category": case["category"],
                "prompt": case["prompt"],
                "source": case.get("source", ""),
                "reference": case.get("reference", ""),
                "candidate": outputs.get(case["id"], ""),
            })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--outputs", type=Path)
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="reference 답안을 후보 출력으로 써서 평가기와 데이터셋을 점검",
    )
    parser.add_argument("--write-review", type=Path, metavar="CSV")
    args = parser.parse_args()

    if args.selftest and args.outputs:
        parser.error("--selftest와 --outputs는 함께 쓸 수 없어")
    if not args.selftest and not args.outputs:
        parser.error("--outputs <JSONL> 또는 --selftest가 필요해")

    try:
        cases = read_jsonl(args.cases)
        validate_cases(cases)
        valid_ids = {case["id"] for case in cases}
        if args.selftest:
            outputs = {case["id"]: case["reference"] for case in cases}
        else:
            outputs = read_outputs(args.outputs, valid_ids)
    except (OSError, ValueError, re.error) as error:
        print(f"평가 입력 오류: {error}", file=sys.stderr)
        return 2

    passed = 0
    total = 0
    missing = []
    for case in cases:
        output = outputs.get(case["id"])
        if output is None:
            missing.append(case["id"])
            continue
        checks = assertions(case, output)
        failures = [label for label, ok in checks if not ok]
        total += len(checks)
        passed += len(checks) - len(failures)
        verdict = "PASS" if not failures else "FAIL"
        print(f"[{verdict}] {case['id']} ({len(checks) - len(failures)}/{len(checks)})")
        for failure in failures:
            print(f"  - {failure}")

    if missing:
        print(f"\n후보 출력 누락: {', '.join(missing)}")

    score = passed / total if total else 0
    print(f"\n안전 게이트: {passed}/{total} ({score:.1%})")
    print("이 점수는 좌표·사실·구조 보존만 봐. 자연스러움은 사람 검수를 함께 써야 해.")

    if args.write_review:
        write_review(args.write_review, cases, outputs)
        print(f"검수표: {args.write_review}")

    return 0 if not missing and passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
