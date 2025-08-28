import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime

def setup_logger(log_dir: Path, name: str, filename: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_dir / filename)
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    return result.returncode, result.stdout, result.stderr

def deploy_service(service_path: str, logs_path: str):
    service_path = Path(service_path).resolve()

    # Load environment
    log_dir = Path(logs_path) / service_path.name
    op_logger = setup_logger(log_dir, "operations", "operations.log")
    err_logger = setup_logger(log_dir, "errors", "errors.log")

    op_logger.info(f"Starting deployment process for {service_path.name}")

    # --- Pre-deployment checks ---
    required_files = ["Dockerfile", "docker-compose.yml", ".env", "requirements.txt"]
    for f in required_files:
        if not (service_path / f).exists():
            msg = f"Missing required file: {f}"
            err_logger.error(msg)
            op_logger.error("Deployment failed due to missing file.")
            return

    # Validate docker-compose syntax
    code, out, err = run_command("docker compose config", cwd=service_path)
    if code != 0:
        err_logger.error(f"docker-compose config failed:\n{err}")
        op_logger.error("Deployment aborted due to invalid docker-compose.yml")
        return
    op_logger.info("docker-compose.yml validated successfully")

    # Validate Python syntax
    script_file = service_path / "script.py"
    if script_file.exists():
        code, out, err = run_command(f"python -m py_compile {script_file}")
        if code != 0:
            err_logger.error(f"Python syntax error:\n{err}")
            op_logger.error("Deployment aborted due to Python syntax errors")
            return
        op_logger.info("Python syntax validated successfully")

    # Validate dependencies
    code, out, err = run_command(f"pip install --dry-run -r requirements.txt", cwd=service_path)
    if code != 0:
        err_logger.error(f"Dependency resolution failed:\n{err}")
        op_logger.error("Deployment aborted due to dependency errors")
        return
    op_logger.info("Dependencies validated successfully")

    # --- Deployment ---
    op_logger.info("Starting Docker deployment...")
    code, out, err = run_command("docker compose up -d --build", cwd=service_path)
    if code != 0:
        err_logger.error(f"Docker deployment failed:\n{err}")
        op_logger.error("Deployment failed during docker compose up")
        return

    op_logger.info(f"Deployment succeeded for {service_path.name}")
    op_logger.info(out)

def load_config_from_env(DEBUG):
    """Load configuration defaults from .env file"""
    if DEBUG == 0:
        from dotenv import load_dotenv
        load_dotenv()

    return {
        "source_path": os.getenv("SOURCE_PATH"),
        "logs_path": os.getenv("DEPLOY_LOGS_PATH")
    }

if __name__ == "__main__":
    import argparse

    DEBUG = 0

    env_config = load_config_from_env(DEBUG)
    
    parser = argparse.ArgumentParser(description="Deploy a microservice with validation")
    parser.add_argument("service_path", type=str, default=env_config["service_path"], help="Path to the service folder to deploy")
    args = parser.parse_args()
    deploy_service(args.service_path, env_config["logs_path"])
