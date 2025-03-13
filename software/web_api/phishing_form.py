from flask import Flask, request, render_template_string
from dotenv import load_dotenv
from database import upsert_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os

load_dotenv()

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")
serializer = URLSafeTimedSerializer(app.secret_key)

def get_email_from_token(token):
    try:
        return serializer.loads(token, salt="email-confirmation-salt", max_age=8000000)
    except (SignatureExpired, BadSignature):
        return None

# Jediná HTML šablona s placeholdery pro token a případnou chybovou zprávu
base_form = '''
<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>Formulář</title>
  <style>
    body { 
      font-family: Arial, sans-serif; 
      background: url('{{ url_for("static", filename="phishing_form_image.jpg") }}') no-repeat center center fixed;
      background-size: cover;
      margin: 0;
      padding: 0;
    }

    .container {
      width: 450px;
      margin: 50px auto;
      background: rgba(255, 255, 255, 0.8);
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
      text-align: center;
      box-sizing: border-box;
    }

    input:not([type="checkbox"]), textarea {
      display: block;
      width: 100%;
      margin: 10px 0;
      padding: 8px;
      font-size: 16px;
      box-sizing: border-box;
    }

    textarea {
      resize: none;     
    }

    .checkbox-line {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      margin: 10px 0;
      white-space: nowrap;
    }

    input[type="submit"] {
      width: auto;
      padding: 10px 20px;
      margin: 0 auto;
      display: block;
      cursor: pointer;
    }

    .message {
      margin-top: 10px;
      font-size: 16px;
      color: red; /* nebo jiná barva */
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>Formulář</h2>
    {% if message %}
      <p class="message">{{ message|safe }}</p>
    {% endif %}
    <form method="post">
      <input type="hidden" name="token" value="{{ token }}">
      <label for="first_name">Jméno:</label>
      <input type="text" name="first_name" placeholder="Vaše jméno">

      <label for="last_name">Příjmení:</label>
      <input type="text" name="last_name" placeholder="Vaše příjmení">

      <label for="email_address">E-mailová adresa:</label>
      <input type="email" name="email_address" placeholder="Váš e-mail">

      <label for="street_address">Ulice a č.p.:</label>
      <input type="text" name="street_address" placeholder="Ulice a č.p.">

      <label for="city_address">Město:</label>
      <input type="text" name="city_address" placeholder="Město">

      <label for="telephone">Telefon:</label>
      <input type="text" name="telephone" placeholder="Telefonní číslo">

      <label for="notes">Poznámky:</label>
      <textarea name="notes" rows="4" placeholder="Další informace..."></textarea>

      <div class="checkbox-line">
        <input type="checkbox" name="consent" id="consent" required>
        <label for="consent">Souhlasím se zpracováním osobních údajů</label>
      </div>

      <input type="submit" value="Odeslat">
    </form>
  </div>
</body>
</html>

'''

@app.route('/form', methods=['GET', 'POST'])
def form():
    message = ""
    message_color = ""
    if request.method == 'GET':
        token = request.args.get('token')
        if not token:
            return "Chybí token.", 400
        email = get_email_from_token(token)
        if not email:
            return "Token je neplatný nebo vypršel.", 400
        return render_template_string(base_form, token=token, message=message, message_color=message_color)
    
    elif request.method == 'POST':
        token = request.form.get('token')
        if not token:
            return "Chybí token.", 400
        email = get_email_from_token(token)
        if not email:
            return "Token je neplatný nebo vypršel.", 400

        # Ověření, zda byl checkbox se souhlasem zaškrtnut
        consent = request.form.get('consent')
        if not consent:
            message = "Musíte souhlasit se zpracováním osobních údajů."
            message_color = "red"
            return render_template_string(base_form, token=token, message=message, message_color=message_color), 400

        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email_address = request.form.get('email_address', '').strip()
        street_address = request.form.get('street_address', '').strip()
        city_address = request.form.get('city_address', '').strip()
        telephone = request.form.get('telephone', '').strip()
        notes = request.form.get('notes', '').strip()

        first_name_filled = bool(first_name)
        last_name_filled = bool(last_name)
        street_address_filled = bool(street_address)
        city_address_filled = bool(city_address)
        telephone_filled = bool(telephone)

        upsert_user(
            email,
            form_submitted=True,
            first_name=first_name_filled,
            last_name=last_name_filled,
            email_address=email_address,
            street_address=street_address_filled,
            city_address=city_address_filled,
            telephone=telephone_filled,
            notes=notes
        )
        return "Děkujeme, vaše informace byly úspěšně uloženy!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
