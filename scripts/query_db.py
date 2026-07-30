import os
from config.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from db.client import DatabaseClient

try:
    client = DatabaseClient()
    print("Connecting to DB to fetch valid products...")
    # Fetch 5 products
    query = "SELECT id, kode_product_external, nama_product, jenis_kredit FROM m_product WHERE nama_product ILIKE '%KMG%' LIMIT 5;"
    results = client.execute_query(query)
    for r in results:
        print(r)
except Exception as e:
    print(e)
