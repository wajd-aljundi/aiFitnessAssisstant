from mysql.connector.pooling import MySQLConnectionPool
from dotenv import load_dotenv
import os


load_dotenv()

HOST = os.getenv("DB_HOST")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Create a pooling for recipe.py
mysql_pool = MySQLConnectionPool(
    pool_name="mypool",
    pool_size=8,
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DB_NAME
)