
#  DOCKER CONTROL

COMPOSE = docker compose -f docker/docker-compose.yml

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f connect

# Start all services (Kafka, Zookeeper, Kafka Connect) in background
# Stop and remove all containers (clean reset)
# Show status of running containers
# Stream logs from Kafka Connect (most common place for failures  -f: follows the logs in real time )


#  KAFKA TOPIC MANAGEMENT


# Creating required topics for the pipeline
# - traffic.raw.events → main data stream
# - traffic.dlq → dead letter queue for failed messages
create-topics:
	# Runs Kafka CLI inside the Kafka container
	# localhost:9092 works because Docker maps container port to host port, where Kafka broker is exposed
	# || true prevents failure if topic already exists (idempotent)
	docker exec -it kafka kafka-topics --create \
	--topic traffic.raw.events \
	--bootstrap-server localhost:9092 || true

	docker exec -it kafka kafka-topics --create \
	--topic traffic.dlq \
	--bootstrap-server localhost:9092 || true

# List all topics (quick verification step)
list-topics:
	docker exec -it kafka kafka-topics --list \
	--bootstrap-server localhost:9092


 
#  KAFKA CONNECT (PIPELINE CONTROL)


# Check which connectors are currently registered
# Kafka Connect exposes a REST API at localhost:8083
connector-status:
	curl http://localhost:8083/connector-plugins
connector-status1:
	curl http://localhost:8083/connectors/snowflake-sink/status
#connector alive and healthy?
# Registers (creates) a connector using JSON config
# This activates the pipeline: Kafka → Snowflake

#Kafka Connect is a running service, and the JSON config is what tells it
# exactly what data to move, from where, to where, and how
# What happens after this runs:
# 1. Kafka Connect receives the request
# 2. It parses the JSON config
# 3. It creates a connector instance (a running job)
# 4. That job starts:
#       Kafka topic → Kafka Connect → Snowflake

# Important:
# - If this step is NOT run, no data will move (pipeline is inactive)

# Breakdown:
# curl
#   → CLI tool used to send HTTP requests

# -X POST
#   → HTTP method "POST" = create something new on the server

# http://localhost:8083/connectors
#   → Kafka Connect REST API endpoint
#   → "connectors" is the resource where connectors are created/listed

# -H "Content-Type: application/json"
#   → Tells Kafka Connect that we are sending JSON data

# -d @docker/kafka-connect/snowflake-connector.json
#   → Sends the contents of this JSON file as the request body
#   → This file contains:
#       - Kafka topic to read from
#       - Snowflake connection details
#       - Authentication (private key, account, etc.)


register-connector:
	curl -X POST http://localhost:8083/connectors \
	-H "Content-Type: application/json" \
	-d @docker/snowflake-connector.json

# View last 50 lines of Kafka Connect logs (useful for debugging failures)
connector-logs:
	docker logs kafka-connect | tail -50



#  TEST PIPELINE (END-TO-END)


# Sends a test JSON message into Kafka
# Flow:
#  echo → kafka-console-producer → Kafka topic → Kafka Connect → Snowflake
test-pipeline:
	# echo creates a sample event
	# pipe (|) sends it into Kafka producer CLI
	# -i allows input streaming into container
	echo '{"route_id":"test","live_seconds":1800,"base_seconds":900}' | \
	docker exec -i kafka kafka-console-producer \
	--topic traffic.raw.events \
	--bootstrap-server localhost:9092









