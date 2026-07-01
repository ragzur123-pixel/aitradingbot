import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
try:
    from langchain_community.document_loaders import YoutubeLoader
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    print("Libraries: OK")
except ImportError as e:
    print(f"Libraries: MISSING ({e})")
