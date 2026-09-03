import pymssql
from config.config import ACS_DB_HOST, ACS_DB_PORT, ACS_DB_NAME, ACS_DB_USER, ACS_DB_PASSWORD
from utils.logger import get_logger

logger = get_logger(__name__)

def get_acs_db_connection():
    try:
        conn = pymssql.connect(
            server=ACS_DB_HOST,
            port=ACS_DB_PORT,
            user=ACS_DB_USER,
            password=ACS_DB_PASSWORD,
            database=ACS_DB_NAME,
            as_dict=True
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to ACS DB Staging: {e}")
        raise

def execute_acs_update(query: str, params: tuple = None) -> int:
    conn = None
    try:
        conn = get_acs_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        rowcount = cursor.rowcount
        conn.commit()
        logger.info(f"Executed ACS query successfully. Rowcount: {rowcount}")
        return rowcount
    except Exception as e:
        logger.error(f"Error executing ACS query: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
