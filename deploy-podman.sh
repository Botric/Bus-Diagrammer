#!/bin/bash
# Bus Diagrammer Podman Deployment Script
# This script builds and deploys the Bus Diagrammer application using Podman

CONTAINER_NAME="bus-diagrammer"
IMAGE_NAME="bus-diagrammer:latest"
PORT="5620"
HOST_PORT="5620"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Function to check if container exists
container_exists() {
    podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to check if container is running
container_running() {
    podman ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -s, --stop      Stop and remove the container"
    echo "  -r, --restart   Restart the container"
    echo "  -l, --logs      Show container logs"
    echo "  --status        Show container status"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Without options, the script will build and deploy the application"
}

# Parse command line arguments
case "$1" in
    -s|--stop)
        echo -e "${YELLOW}Stopping Bus Diagrammer container...${NC}"
        if container_exists; then
            podman stop "$CONTAINER_NAME" 2>/dev/null
            podman rm "$CONTAINER_NAME" 2>/dev/null
            echo -e "${GREEN}Container stopped and removed.${NC}"
        else
            echo -e "${YELLOW}Container does not exist.${NC}"
        fi
        exit 0
        ;;
    -l|--logs)
        echo -e "${YELLOW}Showing logs for Bus Diagrammer container...${NC}"
        if container_exists; then
            podman logs -f "$CONTAINER_NAME"
        else
            echo -e "${RED}Container does not exist.${NC}"
        fi
        exit 0
        ;;
    --status)
        echo -e "${YELLOW}Bus Diagrammer Container Status:${NC}"
        if container_exists; then
            podman ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            echo -e "\n${YELLOW}Container details:${NC}"
            podman inspect "$CONTAINER_NAME" --format "{{.State.Status}}"
        else
            echo -e "${RED}Container does not exist.${NC}"
        fi
        exit 0
        ;;
    -r|--restart)
        echo -e "${YELLOW}Restarting Bus Diagrammer container...${NC}"
        if container_running; then
            podman restart "$CONTAINER_NAME"
            echo -e "${GREEN}Container restarted.${NC}"
        else
            echo -e "${YELLOW}Container is not running. Starting fresh deployment...${NC}"
        fi
        ;;
    -h|--help)
        show_usage
        exit 0
        ;;
    "")
        # No arguments, proceed with deployment
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        show_usage
        exit 1
        ;;
esac

# Main deployment process
echo -e "${CYAN}=== Bus Diagrammer Podman Deployment ===${NC}"
echo -e "${GREEN}Building and deploying Bus Diagrammer application...${NC}"

# Stop and remove existing container if it exists
if container_exists; then
    echo -e "${YELLOW}Stopping existing container...${NC}"
    podman stop "$CONTAINER_NAME" 2>/dev/null
    podman rm "$CONTAINER_NAME" 2>/dev/null
fi

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"
podman build -t "$IMAGE_NAME" .

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to build image!${NC}"
    exit 1
fi

# Create and start the container
echo -e "${YELLOW}Creating and starting container...${NC}"
podman run -d \
    --name "$CONTAINER_NAME" \
    -p "$HOST_PORT:$PORT" \
    --restart unless-stopped \
    -v "$(pwd)/srt_database.json:/home/appuser/app/srt_database.json:Z" \
    "$IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start container!${NC}"
    exit 1
fi

# Wait a moment for the container to start
sleep 3

# Check if container is running
if container_running; then
    echo -e "${GREEN}=== Deployment Successful! ===${NC}"
    echo -e "${CYAN}Bus Diagrammer is now running at: http://localhost:$HOST_PORT${NC}"
    echo -e "${GRAY}Container name: $CONTAINER_NAME${NC}"
    echo -e "\n${YELLOW}Useful commands:${NC}"
    echo -e "${GRAY}  View logs:    ./deploy-podman.sh --logs${NC}"
    echo -e "${GRAY}  Check status: ./deploy-podman.sh --status${NC}"
    echo -e "${GRAY}  Restart:      ./deploy-podman.sh --restart${NC}"
    echo -e "${GRAY}  Stop:         ./deploy-podman.sh --stop${NC}"
else
    echo -e "${RED}Failed to start container!${NC}"
    echo -e "${YELLOW}Checking logs for errors...${NC}"
    podman logs "$CONTAINER_NAME"
    exit 1
fi
