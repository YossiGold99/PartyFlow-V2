import os
import stripe
import qrcode 
import requests
import secrets
import logging
import aiohttp
import asyncio
import csv
from io import StringIO
from datetime import date
from dotenv import load_dotenv
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# FastAPI Imports
from fastapi import FastAPI, HTTPException, Request, Form, Depends, status, BackgroundTasks, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Core Logic
from core import db_manager

# --- Configuration & Setup ---

# 1. Load environment variables
load_dotenv()

# 2. Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 3. Initialize App
app = FastAPI()

# 4. Security Setup (Cookie Based)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def get_current_username(request: Request):
    """
    Checks for a valid session cookie.
    If not found, redirects the user to the login page.
    """
    user = request.cookies.get("session_user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

# 5. Middleware (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Third-Party Keys
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
YOUR_DOMAIN = "http://127.0.0.1:8000"

# 7. Static Files & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- Data Models ---

class TicketRequest(BaseModel):
    event_id: int
    user_name: str
    user_id: int
    phone_number: str
    quantity: int = 1  # Default to 1 if not provided

class EventRequest(BaseModel):
    name: str
    date: str
    location: str
    price: float
    total_tickets: int

class LoginRequest(BaseModel):
    password: str

async def send_telegram_broadcast_task(user_ids, message, event_name):
    """
    Asynchronous version: Sends messages in parallel (non-blocking).
    """
    bot_token = os.getenv("TELEGRAM_TOKEN")
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    logging.info(f"🚀 Starting FAST broadcast for '{event_name}' to {len(user_ids)} users...")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for user_id in user_ids:
            full_text = (
                f"📢 **Update regarding {event_name}**\n\n"
                f"{message}\n\n"
                f"-- PartyFlow Management"
            )
            
            payload = {
                "chat_id": user_id, 
                "text": full_text, 
                "parse_mode": "Markdown"
            }
            task = session.post(send_url, json=payload)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for response in responses:
            if not isinstance(response, Exception) and response.status == 200:
                success_count += 1
                
    logging.info(f"✅ Fast Broadcast complete! Sent to {success_count}/{len(user_ids)} users.")


# --- Routes ---

@app.get("/")
def read_root():
    """Redirects the homepage directly to the dashboard."""
    return RedirectResponse(url="/dashboard")

@app.get("/success", response_class=HTMLResponse)
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})


# --- Authentication Routes (Login / Logout) ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Renders the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Validates credentials and sets a session cookie."""
    
    if not ADMIN_PASSWORD:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Security Error: No admin password configured in .env"
        })

    if username == "admin" and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session_user", value=username)
        return response
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "Invalid credentials"
    })

