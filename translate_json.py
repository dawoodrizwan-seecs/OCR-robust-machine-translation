import os
import json
import time
import threading
import google.generativeai as genai
from dotenv import load_dotenv

# Rate limiter setup
_request_lock = threading.Lock()
_last_request_time = 0.0
REQUEST_INTERVAL = 5.0  # seconds between requests

def wait_for_rate_limit():
    """Blocks until a new request is allowed under the REQUEST_INTERVAL policy."""
    global _last_request_time
    with _request_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < REQUEST_INTERVAL:
            to_sleep = REQUEST_INTERVAL - elapsed
            time.sleep(to_sleep)
            now = time.monotonic()
        _last_request_time = now

def configure_api():
    """Loads the Gemini API key from .env file."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in the .env file.")
    genai.configure(api_key=api_key)

def translate_paragraph(german_text):
    """Translate a German paragraph to English using Gemini.
    
    Args:
        german_text: A string containing German text
    
    Returns:
        str: English translation of the text
    """
    if not german_text or not german_text.strip():
        return ""

    model = genai.GenerativeModel('gemini-flash-lite-latest')
    
    prompt = [
        "Translate the following German paragraph to English. Rules:",
        "1. Maintain technical accuracy and terminology",
        "2. Keep the same flowing, paragraph style",
        "3. Preserve all technical information",
        "4. Output only the English translation, no additional text",
        "---",
        german_text,
        "---"
    ]
    
    max_retries = 12
    base_backoff = 2.0
    
    for attempt in range(1, max_retries + 1):
        try:
            wait_for_rate_limit()
            response = model.generate_content(prompt)
            translation = response.text.strip()
            if translation:
                return translation
            
            print(f"Translation attempt {attempt} produced empty output, retrying...")
            
        except Exception as e:
            print(f"Attempt {attempt}/{max_retries} - Translation error: {e}")
            sleep_seconds = min(60.0, base_backoff * (2 ** (attempt - 1)))
            time.sleep(sleep_seconds)
    
    return "[Translation failed]"

def translate_json_file(input_path, output_path):
    """Translate content from input JSON file and save to output JSON file.
    
    Args:
        input_path: Path to input JSON file with German text
        output_path: Path to save translated JSON file
    """
    print(f"\nReading: {input_path}")
    
    # Read input JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create output structure
    translations = {
        "document": {
            "total_pages": data["document"]["total_pages"],
            "pages": []
        }
    }
    
    # Process each page
    for page in data["document"]["pages"]:
        print(f"Translating page {page['page_number']}...")
        
        # Translate the content
        german_text = page["content"]
        english_text = translate_paragraph(german_text)
        
        # Create the translated page entry
        translated_page = {
            "page_number": page["page_number"],
            "german": german_text,
            "english": english_text
        }
        
        translations["document"]["pages"].append(translated_page)
        
        # Save progress after each page
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        
        print(f"Completed page {page['page_number']}")
    
    print(f"\nTranslation completed. Saved to: {output_path}")

def main():
    """Process all OCR JSON files in the output directory."""
    configure_api()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    
    # Find and process JSON files
    for filename in os.listdir(output_dir):
        if not filename.endswith('_ocr.json'):
            continue
            
        input_path = os.path.join(output_dir, filename)
        output_filename = filename.replace('_ocr.json', '_translated.json')
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            translate_json_file(input_path, output_path)
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    main()