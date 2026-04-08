from debugagent.sandbox.subprocess_backend import SubprocessSandbox


def test_sandbox_pass_case():
    sandbox = SubprocessSandbox()
    code = "def add(a,b):\n    return a+b\n"
    tests = "from solution import add\n\ndef test_add():\n    assert add(1,2)==3\n"
    result = sandbox.run(code, tests, timeout_s=15)
    assert result.exit_code == 0


def test_sandbox_fail_case():
    sandbox = SubprocessSandbox()
    code = "def add(a,b):\n    return a-b\n"
    tests = "from solution import add\n\ndef test_add():\n    assert add(1,2)==3\n"
    result = sandbox.run(code, tests, timeout_s=15)
    assert result.exit_code != 0


def test_sandbox_timeout_case():
    sandbox = SubprocessSandbox()
    code = "def run_forever():\n    while True:\n        pass\n"
    tests = "from solution import run_forever\n\ndef test_timeout():\n    run_forever()\n"
    result = sandbox.run(code, tests, timeout_s=1)
    assert result.timed_out
