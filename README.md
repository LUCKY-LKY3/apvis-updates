# APVIS updates

Signed update bundles for the APVIS layer of APVIS OS (the screens and the
`apvis_os` package). No source code lives here.

APVIS OS reads `latest.json`, downloads the bundle it names, and installs it
only if the bundle's ed25519 signature verifies against the key shipped in
the OS image and every file matches the bundle's manifest. If an updated Home
fails to start, APVIS rolls back automatically.
