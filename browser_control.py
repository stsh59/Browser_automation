from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import pytesseract
import base64
import logging
import time
import json

from config import OPENAI_API_KEY
from ai_processing import interpret_command
from voice_control import listen, speak

logging.basicConfig(level=logging.INFO)

# --------------------- Utility Functions ---------------------

def get_driver():
    """Initialize the Selenium WebDriver with Chrome."""
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    return driver

def get_browser_context(driver):
    """Capture current page title, URL, and a snippet of visible text."""
    current_url = driver.current_url
    page_title = driver.title
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
    except Exception:
        page_text = ""
    return f"Current Page: {page_title}\nURL: {current_url}\nVisible Text: {page_text}"

def capture_screenshot(driver):
    """Take a screenshot and extract visible text using OCR."""
    screenshot_path = "screenshot.png"
    driver.save_screenshot(screenshot_path)
    img = Image.open(screenshot_path)
    extracted_text = pytesseract.image_to_string(img)
    return screenshot_path, extracted_text

def encode_image(image_path):
    """Convert the screenshot to a Base64 encoded string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def safe_find_element(driver, by, value, timeout=10):
    """Wait for an element to be present and return it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except Exception as e:
        logging.error(f"❌ Element not found: {value} | Error: {e}")
        return None

# --------------------- Action Handlers ---------------------

def handle_open(parameters, driver):
    """Opens a website using the provided URL."""
    url = parameters.get("url")
    if not url:
        raise ValueError("Missing URL parameter for 'open' action.")
    driver.get(url)
    logging.info(f"Opened URL: {url}")
    time.sleep(3)  # Allow the page to load

def handle_click(parameters, driver):
    """Clicks an element identified by its visible text."""
    element_text = parameters.get("element_text")
    if not element_text:
        raise ValueError("Missing element_text parameter for 'click' action.")
    element = safe_find_element(driver, By.XPATH, f"//*[contains(text(), '{element_text}')]")
    if element:
        element.click()
        logging.info(f"Clicked on element with text: {element_text}")
    else:
        raise ValueError("Element with specified text not found.")

def handle_scroll(parameters, driver):
    """Scrolls the page based on provided direction and distance."""
    direction = parameters.get("direction", "down")
    distance = parameters.get("distance", 500)
    if direction == "up":
        driver.execute_script(f"window.scrollBy(0, -{distance});")
        logging.info(f"Scrolled up by {distance} pixels.")
    else:
        driver.execute_script(f"window.scrollBy(0, {distance});")
        logging.info(f"Scrolled down by {distance} pixels.")

def handle_fill_form(parameters, driver):
    """Fills a form field with the provided value."""
    field = parameters.get("field")
    value = parameters.get("value")
    if not field or not value:
        raise ValueError("Missing field or value parameter for 'fill_form' action.")
    element = safe_find_element(driver, By.NAME, field)
    if element:
        element.clear()
        element.send_keys(value)
        logging.info(f"Filled form field '{field}' with '{value}'.")
    else:
        raise ValueError("Form field not found.")

def handle_search(parameters, driver):
    """Searches for a query using YouTube's search bar."""
    query = parameters.get("query")
    if not query:
        raise ValueError("Missing query parameter for 'search' action.")
    search_box = safe_find_element(driver, By.NAME, "search_query", timeout=15)
    if search_box:
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        logging.info(f"Searched for: {query}")
    else:
        raise ValueError("Search box not found.")

def handle_play_video(parameters, driver):
    video_index = parameters.get("video_index", 1)
    xpath_expr = f"(//ytd-video-renderer//a[@id='video-title'])[{video_index}]"
    video = safe_find_element(driver, By.XPATH, xpath_expr, timeout=15)
    if video:
        video.click()
        logging.info(f"Played video at index: {video_index}")
    else:
        raise ValueError("Video element not found.")


# Mapping intents to handler functions
ACTION_HANDLERS = {
    "open": handle_open,
    "click": handle_click,
    "scroll": handle_scroll,
    "fill_form": handle_fill_form,
    "search": handle_search,
    "play_video": handle_play_video
}

# --------------------- Command Execution ---------------------

def execute_command(command, driver, context=""):
    """
    Dynamically executes AI-generated browser actions.
    It queries the AI for a structured JSON response and then calls the corresponding action handler.
    """
    while True:
        screenshot_path, extracted_text = capture_screenshot(driver)
        encoded_image = encode_image(screenshot_path)
        page_source = driver.page_source
        context = get_browser_context(driver)
        time.sleep(1.5)  # Cooldown to avoid API overload

        structured_output = interpret_command(command, page_source, extracted_text, encoded_image, context)
        logging.info(f"AI Structured Output: {structured_output}")

        if structured_output.get("missing_info"):
            follow_up_question = structured_output["question"]
            speak(follow_up_question)
            additional_info = listen()
            if additional_info:
                command += " " + additional_info  # Append follow-up info and retry
                continue
            else:
                speak("No additional information provided. Aborting command.")
                break
        else:
            intent = structured_output.get("intent")
            parameters = structured_output.get("parameters", {})

            if not intent:
                logging.error("❌ OpenAI did not return a valid intent.")
                speak("Sorry, I couldn't determine the required action.")
                break

            logging.info(f"🔄 Received intent: {intent} with parameters: {parameters}")

            if intent in ACTION_HANDLERS:
                try:
                    ACTION_HANDLERS[intent](parameters, driver)
                    logging.info(f"✅ Successfully executed intent: {intent}")
                except Exception as e:
                    logging.error(f"❌ Error executing intent '{intent}': {e}")
                    speak(f"There was an error executing the {intent} action.")
                break
            else:
                logging.error(f"❌ Unknown intent: {intent}")
                speak(f"I don't know how to perform the action {intent}.")
                break
