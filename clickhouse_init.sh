#!/bin/bash

if [ -f ./smartbozor/.env ]; then
  set -a
  . ./smartbozor/.env
  set +a
fi

SQL1="CREATE DATABASE smartbozor"

SQL2="CREATE TABLE smartbozor.scan
(
  scan_at DateTime,
  object_type CHAR(1),
  object_id Int64,
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(scan_at)
ORDER BY (scan_at)
PRIMARY KEY scan_at;"

if [ -f /usr/bin/clickhouse-client ]; then
  /usr/bin/clickhouse-client --password="$CLICKHOUSE_PASSWORD" --query="$SQL1"
  /usr/bin/clickhouse-client --password="$CLICKHOUSE_PASSWORD" --query="$SQL2"
else
  CONTAINER=$(docker ps -a --filter "ancestor=clickhouse/clickhouse-server:latest-alpine" --format "{{.ID}}")
   docker exec -t $CONTAINER clickhouse-client --password=$CLICKHOUSE_PASSWORD --query="$SQL1"
   docker exec -t $CONTAINER clickhouse-client --password=$CLICKHOUSE_PASSWORD --query="$SQL2"
fi