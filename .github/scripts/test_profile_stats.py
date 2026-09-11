import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('profile_stats.py')
spec = importlib.util.spec_from_file_location('profile_stats', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PublicStatsTests(unittest.TestCase):
    def setUp(self):
        self.raw = {'generated_at': '2026-09-11', 'exported_at': '2026-09-11T22:00:00Z',
                    'summary': {'total_hours': 2, 'days_active': 1, 'streak_days': 1, 'top_project': 'PRIVATE_SENTINEL'},
                    'daily': [{'date': '2026-09-11', 'hours': 2, 'project': 'PRIVATE_SENTINEL'}],
                    'projects': [{'name': 'PRIVATE_SENTINEL'}], 'apps': [{'name': 'PRIVATE_SENTINEL'}]}

    def test_only_approved_data_survives(self):
        clean = module.public_stats(self.raw)
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(clean))
        self.assertEqual(set(clean), {'generated_at', 'exported_at', 'period_days', 'summary', 'daily'})
        self.assertEqual(clean['summary'], {'total_hours': 2, 'days_active': 1, 'streak_days': 1})
        self.assertEqual(clean['daily'], [{'date': '2026-09-11', 'hours': 2}])

    def test_rejects_text_nonfinite_and_invalid_counts(self):
        for field,value in [('total_hours','PRIVATE_SENTINEL'),('total_hours',float('nan')),('days_active',True),('days_active',8),('streak_days',1.5)]:
            with self.subTest(field=field,value=value):
                data=copy.deepcopy(self.raw);data['summary'][field]=value
                with self.assertRaises(ValueError): module.public_stats(data)

    def test_rejects_dates_outside_window_and_duplicate_days(self):
        for rows in [[{'date':'2026-09-01','hours':1}], self.raw['daily']*2]:
            data=copy.deepcopy(self.raw);data['daily']=rows
            with self.assertRaises(ValueError): module.public_stats(data)

    def test_dispatch_roundtrip_and_stale_event(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'raw.json';source.write_text(json.dumps(self.raw))
            event=Path(folder)/'event.json'
            event.write_bytes(subprocess.check_output([sys.executable,str(SCRIPT),str(source),'--dispatch','coding-stats-updated']))
            output=Path(folder)/'summary.json'
            command=[sys.executable,str(SCRIPT),str(event),'--event','--output',str(output)]
            subprocess.run(command,check=True)
            before=output.read_text()
            self.assertNotIn('PRIVATE_SENTINEL', event.read_text())
            payload=json.loads(event.read_text());payload['client_payload']['stats']['exported_at']='2026-09-11T21:00:00Z'
            event.write_text(json.dumps(payload));subprocess.run(command,check=True)
            self.assertEqual(output.read_text(),before)

if __name__ == '__main__': unittest.main()
