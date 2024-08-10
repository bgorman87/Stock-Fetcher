#!/bin/bash

export $(grep -v '^#' .env.dev | xargs)

docker compose -f docker-compose.yml up --build
