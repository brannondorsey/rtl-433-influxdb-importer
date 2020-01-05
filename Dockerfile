FROM python:3.7-alpine
WORKDIR /root
COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY ./influxdb_import.py .
CMD ["python", "influxdb_import.py"]
