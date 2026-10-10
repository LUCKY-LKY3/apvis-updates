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

## Releases (V3)

| Version | What changed |
|---|---|
| 3.0.6 | Installer: press Restart first, then take the USB out |
| 3.0.5 | Pictures are back ("show me a picture of Paris") |
| 3.0.4 | Ring logo in the top-left is a button back to Home |
| 3.0.3 | New APVIS wordmark logo; cleaner core |
| 3.0.2 | Start-up screen shows just the logo; delayed power command for remote access |
| 3.0.1 | Shutdown/restart fixes; no green smoke; smoother core |
| 3.0.0-dev.10 | The V3 look (lacquer and gold, JARVIS-style core) |
| 3.0.0-dev.9 | AI queue, session memory, plans you approve once |

Full changelog: [APVIS-OS CHANGELOG](https://github.com/LUCKY-LKY3/APVIS-OS/blob/v3/CHANGELOG.md).
