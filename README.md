# doctorcli

[GitHub Repository](https://github.com/AIMLDev726/doctorcli)

`doctorcli` is a specialist-first medical AI CLI for structured conversations, persistent sessions, optional live tools, and multi-provider model support.

## Why use doctorcli

`doctorcli` is built for people who want a focused terminal experience instead of a generic chat window. It gives you specialist personas, saved sessions, provider and model control, and a clean markdown-rendered interface for medical Q&A workflows.

## Highlights

- Specialist personas for multiple medical domains
- Rich terminal UI with streaming markdown responses
- Persistent sessions with memory across runs
- Live model discovery and default model selection per provider
- Optional session tools such as Wikipedia and Tavily web search
- Visible tool-call output with returned sources in chat
- Support for OpenAI, Gemini, Groq, Claude, Ollama, and LM Studio

## Installation

Install from PyPI:

```bash
pip install doctorcli
```

Install from source:

```bash
pip install .
```

Install in editable mode for development:

```bash
pip install -e ".[dev]"
```

## Quick start

Run the CLI:

```bash
doctorcli
```

Typical flow:

1. Open the app.
2. Choose a specialist.
3. Start a new session or continue an existing one.
4. Select a provider and model.
5. Optionally attach tools for that session.
6. Ask questions and continue the session later with memory preserved.

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

- Wikipedia: reference lookup for conditions, medications, symptoms, and background topics
- Tavily: live web search for current medical and factual context

When a model uses an attached tool, `doctorcli` shows the tool call, the returned summary, and the available sources directly in the chat transcript.

## Session features

- Create named sessions with a consultation reason
- Reopen past sessions with the original provider and model setup
- Keep a running transcript and memory through the session lifecycle
- Use `/memory`, `/session`, `/settings`, and `/exit` commands inside chat

## Local storage

`doctorcli` stores local state in your platform application directories.

- Settings: `doctorcli/settings.json`
- Sessions: `doctorcli/sessions/*.json`
- Cached provider model catalogs: stored with settings

## Development

Run tests:

```bash
python -m pytest
```

Build release artifacts:

```bash
python -m build
```

Validate artifacts before publishing:

```bash
python -m twine check dist/*
```

## Contributing

Contributions, issues, and feature requests are welcome.

- Repository: [github.com/AIMLDev726/doctorcli](https://github.com/AIMLDev726/doctorcli)
- Issues: [github.com/AIMLDev726/doctorcli/issues](https://github.com/AIMLDev726/doctorcli/issues)

## License

MIT
