import os, openai

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_codex(prompt, filename, model="gpt-4o-mini"):
    """Simple wrapper that returns the generated code string."""
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
