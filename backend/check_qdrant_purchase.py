import sqlite3

def run():
    conn = sqlite3.connect('qdrant_data_v2/collection/schema_collection/storage.sqlite')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    
    for table in tables:
        table_name = table[0]
        try:
            cur.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            for row in rows:
                row_str = str(row)
                if 'btggasify_purchase_live' in row_str:
                    print(row_str)
        except Exception as e:
            pass

if __name__ == '__main__':
    run()
