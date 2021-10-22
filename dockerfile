FROM python:latest

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y wine-development && \
    apt-get clean  && \
    rm -rf /var/lib/apt/lists/*

ENV WINEARCH=win64 \
    WINEDEBUG=-all

RUN wineboot --init

VOLUME /opt/server
# WORKDIR /opt/server

COPY main.py .
# COPY config.ini .
# COPY opt opt
COPY instances instances
COPY results results
COPY results_errors results_errors

EXPOSE 9600/udp
EXPOSE 9601/tcp
EXPOSE 9602/udp
EXPOSE 9603/tcp

CMD [ "python", "main.py" ]
# CMD ["wine", "/opt/server/accServer.exe"]