FROM nginx:latest
LABEL maintainer="woohaen88@gmail.com"

COPY ./default.conf.tpl /etc/nginx/default.conf.tpl
# COPY ./uwsgi_params /etc/nginx/uwsgi_params
COPY ./run.sh /run.sh

ENV LISTEN_PORT=80
ENV APP_HOST=app
ENV APP_PORT=8000

USER root

RUN mkdir -p /vol/static && \
    chmod 755 /vol/static && \
    chmod +x /run.sh



VOLUME /vol/static

CMD [ "/run.sh" ]