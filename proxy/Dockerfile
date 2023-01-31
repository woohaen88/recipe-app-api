FROM nginx:latest
LABEL maintainer="woohaen88@gmail.com"

COPY ./nginx.conf.defaults /etc/nginx/nginx.conf.defaults
COPY ./run.sh /run.sh

ENV LISTEN_PORT=80
ENV APP_HOST=app
ENV APP_PORT=8000

USER root

RUN mkdir -p /vol/static && \
    chmod 755 /vol/static && \
    chmod +x /run.sh && \
    sh -c /run.sh

VOLUME /vol/static

CMD ["nginx", "-g", "daemon off;"]