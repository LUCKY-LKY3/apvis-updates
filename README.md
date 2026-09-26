# APVIS updates

Signed update bundles for the APVIS layer of APVIS OS (the screens and the
`apvis_os` package). No source code lives here.

APVIS OS reads `latest.json`, downloads the bundle it names, and installs it
only if the bundle's ed25519 signature verifies against the key shipped in
the OS image and every file matches the bundle's manifest. If an updated Home
fails to start, APVIS rolls back automatically.

## Gaming PC boost (optional)

On the Windows gaming PC, open PowerShell **as administrator** in the folder with `tools/gaming-pc-setup.ps1` and run:

```powershell
powershell -ExecutionPolicy Bypass -File gaming-pc-setup.ps1
```

It installs Ollama (winget), lets your home network reach it, opens port 11434 on private networks only, downloads llama3.1:8b and qwen2.5-coder:7b, and prints the address and MAC to type into APVIS (Settings > Local AI > Gaming PC boost, or press Find).
