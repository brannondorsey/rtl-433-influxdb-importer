# RTL_433 InfluxDB Importer

Import data from an Acurite 5-in-1 weather station into InfluxDB.

```bash
# Create the .env and populate it with values
cp .env.example .env
nano .env
```

```bash
# Launch both the influxdb instance and the rtl-433-importer services
docker-compose up -d
```

## Post Init

Once the data has been imported, edit `docker-compose.yaml` and comment out the `--create-and-overwrite-db` and `--backfill` CLI arguments so that the data isn't overwritten each time the `rtl-433-importer` container restarts.

```bash
## Comment out these bottom two lines once the database has been created and filled
## with data from INPUT_FILE. Otherwise the database will be recreated each time
## the container restarts!
#- --create-and-overwrite-db
#- --backfill
```

From now on, each time the container comes up it will start tailing `$INPUT_FILE` without re-creating the database and backfilling the entire contents of the file.

## Multi-host

Alternatively, you can run influxdb and the rtl-433-importer agent on different machines. Just make sure the `INFLUXDB_HOST` env var in `.env` points to the correct influxdb host. In this case, uncomment the `network_mode: host` line in the `rtl-433-importer` service in `docker-compose.yaml`.

```bash
[host1] $ docker-compose up -d influxdb
[host2] $ docker-compose up -d rtl-433-importer
```

The `rtl-433-importer` service monitors a JSON file output from `rtl_433` and imports it into an InfluxDB database named `rtl_433_weather_station`.
