import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_party_promo(event_name, location, date, vibe="energetic"):
    """
    Generates a short, hype-filled promotional message for Telegram using Gemini AI.
    """
    # Using 'gemini-2.5-flash' for speed and stability
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = (
        f"Write a short, hype-filled promotional message for a party named '{event_name}' "
        f"happening at '{location}' on {date}. "
        f"The vibe is {vibe}. "
        "Include emojis. Keep it under 280 characters suitable for a Telegram broadcast."
    )
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Print error to console for debugging
        print(f"Gemini Error: {e}")
        return f"Error generating text. Please check server logs."

def answer_user_question(user_question, events_context):
    """
    Answers a user question based on the list of active events.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Construct a prompt with the event context and the user's question
    prompt = (
        f"You are a helpful support agent for a party ticket bot called 'PartyFlow'.\n"
        f"Here is the current list of active events:\n{events_context}\n\n"
        f"User Question: {user_question}\n"
        f"Answer the user politely and briefly in the same language they asked (Hebrew/English). "
        f"If the answer is not in the event list, say you don't know."
    )
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Chat Error: {e}")
        return "Sorry, I am having trouble answering right now. Please try again later."

def parse_event_details(raw_text):
# Analyzes raw text (e.g., from WhatsApp/Facebook) and extracts event details into a JSON format.
# Returns a dictionary with keys: name, date, location, price, total_tickets.
    model = genai.GenerativeModel('gemini-2.5-flash')
# Instruct the AI to return ONLY raw JSON without markdown formatting
    prompt = (
        f"Analyze the following event text and extract: Name, Date (YYYY-MM-DD), "
        f"Location, Price (number only), and Total Tickets (estimate or default 100). "
        f"Return ONLY a raw JSON object. Do not use Markdown formatting (no ```json blocks). "
        f"Fields: name, date, location, price, total_tickets.\n\n"
        f"Raw Text:\n{raw_text}"
    )
    
    try:
        response = model.generate_content(prompt)
        # Clean up text in case AI added markdown code blocks despite instructions
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(clean_text)
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None