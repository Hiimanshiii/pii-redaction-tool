import unittest
from evaluation.evaluate import calculate_metrics, normalize_text

class TestEvaluationMetrics(unittest.TestCase):
    def test_calculate_metrics_standard(self) -> None:
        # TP = 3, FP = 1, FN = 2
        # Precision = 3 / (3 + 1) = 0.75
        # Recall = 3 / (3 + 2) = 0.6
        # F1 = 2 * 0.75 * 0.6 / (0.75 + 0.6) = 0.9 / 1.35 = 0.6666...
        # Accuracy = 3 / (3 + 1 + 2) = 0.5
        metrics = calculate_metrics(tp=3, fp=1, fn=2)
        
        self.assertAlmostEqual(metrics["precision"], 0.75)
        self.assertAlmostEqual(metrics["recall"], 0.6)
        self.assertAlmostEqual(metrics["f1"], 0.6666666666666666)
        self.assertAlmostEqual(metrics["accuracy"], 0.5)

    def test_calculate_metrics_zero_denominators(self) -> None:
        # All zeros -> should report N/A
        metrics = calculate_metrics(tp=0, fp=0, fn=0)
        self.assertEqual(metrics["precision"], "N/A")
        self.assertEqual(metrics["recall"], "N/A")
        self.assertEqual(metrics["f1"], "N/A")
        self.assertEqual(metrics["accuracy"], "N/A")

        # TP = 0, FP = 2, FN = 0
        # Precision = 0 / 2 = 0
        # Recall = N/A
        # F1 = N/A
        # Accuracy = 0 / 2 = 0
        metrics_zero_tp = calculate_metrics(tp=0, fp=2, fn=0)
        self.assertEqual(metrics_zero_tp["precision"], 0.0)
        self.assertEqual(metrics_zero_tp["recall"], "N/A")
        self.assertEqual(metrics_zero_tp["f1"], "N/A")
        self.assertEqual(metrics_zero_tp["accuracy"], 0.0)

    def test_normalize_text(self) -> None:
        raw_text = "  Sarthak   Malvadkar   "
        self.assertEqual(normalize_text(raw_text), "sarthak malvadkar")

        empty = None
        self.assertEqual(normalize_text(empty), "")

if __name__ == '__main__':
    unittest.main()
