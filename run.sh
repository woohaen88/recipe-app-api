#!/bin/bash

set -e

docker-compose -f docker-compose-deploy down
docker-compose -f docker-compose-deploy up -d