FROM library/mysql:latest
ENV MYSQL_ROOT_PASSWORD=123456
COPY ./build/mysql/mysql_init.sql /docker-entrypoint-initdb.d/