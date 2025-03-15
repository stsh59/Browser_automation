import openai
import json
import re
from config import OPENAI_API_KEY

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)


def interpret_command(command, page_source, extracted_text, encoded_image, context=""):
    """
    Analyzes the browser context and user command to generate a structured JSON response.

    Expected JSON formats:

    If complete:
    {
        "missing_info": false,
        "intent": "<action_name>",
        "parameters": {
            // For "open": {"url": "https://www.example.com"}
            // For "click": {"element_text": "Sign In"}
            // For "scroll": {"direction": "up" or "down", "distance": 500}
            // For "fill_form": {"field": "email", "value": "user@example.com"}
            // For "search": {"query": "python tutorials"}
            // For "play_video": {"video_index": 1}
        }
    }

    If additional information is needed:
    {
        "missing_info": true,
        "question": "What additional information do you want to provide?"
    }

    Respond with ONLY the JSON object.
    """

    # Truncate inputs to control token usage
    shortened_page_source = page_source[:500]
    shortened_extracted_text = extracted_text[:500]

    # Build a concise context; assume that context includes page title and URL.
    concise_context = context if context else "No additional context."

    prompt = f"""
    You are an AI browser automation assistant. Analyze the following information and decide on the best Selenium-based action.

    Context: {concise_context}
    User command: "{command}"
    Visible Text (snippet): {shortened_extracted_text}

    Generate a JSON response following EXACTLY one of these formats:

    Format 1 (if the command is complete):

    - Example for opening a website:
      {{"missing_info": false, "intent": "open", "parameters": {{"url": "https://www.youtube.com"}}}}

    - Example for searching on YouTube:
      {{"missing_info": false, "intent": "search", "parameters": {{"query": "python tutorials"}}}}

    - Example for clicking a button:
      {{"missing_info": false, "intent": "click", "parameters": {{"element_text": "Sign In"}}}}

    - Example for scrolling:
      {{"missing_info": false, "intent": "scroll", "parameters": {{"direction": "down", "distance": 500}}}}

    - Example for filling a form:
      {{"missing_info": false, "intent": "fill_form", "parameters": {{"field": "email", "value": "user@example.com"}}}}

    - Example for playing a video:
      {{"missing_info": false, "intent": "play_video", "parameters": {{"video_index": 1}}}}

    Format 2 (if additional information is needed):
      {{"missing_info": true, "question": "What additional information do you want to provide?"}}

    IMPORTANT: Provide ONLY the JSON object with no extra text or markdown.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt}
                # We omit the Base64 screenshot to reduce token usage
            ],
            stream=True
        )

        full_response = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content

        full_response = full_response.strip()
        # Remove any markdown formatting
        full_response = re.sub(r"```json|```", "", full_response).strip()

        if not full_response:
            print("❌ OpenAI returned an empty response.")
            return {"missing_info": True, "question": "I didn't understand the command. Can you rephrase it?"}

        return json.loads(full_response)

    except json.JSONDecodeError:
        print("❌ Error: OpenAI returned invalid JSON. Raw response:")
        print(full_response)
        return {"missing_info": True, "question": "The response was not clear. Can you specify more details?"}
    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {e}")
        return {"missing_info": True, "question": "OpenAI API error occurred. Try again later."}
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return {"missing_info": True, "question": "Something went wrong. Try again."}
