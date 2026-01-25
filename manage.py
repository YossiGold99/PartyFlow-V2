import sys
import os

sys.path.append(os.getcwd())

from core import db_manager

def main():
    print("Initializing database...")
    db_manager.create_tables()
    print("Database ready! ✅")

    print("\n--- Party Manager ---")
    print("1. Add new event")
    print("2. List all events")
    
    choice = input("Choose an option: ")
    
    if choice == '1':
        name = input("Event Name: ")
        date = input("Date (YYYY-MM-DD): ")
        location = input("Location: ")
        price = float(input("Price: "))
        total_tickets = int(input("Total Tickets: "))
        
        db_manager.add_event(name, date, location, price, total_tickets)
        print("Event added successfully!")
        
    elif choice == '2':
        events = db_manager.get_events()
        for event in events:
            print(f"{event['id']}: {event['name']} - {event['date']}")

if __name__ == "__main__":
    main()