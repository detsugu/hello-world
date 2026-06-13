# FLUX コーヒー器具画像 生成パイプライン

`flux_generate.py` は Black Forest Labs (BFL) の FLUX.2 API を使って、
コーヒー器具のフォトリアルな物撮り風画像(純白背景)を生成する。

現在の主タスクは、既存14点(抽出器具10 + 豆4)に画風を合わせた
**追加11点(No.15〜25 = サポート器具)** の生成。

## 生成対象(No.15〜25 / `--added`)

| # | ファイル | 被写体 |
|---|---|---|
| 15 | 15_grinder_hand.png | 手挽きコーヒーミル |
| 16 | 16_grinder_electric.png | 電動グラインダー(ホッパー付き) |
| 17 | 17_kettle.png | 細口ドリップケトル(グースネック) |
| 18 | 18_scale.png | コーヒースケール(タイマー付き) |
| 19 | 19_server.png | ガラスサーバー(目盛り付き) |
| 20 | 20_paper_filter.png | ペーパーフィルター(円錐形) |
| 21 | 21_espresso_machine.png | 家庭用エスプレッソマシン(半自動) |
| 22 | 22_portable_espresso.png | 手動ポータブルエスプレッソ |
| 23 | 23_tamper.png | タンパー |
| 24 | 24_canister.png | キャニスター |
| 25 | 25_mug.png | コーヒーマグ(無地) |

※ No.1〜10(既存抽出器具)も `--only N` で個別再生成できるよう保持。
豆4点(11〜14)は別被写体のため本スクリプトには含めない。

画風: 純白背景(#FFFFFF)・被写体中央・単体・3/4俯瞰・薄い影は真下〜手前・
柔らかい均一ライティング・文字/ロゴ/ブランド名なし・余白広め・1024x1024 PNG。

## 前提

- Python 3.9+ / `requests`
- BFL の API キー(<https://docs.bfl.ai> で取得)

## セットアップ & 実行

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export BFL_API_KEY="あなたのキー"     # コードやログには絶対に書かない

python3 flux_generate.py --test       # No.15(手挽きミル)1枚でテスト → 既存14点と画風を比較
python3 flux_generate.py --added      # 追加11点(15〜25)を一括生成
python3 flux_generate.py --only 17    # 17番だけ再生成
python3 flux_generate.py --only 17 --seed 1234        # seed固定で微調整
python3 flux_generate.py --only 17 --ref ref.jpg      # 参照画像で形を寄せる
```

出力先は既定で `~/Documents/Claude/flux-coffee/output/`。
`FLUX_OUTPUT_DIR` 環境変数で変更できる。
生成ログ(prompt / task_id / seed / file)は同ディレクトリの
`generation_log.json` に追記される。

## 2026年6月時点の API メモ(更新済みの根拠)

- モデル: `flux-2-pro`(FLUX.2 [pro]、最新フォトリアル向け)
- ベースURL: `https://api.bfl.ai/v1` / 認証ヘッダ: `x-key`
- submit のレスポンスに **region 固有の `polling_url`** が返るため、
  グローバルな `get_result` ではなくその URL を直接ポーリングする
  (FLUX.2 のリージョナルルーティング対応。旧コードの主な修正点)。
- `output_format` の既定は **jpeg**。`.png` 保存に合わせ png を明示要求。
- 結果URLは約10分で失効 → Ready 後すぐにダウンロード。
- スロットリング(poll 1.5s / リクエスト間 2s)は外さないこと。

## コスト目安

FLUX.2 [pro] は1枚あたり概ね数円〜十数円。10枚で数十円〜百数十円程度。
最新価格は <https://bfl.ai/pricing> を確認。
