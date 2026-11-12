"""Gemini Decision 1 のレイテンシ切り分け用スクリプト。

自分のPCから実行して、Museの環境と比べるためのものです。
APIキーは環境変数から読みます。キーをこのファイルに書かないでください。

使い方:
    export GEMINI_API_KEY="自分のAPIキー"
    python3 latency_probe.py

測るもの:
    1. google.com への普通のGET (このPCの一般的な通信速度の目安)
    2. 画像なし・テキストだけの Decisions API 呼び出し
       (ヘッダ到着まで = Googleの回答待ち時間、全体 = 完了まで)

Museの環境での実測値 (2026-11-12):
    GET google.com: 0.73秒
    テキストだけの問い合わせ: 最初の返事まで 15.7秒、全体も 15.7秒
    スクリプト自体の処理は約0.1秒
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("GEMINI_API_KEY が設定されていません。export GEMINI_API_KEY=... してから実行してください。", file=sys.stderr)
    sys.exit(2)

HOST = "generativelanguage.googleapis.com"

# 1. このPCの一般的な通信速度の目安
t0 = time.time()
try:
    with urllib.request.urlopen("https://www.google.com", timeout=30) as resp:
        resp.read(1024)
    print(f"GET google.com: {time.time() - t0:.2f}s status={resp.status}")
except Exception as e:
    print(f"GET google.com: {time.time() - t0:.2f}s -> {type(e).__name__}: {e}")

# 2. 画像なし・テキストだけの Decisions API 呼び出し
payload = {
    "model": "gemini-decision-1",
    "input": [{"type": "text", "text": "The sky is blue on a clear day."}],
    "questions": {"sky_blue": {"type": "noul", "instructions": "Is the sky blue?"}},
}
body = json.dumps(payload).encode()
req = urllib.request.Request(
    f"https://{HOST}/v1beta/decisions",
    data=body,
    headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
    method="POST",
)
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        t_headers = time.time() - t0
        data = json.loads(resp.read())
        t_done = time.time() - t0
    ans = data["answers"]["sky_blue"]
    print(f"decisions text-only: headers_after={t_headers:.2f}s total={t_done:.2f}s status={resp.status}")
    print(f"  answer: noul={ans['noul']:.3f} confidence={ans['confidence']:.3f}")
except urllib.error.HTTPError as e:
    print(f"decisions text-only: {time.time() - t0:.2f}s -> HTTP {e.code}: "
          f"{e.read().decode('utf-8', 'replace')[:200]}")
except Exception as e:
    print(f"decisions text-only: {time.time() - t0:.2f}s -> {type(e).__name__}: {e}")
