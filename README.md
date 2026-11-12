# Gemini Decision 1 ハンズオン

Gemini Decision 1 を実際に動かして確かめたときの、再現用スクリプトとテスト画像です。

検証記事はこちら。

- [Gemini Decision 1を実際に動かしてみた。54問中53問正解、遅かったのはGoogleじゃなく環境だった](https://zenn.dev/shibatamago_dev/articles/gemini-decision-1-hands-on)
- [文章を書かないAI、4社目にGoogle。Gemini Decision 1とJev・Microsoft-Decision-1の違い](https://zenn.dev/shibatamago_dev/articles/decision-models-gemini-vs-jev-microsoft)

## 結果

- 11リクエスト・54問で **53問正解**。外れたのは1問だけ（絵のイヌを「大きな動物」と判定しなかった）。
- 速さは、直接つないだ自分のPC（Windows）ではテキストだけの問い合わせで **0.39秒**。公称の150〜250msに近いです。

## 使い方

APIキーは Google AI Studio（https://aistudio.google.com/apikey）で取得して、環境変数に入れてください。リポジトリにキーは含まれていません。

```bash
export GEMINI_API_KEY="自分のAPIキー"
```

### 54問ぜんぶを実行する

```bash
python standalone_run.py
```

11件のリクエストで54問を投げて、正誤を判定します。`--dry-run` を付けると、APIを呼ばずに仕様だけ確認できます。

### 速さだけ測る

```bash
python latency_probe.py
```

google.com への通信と、テキストだけの Decisions 呼び出しの時間を測ります。

Windows（PowerShell）の場合はこうです。

```powershell
$env:GEMINI_API_KEY = "自分のAPIキー"
python standalone_run.py
```

## ファイル

| ファイル | 内容 |
| --- | --- |
| `standalone_run.py` | 11件・54問の検証スクリプト |
| `latency_probe.py` | 速さだけ測るスクリプト |
| `sample_design_doc.txt` | 設計書テスト用の架空の設計書（欠陥を4つ仕込んであります） |
| `images/` | テスト画像10枚 |

## 画像について

`images/` の画像は、検証用に作った合成画像とAI生成の画像です。実際の写真ではありません。

- `waldo-crowd.png` … プログラムで描いた群衆の絵（ウォーリー探し用）
- `forest-*.png` … プログラムで描いた森の模式図
- `road-*.png` … 道路のテスト画像
- `bear-*.jpg` / `dog.jpg` / `empty.jpg` … AI生成の写真風の画像（クマ・イヌ・空き地）
