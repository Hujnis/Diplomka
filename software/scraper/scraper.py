import os
import unicodedata
import random
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
from dotenv import load_dotenv
from database import get_db_connection, upsert_user
import torch

#___________________________________________________________________________________________________________________
#                                                     DICTIONARY
#___________________________________________________________________________________________________________________

# Absolutní cesta k tomuto souboru (scraper.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cesta k adresáři "dictionaries"
dictionaries_dir = os.path.join(BASE_DIR, "dictionaries")

#___________________________________________________________________________________________________________________
#                                                     First name

# Načtení czech_names.txt
czech_names_path = os.path.join(dictionaries_dir, "czech_names.txt")
try:
    with open(czech_names_path, 'r', encoding='utf-8') as f:
        name_dictionary = set(line.strip() for line in f if line.strip())
except FileNotFoundError:
    print(f"❌ Soubor '{czech_names_path}' nebyl nalezen.")
    name_dictionary = set()

# Užitečné pro porovnávání jmen s diakritikou i bez ní
def remove_diacritics(input_str):
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )

# Vytvoření verze slovníku jmen bez diakritiky pro snazší porovnání
name_no_diacritics = {
    remove_diacritics(name).lower(): name for name in name_dictionary
}

#___________________________________________________________________________________________________________________
#                                                     Last name

surname_dictionaries = {}

def load_surname_dictionary(letter: str):
    """
    Načte (a zcacheuje) příjmení pro dané písmeno (A–Z).
    Vrací slovník {bez_diakritiky: původní_tvar}.
    """
    letter = letter.upper()
    if letter not in surname_dictionaries:
        filename = f"surnames{letter}.txt"
        file_path = os.path.join(dictionaries_dir, filename)
        if not os.path.exists(file_path):
            print(f"⚠️ Soubor {filename} neexistuje.")
            surname_dictionaries[letter] = {}
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                surnames = set(line.strip() for line in f if line.strip())
            surname_dictionaries[letter] = {
                remove_diacritics(s).lower(): s for s in surnames
            }
    return surname_dictionaries[letter]

