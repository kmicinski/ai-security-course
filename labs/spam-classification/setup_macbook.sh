#!/usr/bin/env bash
# Set up the PyTorch spam lab on a MacBook Pro (Apple Silicon or Intel).
#
#   ./setup_macbook.sh        # create .venv and install torch
#   source .venv/bin/activate # then, in your shell
#   python spam_torch.py
#
# The pure-Python lab needs none of this: just `python3 spam_lab.py`.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
echo "Using interpreter: $("$PY" --version 2>&1)"

# Apple Silicon needs the arm64 build of Python. Warn if we're under Rosetta.
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
  PYARCH="$("$PY" -c 'import platform; print(platform.machine())')"
  if [ "$PYARCH" != "arm64" ]; then
    echo "WARNING: this Python is $PYARCH, not arm64 -- you will not get the MPS"
    echo "         (Apple GPU) backend. Install an arm64 python3 (e.g. from"
    echo "         python.org or Homebrew) and re-run."
  fi
fi

echo "Creating virtual environment in .venv ..."
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
echo "Installing PyTorch (this is the big download) ..."
pip install -r requirements.txt

echo
echo "Checking the accelerator PyTorch found:"
python - <<'PYCHECK'
import torch
if torch.backends.mps.is_available():
    dev = "mps (Apple GPU)"
elif torch.cuda.is_available():
    dev = "cuda"
else:
    dev = "cpu"
print(f"  torch {torch.__version__}  ->  device: {dev}")
PYCHECK

echo
echo "Done. Now run:"
echo "    source .venv/bin/activate"
echo "    python spam_torch.py"
