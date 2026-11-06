import asyncio
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import flet as ft


DATA_FILE = Path.home() / ".sleep_tracker_data.json"
BG = "#EAF5F1"
CARD = "#F8FBF9"
PRIMARY = "#1E7F66"
PRIMARY_LIGHT = "#DFF3EA"
INK = "#20342F"
MUTED = "#5E726D"
WARNING = "#D97C5A"
SUCCESS = "#2C7A5F"
EGG_HATCH_SLEEP_MINUTES = 40 * 60
EGG_RARITIES = (
    ("卵", "egg", "ノーマル"),
    ("レア卵", "rare_egg", "レア"),
    ("スーパーレア卵", "super_rare_egg", "スーパーレア"),
    ("伝説卵", "legendary_egg", "伝説"),
)
FAIRY_CANDIDATES = ("🧚 ふわりん", "🧚 きらりん", "🧚 もこりん")
SUPER_RARE_DRAGONS = ("フレアドラゴン", "アイスドラゴン", "サンダードラゴン")
DRAGON_APPEARANCES = {
    "フレアドラゴン": "🔥 フレアドラゴン",
    "アイスドラゴン": "❄️ アイスドラゴン",
    "サンダードラゴン": "⚡ サンダードラゴン",
}
DRAGON_HATCH_STYLES = {
    "フレアドラゴン": ("🔥", "#75402F"),
    "アイスドラゴン": ("❄️", "#245779"),
    "サンダードラゴン": ("⚡", "#594B83"),
}


def default_state():
    return {
        "is_sleeping": False,
        "sleep_started_at": None,
        "sleep_history": [],
        "users": {},
        "current_user": None,
    }


def normalize_inventory(raw_inventory):
    if not isinstance(raw_inventory, dict):
        return {}
    normalized = {}
    for key, value in raw_inventory.items():
        if not isinstance(value, int):
            continue
        rarity_key = next(
            (inventory_key for item_name, inventory_key, _ in EGG_RARITIES if str(key) in (item_name, inventory_key)),
            None,
        )
        if rarity_key:
            normalized[rarity_key] = value
        elif str(key) == "睡眠のちから":
            normalized["sleep_power"] = value
        else:
            normalized[str(key)] = value
    return normalized


def normalize_characters(raw_characters):
    if not isinstance(raw_characters, list):
        return []
    return [str(item) for item in raw_characters if isinstance(item, str)]


def format_character_name(character):
    return DRAGON_APPEARANCES.get(character, character)


def load_state():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_state()

    if not isinstance(data, dict):
        return default_state()

    history = data.get("sleep_history", [])
    if not isinstance(history, list):
        history = []

    cleaned = []
    for item in history:
        if not isinstance(item, dict):
            continue
        started = item.get("started_at")
        ended = item.get("ended_at")
        minutes = item.get("minutes")
        if isinstance(started, str) and isinstance(ended, str) and isinstance(minutes, int):
            cleaned.append({"started_at": started, "ended_at": ended, "minutes": minutes})

    users = data.get("users", {})
    if not isinstance(users, dict):
        users = {}
    cleaned_users = {}
    for username, user_data in users.items():
        if not isinstance(user_data, dict):
            continue
        cleaned_users[str(username)] = {
            "password": str(user_data.get("password", "")),
            "reward_points": int(user_data.get("reward_points", 0) or 0),
            "last_login_date": user_data.get("last_login_date") if isinstance(user_data.get("last_login_date"), str) else None,
            "inventory": normalize_inventory(user_data.get("inventory")),
            "characters": normalize_characters(user_data.get("characters")),
            "egg_sleep_minutes": max(0, int(user_data.get("egg_sleep_minutes", 0) or 0)),
        }

    current_user = data.get("current_user")
    if not isinstance(current_user, str) or current_user not in cleaned_users:
        current_user = None

    return {
        "is_sleeping": bool(data.get("is_sleeping")),
        "sleep_started_at": data.get("sleep_started_at") if isinstance(data.get("sleep_started_at"), str) else None,
        "sleep_history": cleaned,
        "users": cleaned_users,
        "current_user": current_user,
    }


def save_state(state):
    DATA_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_today_key():
    return datetime.now(timezone.utc).date().isoformat()


