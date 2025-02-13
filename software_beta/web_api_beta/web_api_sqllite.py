from flask import Flask, request, render_template_string
import re
import os
import json
import os
import sqlite3
import psycopg2

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Vytvoření databáze a tabulky při startu aplikace
def ensure_db_initialized():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'emails.db')
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Exception occurred: {e}")

ensure_db_initialized()

# Kontrola, zda je text validním emailem
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email)

# Kontrola, zda byl udělen souhlas
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
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'emails.db')
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO emails (email) VALUES (?)', (email,))
                    conn.commit()
                message = "Váš e-mail byl přidán do databáze."
                message_color = "green"
            except sqlite3.IntegrityError:
                message = "Email již existuje!"
                message_color = "red"
            except sqlite3.Error as e:
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
                    background-attachment: fixed;
                    background-size: cover;
                    background-position: center;
                    background-color: #f0f0f0; /* Fallback color if image cannot be loaded */
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.9);
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }
                h1 {
                    color: #333;
                }
                p {
                    color: #666;
                    font-size: 14px;
                }
                input[type="text"] {
                    font-size: 18px;
                    width: 80%;
                    max-width: 300px;
                }
                input[type="checkbox"] {
                    margin-top: 15px;
                }
                input[type="submit"] {
                    padding: 10px 20px;
                    margin-top: 15px;
                    font-size: 16px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    cursor: pointer;
                    border-radius: 4px;
                }
                input[type="submit"]:hover {
                    background-color: #0056b3;
                }
                .message {
                    margin-top: 15px;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="font-size: 30px; margin-top: 20px;">Odolnost proti phishingu</h1>
                <p style="font-size: 20px;">Zadáním e-mailové adresy se přihlašujete do testování na odolnost vůči phishingovým útokům.</p>
                <form method="post">
                    <input type="text" name="email" placeholder="Vložte svůj email" style="font-size: 18px;">
                    <br>
                    <input type="checkbox" name="consent" id="consent" style="vertical-align: baseline; margin-right: 5px;">
                    <label for="consent" style="font-size: 15px;">Souhlasím se zpracováním osobních údajů, které budou využity pouze pro účely tohoto testování</label>
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
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode)
