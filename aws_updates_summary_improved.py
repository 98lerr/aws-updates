#!/usr/bin/env python3
import feedparser
import json
import re
from googletrans import Translator
from collections import defaultdict
from datetime import datetime, date, timedelta
import os
import html
import time
import random

# サービスアイコンマッピング（絵文字を使用）
SERVICE_ICONS = {
    'コンピュート系': '💻',
    'コンテナ系': '🐳',
    'ネットワーク系': '🌐',
    'DBストレージ系': '💾',
    'アプリケーション統合': '🔄',
    '開発環境': '👨‍💻',
    '運用管理': '🔧',
    'セキュリティ': '🔒',
    'データ処理・管理・分析': '📊',
    'AI/ML': '🤖',
    'コンタクトセンター': '📞',
    'IoT': '📱',
    'メディア': '🎬',
    '請求系': '💰',
    '移転と転送系': '🚚',
    'その他': '📦'
}

# 重要キーワード（強調表示用）
IMPORTANT_KEYWORDS = [
    'GA', '一般提供開始', 'プレビュー', '新機能', '新リージョン', 'リリース', 
    'サポート終了', '価格改定', 'セキュリティ', '脆弱性'
]

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

def strip_html(html_text):
    return re.sub('<[^<]+?>', '', html_text)

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

def trim_summary(summary_text, limit=200):
    if len(summary_text) > limit:
        # 文の途中で切れないように調整
        last_period = summary_text[:limit].rfind('。')
        if last_period > limit * 0.7:  # 70%以上の位置に句点があれば、そこで切る
            return summary_text[:last_period+1] + '...'
        return summary_text[:limit-3] + '...'
    return summary_text

def highlight_keywords(text):
    """重要キーワードを強調表示する"""
    for keyword in IMPORTANT_KEYWORDS:
        text = text.replace(keyword, f'**{keyword}**')
    return text

def is_important_update(title, summary):
    """重要な更新かどうかを判定"""
    for keyword in IMPORTANT_KEYWORDS:
        if keyword in title or keyword in summary:
            return True
    return False

def generate_toc(categories):
    """目次を生成"""
    toc = ["## 目次\n"]
    for i, cat in enumerate(categories):
        if cat in SERVICE_ICONS:
            toc.append(f"{i+1}. [{SERVICE_ICONS[cat]} {cat}](#{cat.replace(' ', '-').replace('/', '').lower()})")
    return "\n".join(toc) + "\n\n"

