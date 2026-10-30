from datetime import datetime, timezone

from main import format_clock, format_minutes_to_text, get_elapsed_seconds


def test_format_clock():
    assert format_clock(3661) == "01:01:01"
    assert format_clock(0) == "00:00:00"


def test_format_minutes_to_text():
    assert format_minutes_to_text(65) == "1時間5分"
    assert format_minutes_to_text(30) == "30分"
    assert format_minutes_to_text(120) == "2時間"


def test_get_elapsed_seconds():
    started = datetime.now(timezone.utc).isoformat()
    assert get_elapsed_seconds(started) >= 0
