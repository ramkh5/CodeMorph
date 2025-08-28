import os
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def render_template(env, template_name, context, output_path):
    template = env.get_template(template_name)
    with open(output_path, "w") as f:
        f.write(template.render(context))

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def load_config_from_env(DEBUG):
    """Load configuration defaults from .env file"""
    if DEBUG == 0:
        from dotenv import load_dotenv
        load_dotenv()

    return {
        "source_path": os.getenv("SOURCE_PATH"),
        "output_path": os.getenv("OUTPUT_PATH"),
        "rabbitmq_network": os.getenv("RABBITMQ_NETWORK")
    }

def main():

    import argparse

    DEBUG = 0

    env_config = load_config_from_env(DEBUG)

    parser = argparse.ArgumentParser(description="Microservice Generator Agent")
    parser.add_argument("--service-name", required=True, help="Name of the service to generate")
    parser.add_argument("--source-path", default=env_config["source_path"], help="Service source path")
    parser.add_argument("--output-path", default=env_config["output_path"], help="Output service path")
    parser.add_argument("--image-tag", default="latest", help="Docker image tag")
    parser.add_argument("--rabbitmq-network", type=str, default=env_config["rabbitmq_network"], help="RabbitMQ network name")
    parser.add_argument("--routing-key", type=str, required=False, help="RabbitMQ routing key")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    service_name = args.service_name
    source_path = Path(args.source_path).resolve()
    output_path = Path(args.output_path).resolve()
    source_service_path = source_path / args.service_name
    output_service_path = output_path / args.service_name

    ensure_dir(output_service_path)

    image_tag = args.image_tag
    routing_key = args.routing_key if args.routing_key else f"{service_name}.result"
    rabbitmq_network = args.rabbitmq_network


    # Copy all source files
    for item in source_service_path.iterdir():
        if item.is_file():
            shutil.copy(item, output_service_path / item.name)
        elif item.is_dir():
            shutil.copytree(item, output_service_path / item.name, dirs_exist_ok=True)

    # Ensure aio-pika is in requirements.txt
    req_file = output_service_path / "requirements.txt"
    if req_file.exists():
        with open(req_file, "r+") as f:
            content = f.read()
            if "aio-pika" not in content:
                f.write("\naio-pika\n")

    # Setup Jinja2
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    context = {
        "service_name": service_name,
        "image_tag": image_tag,
        "routing_key": routing_key,
        "rabbitmq_network": rabbitmq_network
    }

    # Render templates
    render_template(env, "Dockerfile.j2", context, output_service_path / "Dockerfile")
    render_template(env, "docker-compose.yml.j2", context, output_service_path / "docker-compose.yml")
    render_template(env, "service.env.j2", context, output_service_path / ".env")
    render_template(env, "asyncapi.yml.j2", context, output_service_path / "asyncapi.yml")
    render_template(env, "service_wrapper.py.j2", context, output_service_path / "service_wrapper.py")

    print(f"✅ Service {service_name} generated successfully at {output_service_path}")

if __name__ == "__main__":
    main()
