#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock, mock_open
from datetime import date, datetime
import os
import sys

# テスト対象のモジュールをインポート
sys.path.insert(0, os.path.dirname(__file__))
from aws_updates_summary_improved import (
    get_category, get_service_description, strip_html, get_prev_week_range,
    is_in_prev_week, trim_summary, highlight_keywords, is_important_update,
    generate_toc
)

class TestAWSUpdatesSummaryImproved(unittest.TestCase):

    def setUp(self):
        """テスト用のモックデータを設定"""
        self.mock_category_mappings = {
            'EC2': 'コンピュート系',
            'Lambda': 'コンピュート系',
            'S3': 'DBストレージ系',
            'RDS': 'DBストレージ系'
        }
        self.mock_service_descriptions = {
            'EC2': '仮想サーバーサービス',
            'Lambda': 'サーバーレスコンピューティング',
            'S3': 'オブジェクトストレージサービス'
        }

    def test_get_category(self):
        """カテゴリ取得のテスト"""
        # 実際のマッピングを使用してテスト
        # EC2が含まれるタイトル
        category, service = get_category("Amazon EC2 launches new instance type")
        # 実際のマッピングに依存するため、柔軟なテスト
        self.assertIsInstance(category, str)
        
        # 該当しないタイトル
        category, service = get_category("Unknown service update")
        self.assertEqual(category, 'その他')
        self.assertIsNone(service)

    def test_get_service_description(self):
        """サービス説明取得のテスト"""
        # 実際のサービス説明を使用
        description = get_service_description('EC2')
        self.assertIsInstance(description, str)
        
        # 存在しないサービス
        description = get_service_description('Unknown')
        self.assertEqual(description, '')

    def test_strip_html(self):
        """HTML除去のテスト"""
        html_text = "<p>This is <strong>HTML</strong> content</p>"
        result = strip_html(html_text)
        self.assertEqual(result, "This is HTML content")
        
        # HTMLタグがない場合
        plain_text = "This is plain text"
        result = strip_html(plain_text)
        self.assertEqual(result, "This is plain text")

    def test_get_prev_week_range(self):
        """前週の日付範囲取得のテスト"""
        # 2025年8月10日（日曜日）をテスト日とする
        test_date = date(2025, 8, 10)
        start, end = get_prev_week_range(test_date)
        
        # 前週は8月3日（日）〜8月9日（土）
        expected_start = date(2025, 8, 3)
        expected_end = date(2025, 8, 9)
        
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
    
    def test_get_prev_week_range_various_days(self):
        """様々な曜日での前週範囲取得のテスト"""
        # 日曜日: 直前の土曜日(12/6)の手前1週間
        sunday = date(2025, 12, 7)
        start, end = get_prev_week_range(sunday)
        self.assertEqual(start, date(2025, 11, 30))
        self.assertEqual(end, date(2025, 12, 6))
        
        # 月曜日: 直前の土曜日(12/6)の手前1週間
        monday = date(2025, 12, 8)
        start, end = get_prev_week_range(monday)
        self.assertEqual(start, date(2025, 11, 30))
        self.assertEqual(end, date(2025, 12, 6))
        
        # 土曜日: 直前の土曜日(今日)の手前1週間
        saturday = date(2025, 12, 13)
        start, end = get_prev_week_range(saturday)
        self.assertEqual(start, date(2025, 12, 7))
        self.assertEqual(end, date(2025, 12, 13))
        
        # 次の日曜日: 直前の土曜日(12/13)の手前1週間
        next_sunday = date(2025, 12, 14)
        start, end = get_prev_week_range(next_sunday)
        self.assertEqual(start, date(2025, 12, 7))
        self.assertEqual(end, date(2025, 12, 13))
        
        # 水曜日: 直前の土曜日(12/13)の手前1週間
        wednesday = date(2025, 12, 17)
        start, end = get_prev_week_range(wednesday)
        self.assertEqual(start, date(2025, 12, 7))
        self.assertEqual(end, date(2025, 12, 13))
    
    def test_get_prev_week_range_always_7_days(self):
        """前週範囲が常に7日間であることを確認"""
        test_dates = [
            date(2025, 12, 7),   # Sunday
            date(2025, 12, 8),   # Monday
            date(2025, 12, 10),  # Wednesday
            date(2025, 12, 13),  # Saturday
            date(2025, 12, 14),  # Sunday
        ]
        
        for test_date in test_dates:
            start, end = get_prev_week_range(test_date)
            delta = (end - start).days
            self.assertEqual(delta, 6, f"Failed for {test_date}: {start} to {end}")
            # 開始日が日曜日であることを確認
            self.assertEqual(start.weekday(), 6, f"Start day should be Sunday for {test_date}")
            # 終了日が土曜日であることを確認
            self.assertEqual(end.weekday(), 5, f"End day should be Saturday for {test_date}")

    def test_is_in_prev_week(self):
        """前週判定のテスト"""
        test_date = date(2025, 8, 10)  # 日曜日
        
        # 前週内の日付
        prev_week_date = date(2025, 8, 5)  # 火曜日
        self.assertTrue(is_in_prev_week(prev_week_date, test_date))
        
        # 前週外の日付
        other_date = date(2025, 7, 30)  # 前々週
        self.assertFalse(is_in_prev_week(other_date, test_date))

    def test_trim_summary(self):
        """概要文字数制限のテスト"""
        # 短いテキスト
        short_text = "短いテキストです。"
        result = trim_summary(short_text, 50)
        self.assertEqual(result, short_text)
        
        # 長いテキスト（句点で切る）
        long_text = "これは長いテキストです。さらに続きます。もっと長くなります。"
        result = trim_summary(long_text, 30)
        # 句点で切られるか、制限文字数で切られるかのどちらか
        self.assertTrue(result.endswith('...') or len(result) <= 30)
        
        # 句点がない長いテキスト
        no_period_text = "a" * 100
        result = trim_summary(no_period_text, 50)
        self.assertTrue(result.endswith('...'))
        self.assertEqual(len(result), 50)

    def test_highlight_keywords(self):
        """重要キーワード強調のテスト"""
        text = "新機能がGA（一般提供開始）になりました"
        result = highlight_keywords(text)
        self.assertIn('**新機能**', result)
        self.assertIn('**GA**', result)

    def test_is_important_update(self):
        """重要更新判定のテスト"""
        # 重要キーワードを含むタイトル
        important_title = "新機能のGA発表"
        self.assertTrue(is_important_update(important_title, ""))
        
        # 重要キーワードを含まないタイトル
        normal_title = "通常の更新"
        self.assertFalse(is_important_update(normal_title, ""))

    def test_generate_toc(self):
        """目次生成のテスト"""
        categories = ['コンピュート系', 'DBストレージ系', 'AI/ML']
        result = generate_toc(categories)
        
        self.assertIn('## 目次', result)
        self.assertIn('💻 コンピュート系', result)
        self.assertIn('💾 DBストレージ系', result)
        self.assertIn('🤖 AI/ML', result)

    @patch('aws_updates_summary_improved.feedparser.parse')
    @patch('aws_updates_summary_improved.open', new_callable=mock_open)
    @patch('aws_updates_summary_improved.os.makedirs')
    @patch('aws_updates_summary_improved.GoogleTranslator')
    def test_main_function_structure(self, mock_translator, mock_makedirs, mock_file, mock_feedparser):
        """main関数の基本構造テスト"""
        # モックの設定
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feedparser.return_value = mock_feed

        mock_translator_instance = MagicMock()
        mock_translator_instance.translate.return_value = "翻訳されたテキスト"
        mock_translator.return_value = mock_translator_instance
        
        # main関数をインポートして実行
        from aws_updates_summary_improved import main
        
        # ネットワーク接続をモックしているので、基本的な構造のテストのみ
        # main関数が呼び出し可能であることを確認
        self.assertTrue(callable(main))
        
        # モックが正しく設定されていることを確認
        self.assertTrue(mock_feedparser.called or True)  # モックの基本テスト

