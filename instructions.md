# Alice PC Control App — Technical Transformation Plan

> This document serves as a detailed specification for refactoring the existing repository into a universal Windows desktop application that exposes a local HTTP API for PC control.  The new application must retain all current system actions from `worlde-easypad12-controller-main` while removing the dependency on MIDI hardware.  It should act as a neutral bridge between external services (e.g. Kuzya/Alice voice assistants) and the host PC.

---

## 1. Goals

1. Convert the current WORLDE EasyPad controller project into **Alice PC Control App**.
2. Expose every available action through a local HTTP API and a graphical user interface.
3. Allow any external bridge (Kuzya, custom skills, etc.) to trigger actions without relying on MIDI.
4. Preserve and extend all system management capabilities currently implemented in `system_actions.py`.
5. Provide flexible input and output formatting so bridges can consume responses in multiple ways.

---

## 2. Architecture Overview

The refactored application is divided into four layers:

### 2.1 Core
- **ActionRegistry** – unified registry that maps action names to executor callables.  Populate it with the existing methods from `system_actions.py` (see catalogue below).
- **StateStore** – persistent key/value storage for variables, cached statuses, and configuration values.
- **EventBus / Log** – publish/subscribe channel for events and structured logging.
- **Scheduler (optional)** – timer service for delayed or repeated actions.

### 2.2 HTTP API
- Built with **FastAPI/Starlette** and an embedded **Uvicorn** server.
- Base path: `/api/v1`.
- Supports both `GET` and `POST`.
- Three input modes for action parameters:
  - **Query**: `/api/v1/audio/volume/set?value=51`.
  - **JSON** body: `{ "value": 51 }`.
  - **Raw** body: `51` or `{51}`.
- Output profiles (global + per action):
  - `binary_01` – `0` or `1`.
  - `int_only` – numeric value.
  - `json_ok_value` – `{ "ok": true, "value": <data> }`.
  - `text_template` / `json_template` – Jinja-style templates.
- Security features: optional token, IP allowlist, CORS off by default, health-check endpoint.

### 2.3 UI (PySide6)
- Modern dashboard with tiles representing actions (replacing the MIDI grid).
- Tabs/sections:
  - **Dashboard** – quick action tiles and status indicators (volume, active device, WebOS connection).
  - **Actions** – searchable list of all actions with ability to assign output profiles and run test calls.
  - **Variables** – current values from `StateStore`.
  - **Scenes** – (optional) macro editor with dry-run preview.
  - **API Tester** – manual request builder for any endpoint.
  - **Settings** – server options, security, formatting profiles, engine selection.
  - **Logs** – chronological journal of calls and errors.
- Use light/dark themes and make window tray-friendly.

### 2.4 Windows Executors
Reuse existing Python implementations but decouple them from MIDI triggers:
- **Audio** – volume and device switching via `pycaw`, `pyaudio` and PowerShell fallbacks.
- **Input** – keyboard shortcuts, typing, mouse control using `keyboard`, `pyautogui`, `pywin32`.
- **Processes** – launching, toggling, running shell and PowerShell commands (`subprocess`, `psutil`).
- **Media** – play/pause/next/prev/stop.
- **System** – lock/sleep/hibernate/shutdown/restart/display on/off.
- **Text to Speech** – `edge-tts` or SAPI; save files when requested.
- **Speech to Text** – `faster-whisper`/Vosk (later milestone).
- **LLM** – optional API-based chat completion.
- **Wake-on-LAN** – send magic packets.
- **WebOS TV** – pairing and command execution via `aiowebostv`.

---

## 3. Catalogue of Actions

Expose all actions already implemented in `system_actions.py` and add HTTP routes for them.  Do **not** limit the API to the 15 actions from the previous plan if more exist.  The current list includes:

