import os
import json
import time
import threading
import google.generativeai as genai
from dotenv import load_dotenv

# ------------------ Rate limiter setup ------------------
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
            time.sleep(REQUEST_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


# ------------------ API configuration ------------------
def configure_api():
    """Loads the Gemini API key from .env file."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in the .env file.")
    genai.configure(api_key=api_key)


# ------------------ Translation function ------------------
def translate_to_urdu(english_text):
    """Translate English paragraph to Urdu using Gemini API."""
    if not english_text or not english_text.strip():
        return ""

    model = genai.GenerativeModel("gemini-flash-lite-latest")

    prompt = [
        "Translate the following English paragraph into Urdu.",
        "Rules:",
        "1. Maintain full meaning and accuracy.",
        "2. Use fluent, natural Urdu — not transliteration.",
        "3. Keep the paragraph format same as original.",
        "4. Output only the Urdu translation, no additional comments.",
        "---",
        english_text,
        "---"
    ]

    max_retries = 12
    base_backoff = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            wait_for_rate_limit()
            response = model.generate_content(prompt)
            urdu_text = response.text.strip()
            if urdu_text:
                return urdu_text

            print(f"Attempt {attempt}: Empty response, retrying...")

        except Exception as e:
            print(f"Attempt {attempt}/{max_retries} failed: {e}")
            sleep_time = min(60.0, base_backoff * (2 ** (attempt - 1)))
            time.sleep(sleep_time)

    return "[Urdu translation failed]"


# ------------------ JSON processing ------------------
def translate_json_file(input_path, output_path):
    """Translate English text in JSON file to Urdu and save output."""
    print(f"\nReading: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    urdu_translations = {
        "document": {
            "total_pages": data["document"]["total_pages"],
            "pages": []
        }
    }

    for page in data["document"]["pages"]:
        page_num = page["page_number"]
        print(f"Translating page {page_num}...")

        english_text = page["english"]
        urdu_text = translate_to_urdu(english_text)

        translated_page = {
            "page_number": page_num,
            "german": page["german"],
            "english": english_text,
            "urdu": urdu_text
        }

        urdu_translations["document"]["pages"].append(translated_page)

        # Save after each page for safety
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(urdu_translations, f, ensure_ascii=False, indent=2)

        print(f"✅ Completed page {page_num}")

    print(f"\nAll pages translated. Saved to: {output_path}")


# ------------------ Main function ------------------
def main():
    """Find and translate all _translated.json files in the output directory."""
    configure_api()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")

    for filename in os.listdir(output_dir):
        if not filename.endswith("_translated.json"):
            continue

        input_path = os.path.join(output_dir, filename)
        output_filename = filename.replace("_translated.json", "_urdu.json")
        output_path = os.path.join(output_dir, output_filename)

        try:
            translate_json_file(input_path, output_path)
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")


if __name__ == "__main__":
    main()
