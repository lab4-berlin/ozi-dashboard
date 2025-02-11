from dagster import Definitions
from etl.etl_load_stats_1d import etl_load_stats_1d
from etl.db_resource import db_connection

defs = Definitions(
    assets=[etl_load_stats_1d],
    resources={"db": db_connection}
)