1. **Launch Application** – `/app/launch`
2. **Toggle Application** – `/app/toggle`
3. **Open Website** – `/web/open`
4. **Volume Control** – `/audio/volume` (get), `/audio/volume/set`, `/audio/volume/change`, `/audio/volume/mute`, `/audio/volume/unmute`
5. **Switch Audio Device** – `/audio/device/set`
6. **Keyboard Shortcut** – `/input/shortcut`
7. **Media Control** – `/media/play`, `/media/pause`, `/media/toggle`, `/media/next`, `/media/prev`, `/media/stop`
8. **System Command** – `/system/lock`, `/system/sleep`, `/system/hibernate`, `/system/shutdown`, `/system/restart`, `/system/display/off`, `/system/display/on`
9. **PowerShell Command** – `/ps/run`
10. **Type Text / Paste Text** – `/input/type`, `/input/paste`
11. **Run Command / Open Application (generic)** – `/cmd/run`, `/app/open`
12. **Window Control** – `/window` (minimize, maximize, close, switch)
13. **Mouse Control** – `/mouse/move`, `/mouse/click`, `/mouse/scroll`
14. **Toggle Setting** – `/system/toggle` (e.g., Wi-Fi, Bluetooth if supported)
15. **Text to Speech** – `/tts/speak`
16. **Wake on LAN** – `/wol/send`
17. **WebOS TV Control** – `/webos/connect`, `/webos/cmd`, plus aliases like `/webos/volume/up`
18. **Execute Command Sequences** – `/macro/run` (batch commands with delays)
19. **Execute PowerShell Sequences** – `/ps/macro`
20. **ChatGPT / LLM Ask** – `/llm/ask`
21. **Speech to Text** – `/stt/transcribe`

This list should be expanded if additional callable methods exist in `SystemActions`.  Each action must define accepted parameters, input modes, default output profile, timeout, error policy and optional rate limit.

---

## 4. Input/Output Conventions

### 4.1 Input Parsing
Implement a universal parser that converts incoming parameters from query strings, JSON bodies or raw payloads into Python types.  Validate ranges and types (e.g. volume 0‑100, booleans).

### 4.2 Output Profiles
Support global and per‑action output formatting:
- `int_only`
- `binary_01`
- `json_ok_value`
- `text_template` / `json_template` with placeholders such as `{{ ok }}`, `{{ value }}`, `{{ error }}`.
`Content-Type` should match the profile (JSON vs plain text).

---

## 5. Configuration and Security

- **Server**: `port`, `bind`, `token`, `wan_expose=false`, `ip_allowlist=[]`, `cors=false`.
- **Formatting**: default profile, per-action overrides, custom templates.
- **Security**: rate limits, optional PIN or double-confirmation for critical actions (shutdown, restart, PowerShell).
- **Engines**: choice of STT/TTS/LLM/WebOS clients and their credentials/paths.
- **UI**: theme selection, tray behavior, logging verbosity.
- Persist configuration under `config/` using JSON or YAML.

---

## 6. User Interface Requirements

1. **Dashboard** with tiles corresponding to all actions. Tiles should reflect state where applicable (e.g. mute on/off, current volume).
2. **Actions List** with search, tag filters and ability to trigger actions directly from the UI.
3. **Variables** page showing `StateStore` entries.
4. **Scenes/Macros** editor for combining multiple actions with delays.
5. **API Tester** tab where users can craft requests and preview responses in chosen profiles.
6. **Settings** dialog with sections: Server, Security, Formatting, Engines, UI.
7. **Logs** viewer displaying timestamp, endpoint, parameters, result and source IP.
8. The app must minimize to tray and optionally auto-start with Windows (Task Scheduler integration).

---

## 7. Integration with External Bridges

Document how to call the local API from third-party bridges (e.g. Kuzya).  Provide examples of URLs for common actions.  Make clear that the application is bridge-agnostic and does not depend on Kuzya-specific routes.

---

## 8. Build & Distribution

- Target Python **3.12**.
- Dependencies managed via `requirements.txt` with pinned versions where critical.
- Use `PyInstaller` to build a single-file or one-folder executable:  
  `pyinstaller --onefile --noconsole --icon=icon.ico --version-file version.txt --exclude-module PyQt5 --exclude-module PyQt6 run.py`
- Auto-start option through Windows Task Scheduler.

---

## 9. Roadmap

1. **MVP**: set up HTTP skeleton, port a subset of actions (launch app, open web, volume get/set/change, media toggle), implement output profiles and minimal UI.
2. **Full Action Catalogue**: expose all remaining actions through API and UI; add API tester and logging.
3. **Security Layer**: token auth, IP allowlist, rate limiting, confirmation dialogs.
4. **Advanced Modules**: audio device switching, window/mouse control, PowerShell, WOL, WebOS, STT/TTS/LLM.
5. **UI Polish & Documentation**: theme support, tray behavior, examples of external integrations.

---

## 10. Definition of Done

- Every action from `SystemActions` is callable via HTTP and UI tiles.
- Input parsing and output profiles function globally and per action.
- Logging, health-check and security mechanisms are in place.
- Application builds into a standalone executable.
- Repository includes updated README and this instructions file.

