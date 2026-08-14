import sys
sys.path.append('backend')
from kh_database import get_kh_connection
conn=get_kh_connection()
c=conn.cursor()
c.execute('SELECT top 1 * from V_MRPT')
print([desc[0] for desc in c.description])
