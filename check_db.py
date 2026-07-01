import sqlite3
import pandas as pd

def check_db():
    try:
        conn = sqlite3.connect("research_journal.db")
        query = "SELECT * FROM shadow_trades ORDER BY timestamp DESC LIMIT 10"
        df = pd.read_sql_query(query, conn)
        print(df)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
