```markdown
# 🤝 Contributing to MyBlog

First off, thank you for considering contributing to **MyBlog**! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

Whether you're fixing a bug, improving the AI documentation, or adding a cool new real-time feature, we welcome your involvement.

## 📋 Table of Contents
- [Getting Started](#-getting-started)
- [How to Contribute](#-how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Pull Request Process](#pull-request-process)
- [Development Guidelines](#-development-guidelines)
  - [Coding Standards](#coding-standards)
  - [AI & RAG Specifics](#ai--rag-specifics)
  - [Real-Time & Async](#real-time--async)
- [Testing](#-testing)

---

## 🚀 Getting Started

Before you start writing code, please ensure you have the project set up locally.

1.  **Fork** the repository on GitHub.
2.  **Clone** your fork locally:
    ```bash
    git clone https://github.com/Muhammedaslamkerala/myblog.git
    cd myblog
    ```
3.  **Set up the environment** (See `README.md` for full details):
    *   Create a virtual environment (`python -m venv venv`).
    *   Install dependencies (`pip install -r requirements.txt`).
    *   **Crucial:** Ensure **Redis** is running (`redis-server`).
    *   Create your `.env` file with a valid **Groq API Key**.

---

## 🛠 How to Contribute

### Reporting Bugs
Bugs are tracked as GitHub Issues. When filing an issue, please include:
*   **Title:** Clear and concise.
*   **Description:** Steps to reproduce the behavior.
*   **Environment:** (e.g., Windows 10, Python 3.11, Browser: Chrome).
*   **Logs:** Relevant error logs from the terminal (Django, Celery, or Daphne logs).

### Suggesting Enhancements
Have an idea for a new AI feature or a better UI?
*   Open a **Feature Request** issue.
*   Explain *why* this enhancement would be useful.
*   If possible, provide mockups or code snippets.

### Pull Request Process
1.  **Create a Branch:** Create a new branch for your feature or fix.
    *   `git checkout -b feature/amazing-feature`
    *   `git checkout -b fix/login-bug`
2.  **Commit Changes:** Make your changes. Keep commits small and descriptive.
    *   ✅ `git commit -m "Add nested comment logic"`
    *   ❌ `git commit -m "fixed stuff"`
3.  **Push:** Push to your fork.
4.  **Open a PR:** Go to the original repository and open a Pull Request.
    *   Link the PR to any relevant issues (e.g., "Closes #42").
    *   Provide a screenshot if the change affects the UI.

---

## 💻 Development Guidelines

### Coding Standards
*   **Python:** Follow **PEP 8** style guidelines.
*   **Imports:** Sort imports using `isort` or group them logically (Standard Lib -> Third Party -> Local Apps).
*   **Comments:** Comment complex logic, especially in the AI generation and WebSocket consumers.

### AI & RAG Specifics
Since this project uses **Retrieval-Augmented Generation**, please follow these rules when touching `ai_utils.py` or the `blog/` app:
1.  **Do NOT commit API Keys.** Always use `os.environ.get('GROQ_API_KEY')`.
2.  **Vector Dimensions:** If you change the embedding model (currently `all-MiniLM-L6-v2`), you must update the database schema as the vector dimension size might change.
3.  **Cost Awareness:** When writing tests for AI features, try to mock the API calls to avoid using up Groq API credits.

### Real-Time & Async
This project uses **Daphne** and **Django Channels**.
*   **Sync vs Async:** Be careful when mixing synchronous Django ORM calls inside asynchronous WebSocket consumers. Use `database_sync_to_async` wrappers where necessary.
*   **Channel Layers:** Ensure all group names (e.g., `chat_post_{id}`) are consistent across `consumers.py` and `signals.py`.

---

## 🧪 Testing

Before submitting a PR, please run the tests to ensure nothing is broken.

```bash
# Run standard Django tests
python manage.py test

# (Optional) Verify that the project starts under ASGI
daphne -p 8001 main.asgi:application
```

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License defined in the `LICENSE` file.

**Happy Coding!** 🤖✨
```