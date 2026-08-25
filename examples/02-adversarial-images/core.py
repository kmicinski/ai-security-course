"""Model, preprocessing, and the attack driver: everything except the UI.

This module is the single source of truth for the demo's algorithm code. Two
consumers read it:

  * ``app.py`` imports it to run the Gradio interface locally.
  * ``build_notebook.py`` inlines the marked regions below into the Colab
    notebook, so the notebook carries its own source and clones nothing.

The ``# --8<-- start:`` / ``# --8<-- end:`` markers delimit those regions.
Keep them, and keep each region independently runnable: a region becomes one
notebook cell, and the cells execute in the order listed in build_notebook.py.
"""

# Imported from the submodules directly, not via attacks/__init__.py: the built
# site drops underscore-prefixed files, so the copy students download has no
# __init__.py. These imports still resolve there, as a namespace package.
from attacks.fgsm import fgsm_attack
from attacks.pgd import pgd_attack

# --8<-- start: setup
from functools import lru_cache

import numpy as np
import torch
from PIL import Image
from torchvision.models import ResNet18_Weights, resnet18
from torchvision.transforms import InterpolationMode
from torchvision.transforms import functional as TF

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
WEIGHTS = ResNet18_Weights.DEFAULT
LABELS = WEIGHTS.meta["categories"]

# ImageNet channel statistics. Note where these are applied: the attacks work on
# raw [0, 1] pixels and normalization is folded into the forward pass below,
# not into preprocessing. That is deliberate — it keeps the epsilon budget
# denominated in units a student can see on screen (1/255 of a pixel channel)
# rather than in post-normalization units that differ per channel.
MEAN = torch.tensor([0.485, 0.456, 0.406], device=DEVICE).view(1, 3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225], device=DEVICE).view(1, 3, 1, 1)


@lru_cache(maxsize=1)
def get_model() -> torch.nn.Module:
    """Download once, cache, and return an evaluation-mode ImageNet model."""
    return resnet18(weights=WEIGHTS).to(DEVICE).eval()


def image_to_tensor(image: Image.Image) -> torch.Tensor:
    """Apply the spatial part of ImageNet preprocessing, preserving pixel scale."""
    image = image.convert("RGB")
    image = TF.resize(image, 256, interpolation=InterpolationMode.BILINEAR)
    image = TF.center_crop(image, [224, 224])
    return TF.to_tensor(image).unsqueeze(0).to(DEVICE)


def logits_for(model: torch.nn.Module, pixels: torch.Tensor) -> torch.Tensor:
    """Normalize, then classify. Both attacks differentiate through this."""
    return model((pixels - MEAN) / STD)
# --8<-- end: setup


# --8<-- start: predict
def prediction(logits: torch.Tensor) -> tuple[int, float]:
    """Return the top-1 class id and its softmax confidence."""
    probabilities = logits.softmax(dim=1)
    confidence, class_id = probabilities.max(dim=1)
    return class_id.item(), confidence.item()


@torch.no_grad()
def classify(model: torch.nn.Module, pixels: torch.Tensor) -> tuple[int, float]:
    """Top-1 (class id, confidence) for a batch of one image. Reporting only."""
    return prediction(logits_for(model, pixels))


def to_numpy_image(tensor: torch.Tensor) -> np.ndarray:
    """Convert a 1x3xHxW tensor in [0, 1] to an HxWx3 uint8 array."""
    array = tensor.squeeze(0).detach().cpu().permute(1, 2, 0).numpy()
    return np.uint8(np.clip(array * 255.0, 0, 255))
# --8<-- end: predict


# --8<-- start: driver
from dataclasses import dataclass


@dataclass
class AttackResult:
    """One image attacked two ways, plus everything needed to report it."""

    epsilon: float
    pixels: torch.Tensor
    clean_id: int
    clean_confidence: float
    fgsm_pixels: torch.Tensor
    fgsm_id: int
    fgsm_confidence: float
    pgd_pixels: torch.Tensor
    pgd_id: int
    pgd_confidence: float

    @property
    def fgsm_changed(self) -> bool:
        """Did FGSM move the model off its original answer?"""
        return self.fgsm_id != self.clean_id

    @property
    def pgd_changed(self) -> bool:
        """Did PGD move the model off its original answer?"""
        return self.pgd_id != self.clean_id

    def amplified_delta(self) -> torch.Tensor:
        """PGD's perturbation rescaled around neutral gray so it is visible."""
        delta = self.pgd_pixels - self.pixels
        return (delta / (2 * max(self.epsilon, 1e-6)) + 0.5).clamp(0, 1)

    def linf(self, attacked: torch.Tensor) -> float:
        """Largest per-channel change. Must never exceed epsilon."""
        return (attacked - self.pixels).abs().max().item()


def run_attacks(
    pixels: torch.Tensor,
    epsilon: float = 0.02,
    pgd_steps: int = 10,
    pgd_step_size: float = 0.005,
) -> AttackResult:
    """Attack one preprocessed image with FGSM and PGD under the same budget.

    Both attacks are *untargeted* and take the model's own clean prediction as
    the label to move away from — not ground truth. So "success" here means
    "the top-1 label changed", which is the weakest useful notion of success.
    """
    model = get_model()
    clean_id, clean_confidence = classify(model, pixels)

    fgsm_pixels, _ = fgsm_attack(model, pixels, clean_id, epsilon, logits_for)
    fgsm_id, fgsm_confidence = classify(model, fgsm_pixels)

    pgd_pixels = pgd_attack(
        model, pixels, clean_id, epsilon, pgd_step_size, pgd_steps, logits_for
    )
    pgd_id, pgd_confidence = classify(model, pgd_pixels)

    return AttackResult(
        epsilon=float(epsilon),
        pixels=pixels,
        clean_id=clean_id,
        clean_confidence=clean_confidence,
        fgsm_pixels=fgsm_pixels,
        fgsm_id=fgsm_id,
        fgsm_confidence=fgsm_confidence,
        pgd_pixels=pgd_pixels,
        pgd_id=pgd_id,
        pgd_confidence=pgd_confidence,
    )
# --8<-- end: driver
