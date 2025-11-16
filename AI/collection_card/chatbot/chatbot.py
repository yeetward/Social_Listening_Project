import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gpt
import json
from pymongo import MongoClient

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://ai_worker_user:YUiDJwjMqqBKEI70@cluster0.dqugl74.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
)
client = MongoClient(MONGO_URI)
db = client["pace_database"]


def stream_text_by_words(text: str, delay: float = 0.05):
    """
    Stream text word by word (faster, more natural)

    Args:
        text: Text to stream
        delay: Delay between words in seconds
    """
    words = text.split(" ")
    for i, word in enumerate(words):
        print(word, end="", flush=True)
        if i < len(words) - 1:
            print(" ", end="", flush=True)
        time.sleep(delay)
    print()  # New line at the end


def load_context(company_name: str, num_articles=20):
    """
    Load all relevant context for the chatbot
    """
    # Get company info
    company = db.company_profiles.find_one({"name": company_name})
    if not company:
        raise ValueError(f"Company {company_name} not found")

    # Get recent articles
    articles = list(
        db.ai_results.find(
            {"status": "done"},
            {
                "ai_title": 1,
                "ai_summary": 1,
                "uri": 1,
                "source": 1,
                "relevance_score": 1,
                "published_ts": 1,
                "_id": 0,
            },
        )
        .sort("created_at", -1)
        .limit(num_articles)
    )

    # Get recent search history
    recent_histories = list(
        db.history.find(
            {"ai_ready": True},
            {"subject": 1, "location": 1, "industry": 1, "created_at": 1},
        )
        .sort("created_at", -1)
        .limit(10)
    )

    context = {
        "company": {
            "name": company["name"],
            "description": company["description"],
            "competitors": company["competitors"],
        },
        "articles": articles,
        "search_history": recent_histories,
    }

    return context


def format_context_for_prompt(context: dict):
    """
    Format context into a readable string for GPT
    """
    company = context["company"]

    prompt_context = f"""
COMPANY INFORMATION:
Name: {company["name"]}
Description: {company["description"]}
Competitors: {", ".join(company["competitors"])}

RECENT ARTICLES ANALYZED:
"""

    for idx, article in enumerate(context["articles"][:15], 1):
        prompt_context += f"\n{idx}. [{article.get('source', 'Unknown')}] {article.get('ai_title', 'Untitled')}\n"
        prompt_context += f"   Summary: {article.get('ai_summary', 'No summary')}\n"
        prompt_context += f"   Relevance: {article.get('relevance_score', 0):.2f}\n"
        prompt_context += f"   URL: {article.get('uri', 'N/A')}\n"

    prompt_context += "\n\nRECENT SEARCH TOPICS:\n"
    for idx, history in enumerate(context["search_history"][:5], 1):
        prompt_context += f"{idx}. {history['subject']} (Location: {history.get('location', 'N/A')}, Industry: {history.get('industry', 'N/A')})\n"

    return prompt_context


def chat(
    context: dict,
    user_message: str,
    conversation_history: list = None,
    stream: bool = True,
):
    """
    Process a user message and return chatbot response

    Args:
        context: Company context
        user_message: User's question
        conversation_history: Previous messages
        stream: Whether to stream the response (typing effect)

    Returns:
        Response text (also prints with streaming if enabled)
    """
    if conversation_history is None:
        conversation_history = []

    context_str = format_context_for_prompt(context)

    history_str = ""
    for msg in conversation_history[-5:]:
        history_str += f"\nUser: {msg['user']}\nAssistant: {msg['assistant']}\n"

    prompt = f"""
You are an AI assistant helping analyze business intelligence for {context["company"]["name"]}.

{context_str}

Previous conversation:
{history_str}

Current user question: {user_message}

Provide a helpful, conversational response based on the information above.
- Answer questions about the company, articles, competitors, and opportunities
- Be specific and reference relevant articles when appropriate
- If asked about something not in the context, let the user know

Response:
"""

    try:
        # Show thinking indicator
        if stream:
            print("Thinking...", end="\r", flush=True)

        response = gpt.load_model(
            prompt, max_tokens=1500, temperature=0.4, stream=False
        )

        # Clear thinking indicator
        if stream:
            print(" " * 20, end="\r", flush=True)

        # Strip any markdown if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1]) if len(lines) > 2 else response

        # Stream the response
        if stream:
            stream_text_by_words(response.strip())

        return response.strip()

    except Exception as e:
        error_msg = f"Sorry, I encountered an error: {str(e)}"
        if stream:
            stream_text_by_words(error_msg)
        return error_msg
