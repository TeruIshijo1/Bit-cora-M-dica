from kh_database import get_kh_connection

def find_active_episode():
    conn = get_kh_connection()
    cursor = conn.cursor()
    
    # Check tables with PC or Episode
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'PC%' OR TABLE_NAME LIKE '%EPISODE%' OR TABLE_NAME LIKE '%ADM%' ORDER BY TABLE_NAME")
    print("Tables:", [r[0] for r in cursor.fetchall()][:10])

    # Check MR_HC_URG and MR_26_01 ControllerKeys for 5704
    cursor.execute("SELECT TOP 5 ControllerName, ControllerKey, CreatedOn FROM MR_HC_URG WHERE PTNum = 5704 ORDER BY CreatedOn DESC")
    print("MR_HC_URG keys:", cursor.fetchall())

    # UPDATE MR_NE_URG for 5704 with ControllerKey = 1301 and ControllerName = 'PC'
    cursor.execute("""
    UPDATE MR_NE_URG
    SET ControllerName = 'PC',
        ControllerKey = 1301,
        MR_ST = 'RG',
        PTID = '188CF68E-FF85-4941-AA81-DA3F20660109',
        CreatedBy = 'jose_prueba',
        ModifiedBy = 'jose_prueba'
    WHERE PTNum = 5704
    """)
    conn.commit()
    print("OK: Updated MR_NE_URG ControllerKey to 1301!")

    cursor.execute("SELECT MRNum_NE_URG, PTNum, ControllerName, ControllerKey, MR_ST, S_SUBJETIVO1 FROM MR_NE_URG WHERE PTNum = 5704")
    print("Current row in MR_NE_URG:", cursor.fetchone())

    conn.close()

if __name__ == '__main__':
    find_active_episode()
