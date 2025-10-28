from groq import Groq
import os

def load_model(prompt, max_tokens=256, temperature=1.0, stream=True):
    """
    Generate text using Groq API with streaming support
    Args:
        prompt: The user's input text
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        stream: Whether to stream output token by token
    """
    
    # Initialize Groq client
    api_key = os.getenv("GROQ_API_KEY", "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")  # Replace with your key
    client = Groq(api_key=api_key)
    
    # Model selection (equivalent to your 120B model)
    model_id = "openai/gpt-oss-20b"  # Closest to 120B, or use "llama3-8b-8192" for faster
    
    # Create completion
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )
    
    if stream:
        # Stream output token by token (just like your TextIteratorStreamer)
        generated_text = ""
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
            generated_text += content
        
        print()  # New line at end
        return generated_text
    else:
        # Non-streaming output
        generated_text = completion.choices[0].message.content
        print(generated_text)
        return generated_text
