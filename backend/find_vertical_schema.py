from kh_database import get_kh_connection

def search():
    conn = get_kh_connection()
    if not conn:
        print("No connection")
        return
    cursor = conn.cursor()
    
    # Check all tables with MR_
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'MR_%' ORDER BY TABLE_NAME")
    tables = [r[0] for r in cursor.fetchall()]
    print("Total MR_ tables:", len(tables))
    
    # Check which tables have data for 5704
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t} WHERE PTNum = 5704")
            cnt = cursor.fetchone()[0]
            if cnt > 0:
                print(f"Table {t} has {cnt} rows for PTNum 5704")
        except Exception:
            pass

    # Check which tables have data ANYWHERE
    print("\nTables with ANY data in MR_ tables:")
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cursor.fetchone()[0]
            if cnt > 0:
                print(f"  {t}: {cnt} rows")
        except Exception:
            pass

    # Check if there is a master medical record index table like MR or MR_DOC or MR_REC
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%DOC%' OR TABLE_NAME LIKE '%NOTE%' OR TABLE_NAME LIKE '%REC%' OR TABLE_NAME LIKE '%EVENT%' ORDER BY TABLE_NAME")
    other_tables = [r[0] for r in cursor.fetchall()]
    print("\nOther potential tables:", other_tables)

    conn.close()

if __name__ == '__main__':
    search()
