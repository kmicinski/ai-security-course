"""Notebook-only code: loading an image, plotting, and the epsilon sweep.

These regions never run inside the Gradio app — it has its own upload widget and
image panels — but they are the whole interface in the notebook. They live in a
real module (rather than as strings inside build_notebook.py) so they can be
imported, executed, and checked like any other code.

Each region assumes the notebook cells before it have already run, so the names
from core.py (``LABELS``, ``run_attacks``, ``to_numpy_image``, …) are in scope.
"""

from core import LABELS, image_to_tensor, run_attacks, to_numpy_image  # noqa: F401
from PIL import Image  # noqa: F401

# --8<-- start: imagery
import io
from urllib.request import urlopen

# A public sample so "Run all" works with no interaction. This is the only
# network fetch in the notebook besides the pretrained ResNet-18 weights.
SAMPLE_URL = "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg"
USE_UPLOAD = False  # Set to True in Colab to attack your own image instead.


def load_image(use_upload: bool = USE_UPLOAD) -> Image.Image:
    """Return a PIL image: one you upload in Colab, or the public sample."""
    if use_upload:
        try:
            from google.colab import files  # Only present inside Colab.
        except ImportError:
            print("Not running in Colab — falling back to the sample image.")
        else:
            uploaded = files.upload()
            if uploaded:
                return Image.open(io.BytesIO(next(iter(uploaded.values()))))
            print("Nothing uploaded — falling back to the sample image.")
    return Image.open(io.BytesIO(urlopen(SAMPLE_URL).read()))


image = load_image()
pixels = image_to_tensor(image)
print("pixel tensor:", tuple(pixels.shape))
print(f"pixel range: [{pixels.min():.3f}, {pixels.max():.3f}]")
# --8<-- end: imagery


# --8<-- start: visualize
import matplotlib.pyplot as plt


def show_result(result) -> None:
    """Four panels: the original, both attacks, and PGD's amplified noise."""
    panels = [
        (result.pixels, "Original",
         result.clean_id, result.clean_confidence),
        (result.fgsm_pixels, "After FGSM",
         result.fgsm_id, result.fgsm_confidence),
        (result.pgd_pixels, "After PGD",
         result.pgd_id, result.pgd_confidence),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.8))
    for axis, (tensor, stage, class_id, confidence) in zip(axes, panels):
        axis.imshow(to_numpy_image(tensor))
        axis.set_title(
            f"{stage}\n{LABELS[class_id]}\n{confidence:.1%}", fontsize=11
        )
        axis.axis("off")

    axes[3].imshow(to_numpy_image(result.amplified_delta()))
    axes[3].set_title(
        "PGD perturbation\n(amplified around gray)\n"
        f"true L-inf = {result.linf(result.pgd_pixels):.4f}",
        fontsize=11,
    )
    axes[3].axis("off")

    fig.suptitle(
        f"epsilon = {result.epsilon:.3f}  ({result.epsilon * 255:.1f}/255 per channel)",
        fontsize=13,
    )
    fig.tight_layout()
    plt.show()


result = run_attacks(pixels, epsilon=0.02, pgd_steps=10, pgd_step_size=0.005)
show_result(result)
# --8<-- end: visualize


# --8<-- start: sweep
def sweep(images, epsilons, pgd_steps: int = 10, pgd_step_size=None):
    """Attack every image at every budget, reporting hits over a denominator.

    ``pgd_step_size=None`` scales the step with the budget (eps/4), which keeps
    PGD searching *inside* the ball at every row. A fixed step size larger than
    epsilon would still be projected back — the budget always holds — but PGD
    would degenerate into bouncing between corners, which is FGSM with extra
    forward passes.
    """
    print(f"{'epsilon':>9} {'x/255':>7} {'FGSM':>11} {'PGD':>11}")
    print("-" * 42)
    rows = []
    for epsilon in epsilons:
        step = pgd_step_size if pgd_step_size else max(epsilon / 4, 1e-5)
        fgsm_hits = pgd_hits = 0
        for candidate in images:
            outcome = run_attacks(candidate, epsilon, pgd_steps, step)
            fgsm_hits += int(outcome.fgsm_changed)
            pgd_hits += int(outcome.pgd_changed)
        total = len(images)
        rows.append((epsilon, fgsm_hits, pgd_hits, total))
        print(
            f"{epsilon:9.4f} {epsilon * 255:7.2f} "
            f"{fgsm_hits:>6}/{total:<4} {pgd_hits:>6}/{total:<4}"
        )
    return rows


# One image is not an evaluation. See the note below the output.
rows = sweep([pixels], [0.0, 0.0002, 0.0005, 0.001, 0.002, 0.008, 0.02])
# --8<-- end: sweep
