# Alice PC Control App

Prototype application for controlling a Windows PC through a local
HTTP API.  The project is in the process of transitioning from a MIDI
controller to a general‑purpose action bridge as outlined in
`instructions.md`.

## Quick start

Install dependencies and launch the API server:

```bash
pip install -r requirements.txt
python run_api.py
```

The server exposes a small subset of actions under `/api/v1`, for
example:

```
GET http://localhost:8000/api/v1/web/open?url=https://example.com
GET http://localhost:8000/api/v1/audio/volume
POST http://localhost:8000/api/v1/audio/volume/set?value=50
```

Additional actions and a graphical user interface will be added in
future iterations.
