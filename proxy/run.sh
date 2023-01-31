#!/bin/sh

set -e

envsubst < /etc/nginx/nginx.conf.defaults > /etc/nginx/nginx.conf