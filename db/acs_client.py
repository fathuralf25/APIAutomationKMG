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

import time

def wait_for_policy_in_acs(policy_no: str, max_retries: int = 60, delay_sec: int = 10) -> bool:
    """
    Polls the ACS database to wait until the policy is synced.
    """
    query = "SELECT COUNT(*) AS cnt FROM UNDERWRITING.UDW_POLICY WHERE POLICY_NO = %s"
    
    for i in range(max_retries):
        conn = None
        try:
            conn = get_acs_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, (policy_no,))
            result = cursor.fetchone()
            if result and result['cnt'] > 0:
                logger.info(f"Policy {policy_no} found in ACS DB after {i * delay_sec} seconds.")
                return True
        except Exception as e:
            logger.warning(f"Error while polling ACS DB: {e}")
        finally:
            if conn:
                conn.close()
                
        logger.info(f"Waiting for Policy {policy_no} to sync to ACS... ({i+1}/{max_retries})")
        time.sleep(delay_sec)
        
    logger.error(f"Timeout: Policy {policy_no} not found in ACS DB after {max_retries * delay_sec} seconds.")
    return False
