#!/usr/bin/env python3
"""Generate adversarial_image_demo.ipynb by inlining this directory's source.

    python3 build_notebook.py            # write the notebook
    python3 build_notebook.py --check    # fail if it is out of date (CI/pre-push)

Why a generator. The notebook has to carry its own source — Colab should not
clone a repository — but a hand-maintained copy of the attacks inside a .ipynb
drifts from the real modules the moment either is edited. So the modules stay
canonical and the notebook is built from them: edit attacks/fgsm.py, rerun this,
and the notebook cell changes with it. Same arrangement as the slide decks,
where slides/<deck>/deck.md is the source and index.html is generated.

The notebook is a build artifact. Do not hand-edit it; edit the source region
and rebuild.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "adversarial_image_demo.ipynb"

START = re.compile(r"^\s*#\s*--8<--\s*start:\s*(\S+)\s*$")
END = re.compile(r"^\s*#\s*--8<--\s*end:\s*(\S+)\s*$")


def read_region(relative_path: str, name: str) -> str:
    """Return the lines between the start/end markers for ``name``."""
    lines = (HERE / relative_path).read_text().splitlines()
    collected: list[str] = []
    depth = 0
    for line in lines:
        if END.match(line) and END.match(line).group(1) == name:
            return "\n".join(collected).strip("\n")
        if depth:
            collected.append(line)
        if START.match(line) and START.match(line).group(1) == name:
            depth = 1
    raise SystemExit(f"build_notebook: no region {name!r} in {relative_path}")


def read_whole(relative_path: str) -> str:
    """Return a whole module, minus its module docstring and __future__ noise.

    The attack modules are already written to be read start to finish, so they
    become notebook cells verbatim. Only the module docstring is dropped: the
    surrounding markdown cell says the same thing better.
    """
    text = (HERE / relative_path).read_text()
    text = re.sub(r'\A\s*(?:"""|\'\'\')(?:.|\n)*?(?:"""|\'\'\')\s*\n', "", text)
    return text.strip("\n")


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(text),
    }


def _lines(text: str) -> list[str]:
    """nbformat stores source as a list of lines, each keeping its newline."""
    body = text.strip("\n").split("\n")
    return [line + "\n" for line in body[:-1]] + [body[-1]]


