import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, Part
import os
import sys
import json
from flask import Flask, request, render_template
import logging

# Initialize Flask app
app = Flask(__name__)

# Initialize Vertex AI
vertexai.init(project=os.getenv("PROJECT_ID"), location=os.getenv("REGION"))

# Initialize Gemini model
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

# Route for movie recommendations
@app.route('/recommendations', methods=['POST'])
def movie_recommendations():
  movies = request.json['movies']
  scenario = request.json['scenario']
  print(f"Received movies: {movies}, Received scenario: {scenario}", file=sys.stdout)

  try:
    recommendation_response = vertex_movie_recommendation(movies, scenario)
  except Exception as e:
    print(f"Error occurred: {e}", file=sys.stderr)
    return e, 500;
  
  result = json.dumps({'recommendation': recommendation_response}, ensure_ascii = False)
  print(f"Result: {result}", file=sys.stdout)
  
  return result, 200, {'Content-Type': 'application/json; charset=utf-8'}

# healthz
@app.route('/healthz')
def healthz():
    return 'OK', 200

# Run the Flask app
if __name__ == '__main__':
  port = int(os.environ.get('PORT', 8080))
  app.run(debug=False, host='0.0.0.0', port=port)
