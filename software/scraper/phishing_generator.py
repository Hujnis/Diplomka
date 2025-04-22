import os
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer, pipeline
from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from database import get_db_connection

# Načtení environment proměnných
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# Cesta k modelu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(BASE_DIR, "models", "distilgpt2")

# Kontrola, zda model existuje, pokud ne, stáhne ho
if not os.path.exists(models_dir):
    print("Model not found locally. Downloading...")
    snapshot_download(repo_id="distilgpt2", local_dir=models_dir)
    print(f"Model stažen do: {models_dir}")
else:
    print("Using local model.")

# Nastavení zařízení na CPU
device = "cpu"  # Pouze CPU
print(f"Použitý hardware: {device.upper()}")

# Inicializace jazykového modelu s použitím lokálně staženého modelu
model = GPT2LMHeadModel.from_pretrained(models_dir, torch_dtype=torch.float32)
tokenizer = GPT2Tokenizer.from_pretrained(models_dir)

# Nastavení pipeline pro generování textu (pro CPU použijeme device=-1)
llm = pipeline("text-generation", model=model, tokenizer=tokenizer, device=-1)  # -1 znamená CPU



def get_users():
    """Načte uživatele a jejich data z databáze."""
    conn = get_db_connection()
    if not conn:
        print("Nepodařilo se připojit k databázi.")
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT email, token, social_media, school, sports, other FROM user_data")
        users = cur.fetchall()
        cur.close()
        return users
    finally:
        conn.close()

def extract_subject(text):
    # Extrahuje subjekt z generovaného textu (např. první věta)
    lines = text.split("\n")
    return lines[0]  # Pokud je první řádek subjekt

def extract_opening_paragraph(text):
    # Extrahuje úvodní část e-mailu (např. druhý řádek až do prvního odstavce)
    lines = text.split("\n")
    return lines[1]  # Pokud je druhý řádek úvodní část


def generate_phishing_email(token, social_media, school, sports, other):
    """Generuje phishingový e-mail na základě uživatelských dat."""
    prompt_intro = f"""
    Create a phishing email subject and opening paragraph using the following user data:
    - Social Media: {social_media}
    - School: {school}
    - Sports: {sports}
    - Other Interests: {other}
    """

    response_intro = llm(prompt_intro, truncation=True, max_new_tokens=200, do_sample=True, temperature=0.7)[0]['generated_text']

    # Extrahuj předmět a úvodní část
    subject = extract_subject(response_intro)
    opening_paragraph = extract_opening_paragraph(response_intro)

    # URL phishingového formuláře
    phishing_form_url = f"http://localhost:5001/form?token={token}"

    # Následně generuj tělo e-mailu
    prompt_body = f"""
    Now, write the rest of the phishing email body using the following:
    Subject: {subject}
    Opening: {opening_paragraph}
    Include a link to update details: {phishing_form_url}
    """

    response_body = llm(prompt_body, truncation=True, max_new_tokens=200, do_sample=True, temperature=0.7)[0]['generated_text']

    generated_mail = f""" 
    {response_body}
    KONEC
    """

    return generated_mail

def main():
    users = get_users()
    if not users:
        print("Žádní uživatelé nebyli nalezeni v databázi.")
        return

    for user in users:
        email, token, social_media, school, sports, other = user
        
        phishing_email = generate_phishing_email(token, social_media, school, sports, other)
        print(f"\nPhishing e-mail pro {email}:\n{phishing_email}\n")

if __name__ == "__main__":
    main()
