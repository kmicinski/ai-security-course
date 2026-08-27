# Adversarial images: FGSM vs. PGD

CIS400/600 demo. A pretrained ImageNet ResNet-18 classifies an image; a one-step
FGSM attack and an iterative PGD attack then try to move it off that prediction
under the same L-infinity budget.

**Colab:** open `adversarial_image_demo.ipynb`. It carries its own source and
runs on what Colab preinstalls — nothing to clone, nothing to install.

**Local, with the Gradio UI:**

```bash
pip install -r requirements.txt
python app.py
```

## Files

| Path | Role |
| :-- | :-- |
| `attacks/fgsm.py`, `attacks/pgd.py` | the attacks |
| `core.py` | model, preprocessing, attack driver — no UI |
| `notebook_cells.py` | notebook-only: image loading, plotting, epsilon sweep |
| `app.py` | Gradio UI; imports `core`, adds no algorithms |
| `build_notebook.py` | generates the notebook from the files above |
| `adversarial_image_demo.ipynb` | generated — do not hand-edit |

The modules are the source of truth. After changing one, rebuild:

```bash
python3 build_notebook.py           # regenerate
python3 build_notebook.py --check   # fail if stale
```

## Checking a change

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r dev-requirements.txt

python3 verify.py            # notebook fresh + invariants + full execution (~10s)
python3 verify.py --quick    # skip executing the notebook (~4s)
```

`verify.py` checks that the notebook matches its source, that the attacks obey
the properties the notebook claims — epsilon = 0 is a no-op, PGD with one step
of size epsilon *is* FGSM, the L-infinity budget survives a step size larger
than epsilon, outputs stay in [0, 1] — and that every cell executes. Deleting
the projection line from `pgd.py` makes it fail three budget checks, which is
the point.
