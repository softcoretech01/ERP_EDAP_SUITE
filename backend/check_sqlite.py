import sqlite3

def run():
    try:
        conn = sqlite3.connect('qdrant_data_v2/collection/schema_collection/storage.sqlite')
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        
        found = False
        for table in tables:
            table_name = table[0]
            try:
                cur.execute(f"SELECT * FROM {table_name}")
                rows = cur.fetchall()
                if 'btggasify_purchase_live' in str(rows):
                    found = True
                    break
            except:
                pass
        
        if found:
            print("YES")
        else:
            print("NO")
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    run()
