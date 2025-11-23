

```markdown
# 🛠️ MyBlog: Comprehensive Setup & Configuration Guide

This guide provides detailed instructions on how to set up the **MyBlog** development environment on your local machine. Because this project uses **Asynchronous Architecture** (WebSockets, AI Background Tasks), the setup requires a few more steps than a standard Django website.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
    *   *Verify:* `python --version`
2.  **Git**: [Download Here](https://git-scm.com/)
    *   *Verify:* `git --version`
3.  **Redis Server**:
    *   **Windows:** [Download Memurai](https://www.memurai.com/) (Developer Edition is free) OR enable WSL2 and install Redis.
    *   **Mac/Linux:** `brew install redis` or `sudo apt-get install redis-server`.
    *   *Verify:* Open a terminal and type `redis-cli ping`. It should return `PONG`.

---

## 📥 Step 1: Clone and Environment Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Muhammedaslamkerala/myblog.git
    cd myblog-project
    ```

2.  **Create a Virtual Environment**
    It is crucial to isolate dependencies.
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Dependencies**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

---

## 🔑 Step 2: External Services Configuration

To make the AI and Email features work, you need to configure external API keys.

### 🤖 1. Groq AI API (Free)
1.  Go to [Groq Cloud Console](https://console.groq.com/).
2.  Sign up/Login.
3.  Go to **API Keys** -> **Create API Key**.
4.  Copy the key (it starts with `gsk_...`).

### 📧 2. Gmail SMTP (For OTPs)
You cannot use your normal login password. You must use an **App Password**.
1.  Go to your [Google Account Security Settings](https://myaccount.google.com/security).
2.  Enable **2-Step Verification** (if not already enabled).
3.  Search for **"App Passwords"** in the search bar.
4.  Create a new app name (e.g., "MyBlog Local").
5.  Copy the **16-character code** generated (remove spaces).

---

## ⚙️ Step 3: Environment Variables (.env)

Create a file named `.env` in the root directory (next to `manage.py`).
**Copy and paste the following configuration:**

```ini
# --- Core Settings ---
SECRET_KEY=django-insecure-change-me-for-prod
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# --- Database (Leave empty to use SQLite default) ---
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# --- AI Configuration ---
# Paste your Groq Key here (No quotes!)
GROQ_API_KEY=gsk_your_key_here

# --- Email Configuration (Gmail) ---
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
# Your real Gmail address
EMAIL_HOST_USER=your_email@gmail.com
# Your 16-char App Password (No spaces, No quotes)
EMAIL_HOST_PASSWORD=abcdefghijklmnop
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

---

## 🗄️ Step 4: Database Initialization

1.  **Apply Migrations** creates the database tables.
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

2.  **Create an Admin User** to access the dashboard.
    ```bash
    python manage.py createsuperuser
    ```
    *Follow the prompts to set a username and password.*

---

## 🚀 Step 5: Running the Application (The 3-Terminal Rule)

Because of the background tasks and WebSockets, you need **3 separate terminals** running simultaneously.

### Terminal 1: Redis Server
This powers the communication layer.
```bash
redis-server
```

### Terminal 2: Celery Worker
This handles the AI processing and Email sending in the background.
*   **Windows Users:** Must use `--pool=solo`.
*   **Mac/Linux Users:** Do not use `--pool=solo`.

```bash
# WINDOWS COMMAND:
celery -A main worker -l info --pool=solo

# MAC/LINUX COMMAND:
celery -A main worker -l info
```

### Terminal 3: The Web Server (Daphne)
This starts the website.
```bash
# Make sure your virtual environment is active!
daphne -b 0.0.0.0 -p 8000 main.asgi:application
```

**🎉 Success!** Open your browser to `http://127.0.0.1:8000/`.

---

## ❓ Troubleshooting Common Issues

### 1. `[Errno -2] Name or service not known` (Email Error)
*   **Cause:** Typo in `.env` or internet issue.
*   **Fix:** Ensure `EMAIL_HOST=smtp.gmail.com` (No quotes, no spaces). Check your internet connection.

### 2. `SMTPAuthenticationError: 535 ... Username and Password not accepted`
*   **Cause:** You used your standard Gmail password.
*   **Fix:** Generate a Google **App Password** (See Step 2).

### 3. Celery freezes or doesn't process tasks (Windows)
*   **Cause:** Celery 4+ has issues with Windows concurrency.
*   **Fix:** Ensure you add `--pool=solo` to the worker command.

### 4. WebSocket Disconnects / Chat not working
*   **Cause:** Redis is not running.
*   **Fix:** Check Terminal 1. If Redis is not running, WebSockets (Daphne) cannot talk to the application.

### 5. `ModuleNotFoundError`
*   **Cause:** You forgot to install requirements or activate the virtual environment.
*   **Fix:** Run `pip install -r requirements.txt` again.
```