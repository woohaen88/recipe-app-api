#!/bin/sh

set -e

envsubst < /etc/nginx/default.conf.tpl > /etc/nginx/nginx.conf
nginx -g 'daemon off;'