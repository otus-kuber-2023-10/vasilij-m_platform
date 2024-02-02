FROM nginx:1.20

ARG NGINX_UID=1001
ARG NGINX_GID=1001

RUN usermod -u $NGINX_UID nginx \
  && groupmod -g $NGINX_GID nginx \
  && chown -R nginx /var/cache/nginx \
  && sed -i 's,/var/run/nginx.pid,/tmp/nginx.pid,' /etc/nginx/nginx.conf \
  && rm /etc/nginx/conf.d/default.conf \
  && mkdir /app \
  && chown nginx /app

COPY web.conf /etc/nginx/conf.d/web.conf
USER nginx
EXPOSE 8000
