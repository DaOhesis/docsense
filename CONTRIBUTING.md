# How we work

## Git workflow
1. `git checkout main && git pull`
2. `git checkout -b feature/<area>-<short-description>` (e.g. `feature/ocr-paddle`)
3. Commit small and often, with clear messages: `ocr: add PaddleOCR wrapper`
4. `pytest` locally, then push and open a Pull Request
5. At least one teammate reviews (the lead reviews anything touching `schemas.py` or `pipeline.py`)
6. Squash-merge into `main`, then delete the branch

## Rhythm
- Two 15-minute syncs per week: what I did / what I'm doing / what's blocking me
- One 1-hour weekly demo: run the full pipeline on the shared test set
- Flag blockers in the group chat the same day, not at the next meeting

## Code conventions
- Python 3.10+, type hints on public functions, short docstrings
- Keep stage logic inside its own module; `pipeline.py` stays thin
- Don't commit datasets, model weights or `.env`

## Definition of done for a task
- Works on at least a few real samples from `data/samples/`
- Has at least one test in `tests/`
- Docstring/README note if behaviour is non-obvious
