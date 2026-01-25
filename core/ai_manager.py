import os
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
    # FIX: Using 'gemini-pro' instead of 'gemini-1.5-flash' for better compatibility
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