# ⚽ Serie A Lineup Agent (RAG)

An intelligent AI Agent designed to provide the most accurate and up-to-date **Serie A starting lineups** for Fantasy Football (*Fantacalcio*) enthusiasts. This project utilizes a **RAG (Retrieval-Augmented Generation)** architecture to bridge the gap between real-time web data and LLM reasoning.

---

## 🚀 Overview

The agent doesn't just "guess" or rely on outdated training data. It follows a multi-step pipeline:
1. **Scraping**: Extracts raw predicted lineups from premium sports sources (e.g., Sky Sport).
2. **Knowledge Base**: Transforms structured JSON data into searchable vector embeddings.
3. **Retrieval**: When a user asks a question, the agent retrieves the most relevant match data.
4. **Reasoning**: An LLM (via Groq) synthesizes the data to handle player roles, ballots (*ballottaggi*), and team strategies.

---

## 🛠️ Technical Stack

* **LLM:** [Groq](https://groq.com/) (Llama 3 / Qwen models) for ultra-fast inference using LPU™ technology.
* **Embeddings:** [Google Gemini](https://ai.google.dev/) (`text-embedding-004`).
* **Vector Database:** [Qdrant](https://qdrant.tech/) (Running in-memory).
* **Framework:** [DataPizza](https://github.com/datapizza-ai/datapizza) (Modular DAG-based AI pipeline).
* **Scraping & Parsing:** `BeautifulSoup4` & `Docling`.

---

## 🧠 Key Features & Technical Solutions

### 1. Custom Google Embedder Patch
Standard libraries often expect specific data structures for embeddings. I implemented a **Monkey Patch** (`FixedGoogleEmbedder`) to override the standard Google Embedder, ensuring compatibility between DataPizza’s retrieval logic and the Google Generative AI API for `retrieval_query` tasks.

### 2. Semantic Role Parsing
The agent is instructed with specific prompt engineering rules to handle fragmented text data:
* **Role Persistence**: Correctly associates roles (e.g., "Defender") even when line breaks separate them from the player's name.
* **Logical Grouping**: Automatically organizes output by Goalkeeper → Defenders → Midfielders → Forwards.

### 3. "The Scout & The Coach" Strategy (Roadmap)
The project is evolving into a multi-agent system:
* **The Scout**: Dedicated to scheduled scraping and data cleaning.
* **The Coach**: Focused on user interaction and cross-referencing multiple sources to resolve discrepancies.

---



1. **Clone the repo:**
   ```bash
   git clone https://github.com/aronetommaso/Fanta-Calcio-Agent.git
   
