import json
import math
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


def app_slices(data):
    apps = [
        {"name": str(row["name"]), "hours": float(row["hours"])}
        for row in data.get("apps", [])
        if float(row["hours"]) > 0
    ]
    if len(apps) > 4:
        apps = apps[:4] + [
            {"name": "Other", "hours": sum(row["hours"] for row in apps[4:])}
        ]
    return apps


def render_svg(data, theme):
    palettes = {
        "dark": {
            "bg": "#0d1117",
            "panel": "#161b22",
            "border": "#30363d",
            "text": "#f0f6fc",
            "muted": "#8b949e",
            "grid": "#21262d",
            "green": "#3fb950",
            "blue": "#58a6ff",
            "orange": "#d29922",
            "track": "#30363d",
            "apps": ["#58a6ff", "#a371f7", "#f0883e", "#3fb950", "#8b949e"],
        },
        "light": {
            "bg": "#ffffff",
            "panel": "#f6f8fa",
            "border": "#d0d7de",
            "text": "#1f2328",
            "muted": "#656d76",
            "grid": "#d8dee4",
            "green": "#1a7f37",
            "blue": "#0969da",
            "orange": "#9a6700",
            "track": "#d8dee4",
            "apps": ["#0969da", "#8250df", "#bc4c00", "#1a7f37", "#656d76"],
        },
    }
    c = palettes[theme]
    summary = data["summary"]
    total = float(summary["total_hours"])
    active = int(summary["days_active"])
    streak = int(summary["streak_days"])
    top_project = str(summary.get("top_project") or "—")
    days = normalized_days(data)
    apps = app_slices(data)
    updated = report_timestamp(data)

    width, height = 1200, 620
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">Code Clock coding activity dashboard</title>",
        f"<desc id=\"desc\">{escape(str(total))} hours coded this week across {active} active days with a {streak} day streak. Includes daily activity and app usage.</desc>",
        f'<rect width="{width}" height="{height}" rx="24" fill="{c["bg"]}"/>',
        f'<rect x="1" y="1" width="1198" height="618" rx="23" fill="none" stroke="{c["border"]}" stroke-width="2"/>',
        f'<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" fill="{c["text"]}">',
        f'<circle cx="54" cy="51" r="8" fill="{c["green"]}"/>',
        '<text x="76" y="60" font-size="30" font-weight="700" letter-spacing="1.5">CODE CLOCK</text>',
        f'<text x="76" y="84" font-size="15" fill="{c["muted"]}" letter-spacing="1">LIVE CODING ACTIVITY</text>',
        f'<text x="1150" y="60" text-anchor="end" font-size="15" fill="{c["muted"]}">Updated {escape(updated)}</text>',
    ]

    metrics = [
        (48, "THIS WEEK", f"{total:g}h", c["green"]),
        (324, "ACTIVE DAYS", f"{active}/7", c["blue"]),
        (600, "CURRENT STREAK", f"{streak} days", c["orange"]),
    ]
    for x, label, value, accent in metrics:
        parts.extend(
            [
                f'<rect x="{x}" y="112" width="252" height="102" rx="14" fill="{c["panel"]}" stroke="{c["border"]}"/>',
                f'<rect x="{x}" y="112" width="5" height="102" rx="2.5" fill="{accent}"/>',
                f'<text x="{x + 24}" y="148" font-size="13" font-weight="600" fill="{c["muted"]}" letter-spacing="1.2">{label}</text>',
                f'<text x="{x + 24}" y="190" font-size="34" font-weight="700">{escape(value)}</text>',
            ]
        )

    parts.extend(
        [
            f'<rect x="876" y="112" width="276" height="102" rx="14" fill="{c["panel"]}" stroke="{c["border"]}"/>',
            f'<text x="900" y="148" font-size="13" font-weight="600" fill="{c["muted"]}" letter-spacing="1.2">TOP PROJECT</text>',
            f'<text x="900" y="186" font-size="23" font-weight="700">{escape(top_project)}</text>',
            f'<text x="48" y="260" font-size="19" font-weight="700">LAST 7 DAYS</text>',
            f'<text x="1152" y="260" text-anchor="end" font-size="19" font-weight="700">APP MIX</text>',
        ]
    )

    chart_x, chart_y, chart_w, chart_h = 48, 292, 700, 238
    baseline = chart_y + chart_h - 34
    max_hours = max((row["hours"] for row in days), default=1) or 1
    for step in range(4):
        y = chart_y + step * 54
        parts.append(
            f'<line x1="{chart_x}" y1="{y}" x2="{chart_x + chart_w}" y2="{y}" stroke="{c["grid"]}" stroke-width="1"/>'
        )

    bar_w, gap = 68, 29
    for index, row in enumerate(days):
        x = chart_x + 20 + index * (bar_w + gap)
        hours = row["hours"]
        bar_h = max(4, (hours / max_hours) * 176) if hours else 4
        y = baseline - bar_h
        opacity = "1" if hours else "0.35"
        parts.extend(
            [
                f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="8" fill="{c["blue"]}" opacity="{opacity}"/>',
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-size="14" font-weight="600">{escape(format_duration(hours))}</text>',
                f'<text x="{x + bar_w / 2:.1f}" y="{baseline + 28}" text-anchor="middle" font-size="14" fill="{c["muted"]}">{row["date"].strftime("%a")}</text>',
            ]
        )

    donut_cx, donut_cy, radius, stroke = 894, 405, 92, 38
    circumference = 2 * math.pi * radius
    parts.append(
        f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{radius}" fill="none" stroke="{c["track"]}" stroke-width="{stroke}"/>'
    )
    app_total = sum(row["hours"] for row in apps)
    offset = 0.0
    for index, row in enumerate(apps):
        pct = row["hours"] / app_total * 100 if app_total else 0
        color = c["apps"][index % len(c["apps"])]
        dash = pct / 100 * circumference
        gap = circumference - dash
        dash_offset = -(offset / 100 * circumference)
        parts.append(
            f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-dasharray="{dash:.3f} {gap:.3f}" stroke-dashoffset="{dash_offset:.3f}" transform="rotate(-90 {donut_cx} {donut_cy})"/>'
        )
        offset += pct

    parts.extend(
        [
            f'<text x="{donut_cx}" y="{donut_cy - 4}" text-anchor="middle" font-size="30" font-weight="700">{total:g}h</text>',
            f'<text x="{donut_cx}" y="{donut_cy + 22}" text-anchor="middle" font-size="13" fill="{c["muted"]}" letter-spacing="1">TRACKED</text>',
        ]
    )

    legend_x, legend_y = 1020, 322
    for index, row in enumerate(apps):
        pct = row["hours"] / app_total * 100 if app_total else 0
        color = c["apps"][index % len(c["apps"])]
        y = legend_y + index * 48
        pct_label = "&lt;1%" if 0 < pct < 1 else f"{pct:.0f}%"
        parts.extend(
            [
                f'<rect x="{legend_x}" y="{y}" width="12" height="12" rx="3" fill="{color}"/>',
                f'<text x="{legend_x + 22}" y="{y + 11}" font-size="14" font-weight="600">{escape(row["name"])}</text>',
                f'<text x="1152" y="{y + 11}" text-anchor="end" font-size="14" fill="{c["muted"]}">{pct_label}</text>',
            ]
        )

    parts.extend(
        [
            f'<line x1="48" y1="566" x2="1152" y2="566" stroke="{c["border"]}"/>',
            f'<text x="48" y="596" font-size="14" fill="{c["muted"]}">Tracked locally · Private project names redacted</text>',
            f'<text x="1152" y="596" text-anchor="end" font-size="14" font-weight="600" fill="{c["blue"]}">github.com/pittsjs/code-clock</text>',
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
