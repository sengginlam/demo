FROM library/python:3.13.5-bookworm
WORKDIR /server
RUN rm -rf /etc/apt/sources.list.d &&\
    cat << 'EOF' >> /etc/apt/sources.list
deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware
deb-src https://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian/ bookworm-backports main contrib non-free non-free-firmware
deb-src https://mirrors.aliyun.com/debian/ bookworm-backports main contrib non-free non-free-firmware
EOF
RUN apt-get update &&\
    apt-get install -y libgomp1 pkg-config python3-dev default-libmysqlclient-dev build-essential &&\
    rm -rf /var/lib/apt/lists/*
COPY ./src .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
CMD ["sh", "-c", "streamlit run ./server/server.py"]