#___________________________________________________________________________________________________________________
#                                          EMAIL SPLIT, DOMAIN ANALYSIS
#___________________________________________________________________________________________________________________
def split_email(email: str):
    """
    Rozdělí e-mail na local_part a domain_part.
    Pokud e-mail obsahuje '@', vrátí (local_part, domain_part) - domain_part zůstane v původním tvaru.
    """
    parts = email.split('@', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return parts[0], ""
    

# Seznam free e-mailových poskytovatelů
free_email_providers = {
    "seznam.cz", "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "centrum.cz", "email.cz"
}

def analyze_domain(domain: str):
    """
    Analyzuje doménovou část e-mailu a určuje, zda se jedná o free e-mail.
    Vrací slovník:
      {
         "is_free": bool,         # True, pokud je doména free
         "domain": str            # Původní doména (např. firma.cz)
      }
    """
    domain = domain.lower().strip()
    result = {"is_free": False, "domain": domain}
    if domain in free_email_providers:
        result["is_free"] = True
    return result
    
#___________________________________________________________________________________________________________________
#                                            EXTRACT NAME FROM LOCAL_PART
#___________________________________________________________________________________________________________________

# Extrahování jména z e-mailové adresy a pokus o jeho porovnání s existujícím jménem ve slovníku
def extract_name_from_email(email: str):
    # Získáme lokální část e-mailu (část před znakem @)
    local_part = email.split('@')[0]
    # Odstraníme všechny znaky kromě malých písmen, tečky, podtržítka a pomlčky
    local_part = re.sub(r"[^a-z.\-_]", "", local_part)

    dividers_found = False

    # 1) Zkusíme rozdělit lokální část pomocí běžných oddělovačů ('.', '_', '-')
    for divider in ['.', '_', '-']:
        if divider in local_part:
            dividers_found = True
            parts = local_part.split(divider, 1)
            if len(parts) != 2:
                continue
            candidate1, candidate2 = parts[0], parts[1]
            candidate1_clean = remove_diacritics(candidate1).lower()
            candidate2_clean = remove_diacritics(candidate2).lower()

            # Varianta A: předpokládáme formát first.last
            if candidate1_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate1_clean]
                if candidate2:
                    first_letter = remove_diacritics(candidate2)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if candidate2_clean in surnames_dict:
                        correct_surname = surnames_dict[candidate2_clean]
                        return f"{correct_first} {correct_surname}"
                    else:
                        return f"{correct_first} {candidate2.title()}"

            # Varianta B: předpokládáme formát surname.first
            if candidate2_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate2_clean]
                if candidate1:
                    first_letter = remove_diacritics(candidate1)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if candidate1_clean in surnames_dict:
                        correct_surname = surnames_dict[candidate1_clean]
                        return f"{correct_first} {correct_surname}"
                    else:
                        return f"{correct_first} {candidate1.title()}"

            # Varianta C: Pokud je rozpoznáno pouze křestní jméno v candidate1
            if candidate1_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate1_clean]
                return f"{correct_first} {candidate2.title()}"

            # Varianta D: Pokud je rozpoznáno pouze křestní jméno v candidate2
            if candidate2_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate2_clean]
                return f"{correct_first} {candidate1.title()}"

            # Teprve poté zkusíme jednopísmennou iniciálu
            if len(candidate1) == 1:
                # candidate1 je křestní jméno (iniciala)
                first_name = candidate1.upper() + "."
                if candidate2:
                    first_letter = remove_diacritics(candidate2)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if candidate2_clean in surnames_dict:
                        surname = surnames_dict[candidate2_clean]
                    else:
                        surname = candidate2.title()
                    return f"{first_name} {surname}"

            if len(candidate2) == 1:
                # candidate2 je křestní jméno (iniciala)
                first_name = candidate2.upper() + "."
                if candidate1:
                    first_letter = remove_diacritics(candidate1)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if candidate1_clean in surnames_dict:
                        surname = surnames_dict[candidate1_clean]
                    else:
                        surname = candidate1.title()
                    return f"{first_name} {surname}"

    # 2) Nebyly nalezeny rozdělovače
    if not dividers_found:
        local_clean = remove_diacritics(local_part).lower()
        # Nejprve zkusíme, zda celé local_part odpovídá křestnímu jménu
        if local_clean in name_no_diacritics:
            return name_no_diacritics[local_clean]

        # Procházíme indexy pozpátku, abychom preferovali delší shody
        for i in reversed(range(1, len(local_clean))):
            first_candidate_clean = local_clean[:i]
            second_candidate_clean = local_clean[i:]
            first_candidate_orig = local_part[:i]
            second_candidate_orig = local_part[i:]

            # Pokud je první část validní křestní jméno
            if first_candidate_clean in name_no_diacritics:
                correct_first = name_no_diacritics[first_candidate_clean]
                # Zkusíme druhou část ve slovníku příjmení
                if second_candidate_orig:
                    first_letter = remove_diacritics(second_candidate_orig)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if second_candidate_clean in surnames_dict:
                        correct_surname = surnames_dict[second_candidate_clean]
                        return f"{correct_first} {correct_surname}"
                    else:
                        return f"{correct_first} {second_candidate_orig.title()}"

            # Nebo pokud je druhá část validní křestní jméno
            if second_candidate_clean in name_no_diacritics:
                correct_first = name_no_diacritics[second_candidate_clean]
                # Zkusíme první část ve slovníku příjmení
                if first_candidate_orig:
                    first_letter = remove_diacritics(first_candidate_orig)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if first_candidate_clean in surnames_dict:
                        correct_surname = surnames_dict[first_candidate_clean]
                        return f"{correct_first} {correct_surname}"
                    else:
                        return f"{correct_first} {first_candidate_orig.title()}"

        # Pokud nic z výše uvedeného nevyšlo, zkusíme odebrat poslední/první znak a ověřit, zda takto zkrácený
        # řetězec není ve slovníku příjmení či jmen
        if len(local_part) > 1:
            # Odebrání posledního znaku
            without_last = local_part[:-1]
            without_last_clean = remove_diacritics(without_last).lower()
            last_char = local_part[-1]

            # Zkusíme, jestli zkrácený řetězec je příjmení
            first_letter_surname = remove_diacritics(without_last)[0].upper()
            surnames_dict = load_surname_dictionary(first_letter_surname)
            if without_last_clean in surnames_dict:
                # Nalezeno jako příjmení
                return f"{last_char.upper()}. {surnames_dict[without_last_clean]}"

            # Zkusíme, jestli zkrácený řetězec je křestní jméno
            if without_last_clean in name_no_diacritics:
                return f"{name_no_diacritics[without_last_clean]} {last_char.upper()}."

            # Odebrání prvního znaku
            without_first = local_part[1:]
            without_first_clean = remove_diacritics(without_first).lower()
            first_char = local_part[0]

            first_letter_surname = remove_diacritics(without_first)[0].upper() if without_first else ""
            surnames_dict = load_surname_dictionary(first_letter_surname) if first_letter_surname else {}
            if without_first_clean in surnames_dict:
                return f"{first_char.upper()}. {surnames_dict[without_first_clean]}"

            if without_first_clean in name_no_diacritics:
                return f"{name_no_diacritics[without_first_clean]} {first_char.upper()}."

    # 3) Fallback: Pokud nic nevyšlo, vrátíme local_part.title()
    return local_part.title()


