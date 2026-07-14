import unittest

import numpy as np
import torch

from nowcasting.experiments import nonnegative_convex_weights
from nowcasting.io import expand_metadata
from nowcasting.models import MaskedTemporalUNet, SpectralMotionNowcaster, SpectralSimVPNowcaster


class CoreContractsTest(unittest.TestCase):
    def test_legacy_metadata_expands_to_harmonics(self):
        base = np.array([0.0, 1.0, 0.0, 1.0], dtype=np.float32)
        expanded = expand_metadata(base)
        self.assertEqual(expanded.shape, (8,))
        np.testing.assert_allclose(expanded, [0, 1, 0, 1, 0, 1, 0, 1])

    def test_spectral_models_accept_partial_frames_and_bands(self):
        image = torch.randn(2, 3, 16, 32, 32)
        metadata = torch.randn(2, 8)
        sensor = torch.tensor([0, 2])
        frame_mask = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 0.0]])
        band_mask = torch.ones(2, 3, 16); band_mask[1, 1:] = 0
        for model in (SpectralMotionNowcaster(base_channels=8), SpectralSimVPNowcaster(base_channels=8), MaskedTemporalUNet(base_channels=8)):
            prediction, aux = model(image, metadata, sensor, frame_mask, band_mask, return_aux=True)
            self.assertEqual(tuple(prediction.shape), (2, 41, 41))
            self.assertTrue(torch.isfinite(prediction).all())
            if "reconstruction" in aux:
                self.assertEqual(tuple(aux["reconstruction"].shape), (2, 16, 32, 32))
            else:
                self.assertEqual(tuple(aux["occurrence_logits"].shape), (2, 41, 41))

    def test_convex_solver_rejects_nonbeneficial_member(self):
        prediction = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]])
        weights = nonnegative_convex_weights(prediction, np.array([0.0, 1.0, 2.0]))
        np.testing.assert_allclose(weights, [1.0, 0.0], atol=1e-6)


if __name__ == "__main__":
    unittest.main()
