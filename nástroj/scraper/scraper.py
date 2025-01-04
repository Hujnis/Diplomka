import requests
from bs4 import BeautifulSoup
import random
import time
from googlesearch import search
import unicodedata
import os

# Získání cesty ke složce, kde je uložen tento skript
script_dir = os.path.dirname(os.path.abspath(__file__))
txt_path = os.path.join(script_dir, 'czech_names.txt')

# Načtení slovníku českých jmen ze souboru s ošetřením chyb
try:
    with open(txt_path, 'r', encoding='utf-8') as f:
        name_dictionary = set(line.strip() for line in f if line.strip())
except FileNotFoundError:
    print(f"Error: Soubor '{txt_path}' nebyl nalezen.")
    name_dictionary = set()
except Exception as e:
    print(f"Error při čtení souboru '{txt_path}': {e}")
    name_dictionary = set()


# Function to remove diacritics from text
# Užitečné pro porovnávání jmen s diakritikou i bez ní
def remove_diacritics(input_str):
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )

# Vytvoření verze slovníku jmen bez diakritiky pro snazší porovnání
dictionary_no_diacritics = {
    remove_diacritics(name).lower(): name for name in name_dictionary
}

# Kontrola, zda je dané jméno ve slovníku (bez ohledu na velikost písmen, bez diakritiky)
def is_name_in_dictionary(name):
    name_no_diacritics = remove_diacritics(name).lower()
    return name_no_diacritics in dictionary_no_diacritics

# Získání správného jména ze slovníku, přičemž se zachovají původní diakritiky, pokud jsou přítomny
def get_correct_name(name):
    name_no_diacritics = remove_diacritics(name).lower()
    return dictionary_no_diacritics.get(name_no_diacritics, name)

# Extrahování jména z e-mailové adresy a pokus o jeho porovnání s existujícím jménem ve slovníku
def extract_name_from_email(email):
    local_part = email.split('@')[0]
    # První kontrola: pokud lokální část obsahuje jméno a příjmení oddělené tečkou
    if '.' in local_part:
        name_parts = local_part.split('.')
        if len(name_parts) == 2:
            # Odstranění diakritiky pro snadnější porovnání
            first_name = remove_diacritics(name_parts[0]).lower()
            last_name = remove_diacritics(name_parts[1]).lower()
            # Kontrola, zda je jméno nebo příjmení přítomno ve slovníku
            if first_name in dictionary_no_diacritics or (last_name and last_name in dictionary_no_diacritics):
                correct_first_name = dictionary_no_diacritics.get(first_name, first_name)
                correct_last_name = dictionary_no_diacritics.get(last_name, last_name)
                potential_name = f"{correct_first_name} {correct_last_name}"
                return potential_name

    # Druhá kontrola: pokud lokální část obsahuje pouze jedno jméno nebo kombinaci jmen
    local_part_no_diacritics = remove_diacritics(local_part).lower()
    if local_part_no_diacritics in dictionary_no_diacritics:
        correct_name = dictionary_no_diacritics[local_part_no_diacritics]
        return correct_name

    # Pokud žádná metoda neuspěje, vrátíme None k indikaci, že jméno nebylo nalezeno
    else:
        return None

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

# Funkce pro zobrazení URL stránek, které se scrapují
def log_scraping_attempt(url):
    print(f"Scraping: {url}")

# Extrahuje data jako adresy, telefonní čísla, sportovní kluby, zaměstnání a sociální profily
def scrape_information_from_url(url, name_to_search):
    log_scraping_attempt(url)  # Logování URL
    try:
        # Odeslání HTTP GET požadavku na poskytnutou URL adresu s náhodným User-Agent záhlavím a nastavením timeoutu
        response = requests.get(url, headers=random.choice(headers_list), timeout=10)
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception:
            print(f"Error parsing HTML for {url}, falling back to 'html5lib'.")
            soup = BeautifulSoup(response.text, 'html5lib')

        text = soup.get_text()
        addresses = set()
        phone_numbers = set()
        sports_clubs = set()
        employment = set()
        social_profiles = set()

        # Definované klíčové fráze pro sociální profily
        social_sites = ["linkedin.com", "facebook.com", "twitter.com", "instagram.com", "tiktok.com"]

        # Přidání vzorů pro analýzu textu
        for line in text.splitlines():
            line = line.strip()
            if name_to_search.lower() in line.lower():
                if "address" in line.lower():
                    addresses.add(line)
                if "phone" in line.lower():
                    phone_numbers.add(line)
                if "club" in line.lower():
                    sports_clubs.add(line)
                if "job" in line.lower():
                    employment.add(line)
            
            # Hledání odkazů na sociální profily
            for site in social_sites:
                if site in line.lower():
                    social_profiles.add(line)

        return {
            'addresses': addresses,
            'phone_numbers': phone_numbers,
            'sports_clubs': sports_clubs,
            'employment': employment,
            'social_profiles': social_profiles
        }
    except requests.exceptions.RequestException as e:
        print(f'Error accessing {url}: {e}')
        return {
            'addresses': set(),
            'phone_numbers': set(),
            'sports_clubs': set(),
            'employment': set(),
            'social_profiles': set()
        }

