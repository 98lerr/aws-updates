#!/usr/bin/env python3
import feedparser
import json
from googletrans import Translator
import re
from collections import defaultdict
from datetime import datetime, date, timedelta
import os

    # 外部JSONからカテゴリと説明を読み込む
try:
    _mapping_file = os.path.join(os.path.dirname(__file__), 'service_mappings.json')
    with open(_mapping_file, 'r', encoding='utf-8') as _f:
        _data = json.load(_f)
    CATEGORY_MAPPINGS = _data.get('category_mappings', {})
    SERVICE_DESCRIPTIONS = _data.get('service_descriptions', {})
except Exception:
    CATEGORY_MAPPINGS = {}
    SERVICE_DESCRIPTIONS = {}

# サービスごとのカテゴリマッピング
def get_category(title):
    for svc, cat in CATEGORY_MAPPINGS.items():
        if svc in title:
            return cat, svc
    return 'その他', None

# サービス概要マッピング
def get_service_description(svc):
    return SERVICE_DESCRIPTIONS.get(svc, '')


def strip_html(html):
    return re.sub('<[^<]+?>', '', html)

# ユーティリティ関数
def get_prev_week_range(today=None):
    if today is None:
        today = date.today()
    current_sunday = today - timedelta(days=(today.weekday()+1) % 7)
    prev_sunday = current_sunday - timedelta(days=7)
    prev_saturday = prev_sunday + timedelta(days=6)
    return prev_sunday, prev_saturday

def is_in_prev_week(pub_date, today=None):
    start, end = get_prev_week_range(today)
    return start <= pub_date <= end

def trim_summary(summary_text, limit=150):
    if len(summary_text) > limit:
        return summary_text[:limit-3] + '...'
    return summary_text


def main():
    feed_url = 'https://aws.amazon.com/about-aws/whats-new/recent/feed/'
    feed = feedparser.parse(feed_url)
    # 前週（日曜～土曜）を計算
    today = date.today()
    current_sunday = today - timedelta(days=(today.weekday()+1) % 7)
    prev_sunday = current_sunday - timedelta(days=7)
    prev_saturday = prev_sunday + timedelta(days=6)
    # 出力ファイル設定
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"awsupdates_{prev_sunday:%Y-%m-%d}_{prev_saturday:%Y-%m-%d}.md"
    filepath = os.path.join(output_dir, filename)
    out_file = open(filepath, 'w', encoding='utf-8')
    # ファイルパスコメントとヘッダーを出力
    print(f"<!-- filepath: {filepath} -->\n# AWS 更新 ({prev_sunday:%Y-%m-%d} ～ {prev_saturday:%Y-%m-%d})\n", file=out_file)

    translator = Translator()
    # 特定サービス名を英語のまま維持するための例外リスト
    exceptional_services = ['AWS Control Tower', 'AWS Glue']
    # 例外サービス名の日本語訳を取得してマッピング
    exceptions_map = {}
    for svc in exceptional_services:
        try:
            jp = translator.translate(svc, dest='ja').text
        except Exception:
            jp = svc
        exceptions_map[jp] = svc

    grouped = defaultdict(list)

    for entry in feed.entries:
        # 公開日を構造体から取得
        if hasattr(entry, 'published_parsed'):
            pub_date = datetime(*entry.published_parsed[:6]).date()
        else:
            continue
        # 前週の期間外はスキップ
        if not is_in_prev_week(pub_date, today):
            continue
        title = entry.title
        link = entry.link
        summary = strip_html(entry.summary)
        category, svc = get_category(title)
        item = {'title': title, 'link': link, 'summary': summary, 'service': svc}
        grouped[category].append(item)

    # Markdown形式で出力
    total_count = 0
    order = [
        'コンピュート系','コンテナ系','ネットワーク系','DBストレージ系','アプリケーション統合',
        '開発環境','運用管理','セキュリティ','データ処理・管理・分析','AI/ML',
        'コンタクトセンター','IoT','メディア','請求系','その他'
    ]
    for cat in order:
        if cat in grouped and grouped[cat]:
            # カテゴリ見出し
            print(f"## {cat}\n", file=out_file)
            for itm in grouped[cat]:
                total_count += 1
                # タイトル見出し
                try:
                    title_ja = translator.translate(itm['title'], dest='ja').text
                except Exception:
                    title_ja = itm['title']
                # 翻訳後に例外サービス名を元の英語表記に戻す
                for jp, orig in exceptions_map.items():
                    title_ja = title_ja.replace(jp, orig)
                print(f"#### {title_ja}", file=out_file)
                # 項目の詳細をリストで出力
                print(f"- リンク: {itm['link']}", file=out_file)
                if itm['service']:
                    print(f"- サービス: {itm['service']}", file=out_file)
                # 概要の翻訳
                try:
                    summary_ja = translator.translate(itm['summary'], dest='ja').text
                except Exception:
                    summary_ja = itm['summary']
                # 翻訳後に例外サービス名を元の英語表記に戻す
                for jp, orig in exceptions_map.items():
                    summary_ja = summary_ja.replace(jp, orig)
                summary_ja = trim_summary(summary_ja)
                print(f"- 概要: {summary_ja}\n", file=out_file)
    # 合計をMarkdown強調で出力
    print(f"**合計**: {total_count} 件のアップデートがありました。", file=out_file)
    # ファイルを閉じる
    out_file.close()

if __name__ == '__main__':
    main()
