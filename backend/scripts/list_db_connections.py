import sys
sys.path.insert(0, r'D:\ERP Assitant')
from backend.app.core.config import settings
import pymysql

def main():
    print('Connecting to', settings.DB_HOST, settings.DB_PORT, 'db', settings.database_name)
    conn = pymysql.connect(host=settings.DB_HOST, port=settings.DB_PORT, user=settings.DB_USER, password=settings.DB_PASSWORD, database=settings.database_name)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, host, database_name, username, is_active FROM db_connections")
            rows = cur.fetchall()
            if not rows:
                print('No db_connections rows found')
            else:
                print('db_connections:')
                for r in rows:
                    print(r)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
