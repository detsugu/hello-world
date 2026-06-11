# FLUX コーヒー器具画像 生成パイプライン

`flux_generate.py` は Black Forest Labs (BFL) の FLUX.2 API を使って、
コーヒー抽出器具10種のフォトリアルな物撮り風画像(白背景)を一括生成する。

## 前提

- Python 3.10+ / `requests`
- BFL の API キー(<https://docs.bfl.ai> で取得)

## セットアップ & 実行

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export BFL_API_KEY="あなたのキー"     # コードやログには絶対に書かない

python3 flux_generate.py --test       # まず1枚テスト(V60)。品質・コスト確認
python3 flux_generate.py              # 全10件生成
python3 flux_generate.py --only 3     # 3番だけ再生成
python3 flux_generate.py --only 3 --seed 1234   # seed固定で微調整
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