@app.get("/logout")
async def logout(request: Request):
    """Logs out the user by deleting the cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_user")
    return response


# -- API Routes --

@app.get("/api/stats")
def get_dashboard_stats():
    return {
        "stats": {
            "total_revenue": db_manager.get_total_revenue(),
            "tickets_sold": db_manager.get_total_tickets_sold(),
            "top_event": db_manager.get_top_event()
        },
        "events": db_manager.get_events()
    }

@app.post("/api/events")
def add_event_api(event: EventRequest):
    db_manager.add_event(
        event.name, event.date, event.location, event.price, event.total_tickets
    )
    return {"message": "Event added successfully"}

@app.get("/events")
def get_events_api():
    return {"events": db_manager.get_events()}

@app.get("/api/tickets/{user_id}")
def get_tickets_api(user_id: int):
    tickets = db_manager.get_user_tickets(user_id)
    return {"tickets": tickets}

@app.post("/api/login")
def login_api(request: LoginRequest):
    if request.password == ADMIN_PASSWORD:
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect password")


# --- Dashboard Routes (Admin) ---

@app.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
def show_dashboard(request: Request, page: int = 1, q: str = "", view: str = "active"):
    """
    view='active' -> standard view
    view='archived' -> archive view
    """
    
    # Set fetch status (1=active, 0=archived)
    is_active_status = 0 if view == 'archived' else 1
    
    raw_events, total_pages = db_manager.get_events_paginated(
        page=page, 
        per_page=5, 
        search_query=q,
        active_status=is_active_status
    )
    
    events_processed = []
    for event in raw_events:
        e_dict = dict(event)
        sold = db_manager.get_tickets_sold(e_dict['id'])
        total = e_dict['total_tickets']
        e_dict['sold'] = sold
        e_dict['remaining'] = total - sold
        e_dict['percent'] = int((sold / total) * 100) if total > 0 else 0
        events_processed.append(e_dict)

    stats = {
        "total_revenue": db_manager.get_total_revenue(),
        "tickets_sold": db_manager.get_total_tickets_sold(),
        "top_event": db_manager.get_top_event()
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "events": events_processed,  
        "stats": stats,
        "current_page": page,
        "total_pages": total_pages,
        "search_query": q,
        "view_mode": view 
    })

@app.post("/dashboard/add", dependencies=[Depends(get_current_username)])
def add_event_web(
    name: str = Form(...), 
    date: str = Form(...), 
    location: str = Form(...), 
    price: float = Form(...), 
    total_tickets: int = Form(...)
):
    db_manager.add_event(name, date, location, price, total_tickets)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/dashboard/broadcast", dependencies=[Depends(get_current_username)])
def broadcast_message(
    background_tasks: BackgroundTasks,
    event_id: int = Form(...), 
    message: str = Form(...)
):
    event = db_manager.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    user_ids = db_manager.get_users_with_tickets_for_event(event_id)
    background_tasks.add_task(send_telegram_broadcast_task, user_ids, message, event['name'])
    
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/dashboard/archive/{event_id}", dependencies=[Depends(get_current_username)])
def archive_event_route(event_id: int):
    db_manager.archive_event(event_id)
    # Redirect to dashboard
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/dashboard/restore/{event_id}", dependencies=[Depends(get_current_username)])
def restore_event_route(event_id: int):
    db_manager.restore_event(event_id)
    # Redirect back to archive view
    return RedirectResponse(url="/dashboard?view=archived", status_code=303)

@app.get("/dashboard/export_csv", dependencies=[Depends(get_current_username)])
def export_events_csv():
    # 1. Fetch data
    events = db_manager.get_all_events_for_export()
    
    # 2. Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Column headers
    writer.writerow(['ID', 'Event Name', 'Date', 'Location', 'Price (NIS)', 'Capacity', 'Tickets Sold', 'Revenue'])
    
    # Write rows
    for e in events:
        writer.writerow([
            e['id'], 
            e['name'], 
            e['date'], 
            e['location'], 
            e['price'], 
            e['total_tickets'], 
            e['sold_count'], 
            e['revenue']
        ])
        
    # 3. Prepare download
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=partyflow_report.csv"}
    )

@app.get("/dashboard/export_tickets", dependencies=[Depends(get_current_username)])
def export_tickets_csv():
    # 1. Fetch all tickets
    tickets = db_manager.get_all_tickets_for_export()
    
    # 2. Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Headers (Matches QR data)
    writer.writerow(['Ticket ID', 'Event Name', 'Owner Name', 'Phone', 'Purchase Time', 'Telegram ID', 'QR String'])
    
    # Write rows
    for t in tickets:
        # Generate QR string (for manual verification)
        qr_string = f"TICKET-ID:{t['ticket_id']} | EVENT:{t['event_name']} | OWNER:{t['telegram_id']}"
        
        writer.writerow([
            t['ticket_id'], 
            t['event_name'], 
            t['user_name'], 
            t['phone_number'], 
            t['purchase_time'],
            t['telegram_id'],
            qr_string
        ])
        
    # 3. Prepare download
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=guest_list.csv"}
    )


# --- Stripe Payment Logic ---

@app.post("/create_checkout_session")
def create_checkout_session(ticket: TicketRequest):
    event = db_manager.get_event_by_id(ticket.event_id)
    sold_count = db_manager.get_tickets_sold(ticket.event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if enough tickets remain for the requested quantity
    if sold_count + ticket.quantity > event['total_tickets']:
        raise HTTPException(status_code=400, detail="Not enough tickets left!")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'ils',
                    'product_data': {'name': f"Ticket: {event['name']}"},
                    'unit_amount': int(event['price'] * 100),
                },
                'quantity': ticket.quantity,  # Use selected quantity
            }],
            mode='payment',
            metadata={
                "event_id": ticket.event_id,
                "user_id": ticket.user_id,
                "user_name": ticket.user_name,
                "phone_number": ticket.phone_number,
                "quantity": ticket.quantity  # Store quantity in metadata
            },
            success_url=YOUR_DOMAIN + "/payment_success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=YOUR_DOMAIN + "/payment_cancel",
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        logging.error(f"Stripe Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payment_success", response_class=HTMLResponse)
def payment_success(session_id: str, request: Request):
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            data = session.metadata
            quantity = int(data.get('quantity', 1)) # Default to 1 if missing
            
            event = db_manager.get_event_by_id(int(data['event_id']))
            
            # Loop to create multiple tickets
            for i in range(quantity):
                ticket_id = db_manager.add_ticket(
                    event_id=int(data['event_id']),
                    user_id=int(data['user_id']),
                    user_name=data['user_name'],
                    phone_number=data['phone_number']
                )
                
                qr_path = generate_qr_code(ticket_id, event['name'], data['user_name'])
                
                caption = (
                    f"🎉 Ticket {i+1}/{quantity} Confirmed!\n"
                    f"Event: {event['name']}\n"
                    f"Ticket ID: #{ticket_id}\n\n"
                    f"Show this QR code at the entrance."
                )
                # Send individual QR to user
                send_ticket_to_telegram(data['user_id'], qr_path, caption)
            
            return templates.TemplateResponse("success.html", {"request": request})
        else:
            return "Payment Failed or Pending."
    except Exception as e:
        logging.error(f"Payment processing error: {e}")
        return f"Error processing payment: {e}"

@app.get("/payment_cancel")
def payment_cancel():
    return {"message": "Order canceled. You can close this window."}


# --- Automatic Reminder Logic ---

scheduler = AsyncIOScheduler()

def check_and_send_reminders():
    today = date.today().isoformat()
    logging.info(f"Scheduler running: checking for events on {today}")

    events = db_manager.get_events_by_date(today)
    if not events:
        logging.info("No events today.")
        return
    
    token = os.getenv("TELEGRAM_TOKEN")
    for event in events:
        logging.info(f"Found event: {event['name']}! Sending reminders...")
        user_ids = db_manager.get_users_with_tickets_for_event(event["id"])

        for user_id in user_ids:
            try:
                msg = (
                    f"Today is the day!\n\n"
                    f"Get ready! **{event['name']}** is happening today.\n"
                    f"Location: {event['location']}\n\n"
                    f"See you there!"
                )
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                    "chat_id": user_id, 
                    "text": msg, 
                    "parse_mode": "Markdown"
                })
            except Exception as e:
                logging.error(f"Failed to send reminder to {user_id}: {e}")

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(check_and_send_reminders, 'cron', hour=10, minute=0)
    scheduler.start()
    logging.info("✅ Scheduler started")


# --- Helpers ---

def generate_qr_code(ticket_id: int, event_name: str, user_name: str):
    if not os.path.exists("static"):
        os.makedirs("static")
    data = f"TICKET-ID:{ticket_id} | EVENT:{event_name} | OWNER:{user_name}"
    qr = qrcode.make(data)
    file_path = f"static/ticket_{ticket_id}.png"
    qr.save(file_path)
    return file_path

def send_ticket_to_telegram(chat_id, file_path, caption):
    bot_token = os.getenv("TELEGRAM_TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(file_path, "rb") as image_file:
        requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"photo": image_file})