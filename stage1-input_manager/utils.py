
import os
import shutil
import subprocess
import sys
import ast
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

@dataclass
class TestResult:
    success: bool
    output_path: Path
    raw_output: str

@dataclass
class ValidationResult:
    has_result_dto: bool
    has_run: bool
    run_is_async: bool
    has_correct_return_type: bool

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def copy_valid_version(version_folder: Path, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)

    ensure_dir(dest)

    # List of original files
    original_files = ["script.py", "requirements.txt", "readme.md"]

    # Copy originals
    for fname in original_files:
        src = version_folder / fname
        if src.exists():
            shutil.copy2(src, dest / fname)

    # Copy test files (anything starting with "test_" and ending in .py)
    for test_file in version_folder.glob("test_*.py"):
        shutil.copy2(test_file, dest / test_file.name)
        
    return

def validate_script_contract(script_path: str) -> ValidationResult:
    """Validate that script.py defines ResultDto and async run() with correct return type."""
    with open(script_path, "r") as f:
        source = f.read()

    tree = ast.parse(source)

    has_result_dto = False
    has_run = False
    run_is_async = False
    has_correct_return_type = False

    for node in tree.body:
        # Look for dataclass ResultDto
        if isinstance(node, ast.ClassDef) and node.name == "ResultDto":
            has_result_dto = True

        # Look for async def run()
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            has_run = True
            run_is_async = True
            # Check annotation for AsyncGenerator[ResultDto, None]
            if node.returns:
                ann = ast.unparse(node.returns)
                if "AsyncGenerator" in ann and "ResultDto" in ann:
                    has_correct_return_type = True
                    
    return ValidationResult(
        has_result_dto=has_result_dto,
        has_run=has_run,
        run_is_async=run_is_async,
        has_correct_return_type=has_correct_return_type
    )


def detect_current_version_folder(case_path: Path) -> Path:
    versions = [int(p.name) for p in case_path.iterdir() if p.is_dir() and p.name.isdigit()]
    
    if not versions:
        # initialize "001" by copying script/requirements/readme
        vpath = case_path / "001"
        ensure_dir(vpath)

        for fname in ("script.py", "requirements.txt", "readme.md"):
            src = case_path / fname
            if src.exists():
                shutil.copy2(src, vpath / fname)

        return vpath
    
    else:
        return case_path / f"{max(versions):03d}"

def create_venv_and_install(version_path: Path) -> Tuple[Path, str]:
    venv_dir = version_path / ".venv"
    py = sys.executable
    subprocess.run([py, "-m", "venv", str(venv_dir)], check=True)
    pip = venv_dir / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    # Ensure requirements exists
    req = version_path / "requirements.txt"
    if not req.exists():
        req.write_text("", encoding="utf-8")
    # Install deps (best-effort) and pytest
    subprocess.run([str(pip), "install", "-r", str(req)], check=False)
    subprocess.run([str(pip), "install", "pytest"], check=False)
    return venv_dir, str(pip)

def run_pytest(version_path: Path, venv_dir: Path) -> TestResult:
    pytest = venv_dir / ("Scripts/pytest.exe" if os.name == "nt" else "bin/pytest")
    out_file = version_path / "test_output.txt"
    cp = subprocess.run([str(pytest), "-q", "--maxfail=20"], cwd=str(version_path), capture_output=True, text=True)
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    out_file.write_text(out, encoding="utf-8")
    return TestResult(success=cp.returncode == 0, output_path=out_file, raw_output=out)

def increment_version_folder(current: Path) -> Path:
    n = int(current.name)
    return current.parent / f"{n+1:03d}"
