import os
import sys

# --- STANDARD IMPORTS ---
# We need the Google library directly to fix the search query behavior
import google.generativeai as genai

# --- DATAPIZZA IMPORTS ---
from datapizza.clients.openai import OpenAIClient
from datapizza.core.vectorstore import VectorConfig
from datapizza.embedders import ChunkEmbedder
# We import the base Google class to inherit from it
from datapizza.embedders.google import GoogleEmbedder
from datapizza.modules.parsers.docling import DoclingParser
from datapizza.modules.splitters import RecursiveSplitter
from datapizza.pipeline import IngestionPipeline, DagPipeline
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.modules.prompt import ChatPromptTemplate

# Load environment variables (.env file)
from load_dotenv import load_dotenv
load_dotenv()

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
INPUT_FILE = "dataset_rag.pdf"
GOOGLE_MODEL_NAME = "models/text-embedding-004"

# --- CUSTOM COMPONENT ---
class FixedGoogleEmbedder(GoogleEmbedder):
    """
    A patched version of DataPizza's GoogleEmbedder.
    
    The original DataPizza class works fine for Ingestion (loading data),
    but fails during Retrieval (Search) because it expects a list of Nodes
    instead of a plain text query string.
    
    This class overrides the `_run` method to handle text queries correctly
    using the standard Google Generative AI library.
    """
    def _run(self, text=None, input=None, **kwargs):
        # 1. Safely retrieve the query text.
        # DataPizza might pass the input as 'text', 'input', or inside kwargs.
        query = text or input or kwargs.get('text') or kwargs.get('input')
        
        if not query:
            return []

        # 2. Use the standard Google library to generate the vector.
        # We specify task_type='retrieval_query' so Google optimizes the vector for searching.
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"
            )
            
            # Google returns a dictionary {'embedding': [...]}, we extract the list.
            return result['embedding']
            
        except Exception as e:
            print(f"Error during Google Search Embedding: {e}")
            return []

