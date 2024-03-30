from influxdb_client import InfluxDBClient
import os

def fluxQuery():
  """Inject an influx DB client"""

  dburl = os.environ["INFLUX_SERVER"]
  token = os.environ["INFLUX_TOKEN"]
  org = os.environ["INFLUX_ORG"]
  client = InfluxDBClient(url=dburl, token=token, org=org, timeout=60000)

  return client.query_api()
