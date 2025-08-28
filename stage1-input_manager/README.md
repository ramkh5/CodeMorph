
# Input Manager Agent (Stage 1)

A self-evolving validation loop for Python cases. It manages versioned folders, generates tests with OpenAI, runs them in an isolated virtual environment, and asks OpenAI to fix code until tests pass or a max attempt limit is reached.

## Folder Contract

```
<workspace>/<case_name>/
    script.py           # must define run() -> None
    requirements.txt
    readme.md
    001/ 002/ 003/...   # versioned subfolders (3-digit)
```

On first run (no version subfolders), the agent creates `001/` and copies the three root files into it.

## Success Output

When all tests pass, the agent copies the **current version folder** to:
```
<valid_cases>/<case_name>/
```

## Failure Output

If `--max-attempts` is reached with failing tests, the agent stops with a clear error message.

## OpenAI Usage

Two interactions:
1. **Test generation**: produce a pytest test file that covers the scenarios from `readme.md` and code from `script.py`.
2. **Code fix**: given failures + code + description, return updated `script.py`, `requirements.txt`, `readme.md`.

Responses are requested in strict JSON (see `prompts.py`) and validated before writing.

## Install

- Python 3.10+
- (Recommended) A Python virtual environment for the agent itself.
- Docker is **not** required for this stage.
- Set your key:
  ```bash
  export OPENAI_API_KEY=sk-...  # required if you call the API
  ```
- Install dependencies for the agent:
  ```bash
  pip install -r requirements-agent.txt
  ```

## Run

```bash
python input_manager.py   --workspace /path/to/workspace   --case-name demo_case   --valid-cases /path/to/valid   --max-attempts 4   --model gpt-4o-mini
```

Flags:
- `--dry-run` → skip OpenAI calls, create placeholders
- `--verbose` → print more logs

## Notes

- The agent creates an isolated venv inside each version folder: `<version>/.venv/`.
- It ensures `pytest` is available inside the venv (installed if not present).
- Test logs are written to `<version>/test_output.txt`.
- You can tailor prompts and strict schemas in `prompts.py`.
