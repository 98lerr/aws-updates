import pytest
from aws_updates_summary import get_prev_week_range, is_in_prev_week, trim_summary, strip_html
from datetime import date

def test_trim_summary_short():
    s = "short"
    assert trim_summary(s, limit=10) == "short"

def test_trim_summary_long():
    s = "a" * 20
    assert trim_summary(s, limit=10) == "a" * 7 + "..."

@pytest.mark.parametrize("html, expected", [
    ("<p>Hello</p>", "Hello"),
    ("<div>Hi <b>there</b></div>", "Hi there"),
])
def test_strip_html(html, expected):
    assert strip_html(html) == expected

def test_get_prev_week_range_standard():
    # 2025-05-23(金)を基準にすると前週は5/11(日)～5/17(土)
    today = date(2025, 5, 23)
    start, end = get_prev_week_range(today)
    assert start == date(2025, 5, 11)
    assert end == date(2025, 5, 17)

@pytest.mark.parametrize("pub, today, expected", [
    (date(2025, 5, 20), date(2025, 5, 27), True),  # 前週内
    (date(2025, 5, 18), date(2025, 5, 27), True),  # 前週の開始日
    (date(2025, 5, 26), date(2025, 5, 27), False), # 当週
])
def test_is_in_prev_week(pub, today, expected):
    assert is_in_prev_week(pub, today) == expected
