# Nitrogen-Surplus-Focused-Restructuring

This repository currently contains the original notebook-based workflow together with a script-based reproduction layer in [`repro/`](./repro).

The clean code path is being built incrementally so we can migrate the analysis out of Jupyter without changing the scientific logic prematurely.

To install the baseline Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

To export the current normalized trade-stage inputs and derived tables outside the notebooks:

```bash
python3 -m repro trade-stage
```
