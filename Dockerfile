FROM python:3.13-slim

# Install Java (OpenJDK 21 - latest available in Debian Trixie)
RUN apt-get update && \
    apt-get install -y openjdk-21-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify Java installation
RUN java -version

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Download NLTK data at build time
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True); nltk.download('averaged_perceptron_tagger', quiet=True); nltk.download('stopwords', quiet=True)"

# Start Gunicorn server (Render will provide $PORT automatically)
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1