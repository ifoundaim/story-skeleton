import os, openai

try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    # Fallback for when OpenAI is not configured
    client = None

def call_codex(prompt, filename, model="gpt-4o-mini"):
    """Simple wrapper that returns the generated code string."""
    if client is None:
        print(f"⚠️ OpenAI client not available, skipping code generation for {filename}")
        return filename
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Codex, generate code only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        code = response.choices[0].message.content
        with open(filename, "w") as f:
            f.write(code.strip() + "\n")
        return filename
    except Exception as e:
        print(f"⚠️ Failed to generate code for {filename}: {e}")
        return filename
