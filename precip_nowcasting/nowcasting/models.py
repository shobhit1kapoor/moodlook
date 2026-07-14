from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from .io import SPECTRAL_GROUPS


def _groups(channels: int) -> int:
    return next(group for group in range(min(8, channels), 0, -1) if channels % group == 0)


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.0):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(_groups(out_channels), out_channels),
            nn.SiLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(_groups(out_channels), out_channels),
            nn.SiLU(inplace=True),
            nn.Dropout2d(dropout) if dropout else nn.Identity(),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.layers(value)


class SensorAdapter(nn.Module):
    """Legacy per-sensor adapter retained for controlled baseline comparisons."""

    def __init__(self, channels: int):
        super().__init__()
        self.adapters = nn.ModuleList([nn.Conv2d(16, channels, kernel_size=1) for _ in range(3)])

    def forward(self, frames: torch.Tensor, sensor: torch.Tensor) -> torch.Tensor:
        output = torch.empty((frames.shape[0], self.adapters[0].out_channels, *frames.shape[-2:]), device=frames.device, dtype=frames.dtype)
        for sensor_id, adapter in enumerate(self.adapters):
            selected = sensor == sensor_id
            if selected.any():
                output[selected] = adapter(frames[selected])
        return output


class SpectralSensorAdapter(nn.Module):
    """Fuse a sensor-specific all-band stem with shared physical band groups."""

    def __init__(self, channels: int):
        super().__init__()
        self.channels = channels
        self.all_band = nn.ModuleList([nn.Conv2d(32, channels, 1) for _ in range(3)])
        self.group_stem = nn.Sequential(nn.Conv2d(10, channels, 1, bias=False), nn.GroupNorm(_groups(channels), channels), nn.SiLU(inplace=True))
        self.fuse = ConvBlock(2 * channels, channels)
        self.film = nn.Embedding(3, 2 * channels)
        nn.init.zeros_(self.film.weight)
        self.register_buffer("group_index", torch.tensor([SPECTRAL_GROUPS[name] for name in ("goes", "himawari", "meteosat")], dtype=torch.long), persistent=False)

    def forward(self, image: torch.Tensor, sensor: torch.Tensor, band_mask: torch.Tensor | None = None) -> torch.Tensor:
        batch, _, height, width = image.shape
        if band_mask is None:
            band_mask = torch.ones((batch, 16), device=image.device, dtype=image.dtype)
        mask = band_mask.to(dtype=image.dtype).unsqueeze(-1).unsqueeze(-1).expand(-1, -1, height, width)
        all_features = torch.empty((batch, self.channels, height, width), device=image.device, dtype=image.dtype)
        grouped = torch.zeros((batch, 5, height, width), device=image.device, dtype=image.dtype)
        group_valid = torch.zeros_like(grouped)
        for sensor_id, adapter in enumerate(self.all_band):
            selected = sensor == sensor_id
            if not selected.any():
                continue
            selected_image = image[selected] * mask[selected]
            all_features[selected] = adapter(torch.cat([selected_image, mask[selected]], dim=1)).to(dtype=image.dtype)
            mapping = self.group_index[sensor_id]
            for group in range(5):
                band_indices = torch.nonzero(mapping == group, as_tuple=False).flatten()
                group_mask = mask[selected][:, band_indices]
                denominator = group_mask.sum(dim=1, keepdim=True).clamp_min(1.0)
                grouped[selected, group:group + 1] = (selected_image[:, band_indices] * group_mask).sum(dim=1, keepdim=True) / denominator
                group_valid[selected, group:group + 1] = (group_mask.sum(dim=1, keepdim=True) > 0).to(image.dtype)
        semantic = self.group_stem(torch.cat([grouped, group_valid], dim=1)).to(dtype=image.dtype)
        value = self.fuse(torch.cat([all_features, semantic], dim=1))
        scale, bias = self.film(sensor).chunk(2, dim=1)
        return value * (1.0 + scale[:, :, None, None]) + bias[:, :, None, None]


