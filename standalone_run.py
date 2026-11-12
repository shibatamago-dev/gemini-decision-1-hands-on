"""Gemini Decision 1 の画像・設計書テストを自分のPCで実行するスクリプト。

Museの環境で実行したもの (11リクエスト・54問・53問正解) と同じ内容です。
APIキーは環境変数から読みます。キーをこのファイルに書かないでください。

使い方:
    export GEMINI_API_KEY="自分のAPIキー"
    python3 standalone_run.py            # 全11ケースを実行
    python3 standalone_run.py --dry-run  # APIを呼ばず、送る内容だけ確認

実行すると、ケースごとに正解・不正解と確信度を表示し、
生の全応答を同じフォルダの results.json に保存します。
1件あたり10〜20秒ほどかかるので、全体で2〜3分かかります。
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
IMG = BASE / "images"
OUT = BASE / "results.json"
HOST = "generativelanguage.googleapis.com"
URL = f"https://{HOST}/v1beta/decisions"

DRY_RUN = "--dry-run" in sys.argv


def api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key and not DRY_RUN:
        print("GEMINI_API_KEY が設定されていません。export GEMINI_API_KEY=... してから実行してください。", file=sys.stderr)
        sys.exit(2)
    return key


def call(payload):
    if DRY_RUN:
        return {"answers": {}, "usage": {}, "_dry_run": True}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key()},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}", flush=True)
        raise
    return data, (time.time() - t0) * 1000


def image_input(name, mime):
    with open(IMG / name, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return [{"type": "image", "mime_type": mime, "data": data}]


def bear_questions():
    return {
        "has_bear": {"type": "noul", "instructions": "Is there a bear in this image?"},
        "has_large_animal": {"type": "noul", "instructions": "Is there any large animal in this image?"},
        "what_animal": {
            "type": "choice", "instructions": "What animal is in this image?",
            "criteria": {
                "none": "There is no animal in the image.",
                "bear": "There is a bear in the image.",
                "dog": "There is a dog in the image.",
                "deer": "There is a deer in the image.",
                "other_animal": "There is some other animal in the image.",
            },
        },
        "proximity": {
            "type": "score", "instructions": "Rate how close or large the animal in this image appears.",
            "criteria": [
                "No animal is visible.",
                "An animal is visible but far away or small.",
                "An animal is visible close up or large in the frame.",
            ],
        },
    }


def road_questions():
    return {
        "has_fallen_luggage": {"type": "noul", "instructions": "Is there fallen luggage or a fallen box lying on the road?"},
        "road_clear": {"type": "noul", "instructions": "Is the road clear and passable for vehicles?"},
        "what_on_road": {
            "type": "choice", "instructions": "What is on the road?",
            "criteria": {
                "nothing": "The road is empty.",
                "luggage_or_box": "Fallen luggage or a fallen box is on the road.",
                "vehicle": "A vehicle is on the road.",
                "person": "A person is on the road.",
            },
        },
        "severity": {
            "type": "score", "instructions": "Rate how severely the road is obstructed.",
            "criteria": [
                "Clear: no obstruction.",
                "Partially obstructed: something is on the road but vehicles can pass.",
                "Blocked: a lane is blocked by fallen luggage or a box.",
            ],
        },
    }


CELLS = [
    "top-left", "top-center", "top-right",
    "middle-left", "middle-center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
]

CASES = []

# 1. ウォーリー (正解: 真ん中右)
waldo_q = {
    "waldo_cell": {
        "type": "choice",
        "instructions": "Which of the 9 grid cells contains Waldo, the person in a red-and-white striped shirt with a red bobble hat and glasses?",
        "criteria": {c: f"Waldo is in the {c} cell of the 3x3 grid." for c in CELLS},
    },
}
for c in CELLS:
    waldo_q[f"is_in_{c}"] = {
        "type": "noul",
        "instructions": f"Is Waldo, the person in a red-and-white striped shirt with a red bobble hat and glasses, in the {c} cell of the 3x3 grid?",
    }
CASES.append({
    "name": "waldo", "input": image_input("waldo-crowd.png", "image/png"), "questions": waldo_q,
    "expected": {"waldo_cell": "middle-right", **{f"is_in_{c}": (c == "middle-right") for c in CELLS}},
})

# 2. 設計書 (4つの欠陥を仕込んだ架空の設計書)
CASES.append({
    "name": "design_doc",
    "input": [{"type": "text", "text": (BASE / "sample_design_doc.txt").read_text(encoding="utf-8")}],
    "questions": {
        "has_purpose": {"type": "noul", "instructions": "Does this design document state its purpose and background?"},
        "has_nonfunctional": {"type": "noul", "instructions": "Does this design document define non-functional requirements such as performance, security, and availability?"},
        "has_constraints": {"type": "noul", "instructions": "Does this design document state its assumptions and constraints?"},
        "numbers_consistent": {"type": "noul", "instructions": "Are the numbers in the main text and in the architecture diagram consistent with each other (for example, the maximum number of simultaneous connections)?"},
        "has_error_handling": {"type": "noul", "instructions": "Does this design document describe how errors and exceptions are handled (input errors, database failures, import failures)?"},
        "terms_defined": {"type": "noul", "instructions": "Are all terms used in this design document defined, including 'inventory mode' (棚卸モード)?"},
        "has_impact_migration": {"type": "noul", "instructions": "Does this design document describe its impact scope and migration method?"},
        "completeness": {
            "type": "score", "instructions": "Rate the overall completeness of this design document.",
            "criteria": [
                "Severely incomplete: most required items are missing.",
                "Incomplete: several required items are missing.",
                "Partially complete: about half of the required items are present.",
                "Mostly complete: only minor items are missing.",
                "Complete: all required items are present.",
            ],
        },
    },
    "expected": {
        "has_purpose": True, "has_nonfunctional": False, "has_constraints": True,
        "numbers_consistent": False, "has_error_handling": False,
        "terms_defined": False, "has_impact_migration": True,
        "completeness": 2.0,
    },
})

# 3. 道路 (2枚)
for fname, exp in [
    ("road-clean.png", {"has_fallen_luggage": False, "road_clear": True, "what_on_road": "nothing", "severity": 0.0}),
    ("road-luggage.png", {"has_fallen_luggage": True, "road_clear": False, "what_on_road": "luggage_or_box", "severity": 2.0}),
]:
    CASES.append({
        "name": f"road/{fname}", "input": image_input(fname, "image/png"),
        "questions": road_questions(), "expected": exp,
    })

# 4. クマの絵 (3枚)
for fname, exp in [
    ("forest-none.png", {"has_bear": False, "has_large_animal": False, "what_animal": "none", "proximity": 0.0}),
    ("forest-bear.png", {"has_bear": True, "has_large_animal": True, "what_animal": "bear", "proximity": 2.0}),
    ("forest-dog.png", {"has_bear": False, "has_large_animal": True, "what_animal": "dog", "proximity": 1.0}),
]:
    CASES.append({
        "name": f"bear/{fname}", "input": image_input(fname, "image/png"),
        "questions": bear_questions(), "expected": exp,
    })

# 5. クマの写真風 (4枚)
for fname, exp in [
    ("bear-close.jpg", {"has_bear": True, "has_large_animal": True, "what_animal": "bear", "proximity": 2.0}),
    ("bear-distant.jpg", {"has_bear": True, "has_large_animal": True, "what_animal": "bear", "proximity": 1.0}),
    ("dog.jpg", {"has_bear": False, "has_large_animal": True, "what_animal": "dog", "proximity": 2.0}),
    ("empty.jpg", {"has_bear": False, "has_large_animal": False, "what_animal": "none", "proximity": 0.0}),
]:
    CASES.append({
        "name": f"realistic/{fname}", "input": image_input(fname, "image/jpeg"),
        "questions": bear_questions(), "expected": exp,
    })


def judge(case, answers):
    verdicts = {}
    for qid, exp in case["expected"].items():
        ans = answers.get(qid, {})
        atype = ans.get("type")
        if atype == "noul":
            got = ans.get("noul", 0) >= 0.5
            verdicts[qid] = {"expected": exp, "got": got, "noul": ans.get("noul"), "confidence": ans.get("confidence"), "pass": got == exp}
        elif atype == "choice":
            got = ans.get("choice")
            verdicts[qid] = {"expected": exp, "got": got, "probabilities": ans.get("probabilities"), "confidence": ans.get("confidence"), "pass": got == exp}
        elif atype == "score":
            got = ans.get("score")
            ok = got is not None and abs(got - exp) <= 0.6
            verdicts[qid] = {"expected": exp, "got": got, "probabilities": ans.get("probabilities"), "confidence": ans.get("confidence"), "pass": ok}
        else:
            verdicts[qid] = {"expected": exp, "got": None, "pass": False, "note": f"unexpected answer type {atype!r}"}
    return verdicts


def main():
    api_key()
    results = []
    total_q = 0
    passed_q = 0
    for case in CASES:
        print(f"=== {case['name']} ===", flush=True)
        payload = {"model": "gemini-decision-1", "input": case["input"], "questions": case["questions"]}
        if DRY_RUN:
            print(f"  [dry-run] input blocks={len(case['input'])} questions={len(case['questions'])}", flush=True)
            continue
        resp, elapsed_ms = call(payload)
        answers = resp.get("answers", {})
        verdicts = judge(case, answers)
        for qid, v in verdicts.items():
            total_q += 1
            passed_q += 1 if v["pass"] else 0
            mark = "OK " if v["pass"] else "MISS"
            print(f"  [{mark}] {qid}: expected={v['expected']!r} got={v.get('got')!r} conf={v.get('confidence')}", flush=True)
        usage = resp.get("usage", {})
        print(f"  elapsed={elapsed_ms:.0f}ms tokens={usage.get('total_input_tokens')} output={usage.get('total_output_tokens')}", flush=True)
        results.append({"case": case["name"], "elapsed_ms": round(elapsed_ms), "usage": usage, "response": resp, "verdicts": verdicts})
        OUT.write_text(json.dumps({"summary": {"passed_questions": passed_q, "total_questions": total_q, "cases": len(results), "partial": True}, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    if DRY_RUN:
        print(f"\nDRY RUN OK: {len(CASES)} cases, {sum(len(c['questions']) for c in CASES)} questions, no API calls made.")
        return
    summary = {"passed_questions": passed_q, "total_questions": total_q, "cases": len(results)}
    OUT.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSUMMARY: {passed_q}/{total_q} questions correct across {len(results)} cases")
    print(f"Full raw responses saved to {OUT}")


if __name__ == "__main__":
    main()
