# DebugAgent

Self-improving autonomous Python debugging agent.

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Fill `.env` with valid Gemini and (optionally) Langfuse keys.
4. Run tests:
   - `pytest tests -v`
5. Run agent:
   - `python -m debugagent.main run --file fixtures/bugs/01_off_by_one/buggy.py --tests fixtures/bugs/01_off_by_one/test_buggy.py`

## CLI

- `debugagent run --file <buggy.py> --tests <test_buggy.py>`
- `debugagent stats`
- `debugagent version`
- `debugagent reset`
