from flask import Flask, render_template, request, jsonify
import requests
import nltk
import re
from collections import Counter
import os

app = Flask(__name__)

# ------------------------------------------------------
# NLTK DOWNLOAD
# ------------------------------------------------------
def download_nltk_data():
    try:
        nltk.download('punkt_tab', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✓ NLTK resources downloaded")
    except Exception as e:
        print(f"⚠ NLTK download warning: {e}")

# ------------------------------------------------------
# LANGUAGE TOOL API (NO JAVA, ALWAYS WORKS)
# ------------------------------------------------------
LT_API_URL = "https://api.languagetool.org/v2/check"


def lt_check(text):
    """Send text to LanguageTool public API."""
    try:
        response = requests.post(
            LT_API_URL,
            data={
                "text": text,
                "language": "en-GB"
            },
            timeout=10
        )
        result = response.json()
        return result.get("matches", [])
    except Exception as e:
        raise Exception(f"LanguageTool API Error: {str(e)}")


# ------------------------------------------------------
# TEXT ANALYSIS FUNCTIONS
# ------------------------------------------------------
def calculate_lexical_diversity(text):
    tokens = nltk.word_tokenize(re.sub(r'[^\w\s]', '', text.lower()))
    tokens = [t for t in tokens if len(t) > 1]

    total_tokens = len(tokens)
    unique_types = len(set(tokens))
    ttr = (unique_types / total_tokens) * 100 if total_tokens > 0 else 0
    word_freq = Counter(tokens)
    most_common = word_freq.most_common(5)

    return total_tokens, unique_types, ttr, most_common


def assess_sentence_complexity(text):
    sentences = nltk.sent_tokenize(text)
    sentence_count = len(sentences)
    words = nltk.word_tokenize(text)
    avg_sentence_length = len(words) / sentence_count if sentence_count > 0 else 0
    return sentence_count, avg_sentence_length


def round_ielts_score(score):
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
    error_density = (error_count / word_count * 100) if word_count > 0 else 0

    gra_score = 9
    lr_score = 9

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

    if avg_sentence_length < 10:
        gra_score -= 1
    elif avg_sentence_length > 25:
        gra_score = min(gra_score + 0.5, 9)

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

    if task_type == "report" and ttr < 55:
        lr_score -= 0.5
    elif task_type == "letter" and error_count > 2:
        gra_score -= 0.5

    gra_score = round_ielts_score(max(4, min(9, gra_score)))
    lr_score = round_ielts_score(max(4, min(9, lr_score)))

    return gra_score, lr_score, error_density


def calculate_task_score(ta_score, cc_score, lr_score, gra_score):
    raw_average = (ta_score + cc_score + lr_score + gra_score) / 4
    return round_ielts_score(raw_average)


# ------------------------------------------------------
# MAIN ANALYSIS
# ------------------------------------------------------
def analyze_text(text, task_type):

    try:
        matches = lt_check(text)
    except Exception as e:
        return {
            "error": f"Grammar checking failed: {str(e)}",
            "lt_tool_available": False
        }

    errors = []
    for match in matches:
        errors.append({
            "message": match.get("message"),
            "context": match.get("context", {}).get("text", ""),
            "suggestions": match.get("replacements", [])[:3]
        })

    tokens, types, ttr, most_common = calculate_lexical_diversity(text)
    sentence_count, avg_length = assess_sentence_complexity(text)

    gra_band, lr_band, error_density = get_band_score(
        len(matches), tokens, ttr, avg_length, task_type
    )

    feedback = []
    if gra_band >= 7 and lr_band >= 7:
        feedback.append("✓ Excellent! Your writing shows good command of grammar and vocabulary.")
    elif gra_band >= 6 and lr_band >= 6:
        feedback.append("✓ Good work! Some minor improvements needed.")
    else:
        feedback.append("⚠ Needs improvement in grammar accuracy and vocabulary variety.")

    if len(matches) > 0:
        feedback.append(f"• Focus on fixing errors (found {len(matches)})")
    if ttr < 55:
        feedback.append(f"• Expand vocabulary variety (TTR: {ttr:.1f}%)")
    if avg_length < 12:
        feedback.append(f"• Use more complex sentences (avg: {avg_length:.1f} words)")

    ta_score = 7.0
    if tokens < 150:
        ta_score = 5.0
    elif tokens < 200:
        ta_score = 6.0
    elif tokens >= 250:
        ta_score = 7.0

    cc_score = 6.5
    if sentence_count < 5:
        cc_score = 5.5
    elif 15 < avg_length < 25:
        cc_score = 7.0

    ta_score = round_ielts_score(ta_score)
    cc_score = round_ielts_score(cc_score)
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
            "ta": ta_score,
            "cc": cc_score,
            "lr": lr_band,
            "gra": gra_band,
            "task_score": task_score,
            "error_density": round(error_density, 2)
        },
        "feedback": feedback,
        "lt_tool_available": True
    }


# ------------------------------------------------------
# ROUTES
# ------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        text = data.get('text', '')
        task_type = data.get('task_type', 'essay')

        if not text.strip():
            return jsonify({"error": "Please provide text to analyze"}), 400

        result = analyze_text(text, task_type)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "languagetool_api": True
    }), 200


# ------------------------------------------------------
# START SERVER
# ------------------------------------------------------
if __name__ == '__main__':
    download_nltk_data()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
