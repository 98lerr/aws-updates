#!/usr/bin/env python3
import feedparser
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import re
import html
import asyncio
import random
from googletrans import Translator

def load_blog_sources():
    with open('blog_sources.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)['blogs']

async def safe_translate_async(translator, text, dest='ja', max_retries=2):
    if not text or len(text.strip()) == 0:
        return text
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                await asyncio.sleep(random.uniform(1, 3))
            result = await translator.translate(text, dest=dest)
            return result.text if hasattr(result, 'text') else text
        except Exception as e:
            if attempt == max_retries - 1:
                return text
    return text

def trim_summary(text, limit=200):
    if len(text) > limit:
        return text[:limit-3] + '...'
    return text

def fetch_blog_posts(blog_url, days=7):
    feed = feedparser.parse(blog_url)
    cutoff_date = datetime.now() - timedelta(days=days)
    posts = []
    
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6])
        if pub_date >= cutoff_date:
            posts.append({
                'title': entry.title,
                'link': entry.link,
                'date': pub_date.strftime('%Y-%m-%d'),
                'summary': entry.get('summary', '')
            })
    
    return sorted(posts, key=lambda x: x['date'], reverse=True)

async def generate_markdown_async(blog_data, start_date, end_date, translator):
    md = f"# AWS ブログ記事まとめ ({start_date} ～ {end_date})\n\n"
    
    for blog in blog_data:
        if not blog['posts']:
            continue
            
        md += f"## {blog['name']}\n\n"
        for post in blog['posts']:
            clean_summary = re.sub('<[^<]+?>', '', post['summary'])
            clean_summary = html.unescape(clean_summary).strip()
            
            title_ja = await safe_translate_async(translator, post['title'])
            summary_ja = await safe_translate_async(translator, clean_summary)
            summary_ja = trim_summary(summary_ja)
            
            md += f"### {title_ja}\n"
            md += f"- **日付**: {post['date']}\n"
            md += f"- **リンク**: [{post['link']}]({post['link']})\n"
            md += f"- **概要**: {summary_ja}\n\n"
            md += "---\n\n"
    
    return md

async def main_async():
    blogs = load_blog_sources()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    translator = Translator()
    
    blog_data = []
    for blog in blogs:
        print(f"Fetching {blog['name']}...")
        posts = fetch_blog_posts(blog['url'])
        blog_data.append({
            'name': blog['name'],
            'posts': posts
        })
    
    print("Translating...")
    markdown = await generate_markdown_async(
        blog_data,
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        translator
    )
    
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    filename = f"awsblogs_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"Generated: {output_path}")

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
