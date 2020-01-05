# RTL_433 InfluxDB Importer

Import data from an Acurite 5-in-1 weather station into InfluxDB.

```bash
# Create the .env and populate it with values
cp .env.example .env
nano .env

# Launch both the influxdb instance and the rtl-433-importer services
docker-compose up -d
```

Alternatively, you can run influxdb and the rtl-433-importer agent on different machines. Just make sure the `INFLUXDB_HOST` env var in `.env` points to the correct influxdb host.

```bash
[host1] $ docker-compose up -d influxdb
[host2] $ docker-compose up -d rtl-433-importer
```

The `rtl-433-importer` service monitors a JSON file output from `rtl_433` and imports it into an InfluxDB database named `rtl_433_weather_station`.
