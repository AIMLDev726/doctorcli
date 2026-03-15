# doctorcli

[GitHub Repository](https://github.com/AIMLDev726/doctorcli)

`doctorcli` is a specialist-first medical AI CLI for structured health conversations, persistent sessions, multi-provider model access, and optional live research tools inside a terminal-first workflow.

## What it does

`doctorcli` is designed for users who want a focused medical AI shell instead of a generic chatbot. You choose a specialist persona, create or reopen sessions, select your preferred model provider, optionally attach tools, and continue conversations with session memory preserved across runs.

## Features

- Specialist medical agents for different domains such as general medicine, cardiology, dermatology, pediatrics, orthopedics, and more
- Rich terminal interface with markdown rendering and streamed model responses
- Persistent sessions with saved transcript, metadata, and memory per conversation
- Provider setup and live model discovery from supported APIs
- Optional tool attachment per session
- Visible tool-call output in chat, including returned sources when tools are used
- Session resume, session deletion, and provider/model reuse for existing conversations
- Support for cloud and local model providers

## Supported providers

Cloud providers:

- OpenAI
- Gemini
- Groq
- Claude

Local providers:

- Ollama
- LM Studio

## Supported tools

- Wikipedia
  - Good for reference lookups on conditions, medications, symptoms, and background concepts
  - No API key required
- Tavily
  - Good for live web search and current-information lookups
  - Requires a Tavily API key

If the selected model supports tool calling and the session has tools attached, the model can decide dynamically when to use them.

## Installation

Install from PyPI:

```bash
pip install doctorcli
```

Install from source:

```bash
pip install .
```

Install for development:

```bash
pip install -e ".[dev]"
```

## Quick start

Run the CLI:

```bash
doctorcli
```

Typical session flow:

1. Open `doctorcli`.
2. Go to `Settings` if you need to configure providers or tool API keys.
3. Open `Dashboard`.
4. Choose a specialist agent.
5. Start a new session or reopen an existing one.
6. Choose a provider and model.
7. Optionally attach tools for that session.
8. Ask your questions and continue the same session later.

## Settings workflow

Inside `Settings`, you can:

- add or update provider API keys
- configure provider base URL overrides when needed
- fetch live model lists from supported APIs
- choose a default model per provider
- configure tool credentials such as Tavily

## In-session commands

While chatting, these commands are available:

- `/memory` to inspect session memory
- `/session` to inspect current session metadata
- `/settings` to jump into settings
- `/exit` to leave the current chat session

## Tool usage behavior

When a tool is used during a response, `doctorcli` shows:

- the tool name
- the tool query
- the returned summary
- the source list, when available

This makes it clear when the model answered from the base model alone versus when it used an attached tool.

## Local storage

`doctorcli` stores local application data in your platform app-data directory.

Typical stored data includes:

- provider settings and cached model catalogs
- session metadata
- chat transcripts and memory

## Example use cases

- create a general medicine session for symptom triage and follow-up questions
- use a dermatology specialist session to organize rash-related questions before a doctor visit
- keep a continuing chronic-care session with the same provider and model setup
- attach Tavily when you want the model to look up current external information
- attach Wikipedia when you want a lightweight reference tool without another API dependency

## Developer guide

Clone the repository:

```bash
git clone https://github.com/AIMLDev726/doctorcli.git
cd doctorcli
```

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run a compile check:

```bash
python -m compileall src
```

Build release artifacts:

```bash
python -m build --outdir release-dist
```

Validate the package before publishing:

```bash
python -m twine check release-dist/*
```

## Release notes

Current package version:

- `1.0.0`

## Contributing

Contributions, bug reports, and feature requests are welcome.

- Repository: [github.com/AIMLDev726/doctorcli](https://github.com/AIMLDev726/doctorcli)
- Issues: [github.com/AIMLDev726/doctorcli/issues](https://github.com/AIMLDev726/doctorcli/issues)

## License

MIT
