# 🏗️ Unified Predator: Phase 3 Launch Commands

Copy and paste the block below into your **Google Cloud Shell** (or your server terminal). This will build the entire intelligence stack, create the strategy database, and start the video ingestion using your L4 GPU.

---

```bash
# 1. Create the Predator's Den and enter it
mkdir -p /home/d2r2brothers/AiTradingBot && cd /home/d2r2brothers/AiTradingBot

# 2. Build the Intelligence Stack (Dependencies)
pip install --upgrade pip
pip install yt-dlp langchain langchain-community chromadb sentence-transformers langchain-huggingface youtube-transcript-api pytube

# 3. Create the Links list (REPLACE THESE with your own strategy URLs later)
# For now, this ensures the file exists so the script doesn't crash.
echo "https://www.youtube.com/watch?v=LqVp1Zp1_fI" > links.txt

# 4. Create the high-performance Ingestion Script (ZERO-LOSS)
cat << 'EOF' > 1_download_youtube.py
import os
import logging
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

def run_ingestion():
    links_file = "links.txt"
    db_dir = "./chroma_db"
    
    if not os.path.exists(links_file):
        print(f"ERROR: {links_file} not found.")
        return

    with open(links_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f">>> Initializing GPU-Powered Embeddings (L4)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={'device': 'cuda'}
    )

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    print(f">>> Connecting to ChromaDB...")
    vector_db = Chroma(persist_directory=db_dir, embedding_function=embeddings)

    print(f">>> Starting ingestion of {len(urls)} videos...")
    for url in urls:
        try:
            print(f"Watching: {url}")
            loader = YoutubeLoader.from_youtube_url(url, add_video_info=True)
            docs = loader.load()
            if not docs:
                print(f"SKIP: No transcript for {url}")
                continue
            chunks = text_splitter.split_documents(docs)
            vector_db.add_documents(chunks)
            print(f"SUCCESS: {url} absorbed into strategy soul.")
        except Exception as e:
            print(f"FAILED {url}: {e}")

    print(">>> DATABASE COMPLETE. Memory is now hot.")

if __name__ == "__main__":
    run_ingestion()
EOF

# 5. Run the Memory Engine
python3 1_download_youtube.py
```

---

### 🚨 Technician's Next Steps
1. Once you see **">>> DATABASE COMPLETE"**, the foundation is finished.
2. We will then move your specific `.py` bot files to the server.
3. We will then hit **START** on the Unified Predator.
