import sqlite3, pathlib

DB = "purdue_mbb.db"
SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "schema" / "articles.sql"

def main():
    con = sqlite3.connect(DB)
    with open(SCHEMA, "r") as f:
        con.executescript(f.read())
    con.commit()
    print("DB initialized:", DB)

if __name__ == "__main__":
    main()
