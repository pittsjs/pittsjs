import json
import re
import sys
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[2]
STATS_PATH = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "stats.json"
ASSETS_DIR = ROOT / "assets"


def format_duration(hours):
    if hours <= 0:
        return "—"
    whole = int(hours)
    minutes = int(round((hours - whole) * 60))
    if minutes == 60:
        whole += 1
        minutes = 0
    if whole:
        return f"{whole}h {minutes:02d}m"
    return f"{minutes}m"


def report_timestamp(data):
    exported = data.get("exported_at")
    if exported:
        try:
            dt = datetime.fromisoformat(exported.replace("Z", "+00:00"))
            et = dt.astimezone(ET)
            hour = et.hour % 12 or 12
            tz = et.tzname() or et.strftime("%Z")
            return (
                f"{et.strftime('%b')} {et.day}, {et.year} at "
                f"{hour}:{et.minute:02d} {et.strftime('%p')} {tz}"
            )
        except ValueError:
            return exported

    report_day = date.fromisoformat(data["generated_at"])
    return f"{report_day.strftime('%b')} {report_day.day}, {report_day.year}"


def normalized_days(data):
    end = date.fromisoformat(data["generated_at"])
    recorded = {row["date"]: float(row["hours"]) for row in data.get("daily", [])}
    return [
        {
            "date": end - timedelta(days=offset),
            "hours": recorded.get((end - timedelta(days=offset)).isoformat(), 0.0),
        }
        for offset in range(6, -1, -1)
    ]


def render_svg(data, theme):
    palettes = {
        "dark": {
            "bg": "#0d1117",
            "border": "#30363d",
            "text": "#f0f6fc",
            "muted": "#8b949e",
            "grid": "#21262d",
            "blue": "#58a6ff",
        },
        "light": {
            "bg": "#ffffff",
            "border": "#d0d7de",
            "text": "#1f2328",
            "muted": "#656d76",
            "grid": "#d8dee4",
            "blue": "#0969da",
        },
    }
    c = palettes[theme]
    summary = data["summary"]
    total = float(summary["total_hours"])
    active = int(summary["days_active"])
    streak = int(summary["streak_days"])
    days = normalized_days(data)
    updated = report_timestamp(data)

    width, height = 1200, 500
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">This week in code</title>",
        f"<desc id=\"desc\">{escape(str(total))} hours coded this week across {active} active days with a {streak} day streak. Includes daily coding activity.</desc>",
        f'<rect width="{width}" height="{height}" fill="{c["bg"]}"/>',
        f'<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" fill="{c["text"]}">',
        '<text x="48" y="54" font-size="26" font-weight="700">This week in code</text>',
        f'<text x="1152" y="54" text-anchor="end" font-size="14" fill="{c["muted"]}">Updated {escape(updated)}</text>',
        f'<line x1="48" y1="78" x2="1152" y2="78" stroke="{c["border"]}"/>',
    ]

    metrics = [
        (48, "HOURS", f"{total:g}h"),
        (416, "ACTIVE DAYS", f"{active}/7"),
        (784, "STREAK", f"{streak} days"),
    ]
    for x, label, value in metrics:
        parts.extend(
            [
                f'<text x="{x}" y="113" font-size="12" font-weight="600" fill="{c["muted"]}" letter-spacing="1">{label}</text>',
                f'<text x="{x}" y="151" font-size="29" font-weight="700">{escape(value)}</text>',
            ]
        )

    for x in (392, 760):
        parts.append(
            f'<line x1="{x}" y1="99" x2="{x}" y2="154" stroke="{c["border"]}"/>'
        )
    parts.append(
        f'<text x="48" y="202" font-size="15" font-weight="600" fill="{c["muted"]}">DAILY ACTIVITY</text>'
    )

    chart_x, chart_y, chart_w = 48, 230, 1104
    baseline = 404
    max_hours = max((row["hours"] for row in days), default=1) or 1
    for step in range(3):
        y = chart_y + step * 72
        parts.append(
            f'<line x1="{chart_x}" y1="{y}" x2="{chart_x + chart_w}" y2="{y}" stroke="{c["grid"]}" stroke-width="1"/>'
        )

    bar_w, gap = 88, 60
    for index, row in enumerate(days):
        x = chart_x + 64 + index * (bar_w + gap)
        hours = row["hours"]
        bar_h = max(3, (hours / max_hours) * 154) if hours else 3
        y = baseline - bar_h
        fill = c["blue"] if hours else c["border"]
        parts.extend(
            [
                f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="4" fill="{fill}"/>',
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 9:.1f}" text-anchor="middle" font-size="13" font-weight="600">{escape(format_duration(hours))}</text>',
                f'<text x="{x + bar_w / 2:.1f}" y="{baseline + 25}" text-anchor="middle" font-size="13" fill="{c["muted"]}">{row["date"].strftime("%a")}</text>',
            ]
        )

    parts.extend(
        [
            f'<line x1="48" y1="458" x2="1152" y2="458" stroke="{c["border"]}"/>',
            f'<text x="1152" y="486" text-anchor="end" font-size="13" fill="{c["muted"]}">Powered by code-clock</text>',
            "</g>",
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


with STATS_PATH.open() as f:
    stats = json.load(f)

ASSETS_DIR.mkdir(exist_ok=True)
for selected_theme in ("dark", "light"):
    (ASSETS_DIR / f"code-clock-{selected_theme}.svg").write_text(
        render_svg(stats, selected_theme), encoding="utf-8"
    )

block = """<a href="https://github.com/pittsjs/code-clock">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/code-clock-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/code-clock-light.svg">
    <img alt="Code Clock live coding activity dashboard" src="assets/code-clock-light.svg" width="100%">
  </picture>
</a>"""

readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
updated_readme = re.sub(
    r"(<!--START_SECTION:coding-stats-->).*?(<!--END_SECTION:coding-stats-->)",
    r"\1\n" + block + r"\n\2",
    readme,
    flags=re.DOTALL,
)
readme_path.write_text(updated_readme, encoding="utf-8")

print("generated profile dashboard")
