from collections import Counter
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from main import (
    DRAGON_HATCH_STYLES,
    draw_gacha,
    format_character_name,
    format_clock,
    format_minutes_to_text,
    get_elapsed_seconds,
    grant_opening_bonus,
    incubate_eggs,
)


def test_dragon_names_show_their_elemental_appearance():
    assert format_character_name("フレアドラゴン") == "🔥 フレアドラゴン"
    assert format_character_name("アイスドラゴン") == "❄️ アイスドラゴン"
    assert format_character_name("サンダードラゴン") == "⚡ サンダードラゴン"
    assert format_character_name("ぽち") == "ぽち"
    assert {name: style[0] for name, style in DRAGON_HATCH_STYLES.items()} == {
        "フレアドラゴン": "🔥",
        "アイスドラゴン": "❄️",
        "サンダードラゴン": "⚡",
    }


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


@pytest.mark.parametrize(
    ("item", "inventory_key"),
    [
        ("レア卵", "rare_egg"),
        ("スーパーレア卵", "super_rare_egg"),
        ("伝説卵", "legendary_egg"),
    ],
)
def test_draw_gacha_preserves_egg_rarity(item, inventory_key):
    state = {"users": {"alice": {"reward_points": 100, "inventory": {}}}}

    with patch("main.random.choice", return_value=item):
        result = draw_gacha(state, "alice")

    assert result["success"] is True
    assert state["users"]["alice"]["inventory"][inventory_key] == 1


def test_draw_gacha_uses_requested_rarity_probabilities():
    state = {"users": {"alice": {"reward_points": 100, "inventory": {}}}}
    rewards_seen = []

    def choose_first(rewards):
        rewards_seen.extend(rewards)
        return rewards[0]

    with patch("main.random.choice", side_effect=choose_first):
        draw_gacha(state, "alice")

    assert len(rewards_seen) == 100
    assert Counter(rewards_seen) == {
        "卵": 80,
        "レア卵": 15,
        "スーパーレア卵": 4,
        "伝説卵": 1,
    }


def test_sleep_time_hatches_egg_after_forty_hours():
    state = {
        "users": {
            "alice": {
                "inventory": {"egg": 1},
                "characters": [],
                "egg_sleep_minutes": 2399,
            }
        }
    }

    with patch("main.random.choice", return_value="ぽち"):
        hatched = incubate_eggs(state, "alice", 0)
        assert hatched == []
        assert state["users"]["alice"]["inventory"]["egg"] == 1
        assert state["users"]["alice"]["egg_sleep_minutes"] == 2399

        hatched = incubate_eggs(state, "alice", 1)

    assert hatched == ["ぽち"]
    assert state["users"]["alice"]["inventory"]["egg"] == 0
    assert state["users"]["alice"]["egg_sleep_minutes"] == 0
    assert "ぽち" in state["users"]["alice"]["characters"]


@pytest.mark.parametrize("egg_key", ["rare_egg"])
def test_sleep_time_hatches_each_egg_rarity_after_forty_hours(egg_key):
    state = {
        "users": {
            "alice": {
                "inventory": {egg_key: 1},
                "characters": [],
                "egg_sleep_minutes": 0,
            }
        }
    }

    with patch("main.random.choice", return_value="ドラゴン"):
        hatched = incubate_eggs(state, "alice", 40 * 60)

    assert hatched == ["ドラゴン"]
    assert state["users"]["alice"]["inventory"][egg_key] == 0
    assert state["users"]["alice"]["egg_sleep_minutes"] == 0


@pytest.mark.parametrize(
    ("dragon_index", "expected_dragon"),
    [
        (0, "フレアドラゴン"),
        (1, "アイスドラゴン"),
        (2, "サンダードラゴン"),
    ],
)
def test_super_rare_egg_hatches_one_of_three_dragons(dragon_index, expected_dragon):
    state = {
        "users": {
            "alice": {
                "inventory": {"super_rare_egg": 1},
                "characters": [],
                "egg_sleep_minutes": 0,
            }
        }
    }

    with patch("main.random.choice", side_effect=lambda candidates: candidates[dragon_index]) as choose:
        hatched = incubate_eggs(state, "alice", 40 * 60)

    assert hatched == [expected_dragon]
    assert choose.call_args.args[0] == ("フレアドラゴン", "アイスドラゴン", "サンダードラゴン")
    assert state["users"]["alice"]["inventory"]["super_rare_egg"] == 0


def test_legendary_egg_hatches_a_cute_fairy():
    state = {
        "users": {
            "alice": {
                "inventory": {"legendary_egg": 1},
                "characters": [],
                "egg_sleep_minutes": 0,
            }
        }
    }

    with patch("main.random.choice", side_effect=lambda candidates: candidates[0]):
        hatched = incubate_eggs(state, "alice", 40 * 60)

    assert hatched == ["🧚 ふわりん"]
    assert state["users"]["alice"]["inventory"]["legendary_egg"] == 0
    assert "🧚 ふわりん" in state["users"]["alice"]["characters"]


def test_rare_egg_hatches_one_of_the_forest_animals():
    state = {
        "users": {
            "alice": {
                "inventory": {"rare_egg": 1},
                "characters": [],
                "egg_sleep_minutes": 0,
            }
        }
    }

    with patch("main.random.choice", side_effect=lambda candidates: candidates[0]):
        hatched = incubate_eggs(state, "alice", 40 * 60)

    assert hatched == ["ライオン"]
    assert state["users"]["alice"]["inventory"]["rare_egg"] == 0
    assert "ライオン" in state["users"]["alice"]["characters"]


def test_normal_egg_hatches_one_of_the_requested_animals():
    state = {
        "users": {
            "alice": {
                "inventory": {"egg": 1},
                "characters": [],
                "egg_sleep_minutes": 0,
            }
        }
    }

    with patch("main.random.choice", side_effect=lambda candidates: candidates[0]):
        hatched = incubate_eggs(state, "alice", 40 * 60)

    assert hatched == ["イヌ"]
    assert state["users"]["alice"]["inventory"]["egg"] == 0
    assert "イヌ" in state["users"]["alice"]["characters"]
