import asyncio
import aio_pika
import os
import json
import logging
from pathlib import Path
from script import run

# Setup logs
logs_dir = os.getenv("LOGS_DIR", "./logs")
logs_level = logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
Path(logs_dir).mkdir(parents=True, exist_ok=True)
msg_log = logging.getLogger("messages")
srv_log = logging.getLogger("service")
msg_handler = logging.FileHandler(Path(logs_dir) / "messages.log")
srv_handler = logging.FileHandler(Path(logs_dir) / "service.log")
msg_log.addHandler(msg_handler)
srv_log.addHandler(srv_handler)
msg_log.setLevel(logs_level)
srv_log.setLevel(logs_level)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
ROUTING_KEY = os.getenv("ROUTING_KEY", "result")


if not callable(run):
    raise RuntimeError("script.run must be callable")
if not is_dataclass(ResultDto):
    raise RuntimeError("script.ResultDto must be a dataclass")

url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
exchange_name = os.getenv("RABBITMQ_EXCHANGE", "events")
exchange_type = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")
routing_key = os.getenv("RABBITMQ_ROUTING_KEY", "case.resultdto")
publish_confirm = _env_bool("RABBITMQ_PUBLISH_CONFIRM", True)
mandatory = _env_bool("RABBITMQ_MANDATORY", True)



async def main():
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            channel = await connection.channel()
            exchange = await channel.declare_exchange("results", aio_pika.ExchangeType.TOPIC)
            srv_log.info("Connected to RabbitMQ")

            async for result in run():
                message = {
                    "service": os.getenv("SERVICE_NAME", "unknown"),
                    "data": result.__dict__,
                }
                body = json.dumps(message).encode()
                await exchange.publish(aio_pika.Message(body=body), routing_key=ROUTING_KEY)
                msg_log.info(message)
        except Exception as e:
            srv_log.error(f"Error: {e}, reconnecting in 5s")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
