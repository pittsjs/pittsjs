"""Allowlist the numeric activity summary published on the GitHub profile."""
import argparse
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def number(value, maximum, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Activity values must be numeric')
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError('Activity value outside permitted range')
    if integer and int(value) != value:
        raise ValueError('Activity count must be an integer')
    return int(value) if integer else value


def public_stats(data):
    end = date.fromisoformat(data['generated_at'])
    exported = datetime.fromisoformat(data['exported_at'].replace('Z', '+00:00'))
    if exported.tzinfo is None:
        raise ValueError('Export timestamp must include timezone')
    summary = data['summary']
    days = []
    seen = set()
    for row in data['daily']:
        day = date.fromisoformat(row['date'])
        if not end - timedelta(days=6) <= day <= end or day in seen:
            raise ValueError('Daily activity must have unique dates in the seven-day window')
        seen.add(day)
        days.append({'date': day.isoformat(), 'hours': number(row['hours'], 24)})
    return {
        'generated_at': end.isoformat(),
        'exported_at': exported.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'period_days': 7,
        'summary': {
            'total_hours': number(summary['total_hours'], 168),
            'days_active': number(summary['days_active'], 7, integer=True),
            'streak_days': number(summary['streak_days'], 100000, integer=True),
        },
        'daily': sorted(days, key=lambda row: row['date']),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--dispatch')
    parser.add_argument('--event', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = json.loads(args.source.read_text())
    if args.event:
        data = data['client_payload']['stats']
    safe = public_stats(data)
    if args.dispatch:
        safe = {'event_type': args.dispatch, 'client_payload': {'stats': safe}}
    if args.output:
        # A delayed notification must not roll the public chart backward.
        if args.output.exists():
            previous = public_stats(json.loads(args.output.read_text()))
            if previous['exported_at'] > safe['exported_at']:
                return
        args.output.write_text(json.dumps(safe, indent=2) + '\n')
    else:
        print(json.dumps(safe))


if __name__ == '__main__':
    main()
