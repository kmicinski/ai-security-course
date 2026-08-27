#!/usr/bin/env python3
"""Check the demo end to end before shipping a change.

    python3 verify.py            # everything below
    python3 verify.py --quick    # skip executing the notebook (much faster)

Three things get checked, in increasing order of cost:

1. The notebook is not stale — it matches what build_notebook.py would write.
2. The invariants the notebook *claims* actually hold, computed here rather
   than asserted in prose.
3. The generated notebook executes top to bottom with no cell raising.

Run it after editing anything under this directory. Setup, once:

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt -r dev-requirements.txt
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
SAMPLE_URL = "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg"

failures: list[str] = []


def check(label: str, passed: bool, detail: str = "") -> None:
    """Record one result and print it as it happens."""
    print(f"  {'PASS' if passed else 'FAIL'}  {label}{f'  — {detail}' if detail else ''}")
    if not passed:
        failures.append(label)


def check_notebook_fresh() -> None:
    print("\n[1/3] notebook freshness")
    done = subprocess.run(
        [sys.executable, "build_notebook.py", "--check"],
        cwd=HERE, capture_output=True, text=True,
    )
    check(
        "notebook matches its source",
        done.returncode == 0,
        (done.stdout + done.stderr).strip().splitlines()[-1] if done.stdout or done.stderr else "",
    )


def check_invariants() -> None:
    """The claims the notebook makes, recomputed."""
    print("\n[2/3] attack invariants")
    sys.path.insert(0, str(HERE))
    from PIL import Image

    from attacks.fgsm import fgsm_attack
    from attacks.pgd import pgd_attack
    from core import LABELS, classify, get_model, image_to_tensor, logits_for, run_attacks

    image = Image.open(io.BytesIO(urlopen(SAMPLE_URL).read()))
    pixels = image_to_tensor(image)
    model = get_model()
    clean_id, clean_confidence = classify(model, pixels)
    print(f"        baseline: {LABELS[clean_id]} at {clean_confidence:.1%}")

    # A zero budget must be a no-op. If this ever fails the harness is lying.
    zero = run_attacks(pixels, epsilon=0.0, pgd_steps=10, pgd_step_size=0.0)
    check(
        "epsilon = 0 changes nothing",
        not zero.fgsm_changed and not zero.pgd_changed,
    )

    # PGD with one step of size epsilon is FGSM, exactly.
    epsilon = 0.02
    fgsm_pixels, _ = fgsm_attack(model, pixels, clean_id, epsilon, logits_for)
    one_step = pgd_attack(model, pixels, clean_id, epsilon, epsilon, 1, logits_for)
    gap = (fgsm_pixels - one_step).abs().max().item()
    check("PGD(steps=1, alpha=eps) reproduces FGSM", gap == 0.0, f"max|diff| = {gap}")

    # The projection must hold the budget even when the step overshoots it.
    for steps, alpha in [(10, 0.005), (10, 0.05), (40, 0.025)]:
        adversarial = pgd_attack(
            model, pixels, clean_id, epsilon, alpha, steps, logits_for
        )
        linf = (adversarial - pixels).abs().max().item()
        check(
            f"L-inf budget holds (steps={steps}, alpha={alpha})",
            linf <= epsilon + 1e-6,
            f"L-inf = {linf:.5f} <= {epsilon}",
        )

    # Attacked images must still be images.
    result = run_attacks(pixels)
    for name, tensor in [("FGSM", result.fgsm_pixels), ("PGD", result.pgd_pixels)]:
        in_range = bool((tensor >= 0).all() and (tensor <= 1).all())
        check(f"{name} output stays in [0, 1]", in_range)

    check(
        "both attacks move the model off its answer at eps=0.02",
        result.fgsm_changed and result.pgd_changed,
        f"FGSM -> {LABELS[result.fgsm_id]}, PGD -> {LABELS[result.pgd_id]}",
    )


def execute_notebook() -> int:
    """Run every cell and report failures. Runs in its own process — see below."""
    import matplotlib

    matplotlib.use("Agg")  # No display in a checkout or on a server.
    import nbformat
    from nbclient import NotebookClient

    notebook = nbformat.read(HERE / "adversarial_image_demo.ipynb", as_version=4)
    NotebookClient(
        notebook, timeout=900, kernel_name="python3",
        resources={"metadata": {"path": str(HERE)}},
    ).execute()

    errors = [
        f"cell {i}: {out.ename}: {out.evalue}"
        for i, cell in enumerate(notebook.cells)
        if cell.cell_type == "code"
        for out in cell.get("outputs", [])
        if out.output_type == "error"
    ]

    # The sweep prints its denominators; surface them so a regression is visible.
    # A cell's stdout arrives as several stream outputs, so join before matching
    # or the table comes out chopped after its first row.
    for cell in notebook.cells:
        streams = "".join(
            out.get("text", "")
            for out in cell.get("outputs", [])
            if out.output_type == "stream"
        )
        if "epsilon" in streams:
            print("        " + streams.strip().replace("\n", "\n        "))

    if errors:
        print("ERRORS: " + "; ".join(errors))
        return 1
    return 0


def check_notebook_runs() -> None:
    """Execute the notebook in a *child* process.

    Not merely tidiness: check_invariants() has already imported torch into this
    process, and starting a Jupyter kernel afterwards from the same interpreter
    hangs instead of running. A clean child sidesteps it, and also means a
    wedged kernel cannot take this script down with it.
    """
    print("\n[3/3] notebook execution")
    done = subprocess.run(
        [sys.executable, str(HERE / "verify.py"), "--execute-notebook"],
        cwd=HERE, capture_output=True, text=True, timeout=1800,
    )
    detail = ""
    for line in done.stdout.splitlines():
        if line.startswith("ERRORS: "):
            detail = line[len("ERRORS: "):]
        else:
            print(line)
    if done.returncode != 0 and not detail:
        tail = done.stderr.strip().splitlines()
        detail = tail[-1] if tail else "child process failed"

    check("every cell executes", done.returncode == 0, detail)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick", action="store_true", help="skip executing the notebook"
    )
    parser.add_argument(
        "--execute-notebook", action="store_true",
        help=argparse.SUPPRESS,  # Internal: the isolated child of step 3.
    )
    args = parser.parse_args()

    if args.execute_notebook:
        return execute_notebook()

    check_notebook_fresh()
    check_invariants()
    if args.quick:
        print("\n[3/3] notebook execution — skipped (--quick)")
    else:
        check_notebook_runs()

    print()
    if failures:
        print(f"FAILED ({len(failures)}): " + "; ".join(failures))
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
