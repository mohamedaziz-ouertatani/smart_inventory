import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import PG_CONFIG

@contextmanager
def get_conn():
  conn = psycopg2.connect(
      host=PG_CONFIG["host"],
      port=PG_CONFIG["port"],
      dbname=PG_CONFIG["database"],
      user=PG_CONFIG["user"],
      password=PG_CONFIG["password"],
      sslmode=PG_CONFIG["sslmode"],
  )
  try:
    yield conn
  finally:
    conn.close()

def execute_values_insert(conn, sql: str, rows: list[tuple]):
  with conn.cursor() as cur:
    psycopg2.extras.execute_values(cur, sql, rows, page_size=10000)
  conn.commit()