FROM python:3.13-slim

# Install Java and required utilities
RUN apt-get update && apt-get install -y default-jre wget unzip && apt-get clean

WORKDIR /app

# Download the Open-Source Offline LanguageTool engine
RUN wget https://languagetool.org/download/LanguageTool-stable.zip \
    && unzip LanguageTool-stable.zip \
    && rm LanguageTool-stable.zip

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Pre-download small NLTK data
RUN python -c "import nltk; \
nltk.download('punkt_tab', quiet=True); \
nltk.download('averaged_perceptron_tagger', quiet=True); \
nltk.download('stopwords', quiet=True)"

# Start BOTH services:
# 1) LanguageTool Java server (offline)
# 2) Gunicorn for Flask
CMD java -cp LanguageTool-*/languagetool-server.jar org.languagetool.server.HTTPServer --port 8081 --allow-origin '*' & \
    gunicorn app:app --bind 0.0.0.0:$PORT
