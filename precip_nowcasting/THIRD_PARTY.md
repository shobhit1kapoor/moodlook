# Third-party models and weights

The default implementation trains from scratch and downloads no model weights.

`pretrained_resnet18` is an optional benchmark branch. Before it is enabled for a
competition run, record the exact source URL, license, SHA-256 checksum, and
location-held-out OOF result below. Do not retain the branch in a finalist
ensemble unless its documented license is permitted by the competition and it
passes the configured OOF acceptance gate.

| Run ID | Weight source | License | SHA-256 | OOF RMSE | Decision |
| --- | --- | --- | --- | --- | --- |
| _No weights used_ | - | - | - | - | Scratch default |

No external satellite, elevation, weather, precipitation, or other raw data is
used by this project.
