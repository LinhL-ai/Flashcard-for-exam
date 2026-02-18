"""
Exam Flashcard Generator
========================
Generates exam-preparation flashcards from course slide PDFs using OpenAI.

Usage:
  python generate_flashcards.py --slides slides.pdf --api-key key.txt
  python generate_flashcards.py --slides slides.pdf --api-key key.txt --outline exam_outline.txt
  python generate_flashcards.py --slides slides.pdf --api-key YOUR_KEY_HERE --outline exam_outline.txt

Arguments:
  --slides    Path to course slide PDF (required)
  --api-key   OpenAI API key, or path to a .txt file containing the key (required)
  --outline   Path to exam outline/focus file (optional, improves relevance)
  --output    Output JSON path (default: flashcards.json in same dir as slides)
  --model     OpenAI model to use (default: gpt-4o)
"""

import argparse
import json
import os
import sys
import base64
import math

try:
    from openai import OpenAI
except ImportError:
    print("Installing openai package...")
    os.system(f"{sys.executable} -m pip install openai")
    from openai import OpenAI


def resolve_api_key(value):
    """Accept either a raw key string or a path to a .txt file."""
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as f:
            return f.read().strip()
    return value.strip()


def extract_slides_via_openai(client, pdf_path, model, exam_outline=None):
    """Send PDF pages to OpenAI vision to extract text content from slides."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"  PDF has {total_pages} pages")

    # Process in batches to stay within token limits
    BATCH_SIZE = 15
    all_slides = {}

    for batch_start in range(0, total_pages, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_pages)
        print(f"  Extracting slides {batch_start+1}-{batch_end}...")

        images = []
        for page_num in range(batch_start, batch_end):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append((page_num + 1, b64))

        # Build message with images
        content = [
            {
                "type": "text",
                "text": (
                    f"Extract the text content from each slide (pages {batch_start+1}-{batch_end}). "
                    "For each slide, return a JSON object with the page number as key and the full text as value. "
                    "Include all text, formulas (in plain text notation), bullet points, and labels. "
                    "Return ONLY valid JSON, no markdown. Example: {\"1\": \"slide text...\", \"2\": \"...\"}"
                ),
            }
        ]
        for page_num, b64 in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"},
                }
            )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=0.1,
            max_tokens=4000,
        )

        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
        text = text.strip()

        try:
            batch_slides = json.loads(text)
            all_slides.update(batch_slides)
            print(f"    -> Extracted {len(batch_slides)} slides")
        except json.JSONDecodeError:
            print(f"    -> Warning: Could not parse batch {batch_start+1}-{batch_end}")

    doc.close()
    return all_slides


def extract_slides_text_only(pdf_path):
    """Fallback: extract text directly from PDF without vision API."""
    import fitz

    doc = fitz.open(pdf_path)
    slides = {}
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            slides[str(i + 1)] = text
    doc.close()
    return slides


def generate_flashcards(client, slides, model, exam_outline=None):
    """Generate flashcards from slide content using OpenAI."""
    # Group slides into chunks for processing
    slide_nums = sorted(slides.keys(), key=lambda x: int(x))
    CHUNK_SIZE = 20
    chunks = []
    for i in range(0, len(slide_nums), CHUNK_SIZE):
        chunk_keys = slide_nums[i : i + CHUNK_SIZE]
        chunk_text = "\n\n".join(
            f"--- Slide {k} ---\n{slides[k]}" for k in chunk_keys
        )
        chunks.append((chunk_keys, chunk_text))

    outline_section = ""
    if exam_outline:
        outline_section = f"\nEXAM FOCUS (prioritize these topics):\n{exam_outline}\n"

    all_flashcards = []
    for idx, (chunk_keys, chunk_text) in enumerate(chunks):
        print(f"  Generating flashcards for slides {chunk_keys[0]}-{chunk_keys[-1]}...")

        prompt = f"""You are creating exam preparation flashcards for a university course.
{outline_section}
SLIDE CONTENT (slides {chunk_keys[0]}-{chunk_keys[-1]}):
{chunk_text}

Generate 6-12 high-quality flashcards from these slides. Each flashcard should:
1. Have a clear, specific QUESTION on the front
2. Have a comprehensive but concise ANSWER on the back
3. Focus on exam-relevant content and key concepts
4. Include practical examples where relevant
5. Cover both conceptual understanding and practical application
6. For mathematical formulas, use plain text notation (e.g., Y_i = b0 + b1*X1 + e_i)
7. Skip purely structural slides (agenda, title pages)

