FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download only NLTK data (small)
RUN python -c "import nltk; \
nltk.download('punkt_tab', quiet=True); \
nltk.download('averaged_perceptron_tagger', quiet=True); \
nltk.download('stopwords', quiet=True)"

# Start app with Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
