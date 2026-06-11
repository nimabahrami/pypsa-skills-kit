#!/usr/bin/env python3
"""run_evals.py - trigger-precision runner for evals.json.

For each eval case, an LLM judge is shown ONLY the 9 L1 descriptions (exactly
what a skill router sees) plus the case prompt, and must answer with one skill
name or NONE. Scored against `expected` / `should_trigger`.

Usage:
    python run_evals.py                 # all cases (one `claude -p` call each)
    python run_evals.py --ids rp-pos-1,neg-pandapower
    python run_evals.py --dry           # print judge prompts, call nothing

Requires the `claude` CLI on PATH (any working model). Each case costs one
small completion; the full set is ~25 calls.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_descriptions() -> dict[str, str]:
    out = {}
    for f in sorted(ROOT.glob("*/SKILL.md")):
        m = re.search(r"^description:\s*(.+?)(?=\n[a-zA-Z-]+:|\n---)",
                      f.read_text(), re.S | re.M)
        if m:
            out[f.parent.name] = " ".join(m.group(1).split())
    return out


def judge_prompt(descriptions: dict[str, str], case_prompt: str) -> str:
    lines = [f"- {name}: {desc}" for name, desc in descriptions.items()]
    return (
        "You are a skill router. Below are the available skills with their "
        "trigger descriptions, then a user prompt. Answer with EXACTLY one "
        "skill name from the list, or NONE if no skill should activate "
        "(e.g. the prompt concerns a different software stack or a "
        "non-energy task). Answer with the single token only.\n\n"
        "SKILLS:\n" + "\n".join(lines) + f"\n\nUSER PROMPT: {case_prompt}\n\nANSWER:"
    )


def ask(prompt: str) -> str:
    r = subprocess.run(["claude", "-p", prompt], capture_output=True,
                       text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {r.stderr[:200]}")
    return r.stdout.strip()


def grade(answer: str, case: dict) -> tuple[bool, str]:
    ans = answer.strip().strip(".`'\"").split()[-1] if answer.strip() else ""
    picked = None
    for name in load_descriptions():
        if name in answer:
            picked = name
            break
    if ans.upper() == "NONE" and picked is None:
        picked = None
    elif picked is None:
        picked = ans if ans.startswith("pypsa-") else None
    if not case["should_trigger"]:
        return picked is None, f"picked={picked}"
    expected = case["expected"]
    accepted = expected if isinstance(expected, list) else [expected]
    return picked in accepted, f"picked={picked} accepted={accepted}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids", help="comma-separated case ids to run")
    ap.add_argument("--dry", action="store_true", help="print prompts only")
    args = ap.parse_args()

    data = json.loads((ROOT / "evals.json").read_text())
    cases = data["cases"]
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    descriptions = load_descriptions()
    if len(descriptions) != 9:
        print(f"WARNING: found {len(descriptions)} descriptions, expected 9")

    fails = 0
    for case in cases:
        prompt = judge_prompt(descriptions, case["prompt"])
        if args.dry:
            print(f"--- {case['id']} ---\n{prompt}\n")
            continue
        try:
            answer = ask(prompt)
            ok, detail = grade(answer, case)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"runner error: {e}"
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {case['id']:20s} {detail}")
    if not args.dry:
        print(f"\n{fails} failure(s) / {len(cases)} case(s)")
    return 1 if (fails and not args.dry) else 0


if __name__ == "__main__":
    sys.exit(main())
