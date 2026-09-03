import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

with open("stats.json") as f:
    data = json.load(f)

s = data["summary"]
daily = data["daily"]
total = s["total_hours"]
days_active = s["days_active"]
streak = s["streak_days"]
top = s.get("top_project") or "—"
gen = data["generated_at"]

exp = data.get("exported_at")
if exp:
    try:
        dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        et = dt.astimezone(ET)
        hour = et.hour % 12 or 12
        tz = et.tzname() or et.strftime("%Z")
        last_updates = (
            f"{et.day}/{et.month}/{et.year} {hour}:{et.minute:02d} "
            f"{et.strftime('%p')} {tz}"
        )
    except ValueError:
        last_updates = exp
else:
    y, mo, da = gen.split("-")
    last_updates = f"{int(da)}/{int(mo)}/{y} (report date)"

max_h = max((d["hours"] for d in daily), default=1) or 1
rows = []
for d in daily[-7:]:
    date = datetime.fromisoformat(d["date"])
    h = d["hours"]
    bar = "█" * int(h / max_h * 16) + "░" * (16 - int(h / max_h * 16))
    time_str = f"{int(h)}h {int((h%1)*60):02d}m" if h >= 1 else f"{int(h*60)}m" if h > 0 else "—"
    rows.append(f"| {date.strftime('%a')} | {time_str} | `{bar}` |")

streak_unit = "DAY" if streak == 1 else "DAYS"

block = f"""<p align="center">
  <img alt="{total} hours coded this week" src="https://img.shields.io/badge/THIS_WEEK-{total}h-238636?style=for-the-badge" />
  <img alt="{days_active} of 7 active days" src="https://img.shields.io/badge/ACTIVE_DAYS-{days_active}%2F7-1f6feb?style=for-the-badge" />
  <img alt="{streak} day coding streak" src="https://img.shields.io/badge/STREAK-{streak}_{streak_unit}-f0883e?style=for-the-badge" />
</p>

| Day | Time | Activity |
|:---|---:|:---|
{chr(10).join(rows)}

<sub>Top project: <strong>{top}</strong> · Updated {last_updates} · Powered by <a href="https://github.com/pittsjs/code-clock">code-clock</a></sub>"""

with open("README.md") as f:
    readme = f.read()

new = re.sub(
    r"(<!--START_SECTION:coding-stats-->).*?(<!--END_SECTION:coding-stats-->)",
    r"\1\n" + block + r"\n\2",
    readme,
    flags=re.DOTALL,
)

with open("README.md", "w") as f:
    f.write(new)

print("updated" if new != readme else "no change")