class TemporalFusion(nn.Module):
    """Gated temporal fusion with optional learned feature-space alignment."""

    def __init__(self, channels: int, *, motion: bool):
        super().__init__()
        self.motion = motion
        self.flow = nn.Sequential(nn.Conv2d(2 * channels, channels, 3, padding=1), nn.SiLU(inplace=True), nn.Conv2d(channels, 2, 3, padding=1)) if motion else None
        self.mix = ConvBlock(5 * channels, channels)
        self.gate = nn.Sequential(nn.Conv2d(channels, channels, 7, padding=3, groups=channels), nn.Sigmoid())

    @staticmethod
    def _warp(value: torch.Tensor, flow: torch.Tensor) -> torch.Tensor:
        _, _, height, width = value.shape
        yy, xx = torch.meshgrid(
            torch.linspace(-1, 1, height, device=value.device, dtype=value.dtype),
            torch.linspace(-1, 1, width, device=value.device, dtype=value.dtype), indexing="ij",
        )
        grid = torch.stack([xx, yy], dim=-1).unsqueeze(0).expand(value.shape[0], -1, -1, -1).clone()
        grid[..., 0] += flow[:, 0] * (2.0 / max(width - 1, 1))
        grid[..., 1] += flow[:, 1] * (2.0 / max(height - 1, 1))
        return F.grid_sample(value, grid, mode="bilinear", padding_mode="border", align_corners=True)

    def forward(self, frames: list[torch.Tensor], frame_mask: torch.Tensor) -> torch.Tensor:
        older0, older1, latest = [value * frame_mask[:, index, None, None, None] for index, value in enumerate(frames)]
        if self.flow is not None:
            older0 = self._warp(older0, torch.tanh(self.flow(torch.cat([older0, latest], dim=1))) * 4.0)
            older1 = self._warp(older1, torch.tanh(self.flow(torch.cat([older1, latest], dim=1))) * 4.0)
        value = self.mix(torch.cat([older0, older1, latest, latest - older0, latest - older1], dim=1))
        return latest + value * self.gate(value)