#___________________________________________________________________________________________________________________
#                                                 WEBDRIVER SETTINGS
#___________________________________________________________________________________________________________________

# Seznam HTTP User-Agent záhlaví pro maskování požadavků, aby napodobovaly různé prohlížeče
headers_list = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36"
    },
    {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.48"
    },
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.105 Mobile Safari/537.36"
    }
]

# Nastavení možností prohlížeče
def initialize_driver():
    service = Service("/usr/bin/chromedriver")
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    
    # Nastavení náhodného User-Agenta
    user_agent = random.choice(headers_list)
    options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(service=service, options=options)
    return driver

#Funkce pro očištění URL od nežádoucích parametrů
def clean_url(url):
    url = re.sub(r"(\?.*|#.*)", "", url)  # Odstraníme query parametry a kotvy
    return url

#___________________________________________________________________________________________________________________
#                                                     SCRAPER
#___________________________________________________________________________________________________________________

models_dir = os.path.join(BASE_DIR, "models", "facebook-bart-large-mnli")

# Kontrola, zda model existuje, pokud ne, stáhne ho
if not os.path.exists(models_dir):
    print("Model not found locally. Downloading...")
    model = AutoModelForSequenceClassification.from_pretrained("facebook/bart-large-mnli")
    tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-mnli")

    # Uloží model lokálně
    model.save_pretrained(models_dir)
    tokenizer.save_pretrained(models_dir)
    print(f"Model stažen do: {models_dir}")
else:
    print("Using local model.")

# Kontrola dostupnosti GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Použitý hardware: {'GPU' if device == 'cuda' else 'CPU'}")

# Načtení modelu a tokenizéru s podporou GPU
model = AutoModelForSequenceClassification.from_pretrained(
    models_dir,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,  # Optimalizace paměti pro GPU
    device_map="auto" if device == "cuda" else None  # Automatické mapování na GPU
)
tokenizer = AutoTokenizer.from_pretrained(models_dir)

# Nastavení pipeline s ručně načteným modelem a tokenizérem
classifier = pipeline("zero-shot-classification", model=model, tokenizer=tokenizer)

def classify_content(text):
    """
    Pomocí zero-shot klasifikace určí kategorii obsahu.
    Vrací tuple (nejpravděpodobnější kategorie, skóre).
    """
    candidate_labels = ["sports", "school", "social media", "other"]
    result = classifier(text, candidate_labels, multi_label=False)
    return result["labels"][0], result["scores"][0]

def analyze_page_content(url, driver):
    try:
        print(f"Analyzing: {url}")
        driver.get(url)

        # Použití WebDriverWait místo pevného time.sleep
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Krátká pauza

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Extrakce titulu, meta description, nadpisů a odstavců
        title = soup.title.string if soup.title else ""
        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_description = meta_tag.get("content", "")

        headings = " ".join([h.get_text(separator=' ', strip=True) for h in soup.find_all(["h1", "h2", "h3"])])
        paragraphs = " ".join([p.get_text(separator=' ', strip=True) for p in soup.find_all("p")])

        # Celý text pro kontrolu jména
        full_text = " ".join([title, meta_description, headings, paragraphs])
        full_text = " ".join(full_text.split())  # odstraní přebytečné mezery
        
        # Pro klasifikaci omezíme text na prvních 300 slov
        words = full_text.split()[:300]
        preprocessed_text = " ".join(words)
        
        # Zero-shot klasifikace na předzpracovaný text
        candidate_labels = ["sports", "school", "social media", "other"]
        classifier_result = classifier(preprocessed_text, candidate_labels, multi_label=False)
        category_ai = classifier_result["labels"][0]
        score_ai = classifier_result["scores"][0]
        print(f"Zero-shot classification result: {category_ai} with score {score_ai:.2f}")

        # Heuristická kontrola, pokud AI není dostatečně přesvědčená (score < 0.5)
        if score_ai < 0.5:
            # Pokud URL obsahuje známé domény sociálních sítí
            if any(domain in url for domain in [...]):
                category_ai = "social media"
                score_ai = 0.9
            # Kontrola pro školní obsah
            elif any(keyword in preprocessed_text.lower() for keyword in ["university", "school", "college", "gymnázium", "škola", "institut", "univerzita", "student", "absolvent", "fakulta", "faculty", "studium"]):
                category_ai = "school"
                score_ai = 0.7
            # Kontrola pro sportovní obsah na základě klíčových slov v textu
            elif any(keyword in preprocessed_text.lower() for keyword in ["sport", "rowing", "basketball", "football", "tennis", "veslování", "basketbal", "fotbal", "tenis", "házená", "volejbal", "turnaj", "pohár", "mistrovství", "championship", "cup", "tournament"]):
                category_ai = "sports"
                score_ai = 0.7

        # Extrakce odkazů na sociální sítě (ponecháváme původní logiku)
        social_media_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(site in href for site in ["facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com", "youtube.com", "linkedin.com", "threads.net"]):
                social_media_links.append(href)
        
        results = {
            "title": title,
            "description": meta_description,
            "full_text": full_text,           # Uložíme si i celý text
            "preprocessed_text": preprocessed_text,
            "category": category_ai,
            "score": score_ai,
            "social_media_links": social_media_links
        }
        return results

    except Exception as e:
        print(f"❌Error analyzing {url}: {e}")
        return {}
    
