# PDS WhatsApp CRM

A lightweight, internal Customer Relationship Management (CRM) tool for Platinum Dental Surgery. This application allows you to manage contact lists, preview message templates, and send WhatsApp broadcast campaigns using the Meta Cloud API.

## 🚀 Features

* **Contact Management:** Create groups, import contacts via CSV, and manage lists.
* **Broadcast Dashboard:** Send approved template messages to thousands of contacts.
* **Live Preview:** "Phone-style" preview of messages before sending.
* **Real-time Analytics:** Track queued, sent, and failed messages instantly.
* **Smart Caching:** Fast loading times by caching Meta API templates.

## 🛠️ Prerequisites

* Python 3.9 or higher
* A Meta Developer Account (with WhatsApp API enabled)
* A verified Business Phone Number ID and WABA ID

## 📦 Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/reu12th/pds-crm.git)
    cd pds-crm
    ```

2.  **Create a Virtual Environment** (Recommended)
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

1.  Create a file named `.env` in the root directory.
2.  Add your Meta API credentials inside it:

    ```ini
    WHATSAPP_ACCESS_TOKEN=your_long_lived_access_token_here
    PHONE_NUMBER_ID=your_phone_number_id_here
    WABA_ID=your_whatsapp_business_account_id_here
    ```

    > **Security Note:** Never share your `.env` file or commit it to GitHub. It is already included in `.gitignore`.

## 🏃‍♂️ How to Run

Start the application using Uvicorn:

```bash
uvicorn app:app --reload
```

* The dashboard will be available at: `http://127.0.0.1:8000`
* The `--reload` flag allows the app to auto-restart if you make code changes.

## 📂 Project Structure

```text
pds-crm/
├── app.py              # Main backend logic (FastAPI)
├── database.db         # Local SQLite database (Auto-generated)
├── .env                # API Secrets (Hidden)
├── requirements.txt    # Python dependencies
├── .gitignore          # Git exclusion rules
├── templates/
│   └── index.html      # Frontend Dashboard
└── uploads/            # Temporary storage for CSV uploads
```

## 📝 CSV Format for Import

When uploading contacts, your CSV file should look like this:

```csv
name,phone
John Doe,2348012345678
Jane Smith,2348098765432
```

* **Headers:** `name` and `phone` (case-insensitive).
* **Phone Numbers:** Should preferably be in international format (e.g., 234...). The system will attempt to normalize them automatically.

## ⚠️ Disclaimer

This tool uses the official WhatsApp Business API. Ensure you comply with Meta's messaging policies and obtain user opt-ins before sending broadcasts to avoid number banning.

---