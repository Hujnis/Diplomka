"""
zdroj: https://www.youtube.com/watch?v=q5HiD5PNuck

funguje pouze se zaplaceným openAI a jede na serveru openAI
"""

""" 

import openai

openai.api_key = "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"

def chat_with_gpt(prompt):
    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choises[0].message.content.strip()

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            break

        response = chat_with_gpt(user_input)
        print("Chatbot: ", response) 
"""

#______________________________________________________________________________________________________________________________________________________________________________

"""
zdroj: https://www.youtube.com/watch?v=d0o89z134CQ

OLLAMA 3, opensource, jede lokálně, chce hodně výkonu
"""
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate


template = """
Answer the question below.

Here is the conversation history: {context}

Question: {question}

Answer:
"""

model = OllamaLLM(model="llama3")
prompt = ChatPromptTemplate.from_template(template)

#CHAIN OF OPERATIONS prompt AND model
chain = prompt | model                                  

#FUNCTION FOR THE CHAT CONTEXT
def handle_conversation():
    context = ""
    print("Welcome to my ChatBot! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        result = chain.invoke({"context": context, "question": user_input})
        print("Bot: ", result)
        context += f"\nUser: {user_input}\nAI: {result}"


if __name__ == "__main__":
    handle_conversation()