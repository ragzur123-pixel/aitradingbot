import sqlite3

def check_tables():
    conn = sqlite3.connect("research_journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    if ('shadow_trades',) in tables:
        cursor.execute("SELECT COUNT(*) FROM shadow_trades")
        count = cursor.fetchone()[0]
        print(f"Row count in shadow_trades: {count}")
    conn.close()

if __name__ == "__main__":
    check_tables()
