import pymysql

def run():
    try:
        conn = pymysql.connect(
            host="100.86.181.18",
            port=3317,
            user="root",
            password="Cor3@369",
            database="btggasify_purchase_live",
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as Total FROM tbl_PurchaseRequisition_Header;")
            print("Total PRs:", cursor.fetchone()['Total'])
            
            cursor.execute("SELECT COUNT(*) as NullPOUtil FROM tbl_PurchaseRequisition_Header WHERE IsPOUtil IS NULL;")
            print("IsPOUtil IS NULL:", cursor.fetchone()['NullPOUtil'])
            
            cursor.execute("SELECT COUNT(*) as ZeroPOUtil FROM tbl_PurchaseRequisition_Header WHERE IsPOUtil = 0;")
            print("IsPOUtil = 0:", cursor.fetchone()['ZeroPOUtil'])
            
            cursor.execute("SELECT COUNT(*) as NotConverted FROM tbl_PurchaseRequisition_Header WHERE (IsPOUtil = 0 OR IsPOUtil IS NULL) AND (IsCancel = 0 OR IsCancel IS NULL);")
            print("Not Converted & Not Cancelled:", cursor.fetchone()['NotConverted'])
            
            cursor.execute("SELECT PR_Number FROM tbl_PurchaseRequisition_Header WHERE (IsPOUtil = 0 OR IsPOUtil IS NULL) LIMIT 5;")
            print("Sample Unutilized PRs:", cursor.fetchall())
            
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    run()
