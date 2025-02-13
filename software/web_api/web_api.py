from flask import Flask, request, render_template_string
import re
import os
import psycopg2
from dotenv import load_dotenv

# Načtení proměnných z .env souboru
load_dotenv()

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Připojení k databázi pomocí proměnných z .env
DB_PARAMS = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': os.getenv('POSTGRES_PORT')
}

def get_db_connection():
    try:
        return psycopg2.connect(**DB_PARAMS)
    except psycopg2.OperationalError as e:
        print(f"❌ Chyba připojení k DB: {e}")
        return None

# Vytvoření databázové tabulky
def ensure_db_initialized():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id SERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE
                )
            ''')
            conn.commit()
            print("✅ Tabulka 'emails' byla úspěšně inicializována!")
        except Exception as e:
            print(f"❌ Chyba při inicializaci tabulky: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        print("❌ Nepodařilo se připojit k databázi pro inicializaci tabulky.")



ensure_db_initialized()

# Kontrola validního emailu
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email)

# Kontrola souhlasu
def has_consent(consent):
    return consent is not None

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ""
    message_color = ""
    if request.method == 'POST':
        email = request.form['email']
        consent = request.form.get('consent')
        if not has_consent(consent) and not is_valid_email(email):
            message = "Pro zapsání e-mailu do databáze <strong>zaškrtněte souhlas</strong> a <strong>zadejte email ve tvaru</strong>: 'example@example.smt'"
            message_color = "red"
        elif not has_consent(consent):
            message = "Pro zapsání e-mailu do databáze <strong>zaškrtněte souhlas</strong>."
            message_color = "red"
        elif not is_valid_email(email):
            message = "Zadejte prosím pouze <strong>e-mailovou adresu ve tvaru</strong>: 'example@example.smt'"
            message_color = "red"
        else:
            try:
                conn = psycopg2.connect(**DB_PARAMS)
                cursor = conn.cursor()
                cursor.execute('INSERT INTO emails (email) VALUES (%s)', (email,))
                conn.commit()
                cursor.close()
                conn.close()
                message = "Váš e-mail byl přidán do databáze."
                message_color = "green"
            except psycopg2.IntegrityError:
                conn.rollback()  # Resetuje transakci
                message = "Email již existuje!"
                message_color = "red"
            except psycopg2.Error as e:
                message = f"Database error: {e}"
                message_color = "red"

    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <title>Odolnost proti phishingu</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: url('{{ url_for('static', filename='web_api_image.webp') }}') no-repeat center center fixed;
                    background-size: cover;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.9);
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }
                input[type="text"] { font-size: 18px; width: 80%; max-width: 300px; }
                input[type="checkbox"] { margin-top: 15px; }
                input[type="submit"] {
                    padding: 10px 20px; margin-top: 15px; font-size: 16px;
                    background-color: #007bff; color: white; border: none; cursor: pointer;
                    border-radius: 4px;
                }
                input[type="submit"]:hover { background-color: #0056b3; }
                .message { margin-top: 15px; font-size: 16px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Odolnost proti phishingu</h1>
                <p>Zadáním e-mailové adresy se přihlašujete do testování na odolnost vůči phishingovým útokům.</p>
                <form method="post">
                    <input type="text" name="email" placeholder="Vložte svůj email">
                    <br>
                    <input type="checkbox" name="consent" id="consent">
                    <label for="consent">Souhlasím se zpracováním osobních údajů</label>
                    <br>
                    <input type="submit" value="Odeslat">
                </form>
                {% if message %}
                <p class="message" style="color: {{ message_color }};">{{ message|safe }}</p>
                {% endif %}
            </div>
        </body>
        </html>
    ''', message=message, message_color=message_color)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)