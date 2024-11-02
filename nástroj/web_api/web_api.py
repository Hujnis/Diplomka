from flask import Flask, request, render_template_string
import re
import os
import sqlite3

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Vytvoření databáze a tabulky při startu aplikace
def ensure_db_initialized():
    conn = sqlite3.connect(r'C:/Users/thujn/Diplomka/nástroj/web_api/emails.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

ensure_db_initialized()



# Kontrola, zda je text validním emailem
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ""
    message_color = ""
    if request.method == 'POST':
        email = request.form['email']
        consent = request.form.get('consent')
        if not consent and not is_valid_email(email):
            message = "Pro zapsání e-mailu do databáze zaškrtněte souhlas a zadejte email ve tvaru 'example@example.smt'"
            message_color = "red"
        elif not consent:
            message = "Pro zapsání e-mailu do databáze zaškrtněte souhlas."
            message_color = "red"
        elif not is_valid_email(email):
            message = "Zadejte prosím pouze e-mailovou adresu ve tvaru: 'example@example.smt'"
            message_color = "red"
        else:
            try:
                conn = sqlite3.connect(r'C:/Users/thujn/Diplomka/nástroj/web_api/emails.db')
                cursor = conn.cursor()
                cursor.execute('INSERT INTO emails (email) VALUES (?)', (email,))
                conn.commit()
                conn.close()
                message = "Váš e-mail byl přidán do databáze."
                message_color = "green"
            except sqlite3.IntegrityError:
                message = "Email již existuje!"
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
                    background-size: cover;
                    background-position: center;
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
                <p class="message" style="color: {{ message_color }};">{{ message }}</p>
                {% endif %}
            </div>
        </body>
        </html>
    ''', message=message, message_color=message_color)

if __name__ == '__main__':
    app.run(debug=True)
