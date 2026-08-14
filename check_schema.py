import pyodbc
import sys
import re

# Extraer el password del script original
try:
    with open('prueba_vertical.py', 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'password = "([^"]+)"', content)
        if match:
            pwd = match.group(1)
        else:
            print("No se encontro password")
            sys.exit(1)
except Exception as e:
    print(e)
    sys.exit(1)

connection_string = f'DRIVER={{SQL Server}};SERVER=bore.pub,37368;DATABASE=KH_HE;UID=escandon_bi_user;PWD={pwd}'
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()
cursor.execute("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='UDR_RPT_HABITACION'")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} ({row[2]})")
