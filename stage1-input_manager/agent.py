
#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

from prompts import TEST_GEN_SYSTEM, TEST_GEN_USER_TEMPLATE, FIX_CODE_SYSTEM, FIX_CODE_USER_TEMPLATE
from utils import (
    copy_valid_version, ensure_dir, copy_tree, detect_current_version_folder,
    create_venv_and_install, run_pytest, increment_version_folder,
    TestResult, validate_script_contract,
)

def load_case_files(folder: Path):
    script = (folder / "script.py").read_text(encoding="utf-8")
    reqs = (folder / "requirements.txt").read_text(encoding="utf-8") if (folder / "requirements.txt").exists() else ""
    readme = (folder / "readme.md").read_text(encoding="utf-8") if (folder / "readme.md").exists() else ""
    return script, reqs, readme

def write_tests(version_folder: Path, tests_dict):
    for item in tests_dict.get("tests", []):
        path = version_folder / item["path"]
        ensure_dir(path.parent)
        path.write_text(item["content"], encoding="utf-8")

def write_fixed_files(dest_folder: Path, fix_dict):
    (dest_folder / "script.py").write_text(fix_dict["script_py"], encoding="utf-8")
    (dest_folder / "requirements.txt").write_text(fix_dict["requirements_txt"], encoding="utf-8")
    (dest_folder / "readme.md").write_text(fix_dict["readme_md"], encoding="utf-8")

def load_config_from_env(DEBUG):
    """Load configuration defaults from .env file"""
    if DEBUG == 0:
        from dotenv import load_dotenv
        load_dotenv()

    return {
        "workspace": os.getenv("WORKSPACE_PATH"),
        "valid_cases": os.getenv("VALID_CASES_PATH"),
        "max_attempts": int(os.getenv("MAX_ATTEMPTS", "3")),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", 0.2)),
    }

def main():
    import argparse

    DEBUG = 0

    env_config = load_config_from_env(DEBUG)

    parser = argparse.ArgumentParser(description="Input Manager Agent")
    parser.add_argument("--case-name", required=True, help="Case name folder under workspace")
    parser.add_argument("--workspace", default=env_config["workspace"], help="Workspace path")
    parser.add_argument("--valid-cases", default=env_config["valid_cases"], help="Valid cases path")
    parser.add_argument("--max-attempts", type=int, default=env_config["max_attempts"], help="Max iterations before giving up")
    parser.add_argument("--model", default=env_config["model"], help="OpenAI model name")
    parser.add_argument("--temperature", type=float, default=env_config["temperature"], help="OpenAI temperature")
    parser.add_argument("--dry-run", action="store_true", help="Run without calling OpenAI")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    valid_cases = Path(args.valid_cases).resolve()
    case_path = workspace / args.case_name
    ensure_dir(case_path)
    ensure_dir(valid_cases)

    # Validate script contract
    validation_result = validate_script_contract(case_path / "script.py")
    if not validation_result.has_correct_return_type:
        print("❌ run() must return AsyncGenerator[ResultDto, None]")
        return

    if not validation_result.has_result_dto:
        print("❌ script.py must define a dataclass named ResultDto")
        return

    if not validation_result.has_run or not validation_result.run_is_async:
        print("❌ script.py must define an async def run() function")
        return
    
    if args.verbose:
        print("✅ script.py contract validated: run() -> AsyncGenerator[ResultDto, None]")

    # Lazy import to allow --dry-run without openai installed
    client = None
    if not args.dry_run:
        from openai_client import OpenAIClient
        client = OpenAIClient(model=args.model, temperature=args.temperature)

    attempt = 0
    while attempt < args.max_attempts:
        attempt += 1
        # 1) detect current version (initialize if none)
        version_folder = detect_current_version_folder(case_path)
        if args.verbose:
            print(f"[attempt {attempt}] Working folder: {version_folder}")

        # 2) Generate tests
        script, reqs, readme = load_case_files(version_folder)
        if args.dry_run:
            write_tests(version_folder, {"tests":[{"path":"test_script.py","content":"def test_import():\n    import script\n"}]})
        else:
            test_prompt = TEST_GEN_USER_TEMPLATE.format(
                readme_content=readme, requirements_content=reqs, script_content=script
            )
            tests_json = client.complete_json(TEST_GEN_SYSTEM, test_prompt)
            write_tests(version_folder, tests_json)

        # 3) Create sandbox & install deps
        venv_dir, pip = create_venv_and_install(version_folder)

        # 4) Run tests
        result: TestResult = run_pytest(version_folder, venv_dir)
        if args.verbose:
            print(result.raw_output[:2000])

        # 5) Evaluate
        if result.success:
            # copy to valid cases and exit success
            dest = valid_cases / args.case_name
            copy_valid_version(version_folder, dest)

            if args.verbose:
                print(f"✅ Success. Copied validated case to: {dest}")
                
            return

        if attempt >= args.max_attempts:
            print(f"❌ Max attempts reached ({args.max_attempts}). See {result.output_path}")
            return

        # else, request a fix from OpenAI and advance version
        if args.dry_run:
            fix_dict = {
                "script_py": script, 
                "requirements_txt": reqs, 
                "readme_md": readme
            }
        else:
            fix_prompt = FIX_CODE_USER_TEMPLATE.format(
                failures=result.raw_output,
                readme_content=readme,
                requirements_content=reqs,
                script_content=script
            )
            fix_dict = client.complete_json(FIX_CODE_SYSTEM, fix_prompt)

        next_version = increment_version_folder(version_folder)
        ensure_dir(next_version)
        write_fixed_files(next_version, fix_dict)
        if args.verbose:
            print(f"→ Wrote next version: {next_version}")

    print("❌ Exiting without success.")

if __name__ == "__main__":
    main()
