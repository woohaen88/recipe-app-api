worker_processes auto;

events {

}

http {
    server {
        listen ${LISTEN_PORT};

        include   mime.types;

        location /static {
            alias /vol/static;
        }

        location /media {
            alias /vol/media;
        }

        location / {
            proxy_pass              http://${APP_HOST}:${APP_PORT};
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        client_max_body_size    10M;
    }
}
