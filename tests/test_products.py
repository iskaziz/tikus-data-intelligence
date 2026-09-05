import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from scripts.analytics.build_products import apply_corrections, final_pre_show_sessions, load_corrections, reconcile_schedule_only_session_ids, latest_by_session

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

    def test_targeted_v13_native_ids_are_quarantined(self):
        bad=snap('paragon-batu-pahat:source:122652','2026-09-05T18:30:00+08:00','2026-09-05T17:52:00+08:00',cinema='paragon-batu-pahat',version='paragon-schedule/1.3.0')
        bad['sourceSessionId']='122652'; bad['quality']={'measurementStatus':'schedule-only','seatMeasured':False}
        good=deepcopy(bad); good['sessionId']='paragon-batu-pahat:source:122655'; good['sourceSessionId']='122655'; good['startAt']='2026-09-05T00:30:00+08:00'
        included,excluded=apply_corrections([bad,good],load_corrections(ROOT))
        self.assertEqual([x['sessionId'] for x in included],['paragon-batu-pahat:source:122655'])
        self.assertEqual(excluded[0]['sessionId'],'paragon-batu-pahat:source:122652')

    def test_schedule_only_fingerprint_merges_into_native_identity(self):
        legacy=snap('paragon-ktcc:fingerprint:2026-09-05:19:40:unknown','2026-09-05T19:40:00+08:00','2026-09-05T00:14:00+08:00',cinema='paragon-ktcc',version='paragon-schedule/1.1.0')
        legacy['quality']={'measurementStatus':'schedule-only','seatMeasured':False}; legacy['sourceSessionId']=None; legacy['source']={'provider':'paragon','collectorVersion':'paragon-schedule/1.1.0'}
        native=deepcopy(legacy); native['sessionId']='paragon-ktcc:source:83243'; native['sourceSessionId']='83243'; native['collectedAt']='2026-09-05T17:52:00+08:00'; native['source']['collectorVersion']='paragon-schedule/1.3.0'
        reconciled,audit=reconcile_schedule_only_session_ids([legacy,native])
        latest=latest_by_session(reconciled)
        self.assertEqual(len(latest),1)
        self.assertEqual(latest[0]['sessionId'],'paragon-ktcc:source:83243')
        self.assertEqual(len(audit),1)
        self.assertIn('paragon-ktcc:fingerprint:2026-09-05:19:40:unknown',audit[0]['mergedSessionIds'])

    def test_distinct_schedule_only_times_do_not_merge(self):
        a=snap('paragon-ktcc:source:1','2026-09-05T19:40:00+08:00','2026-09-05T17:00:00+08:00',cinema='paragon-ktcc',version='paragon-schedule/1.3.0')
        a['quality']={'measurementStatus':'schedule-only','seatMeasured':False}; a['sourceSessionId']='1'; a['source']={'provider':'paragon','collectorVersion':'paragon-schedule/1.3.0'}
        b=deepcopy(a); b['sessionId']='paragon-ktcc:source:2'; b['sourceSessionId']='2'; b['startAt']='2026-09-05T21:55:00+08:00'
        reconciled,audit=reconcile_schedule_only_session_ids([a,b])
        self.assertEqual(len(latest_by_session(reconciled)),2)
        self.assertEqual(audit,[])

if __name__=='__main__':
    unittest.main()

