# -*- coding: utf-8 -*-
import json
import time
import subprocess
import select
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

# InfluxDB connections settings
host = 'localhost'
port = 8086
user = ''
password = ''
dbname = 'rtl-433-weather-station'
station_name = '1001-s-49th-st-philadelphia'
rtl_433_packets_file = 'packets.json'
dbclient = InfluxDBClient(host, port, user, password, dbname)

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
    WeatherStationSeriesHelper(station_name=station_name, **mutate_fields(packet))
    if commit_each_line: WeatherStationSeriesHelper.commit()
    line_count += 1
    if line_count % 1000 == 0 and line_count != 0:
      print('Imported {} lines...'.format(line_count))

if db_exists(dbclient, dbname):
  dbclient.drop_database(dbname)

dbclient.create_database(dbname)

if not retention_policy_exists(dbclient, 'infinity', dbname):
  dbclient.create_retention_policy('infinity', 'INF', 1, default=True)

with open(rtl_433_packets_file, 'r') as f:
  for line in f:
    process_line(line)
# Commit any pending transactions
WeatherStationSeriesHelper.commit()

print('Batch import complete, tailing file...')

tail = subprocess.Popen([ 'tail', '-n', '1', '-F', rtl_433_packets_file ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
poll = select.poll()
poll.register(tail.stdout)
while True:
  if poll.poll(1):
    line = tail.stdout.readline()
    print(line)
    process_line(line, commit_each_line=True)