def apply_login_reward(state, username):
    users = state.setdefault("users", {})
    user = users.setdefault(username, {"password": "", "reward_points": 0, "last_login_date": None})
    today = get_today_key()
    current_points = int(user.get("reward_points", 0) or 0)
    last_login_date = user.get("last_login_date")

    if last_login_date == today:
        return {
            "reward_received": False,
            "amount": 0,
            "balance": current_points,
            "message": "本日はすでに報酬を受け取り済みです。",
        }

    reward_amount = 100
    user["reward_points"] = current_points + reward_amount
    user["last_login_date"] = today
    state["current_user"] = username
    return {
        "reward_received": True,
        "amount": reward_amount,
        "balance": user["reward_points"],
        "message": f"{username}さんに{reward_amount}ptのログイン報酬を付与しました。",
    }


def grant_opening_bonus(state, username):
    users = state.setdefault("users", {})
    user = users.setdefault(
        username,
        {
            "password": "",
            "reward_points": 0,
            "last_login_date": None,
            "inventory": {},
            "characters": [],
        },
    )
    today = get_today_key()
    current_points = int(user.get("reward_points", 0) or 0)
    last_date = user.get("last_opened_date")

    if last_date == today:
        return {
            "reward_received": False,
            "amount": 0,
            "balance": current_points,
            "message": "本日はすでに10ptを受け取り済みです。",
        }

    reward_amount = 10
    user["reward_points"] = current_points + reward_amount
    user["last_opened_date"] = today
    state["current_user"] = username
    return {
        "reward_received": True,
        "amount": reward_amount,
        "balance": user["reward_points"],
        "message": f"アプリを開いたので{reward_amount}ptを獲得しました。",
    }


def authenticate_user(state, username, password):
    name = (username or "").strip()
    pwd = password or ""

    if not name:
        return False, "ユーザー名を入力してください。"
    if not pwd:
        return False, "パスワードを入力してください。"

    users = state.setdefault("users", {})
    if name not in users:
        users[name] = {"password": pwd, "reward_points": 0, "last_login_date": None, "inventory": {}}
        state["current_user"] = name
        return True, "新規ユーザーとして登録しました。"

    if users[name].get("password") != pwd:
        return False, "パスワードが違います。"

    state["current_user"] = name
    return True, "ログインしました。"


def draw_gacha(state, username):
    users = state.setdefault("users", {})
    user = users.setdefault(username, {"password": "", "reward_points": 0, "last_login_date": None, "inventory": {}, "characters": []})
    user_inventory = normalize_inventory(user.get("inventory"))
    user["inventory"] = user_inventory

    current_points = int(user.get("reward_points", 0) or 0)
    gacha_cost = 100

    if current_points < gacha_cost:
        return {
            "success": False,
            "item": None,
            "amount": 0,
            "message": "ポイントが足りないためガチャを回せません。",
            "balance": current_points,
        }

    rewards = (
        ["卵"] * 80
        + ["レア卵"] * 15
        + ["スーパーレア卵"] * 4
        + ["伝説卵"]
    )
    item = random.choice(rewards)
    user["reward_points"] = current_points - gacha_cost

    inventory_key = next(
        (key for item_name, key, _ in EGG_RARITIES if item_name == item),
        "sleep_power" if item == "睡眠のちから" else item,
    )
    user_inventory[inventory_key] = int(user_inventory.get(inventory_key, 0)) + 1
    user["inventory"] = user_inventory

    rarity = next((label for item_name, _, label in EGG_RARITIES if item_name == item), None)
    result_message = f"ガチャの結果: {item}（{rarity}）を手に入れました！" if rarity else f"ガチャの結果: {item} を手に入れました！"
    return {
        "success": True,
        "item": item,
        "amount": 1,
        "message": result_message,
        "balance": user["reward_points"],
    }


