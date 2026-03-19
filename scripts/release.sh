#!/bin/bash
set -e

# Default values
IMAGE_NAME="ghcr.io/kagesenshi/smidir"
TAG="latest"

# Check for custom tag from argument
if [ ! -z "$1" ]; then
    TAG=$1
fi

FULL_IMAGE="${IMAGE_NAME}:${TAG}"

# Determine container tool (podman or docker)
if command -v podman >/dev/null 2>&1; then
    CONTAINER_TOOL="podman"
elif command -v docker >/dev/null 2>&1; then
    CONTAINER_TOOL="docker"
else
    echo "Error: Neither podman nor docker found."
    exit 1
fi

echo "Using ${CONTAINER_TOOL} to build and push ${FULL_IMAGE}..."

# Build the image
# We build with the local name 'smidir' first, then tag it for GHCR
${CONTAINER_TOOL} build -t smidir .

# Tag the image for GHCR
${CONTAINER_TOOL} tag smidir ${FULL_IMAGE}

# Push the image
echo "Pushing ${FULL_IMAGE}..."
${CONTAINER_TOOL} push ${FULL_IMAGE}

echo "Successfully released ${FULL_IMAGE}"
