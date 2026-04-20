import sqlite3

def create_database():
    # creem baza de date
    conn = sqlite3.connect('database.db')
    
    # executam scriptul din schema.sql
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    
    conn.commit()
    conn.close()
    print("Baza de data creata cu succes")

if __name__ == '__main__':
    create_database()