class DistributionIntelligenceTests(unittest.TestCase):
    def test_cinema_momentum_uses_repeated_measurements_only(self):
        from scripts.analytics.build_products import cinema_momentum
        a=snap('x','2026-09-05T20:00:00+08:00','2026-09-05T17:00:00+08:00')
        b=deepcopy(a); b['collectedAt']='2026-09-05T18:00:00+08:00'; b['seat']['used']=4
        rows=cinema_momentum([a,b])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['netUsedDelta'],3)
        self.assertAlmostEqual(rows[0]['averageSeatsPerHour'],3.0)

    def test_prime_time_efficiency_is_capacity_weighted(self):
        from scripts.analytics.build_products import prime_time_efficiency
        a=snap('a','2026-09-05T18:30:00+08:00','2026-09-05T17:00:00+08:00')
        a['seat']={'capacity':100,'used':10,'available':90,'otherUnavailable':0}
        b=snap('b','2026-09-05T15:00:00+08:00','2026-09-05T14:00:00+08:00')
        b['seat']={'capacity':300,'used':0,'available':300,'otherUnavailable':0}
        row=prime_time_efficiency([a,b])[0]
        self.assertAlmostEqual(row['primeOccupancy'],0.10)
        self.assertAlmostEqual(row['allDayOccupancy'],0.025)
        self.assertAlmostEqual(row['occupancyDelta'],0.075)

    def test_allocation_comparison_marks_partial_days_limited(self):
        from scripts.analytics.build_products import allocation_comparison
        a=snap('a','2026-09-05T18:30:00+08:00','2026-09-05T17:00:00+08:00')
        b=snap('b','2026-09-04T18:30:00+08:00','2026-09-04T17:00:00+08:00')
        cmp=allocation_comparison([a],[b],current_complete='observed',previous_complete='partial',previous_date='2026-09-04')
        self.assertEqual(cmp['quality'],'limited-partial-day')
        self.assertEqual(cmp['cinemas'][0]['showDelta'],0)

class DecisionIntelligenceTests(unittest.TestCase):
    def test_multiple_positive_indicators_create_review_signal(self):
        from scripts.analytics.build_products import decision_intelligence
        a=snap('a','2026-09-05T18:30:00+08:00','2026-09-05T17:00:00+08:00')
        a['seat']={'capacity':100,'used':20,'available':80,'otherUnavailable':0}
        latest=[a]
        momentum=[{'cinemaId':'tgv-tebrau-city','qualifyingSessions':2,'netUsedDelta':3,'averageSeatsPerHour':1.5,'maxSeatsPerHour':2.0,'minSeatsPerHour':1.0}]
        prime=[{'cinemaId':'tgv-tebrau-city','primeShows':1,'primeMeasuredSessions':1,'primeOccupancy':0.20,'allDayOccupancy':0.20,'occupancyDelta':0.01}]
        # Force relative overperformance with a second measured cinema in network denominator.
        b=snap('b','2026-09-05T15:00:00+08:00','2026-09-05T14:00:00+08:00',cinema='gsc-mid-valley')
        b['seat']={'capacity':900,'used':1,'available':899,'otherUnavailable':0}
        data=decision_intelligence(latest+[b],momentum,prime,{'status':'unavailable','quality':'no-previous-day','cinemas':[]},daily_completeness='observed')
        row=next(r for r in data['cinemas'] if r['cinemaId']=='tgv-tebrau-city')
        self.assertEqual(row['signal'],'review-opportunity')
        self.assertEqual(row['confidence'],'medium')

    def test_partial_day_forces_low_confidence(self):
        from scripts.analytics.build_products import decision_intelligence
        a=snap('a','2026-09-05T18:30:00+08:00','2026-09-05T17:00:00+08:00')
        a['seat']={'capacity':100,'used':10,'available':90,'otherUnavailable':0}
        data=decision_intelligence([a],[],[],{'status':'unavailable','quality':'no-previous-day','cinemas':[]},daily_completeness='partial')
        self.assertEqual(data['quality'],'provisional-live-observation')
        self.assertEqual(data['cinemas'][0]['confidence'],'low')

    def test_signal_definition_disclaims_forecasts_and_sales(self):
        from scripts.analytics.build_products import decision_intelligence
        data=decision_intelligence([],[],[],{'status':'unavailable','quality':'no-previous-day','cinemas':[]},daily_completeness='observed')
        self.assertIn('not forecasts',data['definition'])
        self.assertIn('ticket-sales',data['definition'])
