#!/usr/bin/env python3
import unittest
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import aws_blog_summary

class TestBlogSummary(unittest.TestCase):
    
    def test_load_blog_sources(self):
        """ブログソース定義ファイルの読み込みテスト (YAML)"""
        blogs = aws_blog_summary.load_blog_sources()
        self.assertIsInstance(blogs, list)
        self.assertGreater(len(blogs), 0)
        self.assertIn('name', blogs[0])
        self.assertIn('url', blogs[0])
    
    def test_trim_summary(self):
        """要約文字数制限のテスト"""
        short_text = "短いテキスト"
        self.assertEqual(aws_blog_summary.trim_summary(short_text, 200), short_text)
        
        long_text = "a" * 300
        result = aws_blog_summary.trim_summary(long_text, 200)
        self.assertLessEqual(len(result), 200)
        self.assertTrue(result.endswith('...'))
    
    @patch('feedparser.parse')
    def test_fetch_blog_posts(self, mock_parse):
        """ブログ記事取得のテスト"""
        mock_entry = Mock()
        mock_entry.title = "Test Blog Post"
        mock_entry.link = "https://example.com/blog"
        mock_entry.summary = "Test summary"
        mock_entry.published_parsed = datetime.now().timetuple()[:6]
        
        mock_feed = Mock()
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed
        
        posts = aws_blog_summary.fetch_blog_posts("https://example.com/feed/", days=7)
        
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['title'], "Test Blog Post")
        self.assertEqual(posts[0]['link'], "https://example.com/blog")
        self.assertIn('date', posts[0])
    
    @patch('feedparser.parse')
    def test_fetch_blog_posts_date_filter(self, mock_parse):
        """日付フィルタリングのテスト"""
        old_entry = Mock()
        old_entry.title = "Old Post"
        old_entry.link = "https://example.com/old"
        old_entry.summary = "Old summary"
        old_entry.published_parsed = (datetime.now() - timedelta(days=10)).timetuple()[:6]
        
        recent_entry = Mock()
        recent_entry.title = "Recent Post"
        recent_entry.link = "https://example.com/recent"
        recent_entry.summary = "Recent summary"
        recent_entry.published_parsed = (datetime.now() - timedelta(days=3)).timetuple()[:6]
        
        mock_feed = Mock()
        mock_feed.entries = [old_entry, recent_entry]
        mock_parse.return_value = mock_feed
        
        posts = aws_blog_summary.fetch_blog_posts("https://example.com/feed/", days=7)
        
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['title'], "Recent Post")
    
    def test_safe_translate_async(self):
        """翻訳機能のテスト"""
        async def run_test():
            mock_translator = Mock()
            mock_result = Mock()
            mock_result.text = "翻訳されたテキスト"
            
            async def mock_translate(*args, **kwargs):
                return mock_result
            
            mock_translator.translate = mock_translate
            
            result = await aws_blog_summary.safe_translate_async(
                mock_translator, 
                "Test text"
            )
            
            self.assertEqual(result, "翻訳されたテキスト")
        
        asyncio.run(run_test())
    
    def test_safe_translate_async_empty_text(self):
        """空文字列の翻訳テスト"""
        async def run_test():
            mock_translator = Mock()
            result = await aws_blog_summary.safe_translate_async(mock_translator, "")
            self.assertEqual(result, "")
        
        asyncio.run(run_test())
    
    def test_generate_markdown_async(self):
        """Markdown生成のテスト"""
        async def run_test():
            mock_translator = Mock()
            mock_result = Mock()
            mock_result.text = "翻訳済み"
            mock_translator.translate = Mock(return_value=mock_result)
            
            blog_data = [
                {
                    'name': 'テストブログ',
                    'posts': [
                        {
                            'title': 'Test Title',
                            'link': 'https://example.com',
                            'date': '2025-11-20',
                            'summary': 'Test summary'
                        }
                    ]
                }
            ]
            
            markdown = await aws_blog_summary.generate_markdown_async(
                blog_data,
                '2025-11-18',
                '2025-11-25',
                mock_translator
            )
            
            self.assertIn('AWS ブログ記事まとめ', markdown)
            self.assertIn('テストブログ', markdown)
            self.assertIn('https://example.com', markdown)
            self.assertIn('2025-11-20', markdown)
        
        asyncio.run(run_test())
    
    def test_generate_markdown_async_empty_posts(self):
        """投稿がない場合のMarkdown生成テスト"""
        async def run_test():
            mock_translator = Mock()
            blog_data = [
                {
                    'name': 'テストブログ',
                    'posts': []
                }
            ]
            
            markdown = await aws_blog_summary.generate_markdown_async(
                blog_data,
                '2025-11-18',
                '2025-11-25',
                mock_translator
            )
            
            self.assertIn('AWS ブログ記事まとめ', markdown)
            self.assertNotIn('テストブログ', markdown)
        
        asyncio.run(run_test())
    
    @patch('aws_blog_summary.fetch_blog_posts')
    @patch('aws_blog_summary.load_blog_sources')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', create=True)
    def test_main_async(self, mock_open, mock_mkdir, mock_load, mock_fetch):
        """メイン処理のテスト"""
        async def run_test():
            mock_load.return_value = [
                {'name': 'テストブログ', 'url': 'https://example.com/feed/'}
            ]
            mock_fetch.return_value = []
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            await aws_blog_summary.main_async()
            
            mock_load.assert_called_once()
            mock_fetch.assert_called_once()
            mock_mkdir.assert_called_once()
            mock_open.assert_called_once()
        
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