class SpectralMotionNowcaster(nn.Module):
    """Sensor-conditioned, motion-aware satellite-to-rain regression model."""

    def __init__(self, *, base_channels: int = 24, dropout: float = 0.1, motion: bool = True, use_metadata: bool = True):
        super().__init__()
        c = base_channels
        self.use_metadata = use_metadata
        self.adapter = SpectralSensorAdapter(c)
        self.enc0 = ConvBlock(c, c, dropout)
        self.enc1 = nn.Sequential(nn.Conv2d(c, 2 * c, 3, stride=2, padding=1), ConvBlock(2 * c, 2 * c, dropout))
        self.enc2 = nn.Sequential(nn.Conv2d(2 * c, 4 * c, 3, stride=2, padding=1), ConvBlock(4 * c, 4 * c, dropout))
        self.fuse0 = TemporalFusion(c, motion=motion)
        self.fuse1 = TemporalFusion(2 * c, motion=motion)
        self.fuse2 = TemporalFusion(4 * c, motion=motion)
        self.time0 = nn.Linear(8, 2 * c) if use_metadata else None
        self.time1 = nn.Linear(8, 4 * c) if use_metadata else None
        self.time2 = nn.Linear(8, 8 * c) if use_metadata else None
        self.up1 = ConvBlock(6 * c, 2 * c, dropout)
        self.up0 = ConvBlock(3 * c, c, dropout)
        self.rain_head = nn.Conv2d(c, 2, 1)
        self.calibration = nn.Embedding(3, 3)  # occurrence bias, log intensity scale, intensity bias
        nn.init.zeros_(self.calibration.weight)
        self.reconstruction_fuser = TemporalFusion(c, motion=False)
        self.reconstruction_head = nn.Conv2d(c, 16, 1)

    def _encode(self, image: torch.Tensor, sensor: torch.Tensor, band_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        value = self.enc0(self.adapter(image, sensor, band_mask))
        return value, self.enc1(value), self.enc2(self.enc1(value))

    @staticmethod
    def _condition(value: torch.Tensor, embedding: nn.Linear | None, metadata: torch.Tensor) -> torch.Tensor:
        if embedding is None:
            return value
        scale, bias = embedding(metadata).chunk(2, dim=1)
        return value * (1.0 + scale[:, :, None, None]) + bias[:, :, None, None]

    def forward(self, image: torch.Tensor, metadata: torch.Tensor, sensor: torch.Tensor, frame_mask: torch.Tensor | None = None, band_mask: torch.Tensor | None = None, *, return_aux: bool = False):
        batch = image.shape[0]
        if frame_mask is None:
            frame_mask = torch.ones((batch, 3), device=image.device, dtype=image.dtype)
        if band_mask is None:
            band_mask = torch.ones((batch, 3, 16), device=image.device, dtype=image.dtype)
        encoded = [self._encode(image[:, frame], sensor, band_mask[:, frame]) for frame in range(3)]
        level0 = self._condition(self.fuse0([item[0] for item in encoded], frame_mask), self.time0, metadata)
        level1 = self._condition(self.fuse1([item[1] for item in encoded], frame_mask), self.time1, metadata)
        level2 = self._condition(self.fuse2([item[2] for item in encoded], frame_mask), self.time2, metadata)
        value = F.interpolate(level2, size=level1.shape[-2:], mode="bilinear", align_corners=False)
        value = self.up1(torch.cat([value, level1], dim=1))
        value = F.interpolate(value, size=level0.shape[-2:], mode="bilinear", align_corners=False)
        value = self.up0(torch.cat([value, level0], dim=1))
        heads = F.interpolate(self.rain_head(value), size=(41, 41), mode="bilinear", align_corners=False)
        occ_bias, log_scale, intensity_bias = self.calibration(sensor).unbind(dim=1)
        occurrence_logits = heads[:, 0] + occ_bias[:, None, None]
        intensity = F.softplus(heads[:, 1] * log_scale.exp()[:, None, None] + intensity_bias[:, None, None])
        prediction = torch.sigmoid(occurrence_logits) * intensity
        if not return_aux:
            return prediction
        # Predict frame t-10 from t-30/t-20 only; no evaluation imagery is used for this auxiliary loss.
        prior_mask = frame_mask.clone(); prior_mask[:, 2] = 0.0
        reconstruction_features = self.reconstruction_fuser([encoded[0][0], encoded[1][0], torch.zeros_like(encoded[2][0])], prior_mask)
        return prediction, {"occurrence_logits": occurrence_logits, "reconstruction": self.reconstruction_head(reconstruction_features)}


class SpectralSimVPNowcaster(SpectralMotionNowcaster):
    """A lower-cost, no-warp candidate intentionally diverse from the motion model."""

    def __init__(self, *, base_channels: int = 24, dropout: float = 0.1, use_metadata: bool = True):
        super().__init__(base_channels=base_channels, dropout=dropout, motion=False, use_metadata=use_metadata)


class TemporalUNet(nn.Module):
    def __init__(self, *, base_channels: int = 32, dropout: float = 0.1, temporal: bool = True, use_metadata: bool = True):
        super().__init__()
        self.temporal = temporal
        self.adapter = SensorAdapter(base_channels)
        factor = 5 if temporal else 1
        self.stem = ConvBlock(base_channels * factor, base_channels * 2, dropout)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base_channels * 2, base_channels * 4, dropout))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base_channels * 4, base_channels * 8, dropout))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(base_channels * 8, base_channels * 8, dropout))
        self.metadata = nn.Sequential(nn.Linear(8, base_channels * 8), nn.SiLU(), nn.Linear(base_channels * 8, base_channels * 8)) if use_metadata else None
        self.up2 = ConvBlock(base_channels * 16, base_channels * 4, dropout)
        self.up1 = ConvBlock(base_channels * 8, base_channels * 2, dropout)
        self.up0 = ConvBlock(base_channels * 4, base_channels, dropout)
        self.head = nn.Sequential(nn.Conv2d(base_channels, base_channels, 3, padding=1), nn.SiLU(), nn.Conv2d(base_channels, 1, 1))

    def forward(self, image: torch.Tensor, metadata: torch.Tensor, sensor: torch.Tensor, frame_mask: torch.Tensor | None = None, band_mask: torch.Tensor | None = None, *, return_aux: bool = False):
        if frame_mask is None:
            frame_mask = torch.ones((image.shape[0], 3), device=image.device, dtype=image.dtype)
        if band_mask is not None:
            image = image * band_mask[:, :, :, None, None]
        adapted = [self.adapter(image[:, frame], sensor) * frame_mask[:, frame, None, None, None] for frame in range(3)]
        value = torch.cat([adapted[0], adapted[1], adapted[2], adapted[1] - adapted[0], adapted[2] - adapted[1]], dim=1) if self.temporal else adapted[2]
        skip0 = self.stem(value); skip1 = self.down1(skip0); skip2 = self.down2(skip1); value = self.down3(skip2)
        if self.metadata is not None:
            value = value + self.metadata(metadata).unsqueeze(-1).unsqueeze(-1)
        value = self.up2(torch.cat([F.interpolate(value, size=skip2.shape[-2:], mode="bilinear", align_corners=False), skip2], dim=1))
        value = self.up1(torch.cat([F.interpolate(value, size=skip1.shape[-2:], mode="bilinear", align_corners=False), skip1], dim=1))
        value = self.up0(torch.cat([F.interpolate(value, size=skip0.shape[-2:], mode="bilinear", align_corners=False), skip0], dim=1))
        prediction = F.softplus(F.interpolate(self.head(value), size=(41, 41), mode="bilinear", align_corners=False)[:, 0])
        return (prediction, {}) if return_aux else prediction


