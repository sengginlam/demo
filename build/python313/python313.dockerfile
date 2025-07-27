FROM python:3.13-slim
WORKDIR /server
RUN printf "" > /etc/apt/sources.list \
    && cat << 'EOF' >> /etc/apt/sources.list \
    deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse \
    deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse \
    deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse \
    deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse \
    EOF\
    &&apt-get update \
    && apt-get install -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY ./src .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["sh", "-c", "python ./mysql_init.py && streamlit run ./server/server.py"]