from pathlib import Path
import os

from dotenv import load_dotenv
import ollama


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b",
)


def generate_chat_completion(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Generate a response using a local Ollama model.
    """

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        options={
            "temperature": 0.0,
        },
    )

    content = response["message"]["content"]

    if not content:
        raise RuntimeError(
            "Ollama returned an empty response."
        )

    return content.strip()