import os
import unicodedata
import random
from duckduckgo_search import DDGS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
import re
import instaloader

#___________________________________________________________________________________________________________________
#                                                     DICTIONARY
#___________________________________________________________________________________________________________________


# Získání cesty ke složce, kde je uložen tento skript
script_dir = os.path.dirname(os.path.abspath(__file__))
txt_path = os.path.join(script_dir, 'czech_names.txt')

# Načtení slovníku českých jmen ze souboru s ošetřením chyb
try:
    with open(txt_path, 'r', encoding='utf-8') as f:
        name_dictionary = set(line.strip() for line in f if line.strip())
except FileNotFoundError:
    print(f"❌Error: Soubor '{txt_path}' nebyl nalezen.")
    name_dictionary = set()
except Exception as e:
    print(f"❌Error při čtení souboru '{txt_path}': {e}")
    name_dictionary = set()

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

#___________________________________________________________________________________________________________________
#                                                     INSTALOADER
#___________________________________________________________________________________________________________________

# Inicializace Instaloaderu
L = instaloader.Instaloader()
scraped_instagrams = set()  # Sada pro ukládání už scrapnutých profilů

def extract_instagram_username(url):
    match = re.search(r"instagram\.com/([^/?#]+)", url)
    return match.group(1) if match else None

# Funkce pro extrakci uživatelského jména z Instagram URL
def get_instagram_profile_details(username, retries=2):
    if username in scraped_instagrams:
        print(f"✅ Instagram profil @{username} už byl scrapnutý, přeskočeno.")
        return None  # Nepokračujeme, pokud už máme data

    for attempt in range(retries):
        try:
            wait_time = random.randint(60, 180)  # Náhodné čekání 1-3 minuty mezi dotazy
            print(f"⏳ Čekám {wait_time} sekund před dotazem na profil @{username}...")
            time.sleep(wait_time)

            profile = instaloader.Profile.from_username(L.context, username)
            scraped_instagrams.add(username)  # Přidáme username do scrapnutých

            return {
                "full_name": profile.full_name,
                "followers": profile.followers,
                "following": profile.followees,
                "bio": profile.biography,
                "external_url": profile.external_url
            }

        except Exception as e:
            print(f"❌ Chyba při získávání profilu @{username} (pokus {attempt + 1}/{retries}): {e}")

            if "Please wait a few minutes" in str(e):
                wait_time = random.randint(600, 1200)  # Čekej 10-20 minut
                print(f"🚨 Instagram limit, čekám {wait_time} sekund před dalším pokusem...")
                time.sleep(wait_time)
            else:
                return None  # Pokud je jiná chyba, ukonči smyčku hned

    return None  # Pokud selžou všechny pokusy, vrať None

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

# Inicializace prohlížeče Chrome
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Extrakce uživatelského jména z URL
def extract_username_from_url(url, site):
    url = clean_url(url)  # Nejprve očistíme URL
    pattern = rf"{re.escape(site)}/([^/?#]+)"
    match = re.search(pattern, url)
    
    if match:
        username = match.group(1)
        # Filtrujeme neplatná uživatelská jména
        if username.lower() not in ["login", "home", "settings", "explore", "company", "sharer", "intent", "help", "people", "accessibility", "recover", "watch", "policies", "legal", "public", "v", "_u", "blog", "about-us"]:
            return re.sub(r"[-\d]+$", "", username)  # Odstraníme koncové čísla/ID
    return None

#Funkce pro očištění URL od nežádoucích parametrů
def clean_url(url):
    url = re.sub(r"(\?.*|#.*)", "", url)  # Odstraníme query parametry a kotvy
    return url


#___________________________________________________________________________________________________________________
#                                                       SCRAPER
#___________________________________________________________________________________________________________________


