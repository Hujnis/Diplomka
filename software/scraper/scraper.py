import os
import unicodedata
import random
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from transformers import pipeline

#___________________________________________________________________________________________________________________
#                                                     DICTIONARY
#___________________________________________________________________________________________________________________

# Absolutní cesta k tomuto souboru (scraper.py)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Cesta k adresáři "dictionaries"
dictionaries_dir = os.path.join(script_dir, "dictionaries")

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

# Extrahování jména z e-mailové adresy a pokus o jeho porovnání s existujícím jménem ve slovníku
def extract_name_from_email(email: str):
    # Získáme lokální část e-mailu (část před znakem @)
    local_part = email.split('@')[0]
    # Odstraníme všechny znaky kromě malých písmen, tečky, podtržítka a pomlčky
    local_part = re.sub(r"[^a-z.\-_]", "", local_part)
    
    # Zkusíme rozdělit lokální část pomocí běžných oddělovačů ('.', '_', '-')
    for divider in ['.', '_', '-']:
        if divider in local_part:
            parts = local_part.split(divider, 1)
            if len(parts) != 2:
                continue
            candidate1, candidate2 = parts[0], parts[1]
            candidate1_clean = remove_diacritics(candidate1).lower()
            candidate2_clean = remove_diacritics(candidate2).lower()
            
            # Varianta: pokud je jedna část pouze jeden znak, předpokládáme, že to je křestní jméno
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
            
            # Standardní varianta A: předpokládáme formát first.last
            if candidate1_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate1_clean]
                if candidate2:
                    first_letter = remove_diacritics(candidate2)[0].upper()
                    surnames_dict = load_surname_dictionary(first_letter)
                    if candidate2_clean in surnames_dict:
                        correct_surname = surnames_dict[candidate2_clean]
                        return f"{correct_first} {correct_surname}"
                    else:
                        # Pokud je candidate2 také nalezitelná jako křestní jméno, preferujeme variantu A a vrátíme ji v title case
                        return f"{correct_first} {candidate2.title()}"
            
            # Varianta B: předpokládáme formát surname.first (tedy candidate2 je křestní jméno)
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
            
            # Varianta C: Pokud je rozpoznáno pouze křestní jméno v candidate1, použijeme candidate2 jako příjmení (title case)
            if candidate1_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate1_clean]
                return f"{correct_first} {candidate2.title()}"
            
            # Varianta D: Pokud je rozpoznáno pouze křestní jméno v candidate2, použijeme candidate1 jako příjmení (title case)
            if candidate2_clean in name_no_diacritics:
                correct_first = name_no_diacritics[candidate2_clean]
                return f"{correct_first} {candidate1.title()}"
    
    # Fallback: Pokud nedojde k žádnému rozpoznání, vrátíme celou lokální část převedenou na title case
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
    options = Options()
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

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

#Funkce pro očištění URL od nežádoucích parametrů
def clean_url(url):
    url = re.sub(r"(\?.*|#.*)", "", url)  # Odstraníme query parametry a kotvy
    return url

#___________________________________________________________________________________________________________________
#                                                       SCRAPER
#___________________________________________________________________________________________________________________

# Inicializace klasifikátoru

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")  # dobrý pro zero-shot klasifikaci

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
        
        # Použití zero-shot klasifikace na předzpracovaný text
        candidate_labels = ["sports", "school", "social media", "other"]
        classifier_result = classifier(preprocessed_text, candidate_labels, multi_label=False)
        category_ai = classifier_result["labels"][0]
        score_ai = classifier_result["scores"][0]
        print(f"Zero-shot classification result: {category_ai} with score {score_ai:.2f}")

        # Heuristická kontrola, pokud AI není dostatečně přesvědčená (score < 0.5)
        if score_ai < 0.5:
            # Pokud URL obsahuje známé domény sociálních sítí
            if any(domain in url for domain in ["facebook.com", "instagram.com", "twitter.com", "youtube.com", "x.com", "tiktok.com", "linkedin.com", "threads.net"]):
                category_ai = "social media"
                score_ai = 0.9  # nastavíme vysokou důvěru
            # Kontrola pro sportovní obsah na základě klíčových slov v textu
            elif any(keyword in preprocessed_text.lower() for keyword in ["sport", "rowing", "basketball", "football", "tennis", "veslování", "basketbal", "fotbal", "tenis", "házená", "volejbal", "turnaj", "pohár", "mistrovství", "championship", "cup", "tournament"]):
                category_ai = "sports"
                score_ai = 0.7
            # Kontrola pro školní obsah
            elif any(keyword in preprocessed_text.lower() for keyword in ["university", "school", "college", "gymnázium", "škola", "institut"]):
                category_ai = "school"
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
#                                                       MAIN
#___________________________________________________________________________________________________________________
def main():
    email_query = input("Zadejte e-mail: ")
    extracted = extract_name_from_email(email_query)
    if extracted:
        print(f"Extrahované jméno a příjmení: {extracted}")
        name_variants = generate_name_variants(extracted)
        print("Vygenerované varianty jména:")
        for variant in name_variants:
            print(variant)
        query_name = extracted
        print(f'Vyhledávám informace pro extrahované jméno: {extracted}')
    else:
        print("Nepodařilo se extrahovat jméno a příjmení.")
        name_variants = []
        query_name = email_query

    # Vyhledávání informací pomocí DuckDuckGo
    search_results_set = set()
    if extracted:
        for variant in name_variants:
            # Každý variant vrátí list výsledků
            results_for_variant = search_duckduckgo(variant)
            search_results_set.update(results_for_variant)
    else:
        search_results_set.update(search_duckduckgo(query_name))
    search_results = list(search_results_set)
    
    print("DuckDuckGo Results:", search_results) # Debug info

    if not search_results:
        print('No search results found')
    else:
        results = {}
        driver = initialize_driver()
        for url in search_results:
            result = analyze_page_content(url, driver)
            # Dodatečný filtr – pokud se v textu stránky nenachází jméno, vyřadíme ji
            if not contains_name(result.get("full_text", ""), extracted):
                print(f"Stránka {url} neobsahuje jméno '{extracted}', vyřazuji.")
                continue
            # Pokud stránka prošla filtrem, uložíme výsledek
            results[url] = result

        driver.quit()

        # Výpis výsledků
        for url, data in results.items():
            print(f"\nResults for {url}")
            print(f"Title: {data.get('title')}")
            print(f"Description: {data.get('description')}")
            print(f"Keyword Count: {data.get('keyword_count')}")
            print(f"Social Media Links: {data.get('social_media_links')}")
            print(f"Structure Info: {data.get('structure_info')}")
            print(f"Sports Events: {data.get('sports_events')}")

if __name__ == "__main__":
    main()