import unittest

import numpy as np
import pandas as pd

from nowcasting.io import observation_names
from nowcasting.splits import stratified_location_folds


class SplitTests(unittest.TestCase):
    def test_three_frame_contract(self):
        self.assertEqual(observation_names("['a.tif', 'b.tif', 'c.tif']"), ["a.tif", "b.tif", "c.tif"])
        self.assertEqual(observation_names("['a.tif']"), ["a.tif"])
        self.assertEqual(observation_names("[]"), [])
        with self.assertRaises(ValueError):
            observation_names("['a.tif', 'b.tif', 'c.tif', 'd.tif']")

    def test_locations_are_never_split(self):
        rows = []
        for sensor in ("goes", "himawari", "meteosat"):
            for location in range(5):
                for sample in range(2):
                    rows.append({"unique_id": f"{sensor}-{location}-{sample}", "name_location": f"{sensor}-{location}", "satellite_target": sensor})
        manifest = pd.DataFrame(rows)
        targets = np.ones((len(rows), 2, 2), dtype=np.float32)
        folds = stratified_location_folds(manifest, targets, folds=5, seed=4)
        self.assertEqual(len(folds), 15)
        self.assertEqual(set(folds["fold"]), set(range(5)))
        self.assertTrue((folds.groupby("satellite_target")["fold"].nunique() == 5).all())


if __name__ == "__main__":
    unittest.main()
