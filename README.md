janus_app/
├── app.py              ← entrypoint: page config, sidebar, routing only
├── config.py           ← AI provider setup, call_model(), shared helpers
├── engines/
    ├── __init__.py
    ├── adie.py         ← ADIE: EXIF/GPS extraction + forensic chat
    └── codex.py        ← CODEX: coding chat + ROCm task focus
