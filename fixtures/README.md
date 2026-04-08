# Fixture Library

Each bug fixture folder contains:
- `buggy.py` (intentionally wrong implementation)
- `test_buggy.py` (failing tests for the buggy code)

To add a new fixture:
1. Create `fixtures/bugs/<NN_name>/`
2. Add `buggy.py`
3. Add `test_buggy.py`
4. Verify the tests fail before running the agent.
