# Spam-classification lab. Two paths: pure Python (no install) and PyTorch.
.PHONY: run torch setup classify clean help
.DEFAULT_GOAL := help

help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  make %-10s %s\n", $$1, $$2}'

run:  ## train & evaluate all four models with pure-Python (no dependencies)
	python3 spam_lab.py

setup:  ## create .venv and install PyTorch (MacBook Pro)
	./setup_macbook.sh

torch:  ## train & evaluate the PyTorch models (run `make setup` first)
	python3 spam_torch.py

classify:  ## score one message, e.g. make classify MSG="win a free prize now"
	python3 spam_lab.py --classify "$(MSG)"

clean:  ## remove the virtualenv and Python caches
	rm -rf .venv __pycache__