def build() -> dict:
    cells = [
        md(
            "# Adversarial examples: FGSM and PGD on ResNet-18\n"
            "\n"
            "**CIS400 / CIS600 — Cybersecurity & AI.** Everything this notebook runs is "
            "written out in the cells below: the preprocessing, both attacks, and the "
            "driver. Nothing is cloned and nothing is `pip install`ed — Colab already "
            "ships PyTorch, torchvision, Pillow, and matplotlib. Read the cells top to "
            "bottom, then start changing them.\n"
            "\n"
            "The only thing fetched from the network is the pretrained ResNet-18 "
            "checkpoint (about 45 MB) and one sample image.\n"
            "\n"
            "**Threat model.** White-box and untargeted: we have the model's weights and "
            "its gradients, and we only try to make the top-1 label *change* — not to "
            "steer it to a chosen class. That is the weakest interesting attack goal, "
            "which is worth remembering when you read a paper reporting a success rate.\n"
            "\n"
            "> Attacks here run against a local, public model on images you supply. "
            "Keep it that way: this is a teaching sandbox, not something to point at a "
            "service you do not own."
        ),
        md(
            "## 0 · Where the code will run\n"
            "\n"
            "A GPU makes PGD's iterations quicker but nothing here needs one; on CPU the "
            "whole notebook still finishes in well under a minute. In Colab, "
            "*Runtime → Change runtime type → T4 GPU* if you want it."
        ),
        code(
            "import torch, torchvision\n"
            "\n"
            "print(\"torch      \", torch.__version__)\n"
            "print(\"torchvision\", torchvision.__version__)\n"
            "print(\"device     \", \"cuda\" if torch.cuda.is_available() else \"cpu\")"
        ),
        md(
            "## 1 · The model, and where normalization happens\n"
            "\n"
            "ResNet-18 expects each channel standardized by the ImageNet mean and standard "
            "deviation. Where you apply that matters for an attack. If normalization were "
            "part of preprocessing, the attack would be perturbing normalized values and "
            "$\\varepsilon$ would mean something slightly different in each channel. So we "
            "keep the image in raw $[0,1]$ pixels and fold normalization into the forward "
            "pass:\n"
            "\n"
            "$$f(x) = \\mathrm{ResNet}\\!\\left(\\frac{x - \\mu}{\\sigma}\\right), "
            "\\qquad x \\in [0,1]^{3 \\times 224 \\times 224}$$\n"
            "\n"
            "Now a budget of $\\varepsilon = 0.02$ means what it looks like it means: no "
            "pixel channel moves by more than about $5/255$. Gradients still flow through "
            "the normalization to $x$, because it is just an affine map."
        ),
        code(read_region("core.py", "setup")),
        md(
            "## 2 · Reading a prediction\n"
            "\n"
            "`prediction` turns logits into a top-1 class and a softmax confidence. "
            "Treat that confidence as a number the model reports, not as a probability the "
            "world owes you — a successful attack usually produces a *confidently* wrong "
            "answer, which is exactly why confidence is a poor detector of one."
        ),
        code(read_region("core.py", "predict")),
        md(
            "## 3 · FGSM — one step to the edge of the budget\n"
            "\n"
            "Goodfellow et al. (2015). Take the loss $J(\\theta, x, y)$ the network was "
            "trained to minimize, and move the *input* in whichever direction raises it:\n"
            "\n"
            "$$x' = \\mathrm{clip}_{[0,1]}\\big(x + \\varepsilon \\cdot "
            "\\mathrm{sign}(\\nabla_x J(\\theta, x, y))\\big)$$\n"
            "\n"
            "The `sign` is the whole trick. A gradient *step* would move furthest along the "
            "few pixels with the largest partial derivatives; taking only the sign spends "
            "the full $\\varepsilon$ on **every** pixel at once. That is the right move when "
            "the constraint is $\\lVert x' - x \\rVert_\\infty \\le \\varepsilon$, since "
            "under an $L_\\infty$ budget the per-pixel spend is free — this is the corner of "
            "the $L_\\infty$ ball that maximizes the first-order increase in loss.\n"
            "\n"
            "One backward pass, and the linear approximation of $J$ it relies on is only "
            "good near $x$. That assumption is what PGD stops making."
        ),
        code(read_whole("attacks/fgsm.py")),
        md(
            "## 4 · PGD — small steps, projected back each time\n"
            "\n"
            "Madry et al. (2018). Iterate FGSM with a smaller step $\\alpha$, and after "
            "every step project back into the $L_\\infty$ ball so the total budget still "
            "holds:\n"
            "\n"
            "$$x^{(t+1)} = \\Pi_{B_\\infty(x, \\varepsilon)}\\Big(x^{(t)} + \\alpha \\cdot "
            "\\mathrm{sign}\\big(\\nabla_x J(\\theta, x^{(t)}, y)\\big)\\Big)$$\n"
            "\n"
            "The projection $\\Pi$ is the two-sided clamp in the code below: clip to "
            "$[x - \\varepsilon,\\, x + \\varepsilon]$, then to $[0,1]$ so the result is "
            "still an image. Because the gradient is recomputed at each $x^{(t)}$, PGD can "
            "follow curvature that FGSM's single linearization misses — with "
            "$\\alpha < \\varepsilon$ it searches inside the ball instead of jumping "
            "straight to a corner.\n"
            "\n"
            "Cost is the honest trade: $T$ steps means $T$ forward and backward passes."
        ),
        code(read_whole("attacks/pgd.py")),
        md(
            "## 5 · Running both under one budget\n"
            "\n"
            "Both attacks get the same $\\varepsilon$, so the comparison is fair. Note the "
            "label being attacked is the model's **own clean prediction**, not ground truth: "
            "we are measuring whether the model can be moved off its answer, which is "
            "well-defined even for an image with no correct ImageNet class."
        ),
        code(read_region("core.py", "driver")),
        md(
            "## 6 · Pick an image\n"
            "\n"
            "Runs on a public sample by default so *Run all* works untouched. To attack "
            "your own image in Colab, set `USE_UPLOAD = True` and rerun this cell."
        ),
        code(read_region("notebook_cells.py", "imagery")),
        md(
            "## 7 · Attack it\n"
            "\n"
            "Four panels: the original, FGSM's result, PGD's result, and PGD's perturbation "
            "rescaled around neutral gray so you can see its structure. The printed "
            "$L_\\infty$ is the largest change any channel actually took — check that it "
            "never exceeds $\\varepsilon$. If it did, the attack would be cheating."
        ),
        code(read_region("notebook_cells.py", "visualize")),
        md(
            "## 8 · The number that actually matters\n"
            "\n"
            "A single flipped image is a demo, not a result. The question to ask of any "
            "attack — in this notebook or in a paper — is **what fraction of which "
            "population of inputs does it break, at what budget?** The sweep below prints "
            "hits over a denominator at each $\\varepsilon$, which with one image is an "
            "honest $n = 1$. Read those rows as anecdote, and note how small the budgets "
            "are: the interesting behavior on this image happens below $1/255$.\n"
            "\n"
            "$\\varepsilon = 0$ is the control: it must report $0$, because a zero-budget "
            "attack cannot change anything. If it ever doesn't, the harness is broken."
        ),
        code(read_region("notebook_cells.py", "sweep")),
        md(
            "## 9 · Things worth trying\n"
            "\n"
            "- **Find the floor.** Push $\\varepsilon$ down until the label stops flipping. "
            "On the sample image it survives to roughly $0.001$ — about $0.3/255$, a change "
            "smaller than one step of an 8-bit pixel value, and far smaller than what "
            "re-saving the image as a JPEG would do to it. Sit with what that implies about "
            "how close the decision boundary runs to an ordinary photograph.\n"
            "- **Watch the confidence, not just the label.** At the default settings PGD "
            "does not merely flip the Samoyed — it reports the wrong class at essentially "
            "$100\\%$. Any defense that plans to screen out attacks by looking for "
            "low-confidence predictions has to explain this row.\n"
            "- **Starve PGD.** Set `pgd_steps=1, pgd_step_size=epsilon` and you have "
            "reconstructed FGSM. Confirm the two produce the same image.\n"
            "- **Get a real denominator.** Load 20–50 images, pass them all to `sweep`, and "
            "watch the FGSM and PGD curves separate. That separation is the actual claim "
            "the PGD paper makes.\n"
            "- **Break the comparison on purpose.** Set `pgd_step_size` larger than "
            "`epsilon`. PGD still respects the budget — the projection sees to that — but "
            "it stops searching and just bounces between corners.\n"
            "- **Then ask the defensive question.** Everything above assumed white-box "
            "gradient access. What would you have to take away from the attacker to stop it, "
            "and what would that cost the people using the model?"
        ),
        md(
            "---\n"
            "\n"
            "The polished Gradio version of this demo — sliders, upload panel, and an "
            "in-app code tutorial — lives beside this notebook in the course repository "
            "and runs locally with `python app.py`. This notebook and that app import the "
            "same attack code; the cells above were generated from it."
        ),
    ]

    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the notebook on disk is not what we would write",
    )
    args = parser.parse_args()

    rendered = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"

    if args.check:
        current = NOTEBOOK.read_text() if NOTEBOOK.exists() else ""
        if current != rendered:
            print(
                f"build_notebook: {NOTEBOOK.name} is stale — "
                "rerun `python3 build_notebook.py`",
                file=sys.stderr,
            )
            return 1
        print(f"build_notebook: {NOTEBOOK.name} is up to date")
        return 0

    NOTEBOOK.write_text(rendered)
    cells = json.loads(rendered)["cells"]
    print(f"build_notebook: wrote {NOTEBOOK.name} ({len(cells)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
