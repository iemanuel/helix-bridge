ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Install Python and build deps
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        linux-headers \
        python3-dev \
        libffi-dev \
    && apk add --no-cache \
        python3 \
        py3-pip \
    && pip3 install --no-cache-dir --break-system-packages \
        paho-mqtt==2.1.0 \
        pyserial==3.5 \
        pyyaml==6.0.2 \
        aiohttp \
        pysolarmanv5==3.0.6 \
        goodwe==0.4.10 \
        huawei-solar==3.0.6 \
        sunsynk==0.9.3 \
    && apk del .build-deps \
    && rm -rf /root/.cache

# Copy the bridge application
COPY app/ /app/

# Copy the run script
COPY run.sh /
RUN chmod a+x /run.sh

WORKDIR /app

CMD ["/run.sh"]
