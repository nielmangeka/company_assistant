
# Conversational Company Assistant (Gradio + OpenAI + Redis)

A lightweight chat assistant that runs in your browser using **Gradio** and calls **OpenAI** to answer questions about your company. It also logs user interactions to **Redis** (via RedisJSON) so you can keep track of questions, emails, and notes.

> **At a glance**
> - Frontend: `gr.ChatInterface`
> - Brain: OpenAI Chat Completions
> - Storage: Redis (JSON), with helper utilities in `tools.py`
> - App entry point: `app.py`

---

## Features

- 🧠 **Company-aware responses** — The assistant is primed with your company profile & summary (see `tools.py`).
- 💾 **Conversation logging** — `record_user_details` captures `name`, `email`, `question`, `notes`, and a timestamp to Redis under keys like `user_details:{email}`.
- 🔧 **Tool calls** — The model can trigger Python “tools” (e.g., saving to Redis) via the function-calling pattern handled in `tools.py`.
- 🖥️ **Zero-setup UI** — Start a local web app with Gradio in one command.

---

## Project Structure

```
.
├── app.py          # Gradio ChatInterface entry; orchestrates the chat loop and tool calls
└── tools.py        # Redis connection/config + company profile + tool handlers (e.g., record_user_details)
```

> The code uses `dotenv`, so configuration is read from a `.env` file at runtime.

---

## Prerequisites

- **Python** 3.9+ (recommended)
- **Redis** with **RedisJSON** module enabled  
  The simplest way is using Redis Stack Docker image:
  ```bash
  docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest
  ```
  This exposes Redis on `localhost:6379` with JSON commands available.

- An **OpenAI API key**.

---

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>.git
   cd <your-repo>
   ```

2. **Create & activate a virtual environment**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -U pip
   pip install gradio python-dotenv redis openai
   ```

   > The code uses `redis-py`’s JSON interface (`client.json()`), which expects a Redis server with RedisJSON enabled (see Docker note above).

4. **Create a `.env` file** in the project root:
   ```env
   # Required
   OPENAI_API_KEY=your_openai_api_key

   # Redis connection (choose one style)
   # If you have a single URL:
   # REDIS_URL=redis://localhost:6379
   # Or specify parts:
   REDIS_HOST=localhost
   REDIS_PORT=6379
   # REDIS_PASSWORD=your_password_if_any

   # Optional knobs (if used by tools.py / your prompts)
   COMPANY_NAME=Your Company, Inc.
   ```

---

## Running the App

```bash
python app.py
```

Gradio will print a local URL (e.g., `http://127.0.0.1:7860`) — open it in your browser and start chatting. If `share=True` is enabled (as in `app.py`), Gradio will also provide a temporary public URL.

---

## How It Works (High Level)

1. **System prompt & tools**  
   `tools.py` constructs a **system prompt** from your company profile and defines **tool functions** (e.g., `record_user_details`) that the model may call.

2. **Chat loop** (`app.py`)  
   The `chat(message, history)` function sends messages to OpenAI.  
   - If the model triggers **tool calls**, `companyProfile().handle_tool_call(...)` is invoked to execute the matching Python function and return tool results.
   - The final assistant message is returned to Gradio for display.

3. **Logging to Redis**  
   When the tool `record_user_details` is called, it writes JSON to Redis using keys like:
   ```text
   user_details:{email}
   ```
   Example stored document (shape may vary based on your code):
   ```json
   {
     "name": "Alice",
     "email": "alice@example.com",
     "question": "Do you offer enterprise plans?",
     "notes": "Follow up by email",
     "timestamp": "2025-08-24 14:05:10"
   }
   ```

---

## Common Tasks

### Test your Redis connection
Using the same environment variables as your app, quickly test connectivity with Python:
```python
import os, redis
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD") or None,
    decode_responses=True
)
print("PING ->", r.ping())
```

### Inspect stored user details
```python
import redis, os
r = redis.Redis(host=os.getenv("REDIS_HOST","localhost"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
print(r.json().get("user_details:alice@example.com"))
```

> If `r.json()` raises an error, ensure your Redis server is **Redis Stack** (has RedisJSON).

### Reset conversation state (optional pattern)
If you keep any per-user state in Redis, you can clear it like:
```python
r.delete(f"conversation:{user_id}")
```

---

## Deployment Notes

- **Production**: Put Gradio behind a reverse proxy (Nginx) and run via a process manager (e.g., `uvicorn`, `gunicorn` for FastAPI variants). For the simple script here, a `tmux`/`screen` session can suffice.
- **Security**: Never commit your `.env`. Consider separate API keys & Redis instances for dev/prod.
- **Scaling**: Because RedisJSON is used, use the `redis/redis-stack` image in all environments to keep command parity.

---

## Troubleshooting

- **`AttributeError: 'Redis' object has no attribute 'json'`**  
  You’re connecting to a Redis server **without RedisJSON**. Run Redis Stack as shown above.

- **Gradio keeps loading**  
  Ensure your OpenAI key is valid; check network; watch your terminal logs for errors.

- **OpenAI quota / auth errors**  
  Verify `OPENAI_API_KEY` and project/organization settings.

- **Cannot connect to Redis**  
  Check `REDIS_HOST`, `REDIS_PORT`, firewall rules, and that the container is running.

---

## Contributing

Feel free to expand the tools, add retry logic, or wire in more metadata (e.g., source URLs, conversation IDs). PRs welcome!

---

## License

MIT (or your preferred license). Add a `LICENSE` file to the repository.
