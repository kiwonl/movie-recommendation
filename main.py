# import base64
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, Part
import os
# import sys
import json
from flask import Flask, request, render_template
import logging
from prometheus_client import generate_latest, REGISTRY, Counter, Gauge, Histogram

# Initialize Flask app
app = Flask(__name__)
# Set werkzeug logger level to ERROR to suppress unnecessary logs
# logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Prometheus metrics
# Counter for total HTTP requests
REQUESTS = Counter('http_requests_total', 'Total HTTP Requests (count)', ['method', 'endpoint', 'status_code'])
# Gauge for number of in-progress HTTP requests
IN_PROGRESS = Gauge('http_requests_inprogress', 'Number of in progress HTTP requests')
# Histogram for HTTP request latency
TIMINGS = Histogram('http_request_duration_seconds', 'HTTP request latency (seconds)')

# Initialize Vertex AI
vertexai.init(project=os.getenv("PROJECT_ID"), location=os.getenv("REGION"))
# Initialize Gemini model
# model = GenerativeModel("gemini-1.5-flash-002")
model = GenerativeModel(os.getenv("GEMINI_MODEL"))
generation_config = {
  "max_output_tokens": 8192,
  "temperature": 1,
  "top_p": 0.95,
}
safety_settings = [
  SafetySetting(
    category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    threshold=SafetySetting.HarmBlockThreshold.OFF
  ),
  SafetySetting(
    category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    threshold=SafetySetting.HarmBlockThreshold.OFF
  ),
  SafetySetting(
    category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    threshold=SafetySetting.HarmBlockThreshold.OFF
  ),
  SafetySetting(
    category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
    threshold=SafetySetting.HarmBlockThreshold.OFF
  ),
]

# Function to get movie recommendations from Vertex AI
def vertex_movie_recommendation(movies, scenario):
  chat = model.start_chat()
  response = chat.send_message(
    f"""당신은 영화 전문가 입니다. 다음 영화들: {" or ".join(movies)} 중에서, {scenario} 상황에 적합한 영화를 추천해 주세요""",
    generation_config=generation_config,
    safety_settings=safety_settings,
    stream=False
  )
  return response.text

# Route for the main page
@app.route('/')
@IN_PROGRESS.track_inprogress()
@TIMINGS.time()
def index():
  # Prometheus metric for GET request to /
  REQUESTS.labels(method='POST', endpoint="/recommendations", status_code=200).inc()
  # Render index page with revision and region from environment variables
  return render_template('index.html', revision=os.getenv("K_REVISION"), region=os.getenv("GCP_REGION"))

# Route for movie recommendations
@app.route('/recommendations', methods=['POST'])
@IN_PROGRESS.track_inprogress()
@TIMINGS.time()
def movie_recommendations():
  movies = request.json['movies']
  scenario = request.json['scenario']
  print(f"Received movies: {movies}, Received scenario: {scenario}")

  try:
    recommendation_response = vertex_movie_recommendation(movies, scenario)
  except Exception as e:
    print(f"Error occurred: {e}")
  
  result = json.dumps({'recommendation': recommendation_response}, ensure_ascii = False)
  print(f"Result: {result}")
  
  # Prometheus metric for POST request to /recommendations
  REQUESTS.labels(method='POST', endpoint="/recommendations", status_code=200).inc()
  return result, 200, {'Content-Type': 'application/json; charset=utf-8'}

# Route for Prometheus metrics
@app.route('/metrics')
@IN_PROGRESS.track_inprogress()
@TIMINGS.time()
def metrics():
    # Prometheus metric for GET request to /metrics
    REQUESTS.labels(method='GET', endpoint="/metrics", status_code=200).inc()
    return generate_latest(REGISTRY)

# Run the Flask app
if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run(debug=False, host='0.0.0.0', port=port)
