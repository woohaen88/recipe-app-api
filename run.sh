#!/bin/bash

set -e

docker-compose -f docker-compose-deploy.yml down
docker-compose -f docker-compose-deploy.yml up -d