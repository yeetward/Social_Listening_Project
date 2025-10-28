import gpt

def call_os():
    prompt = "How are you today?"
    gpt.load_model(prompt, max_tokens=256, temperature=1.0, stream=True)

if __name__ == "__main__":
    call_os()