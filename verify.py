import pyodbc
import sys
import re

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
cursor.execute("SELECT MRNum_NE_URG, PTNum, DIAGNOSTICO FROM [KH_HE].[dbo].[MR_NE_URG] WHERE CreatedBy='api'")
rows = cursor.fetchall()
print(f"Total registros inyectados encontrados: {len(rows)}")
for row in rows:
    print(f"ID: {row[0]}, PTNum: {row[1]}, Diag: {row[2]}")
