# -*- coding: utf-8 -*-
import os
import json
import subprocess
import select
import argparse
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

def parse_args():
    parser = argparse.ArgumentParser(
        description='Import Acurite 5-in-1 weather data into influxdb from an rtl_433 JSON file')
    parser.add_argument('--host', type=str, required=False,
                        default='localhost',
                        help='hostname of InfluxDB http API')
    parser.add_argument('--port', type=int, required=False, default=8086,
                        help='port of InfluxDB http API')
    parser.add_argument('--user', type=str, required=False,
                        default='root',
                        help='InfluxDB username')
    parser.add_argument('--password', type=str, required=True,
                        help='InfluxDB password')
    parser.add_argument('--database', type=str, required=False,
                        default='rtl_433_weather_station',
                        help='Database name. If a database already by this name exists it will be deleted and replaced.')
    parser.add_argument('--station', type=str, required=True,
                        help='The name of the rtl_433 listening station to associate these weather samples with. Usually a location or address. This is a user defined value and can be set to any string.')
    parser.add_argument('--input', type=str, required=True,
                        help='A path to the file containing rtl_433 JSON output to be imported to influxdb')
    parser.add_argument('--create-and-overwrite-db', action='store_true', required=False,
                        help='Create the database, overwriting a database by the same name if it already exists')
    parser.add_argument('--backfill', action='store_true', required=False,
                        help='Backfill the database with the entire contents of the --input file. Usually used when initializing a database from a collection of historical weather data with --create-and-overwrite-db.')
    return parser.parse_args()

args = parse_args()
dbclient = InfluxDBClient(args.host, args.port, args.user, args.password, args.database)

class WeatherStationSeriesHelper(SeriesHelper):
  class Meta:
    client = dbclient
    series_name = 'weather_sample'
    fields = ['wind_speed_kph', 'wind_dir_deg', 'temperature_F', 'humidity', 'rain_inch', 'battery_ok']
    tags = ['station_name', 'model', 'sensor_id', 'channel']
    bulk_size = 10000
    autocommit = True

def db_exists(dbclient, name):
  return len(list(filter(lambda db: db['name'] == name, dbclient.get_list_database()))) > 0

def retention_policy_exists(dbclient, policy_name, db_name):
  return len(list(filter(lambda policy: policy['name'] == policy_name, dbclient.get_list_retention_policies(db_name)))) > 0

def mutate_fields(packet):
  if 'message_type' in packet: del packet['message_type']
  if 'sequence_num' in packet: del packet['sequence_num']
  packet['battery_ok'] = 1 if 'battery' in packet and packet['battery'] == 'OK' else 0
  if 'battery' in packet: del packet['battery']
  return packet

line_count = 0
def process_line(line, commit_each_line=False):
  global line_count
  try: packet = json.loads(line)
  except: return
  if 'model' in packet and packet['model'] == 'Acurite 5n1 sensor':
    WeatherStationSeriesHelper(station_name=args.station, **mutate_fields(packet))
    if commit_each_line: WeatherStationSeriesHelper.commit()
    line_count += 1
    if line_count % 1000 == 0 and line_count != 0:
      print('Imported {} lines...'.format(line_count))

if not os.path.exists(args.input):
  print('Error: --input file does not exist.')
  exit(1)

if args.create_and_overwrite_db:
  if db_exists(dbclient, args.database):
    print('Droping existing database "{}"'.format(args.database))
    dbclient.drop_database(args.database)
  print('Creating new database "{}"'.format(args.database))
  dbclient.create_database(args.database)
  print('Creating retention policy')
  if not retention_policy_exists(dbclient, 'infinity', args.database):
    dbclient.create_retention_policy('infinity', 'INF', 1, default=True)

if args.backfill:
  print('Backfilling "{}" via batch imports'.format(args.input))
  with open(args.input, 'r') as f:
    for line in f:
      process_line(line)
  # Commit any pending transactions
  WeatherStationSeriesHelper.commit()

print('Tailing file "{}"...'.format(args.input))
tail = subprocess.Popen([ 'tail', '-n', '1', '-F', args.input ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
poll = select.poll()
poll.register(tail.stdout)
while True:
  if poll.poll(1):
    line = tail.stdout.readline()
    print(line)
    process_line(line, commit_each_line=True)
