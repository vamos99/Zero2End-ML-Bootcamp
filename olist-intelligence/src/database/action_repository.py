import pandas as pd
from sqlalchemy import text

from src.database.db_client import get_db_connection
from src.database.query_limits import clamp_limit

engine = get_db_connection()


def _to_python_number(value):
    if hasattr(value, "item"):
        return value.item()
    return value


def log_action_to_db(action_type, description, impact_value):
    impact_value = _to_python_number(impact_value)

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO action_logs (action_type, description, impact_value)
                VALUES (:type, :desc, :val)
                """
            ),
            {"type": action_type, "desc": description, "val": impact_value},
        )
        conn.commit()


def get_recent_actions(limit=5):
    limit = clamp_limit(limit, default=5)
    return pd.read_sql(
        text("SELECT * FROM action_logs ORDER BY timestamp DESC LIMIT :limit"),
        engine,
        params={"limit": limit},
    )


def init_bi_tables():
    dialect = engine.dialect.name

    if dialect == "sqlite":
        id_col = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_col = "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
    else:
        id_col = "id SERIAL PRIMARY KEY"
        timestamp_col = "timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP"

    create_sql = f"""
        CREATE TABLE IF NOT EXISTS action_logs (
            {id_col},
            action_type VARCHAR(50),
            description TEXT,
            impact_value FLOAT,
            {timestamp_col}
        )
    """

    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()