def main():
    # --- 0. VALIDATION ---
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith("gsk_"):
        print("ERROR: Invalid or missing GROQ_API_KEY.")
        return
    if not GOOGLE_API_KEY:
        print("ERROR: Missing GOOGLE_API_KEY.")
        return

    # Global configuration for Google GenAI (just to be safe)
    genai.configure(api_key=GOOGLE_API_KEY)

    print("--- 1. SETUP CLIENTS ---")
    
    # A. LLM Client (Groq)
    # We use OpenAIClient generic class but point it to Groq's API URL.
    llm_client = OpenAIClient(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        model="qwen/qwen3-32b",
        temperature=0.6
    )

    # B. Embedder Client (Google Gemini)
    # We use our 'FixedGoogleEmbedder' wrapper.
    print("Loading Google Embedder...")
    embedder_client = FixedGoogleEmbedder(
        api_key=GOOGLE_API_KEY, 
        model_name=GOOGLE_MODEL_NAME
    )

    # C. Vector Database (Qdrant In-Memory)
    print("Initializing Qdrant...")
    vectorstore = QdrantVectorstore(location=":memory:")
    
    # IMPORTANT: Google's 'text-embedding-004' produces 768-dimensional vectors.
    # Qdrant configuration must match this, otherwise calculations will fail.
    vectorstore.create_collection(
        "serie_a_matches",
        vector_config=[VectorConfig(name="", dimensions=768)]
    )

    # --- 2. INGESTION PIPELINE (Loading Data) ---
    print(f"\n--- 2. RUNNING INGESTION PIPELINE ON {INPUT_FILE} ---")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File {INPUT_FILE} not found.")
        return

    ingestion_pipeline = IngestionPipeline(
        modules=[
            # 1. Parse the PDF/Text file
            DoclingParser(), 
            
            # 2. Split text into chunks (max 3000 chars)
            RecursiveSplitter(max_char=3000, overlap=200),             
            
            # 3. Create Embeddings
            # CRITICAL: We set batch_size=50. 
            # Google API rejects requests with more than 100 items. 
            # Setting it to 50 ensures safe processing.
            ChunkEmbedder(
                client=embedder_client, 
                model_name=GOOGLE_MODEL_NAME,
                batch_size=50
            ),   
        ],
        vector_store=vectorstore,
        collection_name="serie_a_matches"
    )

    # Execute Ingestion
    ingestion_pipeline.run(INPUT_FILE, metadata={"source": "scraper_sky"})
    print("Ingestion complete! Data is now in memory.")

    # --- 3. RETRIEVAL PIPELINE (The "Brain") ---
    print("\n--- 3. SETTING UP RETRIEVAL DAG ---")
    
    dag_pipeline = DagPipeline()

    # Define the Prompt Template
    # This instructs the LLM to use only the provided context chunks.
    prompt_template = ChatPromptTemplate(
        user_prompt_template=(
            "You are a helpful football assistant. Below is the information I found from Sky Sports.\n"
            "Use this context to answer the user's question. If the context contains partial lineups, "
            "report what is available. Do not apologize, just provide the data found.\n\n"
            
            "### DATA STRUCTURE RULES:\n"
            "1. **Format**: Players are listed as 'Name Surname (Role)'.\n"
            "2. **Fragmentation**: Names and Roles might be split across multiple lines (e.g., 'Guillermo' on one line, 'Maripán' on another, '(Defender)' on a third). You must join them logically.\n"
            "3. **Role Persistence**: A role in parentheses applies to the name immediately preceding it, even if separated by several line breaks.\n\n"
        
            "### OUTPUT INSTRUCTIONS:\n"
            "- Identify the 'STARTING LINEUP' for the requested team.\n"
            "- Group and display players in this specific order: 1. Goalkeeper, 2. Defenders, 3. Midfielders, 4. Forwards.\n"
            "- Use a clean bullet-point list.\n"
            "- Answer in Italian.\n\n"
            "--- CONTEXT START ---\n"
            "{% for chunk in chunks %}"
            "{{ chunk.text }}\n"
            "-------------------\n"
            "{% endfor %}\n"
            "--- CONTEXT END ---\n\n"
            "Question: {{user_prompt}}\n"
        ),
        retrieval_prompt_template=(
            "SOURCE DOCUMENTS FOUND IN PDF:\n"
            "{% for chunk in chunks %}"
            "--- DOCUMENT {{ loop.index }} ---\n"
            "{{ chunk.text }}\n"
            "{% endfor %}"
            "--- END OF CONTEXT ---"
            )
            
            )

    # Register Modules in the DAG
    dag_pipeline.add_module("embedder", embedder_client)    # Converts query to vector
    dag_pipeline.add_module("retriever", vectorstore)       # Finds relevant docs
    dag_pipeline.add_module("prompt", prompt_template)      # Formats the prompt
    dag_pipeline.add_module("generator", llm_client)        # Generates the answer

    # Connect Modules (The Flow)
    # 1. Embedder -> Retriever (Send vector to find documents)
    dag_pipeline.connect("embedder", "retriever", target_key="query_vector")
    
    # 2. Retriever -> Prompt (Send found chunks to the prompt template)
    dag_pipeline.connect("retriever", "prompt", target_key="chunks")
    
    # 3. Prompt -> Generator (Send final text to LLM)
    dag_pipeline.connect("prompt", "generator", target_key="memory")

    # --- 4. CHAT LOOP ---
    print("\n" + "="*50)
    print(" AGENT READY! (Groq Llama 3.3 + Google Embeddings)")
    print(" Type 'exit' to quit.")
    print("="*50 + "\n")

    while True:
        user_query = input("User: ")
        if user_query.lower() in ["exit", "quit"]:
            break

        try:
            # print("DEBUG: Processing pipeline...")
            
            # Run the DAG.
            # We pass the user query to 'embedder' (for search) and 'prompt' (for context).
            # Note: We pass both 'text' and 'input' keys to the embedder to ensure 
            # our custom _run method catches it regardless of how DataPizza handles it.
            result = dag_pipeline.run({
                "embedder": {"text": user_query, "input": user_query},
                "prompt": {"user_prompt": user_query},
                "retriever": {"collection_name": "serie_a_matches", "k": 15},
                "generator": {"input": "dummy"} # Placeholder input
            })

            print("\n" + "-"*20 + " DEBUG: COSA HA TROVATO NEL PDF? " + "-"*20)
            
            # Datapizza salva i chunk recuperati nella chiave 'retriever' o 'prompt' a seconda del flusso
            # Solitamente il nodo 'retriever' restituisce una lista di Nodi/Chunks
            found_chunks = result.get('retriever', [])
            
            if not found_chunks:
                print("ATTENZIONE: Il Retriever non ha trovato NESSUN documento!")
                print("Possibili cause: Embeddings disallineati o PDF non letto correttamente.")
            else:
                for i, chunk in enumerate(found_chunks):
                    # Stampiamo i primi 150 caratteri di ogni pezzo trovato
                    text_preview = chunk.text[:150].replace('\n', ' ')
                    print(f"[{i+1}] {text_preview}...")
            
            print("-"*60 + "\n")

            # Extract the final response from the generator node
            final_answer = result['generator']
            print(f"\nAgent: {final_answer}\n")

        except Exception as e:
            print(f"Pipeline Error: {e}")
            # Uncomment below for full error details if needed
            # import traceback
            # traceback.print_exc()

if __name__ == "__main__":
    main()