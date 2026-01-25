import sqlite3

def create_tables():

    # Connect to the database (creates it if it doesn't exist)
    conn = sqlite3.connect('party_bot.db')
    cursor = conn.cursor()

    # 1. Create Events table
    print("Creating Events table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique ID / מזהה ייחודי
            name TEXT NOT NULL,                    -- Event name / שם המסיבה
            date TEXT NOT NULL,                    -- Date & Time / תאריך ושעה
            location TEXT NOT NULL,                -- Location / מיקום
            price REAL NOT NULL,                   -- Ticket price / מחיר כרטיס
            total_tickets INTEGER NOT NULL         -- Total capacity / סך כל הכרטיסים
        )
    ''')

    # 2. Create Users table
    print("Creating Users table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT UNIQUE,           -- Unique chat ID 
            name TEXT,                     -- User's name
            is_admin BOOLEAN,              -- Admin status 
            created_at TEXT                -- Account creation date 
        )
    ''')

    # 3. Create Tickets table
    print("Creating Tickets table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            status TEXT,
            purchase_date TEXT,
            ticket_hash TEXT,
            
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database created successfully.")

if __name__ == "__main__":
    create_tables()
    