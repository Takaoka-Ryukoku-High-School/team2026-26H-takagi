import asyncio
import json
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


def default_state():
    return {"is_sleeping": False, "sleep_started_at": None, "sleep_history": []}


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

    return {
        "is_sleeping": bool(data.get("is_sleeping")),
        "sleep_started_at": data.get("sleep_started_at") if isinstance(data.get("sleep_started_at"), str) else None,
        "sleep_history": cleaned,
    }


def save_state(state):
    DATA_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


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
    page.title = "睡眠時間測定"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    state = load_state()

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
    history_list = ft.Column(spacing=8)

    def save_and_refresh():
        try:
            save_state(state)
        except OSError:
            status_badge.content.value = "保存失敗"
        refresh_timer()
        render_history()

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

        total_minutes = sum(item.get("minutes", 0) for item in state.get("sleep_history", []))
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
        save_and_refresh()

    page.run_task(clock_loop)
    content = ft.Container(
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
                        ft.Text("Sleep Tracker", size=12, color=PRIMARY, weight=ft.FontWeight.BOLD),
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
                timer_label,
                ft.Row([start_button, stop_button], spacing=12),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("前回の睡眠", size=12, color=MUTED),
                            last_sleep_value,
                            ft.Text("7日間の合計", size=12, color=MUTED),
                            week_total_value,
                        ],
                        spacing=8,
                    ),
                    padding=18,
                    bgcolor="#F3F8F4",
                    border_radius=14,
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
    )

    page.add(content)
    render_history()
    refresh_timer()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=8550)