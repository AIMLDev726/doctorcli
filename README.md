# doctorcli

> Your AI Medical Specialist in the Terminal

[![PyPI version](https://img.shields.io/pypi/v/doctorcli.svg)](https://pypi.org/project/doctorcli/)

---

## What is doctorcli?

**doctorcli** is a user-friendly command-line tool that brings specialist-level medical AI directly to your terminal. It lets you chat with AI doctors from different specialties (like general medicine, cardiology, dermatology, pediatrics, and more), keep your conversations organized, and even use live research tools—all in a privacy-respecting, session-based workflow.

---

## Why use doctorcli?

- **Specialist AI agents**: Choose the right expert for your needs.
- **Easy session management**: Start, resume, and organize your health conversations.
- **Multiple AI providers**: Use OpenAI, Gemini, Claude, Groq, Ollama, LM Studio, and more.
- **Attach research tools**: Add Wikipedia or Tavily for live lookups.
- **No cloud lock-in**: Use local or cloud models.
- **Your data, your control**: All chats and settings are stored locally.

---

## How was it built?

doctorcli is built in Python and designed for reliability, privacy, and extensibility. It uses a modular architecture with support for multiple AI providers and research tools, and a rich terminal interface for a smooth user experience.

---

## How do I install it?

Install from PyPI (recommended):

```bash
pip install doctorcli
```

Or install from source:

```bash
pip install .
```

---

## How do I use it?

1. **Start the app:**
   ```bash
   doctorcli
   ```
2. **Configure providers (first run):**
   - Go to `Settings` to add your API keys for OpenAI, Gemini, etc., or use local models like Ollama.
   - Optionally, add a Tavily API key for live web search.
3. **Pick your specialist:**
   - Choose from general medicine, dermatology, pediatrics, and more.
4. **Start a session:**
   - Begin a new conversation or resume an old one. Sessions remember your chat history and context.
5. **Ask your questions:**
   - Get structured, specialist-level answers. Attach tools for live research if needed.
6. **Use in-session commands:**
   - `/memory` — See what the AI remembers.
   - `/session` — View session details.
   - `/settings` — Change providers or tools.
   - `/exit` — Leave the session.

---

## Example: Quick Start

```bash
pip install doctorcli

doctorcli
```

- Choose your specialist (e.g., General Medicine)
- Start chatting!

---

## Supported Providers & Tools

- **Cloud AI:** OpenAI, Gemini, Claude, Groq
- **Local AI:** Ollama, LM Studio
- **Tools:**
  - Wikipedia (no API key needed)
  - Tavily (API key required for live web search)

---

## Where is my data stored?

All your settings, sessions, and chat history are stored locally in your system's app data folder. Nothing is sent to any server except the AI/model providers you choose.

---

## Thank You!

Thank you for using doctorcli! We hope it helps you get reliable, specialist-level answers and organize your health questions with confidence.

---

## Want to contribute?

We welcome contributions, bug reports, and feature requests!

- [GitHub Repository](https://github.com/AIMLDev726/doctorcli)
- [Open an Issue](https://github.com/AIMLDev726/doctorcli/issues)

---

## License

MIT
