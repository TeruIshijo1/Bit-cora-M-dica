from kh_database import get_kh_connection

def inspect_exact_keys():
    conn = get_kh_connection()
    if not conn:
        print("No connection")
        return
    cursor = conn.cursor()
    
    cursor.execute("SELECT MRNum_HC_URG, PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, MR_HC_URGID, CreatedBy, CreatedOn, SignedBy, SignedOn FROM MR_HC_URG WHERE PTNum = 5704")
    row = cursor.fetchone()
    cols = [c[0] for c in cursor.description]
    print("Exact metadata for MR_HC_URG for 5704:")
    for k, v in zip(cols, row):
        print(f"  {k}: {repr(v)}")

    cursor.execute("SELECT MRNum_26_01, PTNum, PTID, ControllerName, ControllerKey, ControllerID, MR_ST, CreatedBy, CreatedOn FROM MR_26_01 WHERE PTNum = 5704")
    row2 = cursor.fetchone()
    cols2 = [c[0] for c in cursor.description]
    print("\nExact metadata for MR_26_01 for 5704:")
    for k, v in zip(cols2, row2):
        print(f"  {k}: {repr(v)}")

    conn.close()

if __name__ == '__main__':
    inspect_exact_keys()
