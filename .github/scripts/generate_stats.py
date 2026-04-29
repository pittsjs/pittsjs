import json
import re
from datetime import datetime, timezone

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
        exp_disp = dt.astimezone(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
    except ValueError:
        exp_disp = exp
    footer_sync = f" · export **{exp_disp}**"
else:
    footer_sync = ""

max_h = max((d["hours"] for d in daily), default=1) or 1
rows = []
for d in daily[-7:]:
    date = datetime.fromisoformat(d["date"])
    h = d["hours"]
    bar = "█" * int(h / max_h * 16) + "░" * (16 - int(h / max_h * 16))
    time_str = f"{int(h)}h {int((h%1)*60):02d}m" if h >= 1 else f"{int(h*60)}m" if h > 0 else "—"
    rows.append(f"| {date.strftime('%a')} | {time_str} | `{bar}` |")

block = f"""**{total}h** this week &nbsp;·&nbsp; {days_active}/7 days active &nbsp;·&nbsp; 🔥 {streak} day streak

| Day | Time | |
|-----|------|---|
{chr(10).join(rows)}

> Top project: **{top}** &nbsp;·&nbsp; Metrics **{gen}**{footer_sync} · [code-clock](https://github.com/pittsjs/code-clock)"""

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