#___________________________________________________________________________________________________________________
#                                                      SEARCH
#___________________________________________________________________________________________________________________

# Vyhledání informací na DuckDuckGo
def search_duckduckgo(query):
    try:
        time.sleep(random.uniform(3, 8))  # Náhodná pauza mezi 3–8 sekundami
        with DDGS() as ddgs:
            # Použijeme set comprehension, který zajistí, že každý odkaz (r['href']) bude jedinečný
            results = {r['href'] for r in ddgs.text(query, max_results=10)}
        # Vrátíme výsledky jako list (pokud potřebujeme pracovat s indexací nebo iterací v konkrétním pořadí)
        return list(results)
    except Exception as e:
        print(f'Error during DuckDuckGo search: {e}')
        return []

# Vytvoření variant jmen pro vyhledávání
def generate_name_variants(extracted_name):
    """
    Vytvoří různé kombinace jména a příjmení pro vyhledávání.
    Kromě toho přidává variantu s uvozovkami, abychom dosáhli přesnějších výsledků.
    """
    if not extracted_name or len(extracted_name.split()) != 2:
        return []

    # Přidáme "exact match" variantu s uvozovkami (s diakritikou)
    variants = [f'"{extracted_name}"']

    first_name, last_name = extracted_name.split()

    # Odstranění mezer a diakritiky pro další variace
    first_name_clean = remove_diacritics(first_name).lower()
    last_name_clean = remove_diacritics(last_name).lower()

    variants.extend([
        f"{first_name_clean}{last_name_clean}",
        f"{first_name_clean}.{last_name_clean}",
        f"{first_name_clean}_{last_name_clean}",
        f"{last_name_clean}{first_name_clean}",
        f"{last_name_clean}.{first_name_clean}",
        f"{last_name_clean}_{first_name_clean}"
    ])
    return variants

#___________________________________________________________________________________________________________________
#                                                   NAME CONTROL
#___________________________________________________________________________________________________________________

def contains_name(page_text, extracted_name):
    """
    Ověří, zda se v textu stránky skutečně vyskytuje cílové jméno
    (ať už s diakritikou, nebo bez ní).
    """
    extracted_clean = remove_diacritics(extracted_name).lower()
    page_clean = remove_diacritics(page_text).lower()
    return extracted_clean in page_clean

#___________________________________________________________________________________________________________________
#                                                 DATABASE ACCESS
#___________________________________________________________________________________________________________________

def get_all_users():
    """
    Načte všechny záznamy z tabulky user_data.
    Vrací seznam řádků s hodnotami: email, social_media, school, sports, other.
    """
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT email, social_media, school, sports, other FROM user_data")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return rows
        except Exception as e:
            print(f"Chyba při načítání uživatelů: {e}")
            return []
    return []


