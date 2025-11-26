```markdown
# 📝 IELTS Writing Band Score Checker

An automated tool to analyze IELTS writing samples and provide band scores for Grammar (GRA) and Vocabulary (LR).

## Features
- Grammar and spelling error detection
- Lexical diversity analysis
- Sentence complexity assessment
- IELTS band score estimation (GRA & LR)
- Support for Task 1 (Reports/Letters) and Task 2 (Essays)

## Tech Stack
- Backend: Flask (Python)
- Grammar Checking: LanguageTool
- NLP: NLTK
- Frontend: HTML, CSS, JavaScript

## Local Development

### Prerequisites
- Python 3.9+
- Java Runtime (for LanguageTool)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/crutvik65-create/ielts-writing-checker.git
cd ielts-writing-checker
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Java (if not already installed):
```bash
# macOS
brew install openjdk

# Ubuntu/Debian
sudo apt-get install default-jre

# Windows
# Download from https://www.oracle.com/java/technologies/downloads/
```

5. Run the application:
```bash
python app.py
```

6. Open browser: `http://localhost:3333`

## Deployment

Deployed on Render: [Your Render URL]

## Important Notes

- **TA/TR** (Task Achievement) and **CC** (Coherence & Cohesion) scores are estimates
- Only **GRA** (Grammar) and **LR** (Lexical Resource) are reliably assessed automatically
- For accurate TA/CC assessment, consult trained IELTS examiners

## License
MIT

## Author
Created by crutvik65-create
```

### 1.4 Create `render.yaml` (Optional - for Infrastructure as Code)
```yaml
services:
  - type: web
    name: ielts-writing-checker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
      - key: JAVA_HOME
        value: /opt/java/openjdk
```