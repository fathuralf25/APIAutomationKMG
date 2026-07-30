import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError
from typing import List, Dict, Any, Optional

from config.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseClient:
    """
    Reusable PostgreSQL client for database validations in the QA Framework.
    """

    def __init__(self):
        """
        Initialize the DatabaseClient with credentials from config.
        """
        self.host = DB_HOST
        self.port = DB_PORT
        self.name = DB_NAME
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.connection = None

    def connect(self):
        """
        Establish connection to the PostgreSQL database.
        """
        if self.connection is None or self.connection.closed:
            try:
                logger.info(f"Connecting to database {self.name} at {self.host}:{self.port}")
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=self.name,
                    user=self.user,
                    password=self.password
                )
            except OperationalError as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

    def disconnect(self):
        """
        Close the database connection if active.
        """
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed.")

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return the results as a list of dictionaries.
        
        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): Parameters for the SQL query.
            
        Returns:
            List[Dict[str, Any]]: Result set mapping column names to values.
        """
        self.connect()
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                logger.debug(f"Executing query: {query} with params: {params}")
                cursor.execute(query, params)
                if cursor.description is not None:
                    # It's a SELECT statement
                    result = cursor.fetchall()
                    logger.debug(f"Query returned {len(result)} rows.")
                    self.connection.commit() # Commit to close transaction and get fresh snapshot for next query
                    return [dict(row) for row in result]
                else:
                    self.connection.commit()
                    return []
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            if self.connection:
                self.connection.rollback()
            raise