# Extrahuje data jako adresy, telefonní čísla, sportovní kluby, zaměstnání a sociální profily
def scrape_information_from_url(url, name_to_search):
    try:
        print(f"Scraping: {url} with User-Agent: {user_agent}")  # Debug výpis

        driver.get(url)  
        time.sleep(3)  

        # Posunutí stránky dolů pro načtení dynamického obsahu
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  

        soup = BeautifulSoup(driver.page_source, 'html.parser')  

        # Extrahujeme text stránky a zajistíme, že není None
        text = soup.get_text() if soup else ""

        # Inicializace sad pro ukládání dat
        addresses = set()
        phone_numbers = set()
        sports_clubs = set()
        employment = set()
        social_profiles = set()

        # Seznam sociálních sítí k detekci
        social_sites = ["linkedin.com", "facebook.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com"]
        temp_profiles = set()

        # Hledání odkazů na sociální sítě v HTML kódu
        for link in soup.find_all("a", href=True):  
            href = link["href"]
            link_text = link.get_text(strip=True) if link.get_text() else ""   

            for site in social_sites:
                if site in href:
                    username = extract_username_from_url(href, site)
                    if username:
                        temp_profiles.add(f"{site}/{username}")
                #Pokud URL neobsahuje uživatelské jméno, ale text odkazu ano
                elif site in link_text.lower():
                    temp_profiles.add(f"{site}/{link_text}")

        # Použití textu pro analýzu dalších informací
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

        # Odstraníme možné duplikáty na základě uživatelského jména
        unique_profiles = set()
        for profile in temp_profiles:
            base_profile = re.sub(r"[-\d]+$", "", profile)  # Odstraní čísla na konci
            unique_profiles.add(base_profile)

        # Seřazení podle domény
        sorted_profiles = sorted(unique_profiles, key=lambda x: (x.split('/')[0], x.split('/')[1] if '/' in x else ""))
        # Odstranění doublování
        social_profiles.update(sorted_profiles)  # Uložíme jen unikátní profily

        # Informace z Instaloaderu Instagramu
        instagram_details = {}
        for profile in social_profiles:
            if "instagram.com" in profile:
                username = extract_instagram_username(profile)
                if username:
                    details = get_instagram_profile_details(username)
                    if details:
                        instagram_details[username] = details

        return {
            'addresses': addresses,
            'phone_numbers': phone_numbers,
            'sports_clubs': sports_clubs,
            'employment': employment,
            'social_profiles': social_profiles
        }
    except Exception as e:
        print(f"Error accessing {url}: {e}")
        return {
            'addresses': set(),
            'phone_numbers': set(),
            'sports_clubs': set(),
            'employment': set(),
            'social_profiles': set()
        }

#___________________________________________________________________________________________________________________
#                                                   SEARCH
#___________________________________________________________________________________________________________________


# Vyhledání informací na DuckDuckGo
def search_duckduckgo(query):
    try:
        with DDGS() as ddgs:
            results = [r['href'] for r in ddgs.text(query, max_results=10)]
        return results
    except Exception as e:
        print(f'Error during DuckDuckGo search: {e}')
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


#___________________________________________________________________________________________________________________
#                                                       MAIN
#___________________________________________________________________________________________________________________



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
            search_results.extend(search_duckduckgo(variant))
    else:
        search_results = search_duckduckgo(query_name)
    
    print("DuckDuckGo Results:", search_results) # Debug info

    if not search_results:
        print('No search results found')
    else:
        all_addresses = set()
        all_phone_numbers = set()
        all_sports_clubs = set()
        all_employment = set()
        all_social_profiles = set()
        all_instagram_details = {}

        for link in search_results:
            print(f"Scraping data from: {link}")  # Debug info
            info = scrape_information_from_url(link, query_name)
            all_addresses.update(info['addresses'])
            all_phone_numbers.update(info['phone_numbers'])
            all_sports_clubs.update(info['sports_clubs'])
            all_employment.update(info['employment'])
            all_social_profiles.update(info['social_profiles'])
            if 'instagram_details' in info:
                all_instagram_details.update(info['instagram_details'])


        # Výpis nalezených informací
        print('\nNalezené informace:')
        if all_addresses:
            print('\n📍 Adresy:')
            for address in all_addresses:
                print(address)
        if all_phone_numbers:
            print('\n📞 Telefonní čísla:')
            for number in all_phone_numbers:
                print(number)
        if all_sports_clubs:
            print('\n⚽ Sportovní kluby:')
            for club in all_sports_clubs:
                print(club)
        if all_employment:
            print('\n💼 Zaměstnání:')
            for job in all_employment:
                print(job)
        if all_social_profiles:
            print('\n🌍 Sociální profily:')
            for profile in all_social_profiles:
                print(profile)

        if all_instagram_details:
            print('\n📸 Detailní informace z Instagramu:')
            for username, details in all_instagram_details.items():
                print(f"\n🔹 Instagram: @{username}")
                print(f"   📛 Jméno: {details['full_name']}")
                print(f"   👥 Sledující: {details['followers']}")
                print(f"   🎯 Sleduje: {details['following']}")
                print(f"   📝 Bio: {details['bio']}")
                print(f"   🔗 Odkaz v bio: {details['external_url']}")

        if not (all_addresses or all_phone_numbers or all_sports_clubs or all_employment or all_social_profiles):
            print('Žádné informace nebyly nalezeny.')

    # Ukončení Selenium WebDriveru na konci programu
    driver.quit()
