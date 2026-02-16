# 🤖 DTwinBot – Conversational Digital Twin Builder

**DTwinBot** is an AI-powered assistant that lets you create and manage **Asset Administration Shells (AAS)** through natural conversation — no coding required.

Inspired by Open Claw’s vision of democratizing bots, DTwinBot makes Digital Twin creation accessible to everyone.

---

## 🚀 How It Works

Just chat with the bot:

- **"Create an AAS for my temperature sensor"** → ✅ Instantly generated  
- **"Add operating temperature 72.5°C"** → ✅ Property added  
- **"Link it to IEC 60034-1 standard"** → ✅ Semantic reference created  
- **"Show me the structure"** → 🌳 Interactive tree view  
- **"Export it"** → 📥 Download standards-compliant JSON  

No complex tooling. No manual schema writing. Just conversation.

---

## 🌍 Why It Matters

- **Accessibility** – Anyone can build Digital Twins, not just developers  
- **Speed** – Create AAS models in minutes  
- **Learning by Doing** – The best way to understand AAS is to build one interactively  
- **Standards-Compliant** – Fully aligned with Industry 4.0 specifications  

---

## 🛠 Features

- Create complete Asset Administration Shells  
- Add Submodels and Properties dynamically  
- Link properties to industry standards (e.g., IEC)  
- Generate semantic Concept Descriptions  
- Visualize the AAS structure in a tree view  
- Export standards-compliant JSON files  
- Interactive learning experience for AAS  

---

## ⚠️ A Reality Check

AAS is powerful for standardized asset information and interoperability — but it is **not**:

- A replacement for specialized databases  
- A simulation engine  
- A one-size-fits-all digital platform  

It provides a **common language for Digital Twins**.  
DTwinBot makes creating that language as easy as having a conversation.

---

## 💬 Try It Now

Telegram Bot: **[@dtwin_aas_bot](https://t.me/dtwin_aas_bot)**  

Build Digital Twins. Learn by doing.

---

## 🐳 Run with Docker

You can run DTwinBot using the published Docker image `industryapps/dtwinbot:latest`.

1. **Create a `.env` file** (or use the provided `.env-example`) with:

```bash
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

2. **Run with `docker run`:**

```bash
docker run -d \
  --name dtwinbot \
  --env-file .env \
  industryapps/dtwinbot:latest
```

The bot will start and connect to Telegram using the credentials from your `.env` file.

---

## 📦 Docker Compose

You can also manage the bot with Docker Compose. Example `docker-compose.yml`:

```yaml
version: "3.9"
services:
  dtwinbot:
    image: industryapps/dtwinbot:latest
    env_file:
      - .env
    restart: unless-stopped
```

Then start it with:

```bash
docker compose up -d
```

---

## ❤️ Built With

- **[Eclipse BaSyx Python SDK](https://github.com/eclipse-basyx/basyx-python-sdk)** – for Asset Administration Shell management  
- **[OpenAI GPT-4](https://platform.openai.com/docs/models/gpt-4)** – for conversational AI and natural language processing

---