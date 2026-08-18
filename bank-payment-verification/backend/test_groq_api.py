import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.environ.get("GROQ_API_KEY")
print(f"Loaded Groq Key: {groq_api_key}")

try:
    client = Groq(api_key=groq_api_key)

    # புதிய மற்றும் தற்போதைய செயல்பாட்டில் உள்ள மாடல் பெயர்
    chat_completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": "Hello! Reply with 'Groq API is working perfectly!' if you receive this."
            }
        ],
        temperature=0.1
    )

    print("\n--- Groq AI Response ---")
    print(chat_completion.choices[0].message.content)
    print("\n✅ Groq API is working successfully!")

except Exception as e:
    print(f"\n❌ Error occurred: {e}")