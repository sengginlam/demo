FROM mysql:8
ENV MYSQL_ROOT_PASSWORD=123456
COPY ./mysql_init.sql /docker-entrypoint-initdb.d/