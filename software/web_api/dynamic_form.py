from flask import Flask, request, render_template_string
from dotenv import load_dotenv
import os
import re
from database import token_exists, get_user_id_by_token
from storage import initialize_form_data, append_user_submission, log_link_click

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

initialize_form_data()

def is_strong_password(password):
    if len(password) < 12:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def generate_form_html(action, token):
    if action == "a1z":
        return f'''
        <h2>Změna hesla</h2>
        <form method="POST">
            <input type="hidden" name="token" value="{token}">
            <input type="hidden" name="action" value="a1z">
            <input type="text" name="login" data-required="true" placeholder="Uživatelské jméno*"><br>
            <input type="password" name="old_password" data-required="true" placeholder="Staré heslo*"><br>
            <input type="password" name="new_password" data-required="true" placeholder="Nové heslo*"><br>
            <input type="submit" value="Odeslat">
        </form>
        '''
    elif action == 'b5p':
        return f'''
        <h2>Podpisový formulář</h2>
        <form method="POST">
            <input type="hidden" name="token" value="{token}">
            <input type="hidden" name="action" value="b5p">
            <input type="text" name="first_name" data-required="true" placeholder="Jméno (*)"><br>
            <input type="text" name="last_name" data-required="true" placeholder="Příjmení (*)"><br>
            <input type="text" name="position" data-required="true" placeholder="Pozice (*)"><br>
            <input type="text" name="department" data-required="true" placeholder="Oddělení (*)"><br>
            <input type="text" name="phone" data-required="true" placeholder="Telefon (*)"><br>
            <input type="url" name="linkedin" data-required="false" placeholder="LinkedIn (nepovinné)"><br>
            <input type="checkbox" name="consent" data-required="true"> Souhlasím se zpracováním údajů<br>
            <input type="submit" value="Odeslat">
        </form>
        '''
    elif action == 'c9d':
        return f'''
        <h2>Ověření zařízení</h2>
        <form method="POST">
            <input type="hidden" name="token" value="{token}">
            <input type="hidden" name="action" value="c9d">
            <input type="text" name="login" data-required="true" placeholder="Login (*)"><br>
            <input type="password" name="password" data-required="true" placeholder="Heslo (*)"><br>
            <input type="text" name="device_name" data-required="true" placeholder="Název zařízení (*)"><br>
            <input type="checkbox" name="approve_device" data-required="true"> Přidat mezi důvěryhodná zařízení<br>
            <input type="submit" value="Potvrdit">
        </form>
        '''
    else:
        return "<h2>Neplatná akce</h2>"

def get_title(action):
    return {
        'a1z': 'Změna hesla',
        'b5p': 'Podpisový formulář',
        'c9d': 'Ověření zařízení'
    }.get(action, 'Formulář')

@app.route('/form', methods=['GET', 'POST'])
def form():
    token = request.args.get('token') if request.method == 'GET' else request.form.get('token')
    action = request.args.get('action') if request.method == 'GET' else request.form.get('action')

    if not token or not action:
        return "Chybí token nebo akce.", 400

    if not token_exists(token):
        return "Token není platný.", 400

    user_id = get_user_id_by_token(token)
    if not user_id:
        return "Token nebyl přiřazen žádnému uživateli.", 400

    if request.method == 'GET':
        field_map = {
            "a1z": ["login", "old_password", "new_password"],
            "b5p": ["first_name", "last_name", "position", "department", "phone", "linkedin", "consent"],
            "c9d": ["login", "password", "device_name", "approve_device"]
        }
        if action in field_map:
            log_link_click(user_id, token, action, field_map[action])

    def get_bool(name): return bool(request.form.get(name, '').strip())
    message = ""
    message_color = "green"

    if request.method == 'POST':
        field_truth = {}

        if action == 'a1z':
            new_password = request.form.get("new_password", "")
            field_truth = {
                "login": get_bool("login"),
                "old_password": get_bool("old_password"),
                "new_password": bool(new_password)
            }
            required_fields = {k: v for k, v in field_truth.items()}  # všechno je povinné
            append_user_submission(user_id, token, action, field_truth)
            if not all(required_fields.values()):
                message_color = "red"
                message = "Změna hesla neproběhla – vyplňte všechna povinná pole (*)."
            elif new_password and not is_strong_password(new_password):
                message_color = "red"
                message = "Nové heslo musí mít alespoň 12 znaků, obsahovat velké písmeno, číslo a speciální znak."
            else:
                message_color = "green"
                message = "Heslo bylo úspěšně změněno."


        elif action == 'b5p':
            field_truth = {
                "first_name": get_bool("first_name"),
                "last_name": get_bool("last_name"),
                "position": get_bool("position"),
                "department": get_bool("department"),
                "phone": get_bool("phone"),
                "linkedin": get_bool("linkedin"),
                "consent": get_bool("consent")
            }
            required_fields = {k: v for k, v in field_truth.items() if k != "linkedin"}  # linkedin ignorujeme
            append_user_submission(user_id, token, action, field_truth)
            if not field_truth["consent"]:
                message_color = "red"
                message = "Pro pokračování je třeba potvrdit souhlas se zpracováním údajů."
            elif not all(required_fields.values()):
                message_color = "red"
                message = "Podpisové údaje nebyly kompletní – zkontrolujte vyplnění povinných polí (*)."
            else:
                message_color = "green"
                message = "Podpis byl aktualizován."


        elif action == 'c9d':
            field_truth = {
                "login": get_bool("login"),
                "password": get_bool("password"),
                "device_name": get_bool("device_name"),
                "approve_device": get_bool("approve_device")
            }
            required_fields = {k: v for k, v in field_truth.items() if k != "approve_device"}
            append_user_submission(user_id, token, action, field_truth)
            if not field_truth["approve_device"]:
                message_color = "red"
                message = "Pro pokračování je třeba potvrdit důvěryhodnost zařízení."
            elif not all(required_fields.values()):
                message_color = "red"
                message = "Zařízení nebylo potvrzeno – vyplňte všechna pole."
            else:
                message_color = "green"
                message = "Zařízení bylo přidáno mezi důvěryhodná."

        else:
            return "Neznámá akce.", 400

    form_html = generate_form_html(action, token)
    return render_template_string(f'''
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>{get_title(action)}</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
</head>
<body>
    <div class="header">IT Service Portal</div>
    <div class="container">
        {form_html}
        <p class="message" style="color: {message_color};">{message}</p>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', function () {{
        const form = document.querySelector('form');
        if (!form) return;

        form.addEventListener('submit', function (e) {{
            e.preventDefault();

            const data = new FormData(form);
            fetch('', {{
                method: 'POST',
                body: data
            }})
            .then(res => res.text())
            .then(html => {{
                document.documentElement.innerHTML = html;
            }})
            .catch(err => console.error('Chyba při odesílání formuláře:', err));
        }});
    }});
    </script>
</body>
</html>
''')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
