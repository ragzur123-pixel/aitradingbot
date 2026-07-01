import os
import requests
import json
import logging
import asyncio
from utils import setup_logging
from config_loader import config

logger = setup_logging("local_llm_client")

class LocalLLMClient:
    """
    Bridge to a local Inference instance (Ollama or vLLM).
    Optimized for L4 GPU performance on us-east1d.
    """
    def __init__(self, model="llama3.1:70b"):
        # vLLM is preferred for 70B models on L4 (OpenAI-compatible)
        self.vllm_url = os.getenv("VLLM_URL", "http://localhost:8000/v1")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = model

    async def ainvoke(self, payload_dict):
        """Asynchronous invocation for parallel MC iterations."""
        # Convert dict to flat prompt string for legacy model support
        prompt = json.dumps(payload_dict)
        return await asyncio.to_thread(self.invoke, prompt)

    def invoke(self, prompt):
        """Invoke local model via vLLM (OpenAI style) or Ollama."""
        # Try vLLM first (Higher Performance)
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4
            }
            # vLLM /v1/chat/completions logic ...
            response = requests.post(f"{self.vllm_url}/chat/completions", json=payload, timeout=300)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return type('Res', (object,), {"content": content})
        except:
            # Fallback to Ollama
            try:
                payload = {"model": self.model, "prompt": prompt, "stream": False}
                response = requests.post(self.ollama_url, json=payload, timeout=300)
                if response.status_code == 200:
                    return type('Res', (object,), {"content": response.json().get("response", "")})
            except Exception as e:
                logger.error(f"Inference Failed: {e}")
                return type('Res', (object,), {"content": "VETO: INFERENCE_FAILURE"})


if __name__ == "__main__":
    client = LocalLLMClient()
    res = client.invoke("Tell me why price action is non-deterministic.")
    if res: print(res.content)
