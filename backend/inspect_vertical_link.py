import uuid
from kh_database import get_kh_connection

def inspect_and_fix():
    conn = get_kh_connection()
    if not conn:
        print("No connection")
        return
    cursor = conn.cursor()
    
    # 1. Get patient 5704 GUID and Controller data
    cursor.execute("SELECT ControllerName, ControllerKey, ControllerID, PTID FROM V_MRPT WHERE PTNum = 5704")
    row = cursor.fetchone()
    c_name, c_key, c_id, pt_id = row if row else ('PT', 5704, str(uuid.uuid4()), str(uuid.uuid4()))
    print(f"Patient 5704 metadata: ControllerName={c_name}, ControllerKey={c_key}, ControllerID={c_id}, PTID={pt_id}")
    
    # 2. Update MR_NE_URG row for 5704 with all Vertical internal flags:
    # MR_ST = 'RG' (Registrado)
    # ControllerName = c_name ('PC' or 'PT')
    # ControllerKey = c_key
    # ControllerID = c_id
    # PTID = pt_id
    # CreatedBy = 'jose_prueba'
    # MR_NE_URGID = new GUID
    guid_nota = str(uuid.uuid4()).upper()
    sql_fix = """
    UPDATE MR_NE_URG
    SET MR_ST = 'RG',
        ControllerName = ?,
        ControllerKey = ?,
        ControllerID = ?,
        PTID = ?,
        MR_NE_URGID = ?,
        CreatedBy = 'jose_prueba',
        ModifiedBy = 'jose_prueba',
        ModifiedOn = GETDATE()
    WHERE PTNum = 5704
    """
    cursor.execute(sql_fix, (c_name, c_key, c_id, pt_id, guid_nota))
    conn.commit()
    print("OK: MR_NE_URG row for 5704 enriched with MR_ST='RG', ControllerName/Key/ID and PTID!")

    # Check updated row
    cursor.execute("SELECT MRNum_NE_URG, PTNum, PTID, ControllerName, ControllerKey, MR_ST, CreatedBy, S_SUBJETIVO1 FROM MR_NE_URG WHERE PTNum = 5704")
    print("Updated row:", cursor.fetchone())

    conn.close()

if __name__ == '__main__':
    inspect_and_fix()
