FROM python:buster

COPY .  /src/

RUN pip install -r  /src/requirements.txt

ENV ALIYUNPAN_CONF  "/data/aliyunpan.yaml"

RUN chmod 777 /src/aliyunpan.log

WORKDIR /data/

ENTRYPOINT ["python", "/src/aliyunpan.py"]