class MaskedSensorAdapter(nn.Module):
    """Sensor-specific radiometric projection that receives validity channels."""

    def __init__(self, channels: int):
        super().__init__()
        self.adapters = nn.ModuleList([nn.Conv2d(32, channels, 1) for _ in range(3)])

    def forward(self, image: torch.Tensor, sensor: torch.Tensor, band_mask: torch.Tensor) -> torch.Tensor:
        mask = band_mask[:, :, None, None].to(dtype=image.dtype).expand_as(image)
        output = torch.empty((image.shape[0], self.adapters[0].out_channels, *image.shape[-2:]), device=image.device, dtype=image.dtype)
        for sensor_id, adapter in enumerate(self.adapters):
            selected = sensor == sensor_id
            if selected.any():
                output[selected] = adapter(torch.cat([image[selected] * mask[selected], mask[selected]], dim=1)).to(dtype=image.dtype)
        return output


class LargeKernelAttention(nn.Module):
    """Cheap broad-context block inspired by satellite nowcasting LKA designs."""

    def __init__(self, channels: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Conv2d(channels, channels, 5, padding=2, groups=channels),
            nn.Conv2d(channels, channels, 7, padding=9, dilation=3, groups=channels),
            nn.Conv2d(channels, channels, 1),
            nn.Sigmoid(),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return value * self.attention(value) + value


class SensorSpecificHead(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.heads = nn.ModuleList([nn.Sequential(ConvBlock(channels, channels), nn.Conv2d(channels, 1, 1)) for _ in range(3)])

    def forward(self, value: torch.Tensor, sensor: torch.Tensor) -> torch.Tensor:
        output = torch.empty((value.shape[0], 1, *value.shape[-2:]), device=value.device, dtype=value.dtype)
        for sensor_id, head in enumerate(self.heads):
            selected = sensor == sensor_id
            if selected.any():
                output[selected] = head(value[selected]).to(dtype=value.dtype)
        return output


class MaskedTemporalUNet(nn.Module):
    """Direct-MSE, multi-scale temporal U-Net with sensor-specific rain heads.

    This intentionally removes motion warping and the hurdle product after the
    Fold-0 ablation showed that those additions did not beat the wide U-Net.
    """

    def __init__(self, *, base_channels: int = 32, dropout: float = 0.1, use_metadata: bool = True):
        super().__init__()
        c = base_channels
        self.adapter = MaskedSensorAdapter(c)
        self.use_metadata = use_metadata
        self.stem = ConvBlock(5 * c, 2 * c, dropout)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(2 * c, 4 * c, dropout))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(4 * c, 8 * c, dropout))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(8 * c, 8 * c, dropout), LargeKernelAttention(8 * c))
        self.time0 = nn.Linear(8, 4 * c) if use_metadata else None
        self.time1 = nn.Linear(8, 8 * c) if use_metadata else None
        self.time2 = nn.Linear(8, 16 * c) if use_metadata else None
        self.time3 = nn.Linear(8, 16 * c) if use_metadata else None
        self.up2 = ConvBlock(16 * c, 4 * c, dropout)
        self.up1 = ConvBlock(8 * c, 2 * c, dropout)
        self.up0 = ConvBlock(4 * c, c, dropout)
        self.rain_head = SensorSpecificHead(c)
        self.occurrence_head = SensorSpecificHead(c)
        self.future_satellite_head = nn.Sequential(ConvBlock(c, c), nn.Conv2d(c, 16, 1))

    @staticmethod
    def _film(value: torch.Tensor, layer: nn.Linear | None, metadata: torch.Tensor) -> torch.Tensor:
        if layer is None:
            return value
        scale, bias = layer(metadata).chunk(2, dim=1)
        return value * (1 + scale[:, :, None, None]) + bias[:, :, None, None]

    def forward(self, image: torch.Tensor, metadata: torch.Tensor, sensor: torch.Tensor, frame_mask: torch.Tensor | None = None, band_mask: torch.Tensor | None = None, *, return_aux: bool = False):
        batch = image.shape[0]
        if frame_mask is None:
            frame_mask = torch.ones((batch, 3), device=image.device, dtype=image.dtype)
        if band_mask is None:
            band_mask = torch.ones((batch, 3, 16), device=image.device, dtype=image.dtype)
        frames = [self.adapter(image[:, step], sensor, band_mask[:, step]) * frame_mask[:, step, None, None, None] for step in range(3)]
        temporal = torch.cat([frames[0], frames[1], frames[2], frames[1] - frames[0], frames[2] - frames[1]], dim=1)
        skip0 = self._film(self.stem(temporal), self.time0, metadata)
        skip1 = self._film(self.down1(skip0), self.time1, metadata)
        skip2 = self._film(self.down2(skip1), self.time2, metadata)
        value = self._film(self.down3(skip2), self.time3, metadata)
        value = self.up2(torch.cat([F.interpolate(value, size=skip2.shape[-2:], mode="bilinear", align_corners=False), skip2], dim=1))
        value = self.up1(torch.cat([F.interpolate(value, size=skip1.shape[-2:], mode="bilinear", align_corners=False), skip1], dim=1))
        value = self.up0(torch.cat([F.interpolate(value, size=skip0.shape[-2:], mode="bilinear", align_corners=False), skip0], dim=1))
        value = F.interpolate(value, size=(41, 41), mode="bilinear", align_corners=False)
        prediction = F.softplus(self.rain_head(value, sensor)[:, 0])
        if not return_aux:
            return prediction
        return prediction, {"occurrence_logits": self.occurrence_head(value, sensor)[:, 0], "future_satellite": self.future_satellite_head(F.interpolate(value, size=image.shape[-2:], mode="bilinear", align_corners=False))}


