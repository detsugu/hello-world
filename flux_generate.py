#!/usr/bin/env python3
"""
FLUX APIでコーヒー抽出器具のフォトリアル画像を一括生成するスクリプト。

使い方:
  export BFL_API_KEY="xxxx"
  python3 flux_generate.py            # 全件生成
  python3 flux_generate.py --only 1   # 1番(V60)だけ生成
  python3 flux_generate.py --test     # 先頭1件だけテスト生成
  python3 flux_generate.py --seed 42  # seed固定(再現/微調整用)

出力先は環境変数 FLUX_OUTPUT_DIR で上書き可。未指定なら
~/Documents/Claude/flux-coffee/output/ に保存する。

API仕様(2026年6月時点、https://docs.bfl.ai で確認済み):
  - 最新フォトリアル向けモデルは FLUX.2 = エンドポイント "flux-2-pro"。
  - 認証ヘッダは x-key。
  - submit のレスポンスに region 固有の "polling_url" が返るので、
    グローバルな get_result ではなく必ずその URL をポーリングすること。
  - output_format の既定は jpeg。.png で保存するため明示的に png を要求する。
  - 結果URLは約10分で失効するため、Ready 後すぐにダウンロードする。
"""

from __future__ import annotations  # Python 3.9 互換(int | None 等の遅延評価)

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

# ===== 設定 =====
API_BASE = "https://api.bfl.ai/v1"
MODEL_ENDPOINT = "flux-2-pro"  # FLUX.2 [pro] = 2026年6月時点の最新フォトリアル向け
POLL_INTERVAL = 1.5
SLEEP_BETWEEN = 2.0
WIDTH, HEIGHT = 1024, 1024
OUTPUT_FORMAT = "png"  # 既定は jpeg なので .png 保存に合わせて明示

OUTPUT_DIR = Path(
    os.environ.get("FLUX_OUTPUT_DIR", "")
    or (Path.home() / "Documents/Claude/flux-coffee/output")
)
LOG_PATH = OUTPUT_DIR / "generation_log.json"

PROMPT_TEMPLATE = (
    "professional product photography of {item}, "
    "isolated on pure white seamless background, soft studio lighting, "
    "sharp focus, high detail, photorealistic, "
    "no text, no watermark, no logos, no engraved lettering"
)

EQUIPMENT = [
    (1,  "v60",          "a plain white ceramic conical pour-over coffee dripper with spiral interior ribs and a curved side handle, a single one-piece molded ceramic body where the cone and the base stand are seamlessly integrated as one continuous piece, smooth unmarked surface"),
    (2,  "chemex",       "an hourglass-shaped glass pour-over coffee maker with wooden collar and leather tie"),
    (3,  "french_press", "a glass french press coffee maker with stainless steel frame and plunger"),
    (4,  "aeropress",    "a plastic AeroPress-style manual coffee press with plunger and filter cap"),
    (5,  "siphon",       "a two-cup glass siphon vacuum coffee brewer with alcohol burner and stand"),
    (6,  "moka_pot",     "a classic aluminum stovetop moka pot espresso maker, octagonal shape"),
    (7,  "kalita_wave",  "a stainless steel flat-bottom wave-style coffee dripper"),
    (8,  "nel_drip",     "a Japanese nel drip coffee filter: a soft flannel cloth filter bag shaped as a deep rounded cone with a smoothly curved round bottom (not a sharp triangular pyramid), the cloth mouth stretched over a circular metal hoop ring attached to a wooden handle"),
    (9,  "cold_brew",    "a glass cold brew coffee pot with fine mesh strainer column"),
    (10, "ibrik",        "a traditional hammered copper cezve ibrik turkish coffee pot with long brass handle"),
]


def submit(session: requests.Session, api_key: str, prompt: str, seed: int | None) -> dict:
    """生成リクエストを投げて {id, polling_url} を返す。"""
    payload = {
        "prompt": prompt,
        "width": WIDTH,
        "height": HEIGHT,
        "output_format": OUTPUT_FORMAT,
    }
    if seed is not None:
        payload["seed"] = seed
    resp = session.post(
        f"{API_BASE}/{MODEL_ENDPOINT}",
        headers={"x-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    # 新APIは region 固有の polling_url を返す。無ければ id から組み立てる。
    polling_url = data.get("polling_url") or f"{API_BASE}/get_result"
    return {"id": data["id"], "polling_url": polling_url}


def poll(session: requests.Session, api_key: str, task: dict, timeout_s: int = 180) -> dict:
    """完了までポーリングし、result(sample / seed 等)を返す。"""
    deadline = time.time() + timeout_s
    # polling_url が id クエリを含まないグローバル形式の場合に備えて params を付与。
    params = None if task["polling_url"].rstrip("/").endswith(task["id"]) else {"id": task["id"]}
    while time.time() < deadline:
        resp = session.get(
            task["polling_url"],
            headers={"x-key": api_key},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "Ready":
            return data["result"]
        if status in ("Error", "Failed", "Content Moderated", "Request Moderated"):
            raise RuntimeError(f"generation failed: {data}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"task {task['id']} timed out")


def save_image(session: requests.Session, sample: str, path: Path) -> None:
    """URLまたはbase64文字列から画像を保存する。"""
    if sample.startswith("http"):
        img = session.get(sample, timeout=60)
        img.raise_for_status()
        path.write_bytes(img.content)
    else:
        path.write_bytes(base64.b64decode(sample))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, help="指定番号の器具のみ生成")
    parser.add_argument("--test", action="store_true", help="先頭1件のみテスト生成")
    parser.add_argument("--seed", type=int, default=None, help="seed固定(再現/微調整用)")
    args = parser.parse_args()

    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        print("環境変数 BFL_API_KEY を設定してください", file=sys.stderr)
        return 1

    targets = EQUIPMENT
    if args.only:
        targets = [e for e in EQUIPMENT if e[0] == args.only]
        if not targets:
            print(f"番号 {args.only} は存在しません", file=sys.stderr)
            return 1
    elif args.test:
        targets = EQUIPMENT[:1]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log = json.loads(LOG_PATH.read_text()) if LOG_PATH.exists() else []

    session = requests.Session()
    for num, slug, item in targets:
        prompt = PROMPT_TEMPLATE.format(item=item)
        out_path = OUTPUT_DIR / f"{num:02d}_{slug}.png"
        print(f"[{num:02d}] {slug} を生成中...")
        try:
            task = submit(session, api_key, prompt, args.seed)
            result = poll(session, api_key, task)
            save_image(session, result["sample"], out_path)
            print(f"  -> 保存: {out_path}")
            log.append({
                "num": num, "slug": slug, "prompt": prompt,
                "task_id": task["id"], "seed": result.get("seed", args.seed),
                "file": str(out_path),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
        except Exception as e:
            print(f"  !! 失敗: {e}", file=sys.stderr)
            log.append({"num": num, "slug": slug, "error": str(e),
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
        LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2))
        time.sleep(SLEEP_BETWEEN)

    print("完了。generation_log.json を確認してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