def incubate_eggs(state, username, sleep_minutes):
    users = state.setdefault("users", {})
    user = users.setdefault(username, {"password": "", "reward_points": 0, "last_login_date": None, "inventory": {}, "characters": []})
    inventory = normalize_inventory(user.get("inventory"))
    characters = normalize_characters(user.get("characters"))
    user["inventory"] = inventory
    user["characters"] = characters
    egg_counts = {
        key: max(0, inventory.get(key, 0))
        for _, key, _ in EGG_RARITIES
    }
    total_egg_count = sum(egg_counts.values())
    if total_egg_count == 0:
        user["egg_sleep_minutes"] = 0
        return []

    total_sleep_minutes = max(0, int(user.get("egg_sleep_minutes", 0))) + max(0, int(sleep_minutes))
    hatched_count = min(total_egg_count, total_sleep_minutes // EGG_HATCH_SLEEP_MINUTES)
    character_candidates = ["ぽち", "ねこ", "うさぎ", "くま", "ひよこ", "ドラゴン"]
    hatched_characters = []
    eggs_left_to_hatch = hatched_count
    for _, key, rarity in EGG_RARITIES:
        hatched_from_rarity = min(egg_counts[key], eggs_left_to_hatch)
        if rarity == "伝説":
            candidates = FAIRY_CANDIDATES
        elif rarity == "スーパーレア":
            candidates = SUPER_RARE_DRAGONS
        else:
            candidates = character_candidates
        hatched_characters.extend(
            random.choice(candidates) for _ in range(hatched_from_rarity)
        )
        inventory[key] = egg_counts[key] - hatched_from_rarity
        eggs_left_to_hatch -= hatched_from_rarity
    user["inventory"] = inventory
    characters.extend(hatched_characters)
    user["characters"] = characters
    user["egg_sleep_minutes"] = (
        total_sleep_minutes - hatched_count * EGG_HATCH_SLEEP_MINUTES
        if sum(inventory[key] for _, key, _ in EGG_RARITIES) > 0
        else 0
    )
    return hatched_characters


def format_clock(value):
    value = max(int(value), 0)
    hours, rem = divmod(value, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_minutes_to_text(minutes):
    minutes = max(int(minutes), 0)
    hours, rem = divmod(minutes, 60)
    if hours and rem:
        return f"{hours}時間{rem}分"
    if hours:
        return f"{hours}時間"
    return f"{rem}分"


def get_elapsed_seconds(started_iso):
    if not started_iso:
        return 0
    try:
        started = datetime.fromisoformat(started_iso)
    except ValueError:
        return 0
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - started).total_seconds()))


def format_date_time(iso_value):
    try:
        dt = datetime.fromisoformat(iso_value)
    except ValueError:
        return "--"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_local = dt.astimezone()
    return dt_local.strftime("%m/%d %H:%M")


