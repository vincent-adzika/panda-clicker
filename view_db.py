import sqlite3

DB_PATH = 'botdata.sqlite3'

def show_tables():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in c.fetchall()]
        print("Tables:", tables)
        for table in tables:
            print(f"\n--- {table} ---")
            c.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in c.fetchall()]
            print("Columns:", columns)
            c.execute(f"SELECT * FROM {table}")
            rows = c.fetchall()
            for row in rows:
                print(dict(zip(columns, row)))

if __name__ == "__main__":
    show_tables()
