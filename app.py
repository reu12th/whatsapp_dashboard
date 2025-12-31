from fastapi import FastAPI, UploadFile, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import requests, pandas as pd, time, sqlite3, os, json, re
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WABA_ID = os.getenv("WABA_ID")

if not all([ACCESS_TOKEN, PHONE_NUMBER_ID, WABA_ID]):
    raise RuntimeError("Missing required environment variables")

GRAPH_VERSION = "v24.0"
API_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# ================= TEMPLATE IMAGES =================
TEMPLATE_IMAGES = {
    "subsidized_dental_care": "https://tinyurl.com/pdsflyer",
    "subsidized_dental_care2": "https://tinyurl.com/pdsflyer",
    "default": "https://tinyurl.com/pdsflyer"
}

# ================= CACHE STORAGE =================
# Stores data in memory so we don't ask Facebook every second
CACHE_TEMPLATES = []
CACHE_TIMESTAMP = 0

# ================= GLOBAL STATUS =================
current_status = {
    "is_sending": False,
    "total": 0,
    "sent": 0,
    "group_name": ""
}

app = FastAPI()
templates = Jinja2Templates(directory="templates")
os.makedirs("uploads", exist_ok=True)

# ================= DB INIT =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    status TEXT,
    group_id INTEGER
)
""")
cursor.execute("INSERT OR IGNORE INTO groups (id, name) VALUES (0, 'Uncategorized')")
conn.commit()

# ================= HELPERS =================
def normalize(phone):
    p = str(phone).replace("+", "").replace(" ", "").replace("-", "").strip()
    if p.startswith("0") and len(p) == 11:
        p = "234" + p[1:]
    if p.startswith("234") and len(p) == 13:
        return p
    return None


def check_api_health():
    """Correct health check: PHONE NUMBER endpoint"""
    try:
        r = requests.get(
            f"{API_URL}/{PHONE_NUMBER_ID}",
            headers=HEADERS,
            params={"fields": "display_phone_number,verified_name"},
            timeout=5
        )
        return r.status_code == 200
    except:
        return False


def get_templates():
    global CACHE_TEMPLATES, CACHE_TIMESTAMP
    
    # If we fetched data less than 5 minutes ago, use the saved copy (Instant!)
    if CACHE_TEMPLATES and (time.time() - CACHE_TIMESTAMP < 300):
        return CACHE_TEMPLATES

    try:
        r = requests.get(
            f"{API_URL}/{WABA_ID}/message_templates",
            headers=HEADERS,
            params={"limit": 100},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            # Update the cache
            CACHE_TEMPLATES = data
            CACHE_TIMESTAMP = time.time()
            return data
    except:
        pass
    
    return CACHE_TEMPLATES or [] # Return old cache if API fails


def analyze_template(template):
    info = {"language": template["language"], "header": None, "body_params": 0, "button_params": []}
    for comp in template["components"]:
        if comp["type"] == "HEADER":
            info["header"] = comp.get("format")
        if comp["type"] == "BODY":
            info["body_params"] = len(set(re.findall(r"\{\{[0-9]+\}\}", comp.get("text", ""))))
        if comp["type"] == "BUTTONS":
            for i, btn in enumerate(comp.get("buttons", [])):
                if btn["type"] == "URL" and "{{" in btn.get("url", ""):
                    info["button_params"].append(i)
    return info


def build_payload(phone, name, template):
    analysis = analyze_template(template)
    components = []

    if analysis["header"] == "IMAGE":
        components.append({
            "type": "header",
            "parameters": [{
                "type": "image",
                "image": {"link": TEMPLATE_IMAGES.get(template["name"], TEMPLATE_IMAGES["default"])}
            }]
        })

    if analysis["body_params"] > 0:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": name or "Patient"} for _ in range(analysis["body_params"])]
        })

    for idx in analysis["button_params"]:
        components.append({
            "type": "button",
            "sub_type": "url",
            "index": str(idx),
            "parameters": [{"type": "text", "text": phone}]
        })

    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template["name"],
            "language": {"code": analysis["language"]},
            "components": components
        }
    }


def send_template(phone, name, template):
    try:
        r = requests.post(
            f"{API_URL}/{PHONE_NUMBER_ID}/messages",
            headers=HEADERS,
            json=build_payload(phone, name, template)
        )
        return r.status_code
    except:
        return 500

# ================= BACKGROUND TASK =================
def process_broadcast_task(template_name, group_id, contact_rows):
    global current_status

    current_status.update({
        "is_sending": True,
        "total": len(contact_rows),
        "sent": 0
    })

    templates = get_templates()
    selected = next((t for t in templates if t["name"] == template_name), None)
    if not selected:
        current_status["is_sending"] = False
        return

    db = sqlite3.connect("database.db")
    cur = db.cursor()

    for cid, name, phone in contact_rows:
        code = send_template(phone, name, selected)
        status = "sent" if code in (200, 201) else "failed"
        cur.execute("UPDATE contacts SET status=? WHERE id=?", (status, cid))
        db.commit()
        current_status["sent"] += 1
        time.sleep(2.5)

    db.close()
    current_status["is_sending"] = False

# ================= ROUTES =================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    cursor.execute("""
        SELECT c.id, c.name, c.phone, c.status, g.name 
        FROM contacts c 
        LEFT JOIN groups g ON c.group_id = g.id 
        ORDER BY c.id DESC
    """)
    contacts = cursor.fetchall()
    
    cursor.execute("""
        SELECT g.id, g.name, COUNT(c.id) 
        FROM groups g 
        LEFT JOIN contacts c ON g.id = c.group_id 
        GROUP BY g.id
    """)
    groups = cursor.fetchall()
    
    # FETCH TEMPLATES ONCE (Fast because of cache)
    current_templates = get_templates()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "contacts": contacts,
            "groups": groups,
            "templates": current_templates,           # Reuse variable
            "templates_json": json.dumps(current_templates), # Reuse variable (No extra API call)
            "images_json": json.dumps(TEMPLATE_IMAGES),
            "api_online": check_api_health()
        }
    )

@app.get("/broadcast_status")
def broadcast_status():
    return current_status