Identify the topic/chapter each card belongs to based on the slide content.

Return ONLY a JSON array of objects with "question", "answer", and "topic" fields.
No markdown, no code blocks, just valid JSON.
"""

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
        content = content.strip()

        try:
            cards = json.loads(content)
            print(f"    -> {len(cards)} flashcards generated")
            all_flashcards.extend(cards)
        except json.JSONDecodeError as e:
            print(f"    -> Warning: JSON parse error: {e}")

    return all_flashcards


def build_html(flashcards, output_path):
    """Build the interactive HTML flashcard app with embedded data."""
    html_template_path = os.path.join(os.path.dirname(__file__), "flashcard_template.html")
    if not os.path.exists(html_template_path):
        print(f"  Warning: {html_template_path} not found, skipping HTML build.")
        print(f"  Copy flashcard_template.html to the same folder as this script.")
        return None

    with open(html_template_path, "r", encoding="utf-8") as f:
        template = f.read()

    json_data = json.dumps(flashcards, ensure_ascii=True)
    html = template.replace("__FLASHCARD_DATA_PLACEHOLDER__", json_data)

    html_path = output_path.replace(".json", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  HTML app saved to: {html_path}")
    return html_path


def main():
    parser = argparse.ArgumentParser(description="Generate exam flashcards from course slides")
    parser.add_argument("--slides", required=True, help="Path to course slide PDF")
    parser.add_argument("--api-key", required=True, help="OpenAI API key or path to key file")
    parser.add_argument("--outline", default=None, help="Path to exam outline/focus file (optional)")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model (default: gpt-4o)")
    parser.add_argument("--text-only", action="store_true", help="Extract text from PDF without vision API (faster/cheaper)")
    args = parser.parse_args()

    if not os.path.isfile(args.slides):
        print(f"Error: Slide file not found: {args.slides}")
        sys.exit(1)

    api_key = resolve_api_key(args.api_key)
    client = OpenAI(api_key=api_key)

    output_path = args.output or os.path.join(
        os.path.dirname(args.slides), "flashcards.json"
    )

    # Load exam outline if provided
    exam_outline = None
    if args.outline and os.path.isfile(args.outline):
        with open(args.outline, "r", encoding="utf-8") as f:
            exam_outline = f.read().strip()
        print(f"Loaded exam outline from: {args.outline}")

    # Step 1: Extract slide content
    print("\n[Step 1/3] Extracting slide content...")
    if args.text_only:
        try:
            slides = extract_slides_text_only(args.slides)
            print(f"  Extracted text from {len(slides)} slides (text-only mode)")
        except ImportError:
            print("  Error: PyMuPDF required. Run: pip install pymupdf")
            sys.exit(1)
    else:
        try:
            slides = extract_slides_via_openai(client, args.slides, args.model, exam_outline)
        except ImportError:
            print("  PyMuPDF not found. Installing...")
            os.system(f"{sys.executable} -m pip install pymupdf")
            slides = extract_slides_via_openai(client, args.slides, args.model, exam_outline)

    if not slides:
        print("  Error: No slide content extracted.")
        sys.exit(1)

    # Save extracted slides
    slides_path = output_path.replace(".json", "_slides.json")
    with open(slides_path, "w", encoding="utf-8") as f:
        json.dump(slides, f, indent=2, ensure_ascii=False)
    print(f"  Slide content saved to: {slides_path}")

    # Step 2: Generate flashcards
    print("\n[Step 2/3] Generating flashcards...")
    flashcards = generate_flashcards(client, slides, args.model, exam_outline)

    # Save flashcards JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flashcards, f, indent=2, ensure_ascii=False)
    print(f"\n  {len(flashcards)} flashcards saved to: {output_path}")

    # Step 3: Build HTML app
    print("\n[Step 3/3] Building HTML app...")
    build_html(flashcards, output_path)

    # Summary
    from collections import Counter
    topic_counts = Counter(c.get("topic", "Unknown") for c in flashcards)
    print(f"\n{'='*50}")
    print(f"DONE! {len(flashcards)} flashcards across {len(topic_counts)} topics")
    print(f"{'='*50}")
    for topic, count in topic_counts.most_common():
        print(f"  {topic}: {count}")


if __name__ == "__main__":
    main()
