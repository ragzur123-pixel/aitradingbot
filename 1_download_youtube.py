import os
import json
import logging
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils import setup_logging

# Setup logging
logger = setup_logging("youtube_ingestion")

def run_ingestion():
    """
    Builds the Strategy Intelligence Database from YouTube links.
    Uses local L4 GPU for zero-cost embeddings.
    """
    links_file = "links.txt"
    db_dir = "./chroma_db"
    
    if not os.path.exists(links_file):
        logger.error(f"FATAL: {links_file} not found. Create it with one YouTube URL per line.")
        return

    # 1. Load Links
    with open(links_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        logger.warning("No URLs found in links.txt. Skipping ingestion.")
        return

    logger.info(f"Starting ingestion of {len(urls)} videos...")

    # 2. Setup Local GPU-Powered Embeddings (Zero Cost)
    # Using a small but powerful model optimized for speed
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cuda'} # Hard-wired for your L4 GPU
        )
        logger.info("GPU-Powered Embeddings Engine: ONLINE.")
    except Exception as e:
        logger.warning(f"GPU Embeddings failed ({e}). Falling back to CPU.")
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

    # 3. Process Videos
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    if not os.path.exists(db_dir):
        logger.info(">>> Creating New Strategy Database...")
        vector_db = Chroma(persist_directory=db_dir, embedding_function=embeddings)
    else:
        logger.info(">>> Updating Existing Database...")
        vector_db = Chroma(persist_directory=db_dir, embedding_function=embeddings)

    success_count = 0
    for url in urls:
        try:
            logger.info(f"Watching: {url}")
            # Use transcript-api only (avoiding pytube for now)
            loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
            docs = loader.load()
            
            if not docs:
                logger.error(f"No content found for {url}. Check if video has transcripts.")
                continue

            chunks = text_splitter.split_documents(docs)
            vector_db.add_documents(chunks)
            success_count += 1
            logger.info(f"SUCCESS: {url} absorbed into memory.")
        except Exception as e:
            logger.error(f"FAILED {url}: {e}")

    logger.info(f">>> INGESTION COMPLETE: {success_count}/{len(urls)} videos processed.")
    logger.info("The Predator now has its Strategy Soul. Database ready.")

if __name__ == "__main__":
    run_ingestion()
