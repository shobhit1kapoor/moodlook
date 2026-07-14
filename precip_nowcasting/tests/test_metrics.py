import unittest

import numpy as np

from nowcasting.experiments import accepts_candidate, nonnegative_convex_weights, paired_location_bootstrap
from nowcasting.metrics import rmse, sensor_weighted_rmse


class MetricsTests(unittest.TestCase):
    def test_rmse_and_sensor_weighting(self):
        self.assertAlmostEqual(rmse(np.array([0, 2]), np.array([0, 0])), np.sqrt(2))
        self.assertAlmostEqual(sensor_weighted_rmse({"goes": 1, "himawari": 4, "meteosat": 9}, {"goes": 1, "himawari": 1, "meteosat": 2}), np.sqrt(5.75))

    def test_bootstrap_and_acceptance(self):
        mean, low, high = paired_location_bootstrap({"a": 1.0, "b": 1.0, "c": 1.0}, {"a": 2.0, "b": 2.0, "c": 2.0}, draws=100, seed=1)
        self.assertGreater(mean, 0); self.assertGreater(low, 0); self.assertGreater(high, 0)
        self.assertTrue(accepts_candidate(0.9, 0.91, low))

    def test_simplex_weights(self):
        target = np.array([0.0, 1.0, 2.0, 3.0])
        predictions = np.column_stack([target, np.zeros_like(target)])
        weights = nonnegative_convex_weights(predictions, target, steps=500)
        self.assertAlmostEqual(float(weights.sum()), 1.0, places=5)
        self.assertGreater(weights[0], 0.9)


if __name__ == "__main__":
    unittest.main()
