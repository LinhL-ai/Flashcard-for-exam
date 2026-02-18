# Exam Flashcard Generator

Generate interactive exam-preparation flashcards from any course slide PDF using OpenAI.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate flashcards from your slides
python generate_flashcards.py --slides your_slides.pdf --api-key YOUR_OPENAI_KEY

# 3. Open the generated HTML file in your browser
# -> flashcards.html (same folder as your PDF)
```

## Usage

### Basic (slides only)
```bash
python generate_flashcards.py --slides slides.pdf --api-key sk-proj-xxx
```

### With exam outline (recommended for focused cards)
```bash
python generate_flashcards.py --slides slides.pdf --api-key sk-proj-xxx --outline exam_outline.txt
```

### API key from file
```bash
python generate_flashcards.py --slides slides.pdf --api-key path/to/key.txt
```

### Text-only mode (faster, cheaper, no vision API)
```bash
python generate_flashcards.py --slides slides.pdf --api-key sk-proj-xxx --text-only
```

### All options
| Flag | Description | Required |
|------|-------------|----------|
| `--slides` | Path to course slide PDF | Yes |
| `--api-key` | OpenAI API key or path to key file | Yes |
| `--outline` | Exam outline/focus file (plain text) | No |
| `--output` | Output JSON path (default: flashcards.json) | No |
| `--model` | OpenAI model (default: gpt-4o) | No |
| `--text-only` | Skip vision API, extract text directly | No |

## Output Files

| File | Description |
|------|-------------|
| `flashcards.json` | Raw flashcard data (question/answer/topic) |
| `flashcards.html` | Interactive study app (open in browser) |
| `flashcards_slides.json` | Extracted slide content (intermediate) |

## Exam Outline Format

Plain text file listing exam topics. Example:

```
Slide 32: Interpret linear regression
Slide 51: Interpret coefficient plot
Topic: Difference between clustering & classification
Topic: Three conditions for causality
```

## Flashcard App Features

- **Flip cards** - click or press Space
- **Rate confidence** - Hard / Medium / Easy (keys 1/2/3)
- **Filter by topic** - click topic buttons
- **Filter by difficulty** - Hard Only / Unrated buttons
- **Shuffle** - randomize order (press S)
- **Quiz mode** - type answers before revealing
- **Add/Edit/Delete cards** - click Edit on card or Manage button
- **Import/Export JSON** - backup or share card sets
- **Progress saved** - ratings persist in browser localStorage

## Flashcard JSON Format

```json
[
  {
    "question": "What is linear regression?",
    "answer": "A statistical method that models the relationship between...",
    "topic": "Regression"
  }
]
```

You can manually create or edit this JSON and import it into the app via the Manage button.