def safe_translate(translator, text, dest='ja', max_retries=3):
    """安全な翻訳処理（リトライ機能付き）"""
    for attempt in range(max_retries):
        try:
            # レート制限対策のための待機
            time.sleep(random.uniform(0.5, 1.5))
            result = translator.translate(text, dest=dest)
            return result.text
        except Exception as e:
            print(f"翻訳エラー (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))  # エラー時はより長く待機
            else:
                print(f"翻訳失敗、元のテキストを使用: {text[:50]}...")
                return text
    return text

def main():
    print("AWS更新情報の取得を開始します...")
    
    feed_url = 'https://aws.amazon.com/about-aws/whats-new/recent/feed/'
    feed = feedparser.parse(feed_url)
    
    # 前週（日曜～土曜）を計算
    today = date.today()
    prev_sunday, prev_saturday = get_prev_week_range(today)
    
    # 出力ファイル設定
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"awsupdates_{prev_sunday:%Y-%m-%d}_{prev_saturday:%Y-%m-%d}.md"
    filepath = os.path.join(output_dir, filename)
    out_file = open(filepath, 'w', encoding='utf-8')
    
    # ファイルパスコメントとヘッダーを出力
    print(f"<!-- filepath: {filepath} -->", file=out_file)
    print(f"# AWS 更新情報 ({prev_sunday:%Y-%m-%d} ～ {prev_saturday:%Y-%m-%d})\n", file=out_file)
    print(f"先週の AWS サービスアップデート情報をまとめています。\n", file=out_file)

    print("翻訳サービスを初期化中...")
    translator = Translator()
    
    # 特定サービス名を英語のまま維持するための例外リスト
    exceptional_services = ['AWS Control Tower', 'AWS Glue', 'Amazon SageMaker', 'AWS Lambda']
    # 例外サービス名の日本語訳を取得してマッピング
    exceptions_map = {}
    for svc in exceptional_services:
        jp = safe_translate(translator, svc)
        exceptions_map[jp] = svc

    grouped = defaultdict(list)
    service_count = defaultdict(int)

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
        
        # 重要度の判定
        important = is_important_update(title, summary)
        
        item = {
            'title': title, 
            'link': link, 
            'summary': summary, 
            'service': svc,
            'important': important,
            'date': pub_date.strftime('%Y-%m-%d')
        }
        grouped[category].append(item)
        if svc:
            service_count[svc] += 1

    # カテゴリの順序
    order = [
        'コンピュート系', 'コンテナ系', 'ネットワーク系', 'DBストレージ系', 'アプリケーション統合',
        '開発環境', '運用管理', 'セキュリティ', 'データ処理・管理・分析', 'AI/ML',
        'コンタクトセンター', 'IoT', 'メディア', '請求系', '移転と転送系', 'その他'
    ]
    
    # 目次を生成
    active_categories = [cat for cat in order if cat in grouped and grouped[cat]]
    print(generate_toc(active_categories), file=out_file)
    
    # Markdown形式で出力
    total_count = 0
    for cat in order:
        if cat not in grouped or not grouped[cat]:
            continue
            
        # カテゴリ見出し（アイコン付き）
        icon = SERVICE_ICONS.get(cat, '')
        print(f"## {icon} {cat}\n", file=out_file)
        
        # サービスごとにグループ化
        service_items = defaultdict(list)
        for item in grouped[cat]:
            service_items[item['service'] or '未分類'].append(item)
        
        # サービスごとに出力
        for service, items in service_items.items():
            # サービス名と説明を出力
            service_desc = get_service_description(service)
            if service_desc:
                print(f"### {service} - {service_desc}\n", file=out_file)
            else:
                print(f"### {service}\n", file=out_file)
                
            for item in items:
                total_count += 1
                # 重要な更新には目立つマーカーを追加
                importance_marker = "🔥 " if item['important'] else ""
                
                # タイトル見出し
                title_ja = safe_translate(translator, item['title'])
                
                # 翻訳後に例外サービス名を元の英語表記に戻す
                for jp, orig in exceptions_map.items():
                    title_ja = title_ja.replace(jp, orig)
                
                # 重要キーワードを強調
                title_ja = highlight_keywords(title_ja)
                
                print(f"#### {importance_marker}{title_ja}", file=out_file)
                
                # 項目の詳細をリストで出力
                print(f"- **日付**: {item['date']}", file=out_file)
                print(f"- **リンク**: [{item['link']}]({item['link']})", file=out_file)
                
                # 概要の翻訳
                summary_ja = safe_translate(translator, item['summary'])
                
                # 翻訳後に例外サービス名を元の英語表記に戻す
                for jp, orig in exceptions_map.items():
                    summary_ja = summary_ja.replace(jp, orig)
                
                summary_ja = trim_summary(summary_ja)
                summary_ja = highlight_keywords(summary_ja)
                
                print(f"- **概要**: {summary_ja}\n", file=out_file)
                
                # 区切り線を追加
                print("---\n", file=out_file)
    
    # 統計情報
    print("## 📊 統計情報\n", file=out_file)
    print(f"- **合計**: {total_count} 件のアップデート", file=out_file)
    
    # サービス別の更新数
    if service_count:
        print("- **サービス別更新数**:", file=out_file)
        for svc, count in sorted(service_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {svc}: {count} 件", file=out_file)
    
    # フッター
    print("\n---", file=out_file)
    print(f"*このレポートは {datetime.now():%Y-%m-%d} に自動生成されました*", file=out_file)
    
    # ファイルを閉じる
    out_file.close()
    print(f"更新情報を {filepath} に出力しました。")

if __name__ == '__main__':
    main()