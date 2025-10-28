import argparse
import chatbot
import sys

def interactive_mode(company_name: str, stream: bool = True):
    """
    Run chatbot in interactive mode
    
    Args:
        company_name: Company to analyze
        stream: Enable streaming/typing effect
    """
    print(f"🤖 Loading context for {company_name}...")
    context = chatbot.load_context(company_name)
    print(f"✓ Loaded {len(context['articles'])} articles")
    
    if stream:
        print(f"✓ Streaming enabled")
    
    print(f"\nChatbot ready! Ask me anything.")
    print("Type 'exit' to quit.\n")
    
    conversation_history = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("👋 Goodbye!")
                break
            
            print()  # Blank line before response
            
            # Get response
            response = chatbot.chat(
                context, 
                user_input, 
                conversation_history,
                stream
            )
            
            print()  # Blank line after response
            
            # Update history
            conversation_history.append({
                "user": user_input,
                "assistant": response
            })
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive chatbot for business intelligence")
    parser.add_argument("company_name", type=str, help="Company name")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming effect")
    args = parser.parse_args()
    
    interactive_mode(
        args.company_name,
        stream=not args.no_stream
    )