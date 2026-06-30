import sys
sys.path.insert(0, r'D:\ERP Assitant')
from backend.app.core.config import settings
from cryptography.fernet import Fernet
import pymysql

def main():
    db = settings.database_name
    print('Connecting to', settings.DB_HOST, settings.DB_PORT, 'db', db)
    conn = pymysql.connect(host=settings.DB_HOST, port=settings.DB_PORT, user=settings.DB_USER, password=settings.DB_PASSWORD, database=db)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM db_connections")
            cnt = cur.fetchone()[0]
            if cnt > 0:
                print('db_connections already populated, count=', cnt)
                return
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            encrypted_pw = fernet.encrypt(settings.DB_PASSWORD.encode()).decode()
            cur.execute("INSERT INTO db_connections (name, host, port, database_name, username, encrypted_password, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        ('Tradeware Live', settings.DB_HOST, settings.DB_PORT, settings.database_name, settings.DB_USER, encrypted_pw, 1))
            conn.commit()
            print('Inserted default db_connections row')
    finally:
        conn.close()

if __name__ == '__main__':
    main()
