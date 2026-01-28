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