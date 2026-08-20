import pyodbc
from dotenv import load_dotenv
import os

load_dotenv('backend/.env')
server = os.getenv('KH_SERVER').strip().strip('"').strip("'")
database = os.getenv('KH_DATABASE', 'KH_HE')
username = os.getenv('KH_USERNAME')
password = os.getenv('KH_PASSWORD')

drivers = ['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'SQL Server']
conn = None
for d in drivers:
    try:
        cs = f'DRIVER={{{d}}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Encrypt=no;'
        conn = pyodbc.connect(cs, timeout=5)
        break
    except Exception as e:
        continue

if not conn:
    print("Could not connect")
    exit(1)

cursor = conn.cursor()
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'MR_NE_URG'
    ORDER BY ORDINAL_POSITION
""")

for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2]})")
