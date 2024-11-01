import requests
from bs4 import BeautifulSoup
import re
import random
import time
from googlesearch import search
import unicodedata

# Slovník běžných českých jmen pro kontrolu
name_dictionary = {
    "Jan", "Petr", "Jana", "Josef", "Marie", "Eva", "Jiří", "Pavel", "Lucie", "Martin",
    "Jakub", "Veronika", "Tomáš", "Michal", "Anna", "Tereza", "Miroslav", "Karel", "Václav", "Alena",
    "Lenka", "Marek", "Zdeněk", "David", "Jaroslav", "Vladimír", "Petra", "Helena", "Věra", "Roman",
    "Ondřej", "Filip", "Hana", "Radek", "Daniel", "Šárka", "Ivana", "Barbora", "Michala", "Libor"
}


def remove_diacritics(input_str):
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )

# Slovník bez diakritiky pro porovnání
name_dictionary_no_diacritics = {
    remove_diacritics(name).lower(): name for name in name_dictionary
}

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
]


def scrape_information_from_url(url, name_to_search):
    try:
        response = requests.get(url, headers=random.choice(headers_list))
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        addresses = set()
        phone_numbers = set()
        sports_clubs = set()
        employment = set()
        social_profiles = set()

        # (Přidat kód pro scraping adres, telefonních čísel, sociálních sítí atd.)

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


def remove_diacritics(input_str):
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )

def is_name_in_dictionary(name):
    name_no_diacritics = remove_diacritics(name).lower()
    return name_no_diacritics in name_dictionary_no_diacritics

def get_correct_name(name):
    name_no_diacritics = remove_diacritics(name).lower()
    return name_dictionary_no_diacritics.get(name_no_diacritics, name)

def extract_name_from_email(email):
    local_part = email.split('@')[0]
    print(f'Lokální část e-mailu: {local_part}')  # Debug print
    # První kontrola: Pokud lokální část obsahuje jméno a příjmení oddělené tečkou
    if '.' in local_part:
        name_parts = local_part.split('.')
        print(f'Rozdělená jména: {name_parts}')  # Debug print
        if len(name_parts) == 2:
            first_name = remove_diacritics(name_parts[0]).lower()
            last_name = remove_diacritics(name_parts[1]).lower()
            print(f'První jméno (bez diakritiky): {first_name}, Příjmení (bez diakritiky): {last_name}')  # Debug print
            print(f'Aktuální klíče ve slovníku jmen: {list(name_dictionary_no_diacritics.keys())}')  # Debug print slovníku
            if first_name in name_dictionary_no_diacritics or last_name in name_dictionary_no_diacritics:
                correct_first_name = name_dictionary_no_diacritics.get(first_name, first_name)
                correct_last_name = last_name
                potential_name = f"{correct_first_name} {correct_last_name}"
                print(f'Jméno extrahované z e-mailu: {potential_name}')
                return potential_name
            else:
                print(f'Jméno nebo příjmení nebylo nalezeno ve slovníku.')  # Debug print

    # Druhá kontrola: Pokud lokální část obsahuje pouze jedno jméno nebo kombinaci jmen
    local_part_no_diacritics = remove_diacritics(local_part).lower()
    print(f'Lokální část bez diakritiky: {local_part_no_diacritics}')  # Debug print
    if local_part_no_diacritics in name_dictionary_no_diacritics:
        correct_name = name_dictionary_no_diacritics[local_part_no_diacritics]
        print(f'Jméno extrahované z e-mailu: {correct_name}')
        return correct_name

    # Pokud žádná metoda neuspěje, vracíme informaci o nenalezeném jménu
    else:
        print('Jméno nebylo extrahováno z e-mailu.')  # Debug print
        return None

def search_google(query):
    try:
        search_results = search(query, num_results=10)
        return list(search_results)
    except Exception as e:
        print(f'Error during Google search: {e}')
        return []

def main():
    email_query = input('Zadejte e-mail nebo klíčové slovo pro hledání: ')
    print(f'Hledám informace pro jméno nebo e-mail: {email_query}')
    # Zjištění jména a příjmení na základě e-mailu
    extracted_name = extract_name_from_email(email_query)

    if extracted_name:
        query_name = extracted_name
        print(f'Vyhledávám informace pro extrahované jméno: {query_name}')  # Debug print
    else:
        query_name = email_query
        print(f'Vyhledávám informace pro e-mail: {query_name}')  # Debug print

    # Vyhledávání informací o osobě spjaté s tímto e-mailem
    search_results = search_google(query_name)
    if not search_results:
        print('No search results found')
        return

    all_addresses = set()
    all_phone_numbers = set()
    all_sports_clubs = set()
    all_employment = set()
    all_social_profiles = set()

    for link in search_results:
        time.sleep(random.uniform(1, 3))  # Pauza mezi požadavky, aby se omezilo blokování
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
    else:
        print('Adresy: žádné nenalezeny.')
    if all_phone_numbers:
        print('Telefonní čísla:')
        for number in all_phone_numbers:
            print(number)
    else:
        print('Telefonní čísla: žádná nenalezena.')
    if all_sports_clubs:
        print('Sportovní kluby:')
        for club in all_sports_clubs:
            print(club)
    else:
        print('Sportovní kluby: žádné nenalezeny.')
    if all_employment:
        print('Zaměstnání:')
        for job in all_employment:
            print(job)
    else:
        print('Zaměstnání: žádné nenalezeno.')
    if all_social_profiles:
        print('Sociální profily:')
        for profile in all_social_profiles:
            print(profile)
    else:
        print('Sociální profily: žádné nenalezeny.')


if __name__ == '__main__':
    main()