def main(page: ft.Page):
    page.title = "ねむログ"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    state = load_state()
    state.setdefault("users", {})
    state.setdefault("current_user", "guest")
    state["users"].setdefault(
        "guest",
        {
            "password": "",
            "reward_points": 0,
            "last_login_date": None,
            "last_opened_date": None,
            "inventory": {},
            "characters": [],
            "egg_sleep_minutes": 0,
        },
    )
    state["current_user"] = "guest"
    opening_bonus = grant_opening_bonus(state, "guest")
    try:
        save_state(state)
    except OSError:
        pass

    async def clock_loop():
        while True:
            refresh_timer()
            await asyncio.sleep(1)

    status_badge = ft.Container(
        content=ft.Text("休憩中", size=12, weight=ft.FontWeight.BOLD, color=SUCCESS),
        padding=ft.Padding(8, 6, 8, 6),
        bgcolor=PRIMARY_LIGHT,
        border_radius=16,
    )
    timer_label = ft.Text("00:00:00", size=42, weight=ft.FontWeight.W_700, color=INK)
    start_button = ft.ElevatedButton(
        "睡眠を開始",
        icon=ft.Icons.NIGHTLIGHT_ROUNDED,
        bgcolor=PRIMARY,
        color="white",
        on_click=lambda e: start_sleep(),
    )
    stop_button = ft.OutlinedButton(
        "睡眠を終了",
        icon=ft.Icons.STOP_CIRCLE_OUTLINED,
        on_click=lambda e: stop_sleep(),
        disabled=True,
    )
    last_sleep_value = ft.Text("まだ記録がありません", size=13, color=MUTED)
    week_total_value = ft.Text("0分", size=13, color=MUTED)
    reward_balance = ft.Text("報酬残高: 0pt", size=13, color=PRIMARY)
    history_list = ft.Column(spacing=8)
    current_user_label = ft.Text("ゲスト", size=12, color=PRIMARY, weight=ft.FontWeight.W_600)
    opening_bonus_message = ft.Text(opening_bonus["message"], size=12, color=SUCCESS)
    gacha_result = ft.Text("ガチャを回して卵をGET！", size=12, color=PRIMARY)
    gacha_animation_icon = ft.Text(
        "✨",
        size=108,
        color="#FFE58A",
        scale=0.8,
        animate_scale=220,
    )
    gacha_animation_label = ft.Text(
        "運命の結果は...",
        size=25,
        weight=ft.FontWeight.BOLD,
        color="white",
        text_align=ft.TextAlign.CENTER,
    )
    gacha_inventory = ft.Text("卵: 0個", size=12, color=MUTED)
    hatch_result = ft.Text("卵は睡眠時間で孵化します。", size=12, color=MUTED)
    character_list = ft.Text("キャラクター: なし", size=12, color=PRIMARY)
    gacha_button = ft.ElevatedButton("ガチャを回す (100pt)")
    gacha_backdrop = ft.Container(
        left=0,
        top=0,
        right=0,
        bottom=0,
        bgcolor="#103D36",
        content=ft.Column(
            [
                ft.Text("✦          ✧          ✦", size=28, color="#F4D887"),
                ft.Container(
                    content=gacha_animation_icon,
                    width=220,
                    height=220,
                    alignment=ft.Alignment.CENTER,
                    shape=ft.BoxShape.CIRCLE,
                    bgcolor="#1C5E50",
                    border=ft.Border.all(2, "#F4D887"),
                    shadow=ft.BoxShadow(
                        blur_radius=36,
                        color="#668F6B",
                        spread_radius=4,
                    ),
                ),
                gacha_animation_label,
                ft.Text("✧          ✦          ✧", size=24, color="#8DE0BD"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=28,
        ),
    )
    gacha_overlay = ft.Stack(
        expand=True,
        visible=False,
        controls=[gacha_backdrop],
    )
    page.overlay.append(gacha_overlay)

    def save_and_refresh():
        try:
            save_state(state)
        except OSError:
            status_badge.content.value = "保存失敗"
        refresh_timer()
        render_history()
        update_reward_display()

    def update_reward_display():
        current_user = state.get("current_user")
        if current_user and current_user in state.get("users", {}):
            reward_balance.value = f"報酬残高: {state['users'][current_user].get('reward_points', 0)}pt"
            current_user_label.value = "ゲスト"
            inventory = normalize_inventory(state['users'][current_user].get('inventory', {}))
            egg_counts = {key: inventory.get(key, 0) for _, key, _ in EGG_RARITIES}
            if sum(egg_counts.values()) > 0:
                progress = state["users"][current_user].get("egg_sleep_minutes", 0)
                gacha_inventory.value = (
                    f"ノーマル卵: {egg_counts['egg']}個 / レア卵: {egg_counts['rare_egg']}個\n"
                    f"スーパーレア卵: {egg_counts['super_rare_egg']}個 / 伝説卵: {egg_counts['legendary_egg']}個\n"
                    "孵化進捗: "
                    f"{progress}/{EGG_HATCH_SLEEP_MINUTES}分"
                )
            else:
                gacha_inventory.value = (
                    "ノーマル卵: 0個 / レア卵: 0個\n"
                    "スーパーレア卵: 0個 / 伝説卵: 0個"
                )
            characters = normalize_characters(state['users'][current_user].get('characters', []))
            if characters:
                character_list.value = (
                    f"キャラクター: {', '.join(format_character_name(character) for character in characters)}"
                )
            else:
                character_list.value = "キャラクター: なし"
        else:
            reward_balance.value = "報酬残高: 0pt"
            current_user_label.value = "ゲスト"
            gacha_inventory.value = (
                "ノーマル卵: 0個 / レア卵: 0個\n"
                "スーパーレア卵: 0個 / 伝説卵: 0個"
            )
            character_list.value = "キャラクター: なし"
        page.update()

    def refresh_timer():
        if state.get("is_sleeping") and state.get("sleep_started_at"):
            elapsed = get_elapsed_seconds(state["sleep_started_at"])
            timer_label.value = format_clock(elapsed)
            status_badge.content.value = "睡眠中"
            status_badge.bgcolor = "#CFEFDB"
            status_badge.content.color = SUCCESS
            start_button.disabled = True
            stop_button.disabled = False
        else:
            timer_label.value = "00:00:00"
            status_badge.content.value = "休憩中"
            status_badge.bgcolor = PRIMARY_LIGHT
            status_badge.content.color = SUCCESS
            start_button.disabled = False
            stop_button.disabled = True

        week_minutes = sum(
            item.get("minutes", 0)
            for item in state.get("sleep_history", [])[-7:]
        )
        week_total_value.value = f"7日間の合計: {format_minutes_to_text(week_minutes)}"
        if state.get("sleep_history"):
            last = state["sleep_history"][-1]
            last_sleep_value.value = (
                f"前回: {format_minutes_to_text(last.get('minutes', 0))} "
                f"({format_date_time(last['started_at'])}〜{format_date_time(last['ended_at'])})"
            )
        else:
            last_sleep_value.value = "まだ記録がありません"

        page.update()

    def render_history():
        entries = state.get("sleep_history", [])[-5:]
        rows = []
        if not entries:
            rows.append(ft.Text("まだ睡眠記録がありません。", color=MUTED, size=12))
        else:
            for entry in reversed(entries):
                rows.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.BEDTIME_OUTLINED, color=PRIMARY),
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"{format_date_time(entry['started_at'])} 〜 {format_date_time(entry['ended_at'])}",
                                            size=12,
                                            weight=ft.FontWeight.W_600,
                                            color=INK,
                                        ),
                                        ft.Text(
                                            f"睡眠時間: {format_minutes_to_text(entry.get('minutes', 0))}",
                                            size=11,
                                            color=MUTED,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                        border=ft.Border.all(1, "#D9EAE3"),
                        border_radius=10,
                        bgcolor="#FFFFFF",
                    )
                )
        history_list.controls = rows
        page.update()

    def start_sleep():
        if state.get("is_sleeping"):
            return
        state["is_sleeping"] = True
        state["sleep_started_at"] = datetime.now(timezone.utc).isoformat()
        save_and_refresh()

    def stop_sleep():
        if not state.get("is_sleeping") or not state.get("sleep_started_at"):
            return
        started = datetime.fromisoformat(state["sleep_started_at"])
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        ended = datetime.now(timezone.utc)
        minutes = max(1, int((ended - started).total_seconds() // 60))
        state["sleep_history"].append(
            {
                "started_at": started.isoformat(),
                "ended_at": ended.isoformat(),
                "minutes": minutes,
            }
        )
        state["sleep_history"] = state["sleep_history"][-20:]
        state["is_sleeping"] = False
        state["sleep_started_at"] = None
        current_user = state.get("current_user")
        if current_user:
            hatched_characters = incubate_eggs(state, current_user, minutes)
            if hatched_characters:
                fairy_characters = [
                    character for character in hatched_characters
                    if character in FAIRY_CANDIDATES
                ]
                if fairy_characters:
                    hatch_result.value = (
                        f"伝説の卵からかわいい妖精「{'、'.join(fairy_characters)}」が孵化しました！"
                    )
                else:
                    displayed_characters = (
                        format_character_name(character)
                        for character in hatched_characters
                    )
                    hatch_result.value = f"睡眠で{'、'.join(displayed_characters)}が孵化しました！"
                hatch_result.color = SUCCESS
                hatched_dragons = [
                    character for character in hatched_characters
                    if character in DRAGON_HATCH_STYLES
                ]
                if hatched_dragons:
                    page.run_task(reveal_hatched_dragons, hatched_dragons)
            elif any(
                state["users"][current_user]["inventory"].get(key, 0) > 0
                for _, key, _ in EGG_RARITIES
            ):
                hatch_result.value = "睡眠で孵化が進みました。"
                hatch_result.color = MUTED
            else:
                hatch_result.value = "卵を入手すると、睡眠時間で孵化します。"
                hatch_result.color = MUTED
        save_and_refresh()

    async def reveal_hatched_dragons(dragons):
        gacha_overlay.visible = True
        gacha_backdrop.bgcolor = "#103D36"
        gacha_animation_icon.color = "#FFFFFF"
        gacha_animation_icon.scale = 0.8
        gacha_animation_icon.value = "🥚"
        gacha_animation_label.value = "卵が揺れている..."
        page.update()
        await asyncio.sleep(0.45)

        gacha_animation_icon.value = "🥚💥"
        gacha_animation_icon.scale = 1.05
        gacha_animation_label.value = "殻にヒビが入った！"
        page.update()
        await asyncio.sleep(0.4)

        for dragon in dragons:
            element, backdrop = DRAGON_HATCH_STYLES[dragon]
            gacha_backdrop.bgcolor = backdrop
            gacha_animation_icon.value = f"🐉{element}"
            gacha_animation_icon.color = "#FFFFFF"
            gacha_animation_icon.scale = 1.35
            gacha_animation_label.value = (
                f"卵の中から\n{format_character_name(dragon)}が誕生！"
            )
            page.update()
            await asyncio.sleep(1.5)

        gacha_overlay.visible = False
        page.update()

    async def reveal_gacha(item):
        gacha_overlay.visible = True
        gacha_animation_label.value = "運命の結果は..."
        page.update()

        symbols = ["✨", "🥚", "💫", "🌙", "✨", "🎁", "⭐"]
        backdrops = ["#103D36", "#174A55", "#493C65", "#754C36"]
        for index, symbol in enumerate(symbols):
            gacha_animation_icon.value = symbol
            gacha_animation_icon.scale = 1.18 if index % 2 == 0 else 0.84
            gacha_animation_icon.color = "#FFE58A" if index % 2 == 0 else "#FFFFFF"
            gacha_animation_label.value = "アイテム召喚中..."
            gacha_backdrop.bgcolor = backdrops[index % len(backdrops)]
            page.update()
            await asyncio.sleep(0.12 + index * 0.035)

        item_symbols = {
            "卵": "🥚",
            "レア卵": "🌟",
            "スーパーレア卵": "💎",
            "伝説卵": "👑",
            "睡眠のちから": "🌙",
        }
        gacha_animation_icon.value = item_symbols.get(item, "🎁")
        gacha_animation_icon.scale = 1.35
        rarity = next((label for item_name, _, label in EGG_RARITIES if item_name == item), None)
        rarity_colors = {
            "ノーマル": ("#FFF1A8", "#24634D"),
            "レア": ("#9DEBFF", "#174A70"),
            "スーパーレア": ("#F0A9FF", "#4E286B"),
            "伝説": ("#FFCF74", "#713B26"),
        }
        gacha_animation_icon.color, gacha_backdrop.bgcolor = rarity_colors.get(
            rarity,
            ("#FFF1A8", "#24634D"),
        )
        gacha_animation_label.value = f"{rarity}ランク！\n{item}を獲得！" if rarity else f"{item}を獲得！"
        page.update()
        await asyncio.sleep(2.0)
        gacha_overlay.visible = False
        gacha_button.disabled = False
        page.update()

    def handle_gacha(e):
        current_user = state.get("current_user")
        if not current_user:
            gacha_result.value = "アプリを開いてポイントを受け取ってください。"
            gacha_result.color = WARNING
            page.update()
            return

        result = draw_gacha(state, current_user)
        gacha_result.value = result["message"]
        gacha_result.color = SUCCESS if result["success"] else WARNING
        if result["success"]:
            gacha_button.disabled = True
            reward_balance.value = f"報酬残高: {result['balance']}pt"
        update_reward_display()
        try:
            save_state(state)
        except OSError:
            gacha_result.value = "ガチャ結果の保存に失敗しました。"
            gacha_result.color = WARNING
        page.update()
        if result["success"]:
            page.run_task(reveal_gacha, result["item"])

    gacha_button.on_click = handle_gacha

    page.run_task(clock_loop)

    tracker_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text("睡眠", color="white", size=14, weight=ft.FontWeight.BOLD),
                            width=40,
                            height=40,
                            bgcolor=PRIMARY,
                            border_radius=12,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text("ねむログ", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("今日の睡眠時間", size=15, color=MUTED),
                        status_badge,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                current_user_label,
                timer_label,
                ft.Row([start_button, stop_button], spacing=12),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("前回の睡眠", size=12, color=MUTED),
                            last_sleep_value,
                            ft.Text("7日間の合計", size=12, color=MUTED),
                            week_total_value,
                            reward_balance,
                            opening_bonus_message,
                        ],
                        spacing=8,
                    ),
                    padding=18,
                    bgcolor="#F3F8F4",
                    border_radius=14,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("ガチャ", size=14, weight=ft.FontWeight.W_600, color=INK),
                            ft.Text(
                                "100pt / ノーマル80%・レア15%・激レア4%・伝説1%",
                                size=11,
                                color=MUTED,
                            ),
                            gacha_button,
                            gacha_result,
                            gacha_inventory,
                            hatch_result,
                            character_list,
                        ],
                        spacing=8,
                    ),
                    padding=18,
                    bgcolor="#FFF8E8",
                    border_radius=14,
                    border=ft.Border.all(1, "#F3D7A6"),
                ),
                ft.Text("記録一覧", size=14, weight=ft.FontWeight.W_600, color=INK),
                history_list,
            ],
            spacing=18,
        ),
        width=420,
        padding=22,
        bgcolor=CARD,
        border_radius=20,
        border=ft.Border.all(1, "#DDEFE3"),
        shadow=ft.BoxShadow(blur_radius=26, color="#1B3B3518", offset=ft.Offset(0, 8)),
        visible=True,
    )

    page.add(tracker_card)
    render_history()
    refresh_timer()
    update_reward_display()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=8550)