class PretrainedResNet18(nn.Module):
    """Optional licensed-weight benchmark, never a default finalist."""
    def __init__(self, *, pretrained: bool = False):
        super().__init__()
        from torchvision.models import ResNet18_Weights, resnet18
        weights = ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        self.adapters = nn.ModuleList([nn.Conv2d(16, 3, 1) for _ in range(3)])
        backbone = resnet18(weights=weights)
        self.encoder = nn.Sequential(*list(backbone.children())[:-2])
        self.fusion = nn.Sequential(nn.Conv2d(512 * 5, 256, 3, padding=1), nn.SiLU(), nn.Conv2d(256, 64, 3, padding=1), nn.SiLU(), nn.Conv2d(64, 1, 1))

    def forward(self, image: torch.Tensor, metadata: torch.Tensor, sensor: torch.Tensor, frame_mask: torch.Tensor | None = None, band_mask: torch.Tensor | None = None, *, return_aux: bool = False):
        if frame_mask is None:
            frame_mask = torch.ones((image.shape[0], 3), device=image.device, dtype=image.dtype)
        if band_mask is not None:
            image = image * band_mask[:, :, :, None, None]
        encoded = []
        for frame in range(3):
            rgb = torch.empty((image.shape[0], 3, *image.shape[-2:]), device=image.device, dtype=image.dtype)
            for sensor_id, adapter in enumerate(self.adapters):
                selected = sensor == sensor_id
                if selected.any():
                    rgb[selected] = adapter(image[selected, frame])
            encoded.append(self.encoder(rgb * frame_mask[:, frame, None, None, None]))
        fused = torch.cat([encoded[0], encoded[1], encoded[2], encoded[1] - encoded[0], encoded[2] - encoded[1]], dim=1)
        prediction = F.softplus(F.interpolate(self.fusion(fused)[:, 0:1], size=(41, 41), mode="bilinear", align_corners=False)[:, 0])
        return (prediction, {}) if return_aux else prediction


def build_model(config: dict) -> nn.Module:
    model = config["model"]
    name = model["name"]
    if name == "spectral_motion":
        return SpectralMotionNowcaster(base_channels=int(model.get("base_channels", 24)), dropout=float(model.get("dropout", 0.1)), motion=True, use_metadata=bool(model.get("use_metadata", True)))
    if name == "spectral_simvp":
        return SpectralSimVPNowcaster(base_channels=int(model.get("base_channels", 24)), dropout=float(model.get("dropout", 0.1)), use_metadata=bool(model.get("use_metadata", True)))
    if name == "masked_temporal_unet":
        return MaskedTemporalUNet(base_channels=int(model.get("base_channels", 32)), dropout=float(model.get("dropout", 0.1)), use_metadata=bool(model.get("use_metadata", True)))
    if name == "temporal_unet":
        return TemporalUNet(base_channels=int(model["base_channels"]), dropout=float(model["dropout"]), temporal=True, use_metadata=bool(model["use_metadata"]))
    if name == "latest_unet":
        return TemporalUNet(base_channels=int(model["base_channels"]), dropout=float(model["dropout"]), temporal=False, use_metadata=bool(model["use_metadata"]))
    if name == "pretrained_resnet18":
        return PretrainedResNet18(pretrained=bool(model.get("pretrained", False)))
    raise ValueError(f"Unknown model name: {name}")
