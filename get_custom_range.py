#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from aws_updates_summary_improved import *
from datetime import date

async def custom_range_async():
    print("AWS更新情報の取得を開始します...")
    
    feed_url = 'https://aws.amazon.com/about-aws/whats-new/recent/feed/'
    feed = feedparser.parse(feed_url)
    
    # カスタム期間
    start_date = date(2025, 11, 23)
    end_date = date(2025, 11, 25)
    
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"awsupdates_{start_date:%Y-%m-%d}_{end_date:%Y-%m-%d}.md"
    filepath = os.path.join(output_dir, filename)
    out_file = open(filepath, 'w', encoding='utf-8')
    
    print(f"<!-- filepath: {filepath} -->", file=out_file)
    print(f"# AWS 更新情報 ({start_date:%Y-%m-%d} ～ {end_date:%Y-%m-%d})\n", file=out_file)
    print(f"期間内の AWS サービスアップデート情報をまとめています。\n", file=out_file)

    print("翻訳サービスを初期化中...")
    try:
        translator = Translator()
        test_result = await safe_translate_async(translator, "test")
        print(f"翻訳テスト結果: {test_result}")
    except Exception as e:
        print(f"翻訳サービス初期化エラー: {e}")
        translator = None
    
    exceptional_services = ['AWS Control Tower', 'AWS Glue', 'Amazon SageMaker', 'AWS Lambda']
    exceptions_map = {}
    if translator:
        for svc in exceptional_services:
            jp = await safe_translate_async(translator, svc)
            exceptions_map[jp] = svc

    grouped = defaultdict(list)
    service_count = defaultdict(int)

    for entry in feed.entries:
        if hasattr(entry, 'published_parsed'):
            pub_date = datetime(*entry.published_parsed[:6]).date()
        else:
            continue
        
        if not (start_date <= pub_date <= end_date):
            continue
        
        title = entry.title
        link = entry.link
        summary = strip_html(entry.summary)
        category, svc = get_category(title)
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

    order = [
        'コンピュート系', 'コンテナ系', 'ネットワーク系', 'DBストレージ系', 'アプリケーション統合',
        '開発環境', '運用管理', 'セキュリティ', 'データ処理・管理・分析', 'AI/ML',
        'コンタクトセンター', 'IoT', 'メディア', '請求系', '移転と転送系', 'その他'
    ]
    
    active_categories = [cat for cat in order if cat in grouped and grouped[cat]]
    print(generate_toc(active_categories), file=out_file)
    
    total_count = 0
    for cat in order:
        if cat not in grouped or not grouped[cat]:
            continue
            
        icon = SERVICE_ICONS.get(cat, '')
        print(f"## {icon} {cat}\n", file=out_file)
        
        service_items = defaultdict(list)
        for item in grouped[cat]:
            service_items[item['service'] or '未分類'].append(item)
        
        for service, items in service_items.items():
            service_desc = get_service_description(service)
            if service_desc:
                print(f"### {service} - {service_desc}\n", file=out_file)
            else:
                print(f"### {service}\n", file=out_file)
                
            for item in items:
                total_count += 1
                importance_marker = "🔥 " if item['important'] else ""
                
                if translator:
                    title_ja = await safe_translate_async(translator, item['title'])
                else:
                    title_ja = item['title']
                
                for jp, orig in exceptions_map.items():
                    title_ja = title_ja.replace(jp, orig)
                
                title_ja = highlight_keywords(title_ja)
                
                print(f"#### {importance_marker}{title_ja}", file=out_file)
                print(f"- **日付**: {item['date']}", file=out_file)
                print(f"- **リンク**: [{item['link']}]({item['link']})", file=out_file)
                
                if translator:
                    summary_ja = await safe_translate_async(translator, item['summary'])
                else:
                    summary_ja = item['summary']
                
                for jp, orig in exceptions_map.items():
                    summary_ja = summary_ja.replace(jp, orig)
                
                summary_ja = trim_summary(summary_ja)
                summary_ja = highlight_keywords(summary_ja)
                
                print(f"- **概要**: {summary_ja}\n", file=out_file)
                print("---\n", file=out_file)
    
    print("## 📊 統計情報\n", file=out_file)
    print(f"- **合計**: {total_count} 件のアップデート", file=out_file)
    
    if service_count:
        print("- **サービス別更新数**:", file=out_file)
        for svc, count in sorted(service_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {svc}: {count} 件", file=out_file)
    
    print("\n---", file=out_file)
    print(f"*このレポートは {datetime.now():%Y-%m-%d} に自動生成されました*", file=out_file)
    
    out_file.close()
    print(f"更新情報を {filepath} に出力しました。")

if __name__ == '__main__':
    asyncio.run(custom_range_async())
