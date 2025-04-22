import os
import psycopg2
from dotenv import load_dotenv

# Načtení proměnných prostředí z .env souboru
load_dotenv()

# Parametry pro připojení k databázi
DB_PARAMS = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': os.getenv('POSTGRES_PORT')
}

def get_db_connection():
    """Naváže spojení s databází pomocí nastavení z DB_PARAMS."""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Chyba připojení k DB: {e}")
        return None

def initialize_database():
    """
    Inicializuje databázi vytvořením tabulky user_data se sloupci:
    id, email, token, email_domain,
    social_media, school, sports, other
    """
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    id SERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    token TEXT,
                    email_domain TEXT,
                    social_media TEXT,
                    school TEXT,
                    sports TEXT,
                    other TEXT
                );
            ''')
            conn.commit()
            print("✅ Databáze byla úspěšně inicializována.")
        except Exception as e:
            print(f"❌ Chyba při inicializaci databáze: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        print("❌ Nepodařilo se připojit k databázi pro inicializaci.")

def upsert_user(email, token=None, email_domain=None,
                social_media=None, school=None, sports=None, other=None):
    """
    Vloží nový záznam do tabulky user_data nebo aktualizuje existující záznam dle emailu.
    Aktualizují se sloupce: token, social_media,email_domain, school, sports, other.
    """
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO user_data (
                    email, token, email_domain,
                    social_media, school, sports, other
                )
                VALUES (%s, %s, %s,
                        %s, %s, %s, %s)
                ON CONFLICT (email) 
                DO UPDATE SET 
                    token = COALESCE(EXCLUDED.token, user_data.token),
                    email_domain = COALESCE(EXCLUDED.email_domain, user_data.email_domain),
                    social_media = COALESCE(EXCLUDED.social_media, user_data.social_media),
                    school = COALESCE(EXCLUDED.school, user_data.school),
                    sports = COALESCE(EXCLUDED.sports, user_data.sports),
                    other = COALESCE(EXCLUDED.other, user_data.other);
            ''', (email, token, email_domain,
                  social_media, school, sports, other))
            conn.commit()
            print("✅ Data byla úspěšně vložena/aktualizována.")
        except Exception as e:
            conn.rollback()
            print(f"❌ Chyba při vkládání/aktualizaci dat: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        print("❌ Nepodařilo se připojit k databázi.")

if __name__ == '__main__':
    initialize_database()