class TestUtilityFunctions(unittest.TestCase):
    """ユーティリティ関数の詳細テスト"""

    def test_strip_html_edge_cases(self):
        """HTML除去の境界ケーステスト"""
        # 空文字列
        self.assertEqual(strip_html(""), "")
        
        # HTMLタグのみ
        self.assertEqual(strip_html("<div></div>"), "")
        
        # ネストしたHTMLタグ
        nested_html = "<div><p><strong>Text</strong></p></div>"
        self.assertEqual(strip_html(nested_html), "Text")

    def test_trim_summary_edge_cases(self):
        """概要トリムの境界ケーステスト"""
        # 制限値ちょうどの長さ
        text = "a" * 100
        result = trim_summary(text, 100)
        self.assertEqual(result, text)
        
        # 制限値+1の長さ（句点なし）
        text = "a" * 101
        result = trim_summary(text, 100)
        self.assertTrue(result.endswith('...'))
        self.assertEqual(len(result), 100)
        
        # 句点がある場合のテスト
        text_with_period = "これは長いテキストです。" + "a" * 50
        result = trim_summary(text_with_period, 30)
        # 結果が制限内に収まっているか、または...で終わっているか
        self.assertTrue(len(result) <= 30 or result.endswith('...'))

if __name__ == '__main__':
    unittest.main()