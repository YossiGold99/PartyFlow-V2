import sqlite3
import os

# Path to the database file
DB_NAME = os.path.join("database", "party_bot.db")

# --- Existing Functions ---

def create_tables():
    """Creates the necessary tables if they don't exist."""
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create Events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT NOT NULL, 
            date TEXT NOT NULL, 
            location TEXT NOT NULL, 
            price REAL NOT NULL, 
            total_tickets INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Create Tickets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            event_id INTEGER NOT NULL, 
            user_id INTEGER NOT NULL, 
            user_name TEXT, 
            phone_number TEXT, 
            purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_ticket(event_id, user_id, user_name, phone_number):
    """Adds a new ticket to the database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tickets (event_id, user_id, user_name, phone_number) 
            VALUES (?, ?, ?, ?)
        ''', (event_id, user_id, user_name, phone_number))
        
        conn.commit()
        last_row_id = cursor.lastrowid # Returns the ID of the created ticket
        conn.close()
        return last_row_id
    except Exception as e:
        print(f"Database Error: {e}")
        return False

def get_events():
    """Fetches all ACTIVE events."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Filter by is_active = 1
    cursor.execute("SELECT * FROM events WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_event(name, date, location, price, total_tickets):
    """Adds a new event."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (name, date, location, price, total_tickets, is_active) 
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (name, date, location, price, total_tickets))
    conn.commit()
    conn.close()

def get_event_by_id(event_id):
    """Fetches a single event by ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    conn.close()
    return dict(event) if event else None

def get_tickets_sold(event_id):
    """Counts how many tickets were sold for a specific event."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE event_id = ?", (event_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_revenue():
    """Calculates total revenue from all ticket sales."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(events.price) 
        FROM tickets 
        JOIN events ON tickets.event_id = events.id
    ''')
    result = cursor.fetchone()[0]
    conn.close()
    return round(result, 2) if result else 0

def get_total_tickets_sold():
    """Counts total tickets sold across all events."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets")
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0

def get_top_event():
    """Finds the event with the highest sales."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT events.name, COUNT(tickets.id) as ticket_count 
        FROM tickets 
        JOIN events ON tickets.event_id = events.id 
        GROUP BY events.id 
        ORDER BY ticket_count DESC 
        LIMIT 1
    ''')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "No Sales Yet"

def get_user_tickets(user_id):
    """Fetches all tickets for a specific user ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query to join ticket data with event details
    cursor.execute("""
        SELECT t.id, e.name, e.date, e.location 
        FROM tickets t
        JOIN events e ON t.event_id = e.id
        WHERE t.user_id = ?
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_events_by_date(target_date):
    # Returns all events happening on a specific date (format: YYYY-MM-DD).
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE date = ? AND is_active = 1", (target_date,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_users_with_tickets_for_event(event_id):
    # Returns a list of user_ids that have a ticket for a specific event.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM tickets WHERE event_id = ?", (event_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# --- Pagination, Archive & Export Functions ---

def get_events_paginated(page=1, per_page=5, search_query="", active_status=1):
    """
    active_status=1 -> fetches active events
    active_status=0 -> fetches archived events
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    offset = (page - 1) * per_page
    
    if search_query:
        query = "SELECT * FROM events WHERE is_active = ? AND name LIKE ? ORDER BY id ASC LIMIT ? OFFSET ?"
        params = (active_status, f"%{search_query}%", per_page, offset)
        
        count_query = "SELECT COUNT(*) FROM events WHERE is_active = ? AND name LIKE ?"
        count_params = (active_status, f"%{search_query}%")
    else:
        query = "SELECT * FROM events WHERE is_active = ? ORDER BY id ASC LIMIT ? OFFSET ?"
        params = (active_status, per_page, offset)
        
        count_query = "SELECT COUNT(*) FROM events WHERE is_active = ?"
        count_params = (active_status,)

    cursor.execute(query, params)
    events = [dict(row) for row in cursor.fetchall()]

    cursor.execute(count_query, count_params)
    total_items = cursor.fetchone()[0]
    total_pages = (total_items + per_page - 1) // per_page

    conn.close()
    return events, total_pages

def archive_event(event_id):
    """Marks an event as archived (inactive)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET is_active = 0 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

def restore_event(event_id):
    """Restores an archived event (sets is_active = 1)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET is_active = 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

def get_all_events_for_export():
    """Fetches all events with sales data for CSV export."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Complex query that also fetches sold ticket count and revenue per event
    query = '''
        SELECT 
            e.id, e.name, e.date, e.location, e.price, e.total_tickets,
            COUNT(t.id) as sold_count,
            (COUNT(t.id) * e.price) as revenue
        FROM events e
        LEFT JOIN tickets t ON e.id = t.event_id
        WHERE e.is_active = 1
        GROUP BY e.id
        ORDER BY e.date DESC
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_tickets_for_export():
    """Fetches all tickets with event details for the Guest List export."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query linking ticket to event details
    query = '''
        SELECT 
            t.id as ticket_id,
            e.name as event_name,
            t.user_name,
            t.phone_number,
            t.purchase_time,
            t.user_id as telegram_id
        FROM tickets t
        JOIN events e ON t.event_id = e.id
        ORDER BY t.id DESC
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]