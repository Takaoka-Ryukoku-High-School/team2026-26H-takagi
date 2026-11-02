from datetime import datetime, timezone
from unittest.mock import patch

from main import (
    draw_gacha,
    format_clock,
    format_minutes_to_text,
    get_elapsed_seconds,
    grant_opening_bonus,
    incubate_eggs,
)


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


def test_grant_opening_bonus_once_per_day():
    state = {"users": {}}

    first = grant_opening_bonus(state, "guest")
    second = grant_opening_bonus(state, "guest")

    assert first["reward_received"] is True
    assert first["amount"] == 10
    assert state["users"]["guest"]["reward_points"] == 10
    assert second["reward_received"] is False
    assert second["amount"] == 0
    assert state["users"]["guest"]["reward_points"] == 10


def test_draw_gacha_gives_egg_and_deducts_points():
    state = {"users": {"alice": {"reward_points": 200, "inventory": {"egg": 0}}}}

    with patch("main.random.choice", return_value="卵"):
        result = draw_gacha(state, "alice")

    assert result["success"] is True
    assert result["item"] == "卵"
    assert result["amount"] == 1
    assert state["users"]["alice"]["reward_points"] == 100
    assert state["users"]["alice"]["inventory"]["egg"] == 1


def test_sleep_time_hatches_egg_after_eight_hours():
    state = {
        "users": {
            "alice": {
                "inventory": {"egg": 1},
                "characters": [],
                "egg_sleep_minutes": 450,
            }
        }
    }

    with patch("main.random.choice", return_value="ぽち"):
        hatched = incubate_eggs(state, "alice", 30)

    assert hatched == ["ぽち"]
    assert state["users"]["alice"]["inventory"]["egg"] == 0
    assert state["users"]["alice"]["egg_sleep_minutes"] == 0
    assert "ぽち" in state["users"]["alice"]["characters"]
