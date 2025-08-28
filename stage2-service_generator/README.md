# Stage 2 Agent

This agent converts a validated Python service (with `run()`) into a RabbitMQ microservice.

## Steps
1. Reads service source from SOURCE_PATH/<service_name>
2. Copies files into VALID_SERVICE_PATH/<service_name>
3. Generates:
   - Dockerfile
   - docker-compose.yml
   - .env file
   - AsyncAPI spec
   - service_wrapper.py
4. Appends aio-pika to requirements.txt if not present
5. Creates RabbitMQ compose & env under VALID_SERVICE_PATH/rabbitmq

See README inside for usage instructions.
