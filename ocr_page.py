import google.generativeai as genai
from PIL import Image
import time
import re
import threading
import json
import os

# Rate limiter to avoid sending more than 12 requests per minute
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

def ocr_with_gemini(image):
    """Performs OCR on a single image using Gemini, filtering for meaningful automotive-related sentences.

    Args:
        image: A PIL Image object containing the scanned page

    Returns:
        str: Extracted text with one sentence per line, filtered for automotive content
    """
    model = genai.GenerativeModel('gemini-flash-lite-latest')

    prompt = [
        "You are an expert OCR tool. Analyze the provided image and express its content following these rules:",
        "1. Read and understand all the text content on the page.",
        "2. Rewrite the entire page's content as a single, flowing paragraph in German.",
        "3. Make minimal adjustments to connect ideas smoothly while keeping the original meaning.",
        "4. Maintain all technical information, facts, and key points accurately.",
        "5. Exclude headers, footers, page numbers, and image captions.",
        "6. Keep the technical terminology exactly as written.",
        "7. Output only the final paragraph without any additional text or commentary.",
        "8. Focus on creating a natural flow while preserving the original German content.",
        image
    ]

    max_retries = 12
    base_backoff = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            wait_for_rate_limit()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err_text = str(e)
            print(f"Attempt {attempt}/{max_retries} - OCR error: {err_text}")

            # Try to parse a suggested retry delay from the message
            sleep_seconds = None
            m = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", err_text)
            if m:
                try:
                    sleep_seconds = float(m.group(1)) + 1.0
                except Exception:
                    sleep_seconds = None
            else:
                m2 = re.search(r"retry_delay\W+seconds:\s*([0-9]+)", err_text)
                if m2:
                    try:
                        sleep_seconds = float(m2.group(1)) + 1.0
                    except Exception:
                        sleep_seconds = None

            if sleep_seconds is None:
                # exponential backoff (cap at 60s)
                sleep_seconds = min(60.0, base_backoff * (2 ** (attempt - 1)))

            print(f"Waiting {sleep_seconds:.1f}s before retrying OCR (attempt {attempt})")
            time.sleep(sleep_seconds)

    print(f"OCR failed after {max_retries} attempts.")
    return ""

def process_pdf_pages(images, output_path):
    """Process a list of page images and save the results to a JSON file.
    
    Args:
        images: List of PIL Image objects, one per page
        output_path: Path where to save the JSON output file
    
    Returns:
        dict: Dictionary containing the processed results
    """
    results = {
        "document": {
            "total_pages": len(images),
            "pages": []
        }
    }
    
    for page_num, image in enumerate(images, 1):
        print(f"Processing page {page_num}/{len(images)}...")
        
        # Extract text from the page
        extracted_text = ocr_with_gemini(image)
        
        # Clean up the extracted text and ensure it's a single paragraph
        content = extracted_text.strip()
        
        # Add page data to results
        page_data = {
            "page_number": page_num,
            "content": content
        }
        results["document"]["pages"].append(page_data)
        
        # Save intermediate results after each page
        save_json_results(results, output_path)
        
    return results

def save_json_results(results, output_path):
    """Save results to a JSON file with proper formatting.
    
    Args:
        results: Dictionary containing the results
        output_path: Path where to save the JSON file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import fitz  # PyMuPDF
    import io
    import sys
    from dotenv import load_dotenv

    # Configure API
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file")
        sys.exit(1)
    genai.configure(api_key=api_key)

    # Set up directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_dir = os.path.join(script_dir, 'pdfs')
    output_dir = os.path.join(script_dir, 'output')

    if not os.path.isdir(pdf_dir):
        print(f"Error: PDF directory not found at {pdf_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Process each PDF in the directory
    for filename in os.listdir(pdf_dir):
        if not filename.lower().endswith('.pdf'):
            continue

        pdf_path = os.path.join(pdf_dir, filename)
        base_name = os.path.splitext(filename)[0]
        json_output_path = os.path.join(output_dir, f"{base_name}_ocr.json")

        print(f"\nProcessing PDF: {filename}")

        try:
            # Open PDF and convert pages to images
            doc = fitz.open(pdf_path)
            images = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
            
            # Process all pages and save results
            results = process_pdf_pages(images, json_output_path)
            print(f"Successfully processed {filename}. Output saved to {json_output_path}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

        finally:
            # Clean up
            for img in images:
                try:
                    img.close()
                except:
                    pass
            try:
                doc.close()
            except:
                pass
