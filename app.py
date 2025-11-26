from flask import Flask, render_template, request, jsonify
import language_tool_python
import nltk
import re
from collections import Counter
import os
import subprocess
import sys

app = Flask(__name__)

def check_java():
    """Check if Java is available"""
    try:
        result = subprocess.run(['java', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        print("✓ Java is available")
        return True
    except FileNotFoundError:
        print("✗ Java not found in PATH")
        return False
    except Exception as e:
        print(f"✗ Java check failed: {e}")
        return False

# Download required NLTK data
def download_nltk_data():
    try:
        nltk.download('punkt_tab', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✓ NLTK resources downloaded successfully.")
    except Exception as e:
        print(f"⚠ Warning: Could not download NLTK resources: {e}")

# Check Java availability
java_available = check_java()

# Initialize LanguageTool only if Java is available
lt_tool = None
if java_available:
    try:
        lt_tool = language_tool_python.LanguageTool('en-GB')
        print("✓ LanguageTool initialized successfully.")
    except Exception as e:
        print(f"✗ Error initializing LanguageTool: {e}")
        lt_tool = None
else:
    print("⚠ LanguageTool disabled: Java not available")
    print("  Grammar checking will not work without Java.")
    print("  Please install Java in your deployment environment.")

def calculate_lexical_diversity(text):
    """Calculate lexical diversity metrics for vocabulary assessment."""
    tokens = nltk.word_tokenize(re.sub(r'[^\w\s]', '', text.lower()))
    tokens = [t for t in tokens if len(t) > 1]
    
    total_tokens = len(tokens)
    unique_types = len(set(tokens))
    ttr = (unique_types / total_tokens) * 100 if total_tokens > 0 else 0
    word_freq = Counter(tokens)
    most_common = word_freq.most_common(5)
    
    return total_tokens, unique_types, ttr, most_common

def assess_sentence_complexity(text):
    """Assess sentence structure complexity."""
    sentences = nltk.sent_tokenize(text)
    sentence_count = len(sentences)
    words = nltk.word_tokenize(text)
    avg_sentence_length = len(words) / sentence_count if sentence_count > 0 else 0
    return sentence_count, avg_sentence_length

def round_ielts_score(score):
    """
    Round score according to IELTS official rules.
    - If ends in .25, round up to .5
    - If ends in .75, round up to next whole number
    - Otherwise round to nearest 0.5
    """
    decimal_part = score - int(score)
    
    if decimal_part < 0.25:
        return int(score)
    elif decimal_part < 0.5:
        return int(score) + 0.5
    elif decimal_part < 0.75:
        return int(score) + 0.5
    else:
        return int(score) + 1

def get_band_score(error_count, word_count, ttr, avg_sentence_length, task_type):
    """
    Estimate IELTS band score based on multiple criteria.
    This is a simplified estimation based on common IELTS assessment patterns.
    """
    # Error density (errors per 100 words)
    error_density = (error_count / word_count * 100) if word_count > 0 else 0
    
    # Initialize scores for each criterion (0-9 scale)
    gra_score = 9  # Grammatical Range and Accuracy
    lr_score = 9   # Lexical Resource
    
    # --- GRA Score (Grammar & Accuracy) ---
    if error_density == 0:
        gra_score = 9
    elif error_density <= 1:
        gra_score = 8
    elif error_density <= 2:
        gra_score = 7
    elif error_density <= 4:
        gra_score = 6
    elif error_density <= 6:
        gra_score = 5
    else:
        gra_score = 4
    
    # Adjust for sentence complexity
    if avg_sentence_length < 10:
        gra_score -= 1  # Simple sentences reduce GRA
    elif avg_sentence_length > 25:
        gra_score = min(gra_score + 0.5, 9)  # Complex sentences boost GRA
    
    # --- LR Score (Vocabulary) ---
    if ttr >= 70:
        lr_score = 9
    elif ttr >= 65:
        lr_score = 8
    elif ttr >= 58:
        lr_score = 7
    elif ttr >= 50:
        lr_score = 6
    elif ttr >= 42:
        lr_score = 5
    else:
        lr_score = 4
    
    # Task-specific adjustments
    if task_type == "report":
        # Reports need more formal vocabulary and data description
        if ttr < 55:
            lr_score -= 0.5
    elif task_type == "letter":
        # Letters need appropriate tone and format
        if error_count > 2:
            gra_score -= 0.5
    
    # Apply IELTS rounding rules
    gra_score = round_ielts_score(max(4, min(9, gra_score)))
    lr_score = round_ielts_score(max(4, min(9, lr_score)))
    
    return gra_score, lr_score, error_density

def calculate_task_score(ta_score, cc_score, lr_score, gra_score):
    """
    Calculate individual task score from 4 criteria.
    Task Score = Average of all 4 criteria (TA/TR, CC, LR, GRA)
    """
    raw_average = (ta_score + cc_score + lr_score + gra_score) / 4
    return round_ielts_score(raw_average)

def calculate_overall_writing_score(task1_score, task2_score):
    """
    Calculate overall writing score according to IELTS rules.
    Task 2 is worth twice as much as Task 1.
    Formula: (Task 1 + Task 2 × 2) ÷ 3
    """
    raw_score = (task1_score + (task2_score * 2)) / 3
    return round_ielts_score(raw_score)

def analyze_text(text, task_type):
    """Analyze text and provide detailed IELTS band score breakdown."""
    if not lt_tool:
        return {
            "error": "Grammar checking is unavailable. Java is required for LanguageTool but is not installed on this server. Please contact the administrator or try again later.",
            "java_available": False
        }
    
    # Grammar check
    matches = lt_tool.check(text)
    
    errors = []
    for match in matches:
        errors.append({
            "message": match.message,
            "context": match.context,
            "suggestions": match.replacements[:3]
        })
    
    # Lexical analysis
    tokens, types, ttr, most_common = calculate_lexical_diversity(text)
    sentence_count, avg_length = assess_sentence_complexity(text)
    
    # Calculate band scores
    gra_band, lr_band, error_density = get_band_score(
        len(matches), tokens, ttr, avg_length, task_type
    )
    
    # Generate feedback
    feedback = []
    if gra_band >= 7 and lr_band >= 7:
        feedback.append("✓ Excellent! Your writing shows good command of grammar and vocabulary.")
    elif gra_band >= 6 and lr_band >= 6:
        feedback.append("✓ Good work! Some minor improvements in accuracy and vocabulary range needed.")
    else:
        feedback.append("⚠ Needs improvement in grammar accuracy and vocabulary variety.")
    
    if len(matches) > 0:
        feedback.append(f"• Focus on fixing spelling and grammar errors (found {len(matches)})")
    if ttr < 55:
        feedback.append(f"• Expand vocabulary variety (current TTR: {ttr:.1f}%)")
    if avg_length < 12:
        feedback.append(f"• Use more complex sentence structures (current avg: {avg_length:.1f} words)")
    
    # Note: We cannot automatically assess TA/TR and CC as they require human judgment
    # For demonstration, we'll estimate TA/CC based on available metrics
    # In a real IELTS test, these would be assessed by trained examiners
    
    # Estimate Task Achievement/Response (simplified)
    ta_score = 7.0  # Default - would need human assessment
    if tokens < 150:
        ta_score = 5.0  # Under word count
    elif tokens < 200:
        ta_score = 6.0
    elif tokens >= 250:
        ta_score = 7.0
    
    # Estimate Coherence and Cohesion (simplified)
    cc_score = 6.5  # Default - would need human assessment
    if sentence_count < 5:
        cc_score = 5.5  # Too few sentences
    elif avg_length > 15 and avg_length < 25:
        cc_score = 7.0  # Good sentence variety
    
    # Apply IELTS rounding
    ta_score = round_ielts_score(ta_score)
    cc_score = round_ielts_score(cc_score)
    
    # Calculate task score (average of 4 criteria)
    task_score = calculate_task_score(ta_score, cc_score, lr_band, gra_band)
    
    return {
        "errors": errors,
        "error_count": len(matches),
        "lexical": {
            "total_words": tokens,
            "unique_words": types,
            "ttr": round(ttr, 2),
            "most_common": [{"word": w, "count": c} for w, c in most_common]
        },
        "structure": {
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_length, 1)
        },
        "scores": {
            "ta": ta_score,  # Task Achievement/Response
            "cc": cc_score,  # Coherence and Cohesion
            "lr": lr_band,   # Lexical Resource
            "gra": gra_band, # Grammatical Range and Accuracy
            "task_score": task_score,  # Overall task score
            "error_density": round(error_density, 2)
        },
        "feedback": feedback,
        "notes": [
            "⚠️ IMPORTANT: TA (Task Achievement) and CC (Coherence & Cohesion) scores shown are ESTIMATES.",
            "These criteria require human assessment by trained IELTS examiners.",
            "Only GRA and LR scores are reliably assessed by this automated tool.",
            "The task score shown is calculated using estimated TA/CC values."
        ],
        "java_available": True
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    text = data.get('text', '')
    task_type = data.get('task_type', 'essay')
    
    if not text.strip():
        return jsonify({"error": "Please provide text to analyze"}), 400
    
    result = analyze_text(text, task_type)
    return jsonify(result)

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "java_available": java_available,
        "languagetool_available": lt_tool is not None
    }), 200

if __name__ == '__main__':
    download_nltk_data()
    port = int(os.environ.get('PORT', 3333))
    app.run(host='0.0.0.0', port=port, debug=False)