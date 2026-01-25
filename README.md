# OCR-Robust Machine Translation for Vocational Education

This repository contains the **codebase accompanying the paper**:

> **Robustness of Large Language Models to OCR Noise in Domain-Specific Machine Translation: A Vocational Case Study**

The project implements an **end-to-end OCR-to-Machine Translation (MT) pipeline**
for translating **scanned German vocational manuals** into English and evaluating
the robustness of **instruction-tuned large language models (LLMs)** compared to
conventional neural machine translation (NMT) systems under **naturally occurring
OCR noise**.

---

## End-to-End OCR-to-MT Pipeline

The following diagram illustrates the complete workflow used in the paper, covering
OCR preprocessing, domain-adaptive translation, and multi-level evaluation.

![OCR-to-MT Pipeline](figures/framework.png)

### Pipeline Overview

- **OCR Preprocessing**
  - Input: scanned German PDF manuals
  - Layout-aware multimodal OCR
  - No manual correction or post-editing
  - Output serialized as structured JSON

- **Domain-Adaptive Translation**
  - Instruction-tuned LLMs:
    - Gemini Flash
    - Qwen 2.5 (14B)
    - Llama 3.1 (8B)
    - Aya (8B)
  - NMT baselines:
    - NLLB-200 (600M)
    - MarianMT

- **Evaluation Framework**
  - Reference-free LLM-as-a-Judge evaluation on the full corpus
  - Reference-based automatic metrics and expert human evaluation on a verified subset

All translation systems operate on **identical OCR-derived input** to enable fair
robustness comparison.

---


## Setup

1. ```bash
   cd ocr
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Project Structure

```
.
├── pdfs/           # Place PDF files here for processing
├── output/         # Generated JSON files will be stored here
├── ocr_page.py     # Main OCR script
├── translate_json.py # Translation script
└── .env            # Environment variables (API key)
```

## Usage

1. Place your PDF files in the `pdfs` directory.

2. Run the OCR process:
   ```bash
   python ocr_page.py
   ```
   This will:
   - Process each PDF in the `pdfs` directory
   - Convert PDF pages to images
   - Perform OCR using Gemini AI
   - Save results as `{filename}_ocr.json` in the `output` directory

3. Translate the extracted text:
   ```bash
   python translate_json.py
   ```
   This will:
   - Process each `*_ocr.json` file in the `output` directory
   - Translate German text to English
   - Save results as `{filename}_translated.json`

## Output Format

### OCR Output (`*_ocr.json`):
```json
{
  "document": {
    "total_pages": <number>,
    "pages": [
      {
        "page_number": <number>,
        "content": "<extracted German text>"
      }
    ]
  }
}
```

### Translation Output (`*_translated.json`):
```json
{
  "document": {
    "total_pages": <number>,
    "pages": [
      {
        "page_number": <number>,
        "german": "<original German text>",
        "english": "<translated English text>"
      }
    ]
  }
}
```

## Rate Limiting

The scripts implement rate limiting to avoid overwhelming the Gemini API:
- 5-second interval between requests
- Exponential backoff for failed requests
- Maximum of 12 retry attempts per request

## Error Handling

- Failed OCR or translation attempts are automatically retried
- Intermediate results are saved after each page
- Detailed error messages are printed to the console
- Empty or failed translations are marked with "[Translation failed]"

