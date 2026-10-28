
import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)


def ask_ai(question: str, context: str = "") -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "The Gemini API key is not configured."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=(
            "You are the SIRA academic assistant. "
            "Answer clearly using the provided context. "
            "Do not invent academic data. "
            "If the context does not contain the answer, "
            "say that the information is unavailable.\n\n"
            f"Context:\n{context}\n\n"
            f"User question:\n{question}"
        ),
    )

    answer = response.text

    if not answer:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return answer
