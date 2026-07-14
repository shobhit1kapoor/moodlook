import os
from pathlib import Path
import unittest

from nowcasting.io import validate_archive


class ArchiveContractTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("SOLAFUNE_TRAIN_ZIP"), "set SOLAFUNE_TRAIN_ZIP to validate provided archive")
    def test_train_manifest_references_exist(self):
        manifest = validate_archive(Path(os.environ["SOLAFUNE_TRAIN_ZIP"]), "train")
        self.assertEqual(len(manifest), 40686)


if __name__ == "__main__":
    unittest.main()