#___________________________________________________________________________________________________________________
#                                                       MAIN
#___________________________________________________________________________________________________________________
def main():
    # Načtení všech uživatelů z databáze (tabulka user_data)
    users = get_all_users()
    if not users:
        print("V databázi nebyl nalezen žádný záznam.")
        return
    

    for user in users:
        email, social_media, school, sports, other = user
        # Pokud již má alespoň jeden ze sloupců data ze scraperu, přeskočíme tento email
        if social_media or school or sports or other:
            print(f"Email {email} již má data ze scraperu. Přeskakuji.")
            continue

        local_part, domain_part = split_email(email)
        domain_info = analyze_domain(domain_part)
        extracted = extract_name_from_email(email)
        
        print(f"\nZpracovávám email: {email}")
        print(f"Local part: {local_part}")
        print(f"Domain part: {domain_part}")
        print(f"Domain info: {domain_info}")
        if extracted:
            print(f"Extrahované jméno: {extracted}")
        else:
            print("Nepodařilo se extrahovat jméno.")

        # Sestavení vyhledávacích dotazů
        search_queries = []
        if extracted:
            # 1) Přesná shoda s uvozovkami + doména (firemní e-mail)
            if not domain_info["is_free"]:
                # U dotazu s doménou kontrolujeme jméno (protože obsahuje i jméno)
                search_queries.append((f'"{extracted}" {domain_part}', True))
            # 2) Přesná shoda jména bez domény
            search_queries.append((f'"{extracted}"', True))
            # 3) Generované varianty jména s a bez domény
            name_variants = generate_name_variants(extracted)
            for variant in name_variants:
                # Varianta bez domény
                search_queries.append((variant, True))
                # Varianta s doménou (firemní)
                if not domain_info["is_free"]:
                    search_queries.append((f"{variant} {domain_part}", True))
            # 4) Samostatné vyhledání domény (pokus o nalezení firmy) – zde NEkontrolujeme jméno
            if domain_part and not domain_info["is_free"]:
                search_queries.append((domain_part, False))
        # Pokud se jméno nepodařilo extrahovat, vyhledáme aspoň e-mail nebo doménu
        else:
            search_queries.append((email, False))
            if domain_part:
                search_queries.append((domain_part, False))
        print("Search queries:", search_queries)

        # Vyhledání informací pomocí DuckDuckGo a uložení s příznakem check_name
        all_urls = {}
        for (q, check_name) in search_queries:
            results = search_duckduckgo(q)
            for url in results:
                if url in all_urls:
                    # Pokud se URL již vyskytuje, nová hodnota bude logický součin (pokud jeden dotaz nevyžaduje kontrolu, nastavíme False)
                    all_urls[url] = all_urls[url] and check_name
                else:
                    all_urls[url] = check_name
        print("DuckDuckGo Results:", list(all_urls.keys()))

        # Nyní zpracujeme každé URL s ohledem na check_name
        if not all_urls:
            print('Nebyla nalezena žádná URL.')
            continue
        else:
            results_data = {}
            driver = initialize_driver()
            for url, check in all_urls.items():
                result = analyze_page_content(url, driver)
                # Pokud check_name je True, provádíme kontrolu, zda stránka obsahuje hledané jméno
                if check and extracted:
                    text_clean = remove_diacritics(result.get("full_text", "")).lower()
                    name_clean = remove_diacritics(extracted).lower()
                    if name_clean not in text_clean:
                        print(f"Stránka {url} neobsahuje hledané jméno '{extracted}', vyřazuji.")
                        continue
                results_data[url] = result
            driver.quit()

            # Inicializace seznamů pro jednotlivé kategorie
            social_media_results = []
            school_results = []
            sports_results = []
            other_results = []

            # Procházíme výsledky a rozdělíme je podle kategorie
            for url, data in results_data.items():
                summary = f"URL: {url}, Title: {data.get('title', 'N/A')}, Desc: {data.get('description', 'N/A')}, Score: {data.get('score', 0):.2f}"
                category = data.get("category", "").lower()
                if "social media" in category:
                    social_media_results.append(summary)
                elif "school" in category:
                    school_results.append(summary)
                elif "sports" in category:
                    sports_results.append(summary)
                else:
                    other_results.append(summary)

            social_media_value = "\n".join(social_media_results) if social_media_results else None
            school_value = "\n".join(school_results) if school_results else None
            sports_value = "\n".join(sports_results) if sports_results else None
            other_value = "\n".join(other_results) if other_results else None

            # Uložíme všechna nalezená data do databáze
            upsert_user(email,
                        email_domain=domain_part,
                        social_media=social_media_value,
                        school=school_value,
                        sports=sports_value,
                        other=other_value)
            print(f"Databáze aktualizována pro {email} s kategoriemi:")
            print("Social media:", social_media_value)
            print("School:", school_value)
            print("Sports:", sports_value)
            print("Other:", other_value)


if __name__ == "__main__":
    load_dotenv()
    main()