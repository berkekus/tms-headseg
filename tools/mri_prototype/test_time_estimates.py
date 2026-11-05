"""Synthetic timing fixtures; these numbers are not project measurements."""
import unittest
from time_estimates import clock_seconds, prediction_progress, queued_batch_estimate


class EstimateTests(unittest.TestCase):
    def test_prediction_eta_is_stage_specific_and_needs_measured_iterations(self):
        text="Predicting prediction_model:\n 4%|# | 1/27 [00:05<02:16, 5s/it]"
        self.assertIsNone(prediction_progress(text)["remaining"])
        text+="\r 7%|# | 2/27 [00:09<01:57, 4s/it]"
        value=prediction_progress(text)
        self.assertEqual((value['done'],value['total'],value['remaining']),(2,27,117))

    def test_completed_prediction_does_not_mean_complete_job(self):
        text="Predicting prediction_model:\n100%|##| 27/27 [02:04<00:00, 5s/it]"
        self.assertEqual(prediction_progress(text)['stage'],'saving')
        text+="\nCollecting results: 0%| | 0/1 [00:00<?, ?it/s]"
        value=prediction_progress(text)
        self.assertEqual(value['stage'],'saving')
        self.assertIsNone(value['remaining'])

    def test_unrelated_malformed_or_unknown_progress_has_no_estimate(self):
        self.assertIsNone(prediction_progress('70%|##| 19/27 [01:25<00:34, x]'))
        self.assertIsNone(prediction_progress('Predicting x:\n99%|#| 9/2 [00:01<00:02, x]'))
        value=prediction_progress('Predicting x:\n0%| | 0/27 [00:00<?, ?it/s]')
        self.assertIsNone(value['remaining'])
        self.assertIsNone(clock_seconds('02:80'))
        self.assertEqual(clock_seconds('1:02:03'),3723)

    def test_batch_estimate_excludes_active_failed_and_invalid_measurements(self):
        cases=[{'state':'completed','record':{'minutes':10}}, {'state':'completed','record':{'minutes':20}},
               {'state':'failed','record':{'minutes':100}}, {'state':'running','record':{}},
               {'state':'completed','record':{'minutes':float('nan')}}, {'state':'pending'}, {'state':'pending'}]
        result=queued_batch_estimate(cases)
        self.assertEqual(result,{'seconds':1800,'samples':2,'pending':2})
        self.assertIsNone(queued_batch_estimate([cases[0],cases[-1]]))


if __name__=='__main__':
    unittest.main()
