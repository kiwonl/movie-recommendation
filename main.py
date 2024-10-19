import os
from flask import Flask, request, jsonify, render_template
from langchain_google_vertexai import VertexAI
from langchain_google_vertexai import VertexAIEmbeddings, VertexAI
from langchain_google_alloydb_pg import AlloyDBEngine
from langchain_core.prompts import PromptTemplate
from langchain_google_alloydb_pg import (
    AlloyDBEngine,
    AlloyDBVectorStore,
)
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.documents import Document

project_id = os.environ["PROJECT_ID"]
instance_name = "movies-instance"
cluster_name = "movies-cluster"
alloy_region = "us-central1"
alloy_user = "postgres"
alloy_password = "movies-demo-password"
database = "movies"
vector_table_name = "movie_titles"

llm = VertexAI(model_name="gemini-1.5-flash-001", project=project_id, max_output_tokens=2048)

engine = AlloyDBEngine.from_instance(
    project_id=project_id,
    instance=instance_name,
    region=alloy_region,
    cluster=cluster_name,
    database=database,
    user=alloy_user,
    password=alloy_password,
)

# Initialize the embedding service
embeddings_service = VertexAIEmbeddings(
    model_name="textembedding-gecko@003", project=project_id
)

vector_store = AlloyDBVectorStore.create_sync(
    engine=engine,
    embedding_service=embeddings_service,
    table_name=vector_table_name,
    metadata_columns=[
        "show_id",
        "type",
        "country",
        "date_added",
        "release_year",
        "duration",
        "listed_in",
    ],
)

prompt = PromptTemplate.from_template("""

You are an expert on box office movies.

Comment on the movies {movies} and how good of a fit they are for the scenario described as "{scenario}".

Given the similar entries from your movie library, also provide recommendations for alternative movies.
Make sure your additional recommendations include duration, release_year and show_id of the movies.

Use all the information from the context to answer the question.
If the context includes relevant information, include them in your recommendation.

Similar movies from your movie library:

```{context}
```
""")

retriever = vector_store.as_retriever(
    search_type="mmr", search_kwargs={"k": 5, "lambda_mult": 0.8}
)

customDocumentPrompt = PromptTemplate.from_template("""
Result:

Summary:
{page_content}

Metadata:
show_id: {show_id}
release_year: {release_year}
duration: {duration}
""")


combine_docs_chain = create_stuff_documents_chain(
    llm, prompt, document_prompt=customDocumentPrompt
)

app = Flask(__name__)
@app.route('/recommendations', methods=['POST'])
def movie_recommendations():
  """
  Returns a list of movie recommendations based on the user's input.
  """
  if not request.json:
      return jsonify({'error': 'Missing JSON payload'}), 400

  movies = ", or".join(request.json['movies'])
  scenario = request.json['scenario']

  movie_recommendations = vector_store.similarity_search(f"Movie that is great for {scenario} and similar to {movies}", k=5)

  response = combine_docs_chain.invoke({"scenario": scenario, "movies": movies, "context": movie_recommendations})

  return jsonify({'recommendation': response})

@app.route('/')
def index():
  """
  Renders the index page.
  """
  return render_template('index.html', revision=os.getenv("K_REVISION"), region=os.getenv("GCP_REGION"))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)


