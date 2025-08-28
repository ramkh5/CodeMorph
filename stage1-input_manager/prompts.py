
from textwrap import dedent

TEST_GEN_SYSTEM = dedent("""\
You are a senior Python test engineer. You produce thorough, deterministic, minimal-flakiness unit tests.
Output must be VALID JSON only, matching the schema requested by the user. Do not include explanations.
""")

TEST_GEN_USER_TEMPLATE = """\
You are given:
1) Python file `script.py` that must expose a function signature: `async def run() -> AsyncGenerator[ResultDto, None]:` and a dataclass `ResultDto` with fields already defined by the user.
2) A plain-text description in `readme.md` describing the intended behavior and usage scenarios.
3) The dependencies list `requirements.txt`.

Task: Write ONE pytest test file to thoroughly verify the behavior of `run()` and any public helpers uncovered by static reading.
Focus on observable effects, inputs/outputs, and side effects documented in `readme.md`.
If IO, network, or time are involved, mock them (no real external calls). Do not rely on environment specifics.

Return STRICT JSON with this schema:
{{
  "tests": [
    {{"path": "test_script.py", "content": "<pytest test file content>"}}
  ]
}}

Constraints:
- Use only 'pytest' and 'unittest.mock' for testing and mocking.
- Avoid time-based flakiness; use deterministic inputs.
- Assume tests run from within the same folder as script.py.
- If readme.md is vague, derive reasonable tests from code; prefer smaller, focused tests.
- When testing `run()`, use `pytest.mark.asyncio` and iterate results with:
    async for item in run():
        ...
- Assert that each yielded item is an instance of ResultDto and check its fields for correctness.

---
# FILES
## readme.md
{readme_content}

## requirements.txt
{requirements_content}

## script.py
{script_content}
"""

FIX_CODE_SYSTEM = dedent("""\
You are a senior Python engineer and build fixer. You receive failing tests, the current code, and its description.
Your job: update the code so that tests pass while aligning with the description and good engineering practices.
Always keep changes minimal, focused, and backward compatible unless a breaking change is demanded by the description.
Output must be VALID JSON only, matching the requested schema. Do not include explanations.
""")

FIX_CODE_USER_TEMPLATE = """\
You are given:
- Failing test run logs that include assertion errors, tracebacks, and stderr/stdout.
- Current files: script.py, requirements.txt, readme.md.

Task:
1) Propose and apply minimal safe code edits to fix failures and align with documented behavior.
2) If a package is clearly required or unused, adjust requirements.txt (pin if necessary).
3) If the intended behavior in readme.md needs clarification, update it minimally to reflect the changes.

Return STRICT JSON with this schema:
{{
  "script_py": "<new script.py content>",
  "requirements_txt": "<new requirements.txt content>",
  "readme_md": "<new readme.md content>"
}}

Rules:
- Preserve the required function signature: `async def run() -> AsyncGenerator[ResultDto, None]:`.
- Ensure that `run()` yields only instances of ResultDto (never raw dicts, strings, or other types).
- If `run()` produces no output, it must exit gracefully without raising.
- Avoid adding heavy dependencies unnecessarily.
- Do not introduce network calls or filesystem writes unless the tests/mock expect them.
- Keep style consistent; prefer clear, small functions.
- Ensure the module remains importable and pythonic.

---
# FAILURES (pytest output)
{failures}

---
# CURRENT readme.md
{readme_content}

# CURRENT requirements.txt
{requirements_content}

# CURRENT script.py
{script_content}
"""
