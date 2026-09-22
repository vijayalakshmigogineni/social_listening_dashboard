# problem-intelligence

Source-by-source feasibility work. One folder per source, so each
investigation can be read on its own.

| Folder | Source | Status |
|---|---|---|
| [aapc/](aapc/) | AAPC discussion forums | Investigated — RSS + HTML paths confirmed |
| [reddit/](reddit/) | Reddit (via Apify) | Investigated + Phase 1 labelled dataset |
| [medical-billing-live/](medical-billing-live/) | Medical Billing Live forum (SMF) | Investigated — feasibility only |

Longer write-ups for Reddit live at the repo root:
`REDDIT-SOURCE-INVESTIGATION.md` and `REDDIT-APIFY-DATA-VALIDATION.md`.

## Running anything here

Scripts resolve their own paths, so run them **from inside their own folder**:

```bash
cd problem-intelligence/medical-billing-live
python mbl_access_test.py
```

The Reddit scripts read the existing Apify credential from `linkedin/.env`
at the repo root; they locate it relative to their own file, not the shell's
working directory.

## Layout notes

- `reddit/data/` and `reddit/results/` moved with the Reddit scripts, so the
  `Path(__file__).parent` lookups inside them still resolve.
- Each source folder writes its JSON output next to its scripts.
