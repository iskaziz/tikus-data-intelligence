import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from scripts.analytics.build_products import apply_corrections, final_pre_show_sessions, load_corrections

ROOT=Path(__file__).resolve().parents[1]

def snap(sid, start, collected, cinema='tgv-tebrau-city', version='1.0.0'):
    return {
        'sessionId':sid,'cinemaId':cinema,'showDate':start[:10],
        'startAt':start,'collectedAt':collected,
        'source':{'collectorVersion':version},
        'quality':{'seatMeasured':True},
        'seat':{'capacity':100,'used':1,'available':99,'otherUnavailable':None}
    }

class ProductCorrectnessTests(unittest.TestCase):
    def test_future_session_is_not_final_pre_show(self):
        s=snap('x','2026-09-05T10:00:00+08:00','2026-09-05T00:15:00+08:00')
        finals,state=final_pre_show_sessions([s],as_of=datetime.fromisoformat('2026-09-05T00:20:00+08:00'))
        self.assertEqual(finals,[])
        self.assertEqual(state['status'],'provisional')
        self.assertEqual(state['futureSessions'],1)

    def test_started_session_uses_last_pre_show_observation(self):
        a=snap('x','2026-09-05T10:00:00+08:00','2026-09-05T09:00:00+08:00')
        b=deepcopy(a); b['collectedAt']='2026-09-05T09:55:00+08:00'; b['seat']['used']=4
        c=deepcopy(a); c['collectedAt']='2026-09-05T10:05:00+08:00'; c['seat']['used']=7
        finals,state=final_pre_show_sessions([a,b,c],as_of=datetime.fromisoformat('2026-09-05T10:10:00+08:00'))
        self.assertEqual(len(finals),1)
        self.assertEqual(finals[0]['seat']['used'],4)
        self.assertEqual(state['status'],'complete')

    def test_known_bad_paragon_versions_are_quarantined(self):
        bad=snap('bad','2026-09-05T00:30:00+08:00','2026-09-05T00:14:00+08:00',cinema='paragon-batu-pahat',version='paragon-schedule/1.1.0')
        good=snap('good','2026-09-05T12:15:00+08:00','2026-09-05T00:30:00+08:00',cinema='paragon-batu-pahat',version='paragon-schedule/1.2.0')
        included,excluded=apply_corrections([bad,good],load_corrections(ROOT))
        self.assertEqual([x['sessionId'] for x in included],['good'])
        self.assertEqual(excluded[0]['sessionId'],'bad')

if __name__=='__main__':
    unittest.main()
