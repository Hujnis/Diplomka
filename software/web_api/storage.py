import os
import json
from datetime import datetime, timedelta, timezone
from database import get_db_connection

JSON_DB_PATH = 'form_data.json'

def load_json_data():
    if os.path.exists(JSON_DB_PATH):
        with open(JSON_DB_PATH, 'r') as f:
            return json.load(f)
    return {"users": {}}

def save_json_data(data):
    with open(JSON_DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def initialize_form_data():
    """Načte ID všech uživatelů z databáze a vytvoří prázdnou strukturu v JSON (pokud neexistuje)."""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM user_data")
            user_ids = [str(row[0]) for row in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Chyba při načítání uživatelů: {e}")
            user_ids = []
    else:
        user_ids = []

    data = load_json_data()
    if "users" not in data:
        data["users"] = {}

    for user_id in user_ids:
        if user_id not in data["users"]:
            data["users"][user_id] = []

    save_json_data(data)

def log_link_click(user_id, token, action, fields):
    """Zaznamená kliknutí na odkaz, nastaví všechna pole na False."""
    data = load_json_data()
    user_id = str(user_id)

    if "users" not in data:
        data["users"] = {}
    if user_id not in data["users"]:
        data["users"][user_id] = []

    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    record = {
        "timestamp": now,
        "token": token,
        "action": action,
        "link_click": True,
        "submitted": False,
        "data": {field: False for field in fields}
    }

    data["users"][user_id].append(record)
    save_json_data(data)

def append_user_submission(user_id, token, action, field_truth_dict):
    """Přepíše recentní link_click záznam, nebo vytvoří nový záznam jako submitted."""
    data = load_json_data()
    user_id = str(user_id)

    if "users" not in data:
        data["users"] = {}
    if user_id not in data["users"]:
        data["users"][user_id] = []

    now = datetime.now(timezone.utc)
    updated = False

    # Vždycky vezmeme pouze required fields
    required_fields = {k: v for k, v in field_truth_dict.items() if k != "linkedin"}
    validation_failed = not all(required_fields.values())

    for record in reversed(data["users"][user_id]):
        if (
            record.get("token") == token and
            record.get("action") == action and
            not record.get("submitted", False)
        ):
            try:
                ts = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                if abs(now - ts) <= timedelta(minutes=10):
                    new_record = {
                        "timestamp": record["timestamp"],
                        "token": token,
                        "action": action,
                        "submitted": True,
                        "validation_failed": validation_failed,
                        "data": field_truth_dict
                    }
                    index = data["users"][user_id].index(record)
                    data["users"][user_id][index] = new_record
                    updated = True
                    break
            except Exception as e:
                print(f"Chyba při parsování timestampu: {e}")

    if not updated:
        new_record = {
            "timestamp": now.isoformat().replace('+00:00', 'Z'),
            "token": token,
            "action": action,
            "submitted": True,
            "validation_failed": validation_failed,
            "data": field_truth_dict
        }
        data["users"][user_id].append(new_record)

    save_json_data(data)