# Vyhledání informací na Googlu spojených s daným dotazem
def search_google(query):
    try:
        search_results = search(query, num_results=10)
        return list(search_results)
    except Exception as e:
        print(f'Error during Google search: {e}')
        return []

# Vytvoření variant jmen pro vyhledávání
def generate_name_variants(extracted_name):
    """
    Vytvoří různé kombinace jména a příjmení pro vyhledávání.

    :param extracted_name: Jméno ve formátu "Jméno Příjmení".
    :return: Seznam variant jména pro vyhledávání.
    """
    if not extracted_name or len(extracted_name.split()) != 2:
        return []

    first_name, last_name = extracted_name.split()

    # Odstranění mezer a diakritiky pro variace
    first_name = remove_diacritics(first_name).lower()
    last_name = remove_diacritics(last_name).lower()

    variants = [
        f"{first_name}{last_name}",
        f"{first_name}.{last_name}",
        f"{first_name}_{last_name}",
        f"{last_name}{first_name}",
        f"{last_name}.{first_name}",
        f"{last_name}_{first_name}"
    ]

    return variants

if __name__ == "__main__":
    email_query = input("Zadejte e-mail nebo klíčové slovo pro hledání: ")
    extracted_name = extract_name_from_email(email_query)
    print(f'Lokální část e-mailu: {email_query.split("@")[0]}')  # Debug výpis lokální části e-mailu
    if extracted_name:
        print(f'Extrahované jméno z e-mailu: {extracted_name}')
    else:
        print('Jméno nebylo extrahováno z e-mailu.')
    # Analýza jména na základě slovníku
    if extracted_name:
        if is_name_in_dictionary(extracted_name.split()[0]):
            print(f'Jméno "{extracted_name.split()[0]}" bylo nalezeno ve slovníku.')
        else:
            print(f'Jméno "{extracted_name.split()[0]}" nebylo nalezeno ve slovníku.')
    if extracted_name:
        name_variants = generate_name_variants(extracted_name)
        print("Vygenerované varianty jména:")
        for variant in name_variants:
            print(variant)
            query_name = variant
        print(f'Vyhledávám informace pro extrahované jméno: {extracted_name}')
    else:
        query_name = email_query
        print(f'Vyhledávám informace pro e-mail: {query_name}')

    # Vyhledávání informací o osobě spjaté s tímto e-mailem
    search_results = []
    if extracted_name:
        for variant in name_variants:
            search_results.extend(search_google(variant))
    else:
        search_results = search_google(query_name)

    if not search_results:
        print('No search results found')
    else:
        all_addresses = set()
        all_phone_numbers = set()
        all_sports_clubs = set()
        all_employment = set()
        all_social_profiles = set()

        for link in search_results:
            info = scrape_information_from_url(link, query_name)
            all_addresses.update(info['addresses'])
            all_phone_numbers.update(info['phone_numbers'])
            all_sports_clubs.update(info['sports_clubs'])
            all_employment.update(info['employment'])
            all_social_profiles.update(info['social_profiles'])

        # Výpis nalezených informací
        print('Nalezené informace:')
        if all_addresses:
            print('Adresy:')
            for address in all_addresses:
                print(address)
        if all_phone_numbers:
            print('Telefonní čísla:')
            for number in all_phone_numbers:
                print(number)
        if all_sports_clubs:
            print('Sportovní kluby:')
            for club in all_sports_clubs:
                print(club)
        if all_employment:
            print('Zaměstnání:')
            for job in all_employment:
                print(job)
        if all_social_profiles:
            print('Sociální profily:')
            for profile in all_social_profiles:
                print(profile)
        if not (all_addresses or all_phone_numbers or all_sports_clubs or all_employment or all_social_profiles):
            print('Žádné informace nebyly nalezeny.')
