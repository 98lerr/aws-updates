# AWS Updates Summary

AWSの週次アップデート情報を自動収集・翻訳・分類するツールです。

## 機能

- AWS公式RSSフィードから最新のアップデート情報を取得
- 日本語への自動翻訳
- サービス別・カテゴリ別の自動分類
- 重要な更新の強調表示
- Markdownレポートの自動生成

## 使用方法

### 基本実行

```bash
python3 aws_updates_summary_improved.py
```

### 必要な依存関係のインストール

```bash
pip install -r requirements.txt
```

## 出力

`output/` フォルダに以下の形式でファイルが生成されます：
- `awsupdates_YYYY-MM-DD_YYYY-MM-DD.md`

## テスト実行

```bash
python3 test_aws_updates_summary_improved.py
```

## ファイル構成

- `aws_updates_summary_improved.py` - メインスクリプト
- `service_mappings.json` - サービス分類設定
- `test_aws_updates_summary_improved.py` - ユニットテスト
- `requirements.txt` - 依存関係
- `output/` - 生成されたレポート格納フォルダ

## GitHub Actions

プッシュ時に自動でユニットテストが実行されます。

## ライセンス

MIT License