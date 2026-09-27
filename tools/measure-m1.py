#!/usr/bin/env python3
"""V3 M1 measurements on a real APVIS machine (run it on the OptiPlex, as the desktop user).

    python3 scripts/measure-m1.py --label browser-closed
    (open the APVIS browser with a page or two, then)
    python3 scripts/measure-m1.py --label browser-open

It measures, with real data only:
  * RAM: total/available, Home, the browser (QtWebEngine), Ollama and the models Ollama has loaded;
  * embedding: a full index build of your real vault into a temporary file (your own index is untouched),
    time per note and per chunk;
  * search: keyword vs hybrid time for sample questions, with raw cosine scores to tune the calibration;
  * Ask (optional, --ask): time to first word with meaning search off and on, same question and model.
Nothing is changed on the system. Results print and are saved to ~/apvis-m1-<label>-<time>.json.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path


def add_apvis_to_path() -> str:
    """Use the active APVIS update if there is one (that's what Home runs), else the image's copy,
    else this checkout."""
    updates = Path.home() / ".local/share/apvis-os/updates"
    try:
        active = (updates / "current").read_text().strip()
    except OSError:
        active = ""
    candidates = [(f"update {active}", updates / active / "python")] if active else []
    candidates += [("image", Path("/usr/lib/python3/dist-packages")),
                   ("checkout", Path(__file__).resolve().parent.parent / "config/includes.chroot/usr/lib/python3/dist-packages")]
    for label, path in candidates:
        if (path / "apvis_os" / "semantic.py").is_file():
            sys.path.insert(0, str(path))
            return f"{label} ({path})"
    raise SystemExit("No APVIS layer with semantic.py found: install the M1 update first, or run from the checkout.")


def mb(n: float) -> float:
    return round(n / 1048576, 1)


def ram_snapshot(client) -> dict:
    import psutil
    vm = psutil.virtual_memory()
    groups = {"home": 0, "browser": 0, "ollama": 0}
    for proc in psutil.process_iter(["name", "cmdline", "memory_info"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [])
            rss = proc.info["memory_info"].rss if proc.info["memory_info"] else 0
        except (psutil.Error, TypeError):
            continue
        name = proc.info["name"] or ""
        if "QtWebEngineProcess" in name or "QtWebEngineProcess" in cmd:
            groups["browser"] += rss
        elif "apvis-v2-shell" in cmd or "apvis_os.shell_app" in cmd:
            groups["home"] += rss
        elif name.startswith("ollama") or "/ollama" in cmd.split(" ")[0]:
            groups["ollama"] += rss
    loaded = []
    try:
        with client._open("/api/ps", None, 5) as response:
            for m in json.load(response).get("models", []):
                loaded.append({"model": m.get("name"), "size_mb": mb(m.get("size", 0))})
    except Exception as exc:  # noqa: BLE001 - a measurement script reports, it doesn't fail
        loaded = [{"error": str(exc)}]
    return {"total_mb": mb(vm.total), "available_mb": mb(vm.available), "used_mb": mb(vm.total - vm.available),
            "swap_used_mb": mb(psutil.swap_memory().used),
            "home_rss_mb": mb(groups["home"]), "browser_rss_mb": mb(groups["browser"]),
            "ollama_rss_mb": mb(groups["ollama"]), "ollama_loaded": loaded}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", default="run", help="e.g. browser-open or browser-closed")
    parser.add_argument("--model", default="", help="embedding model (default: nomic-embed-text, else all-minilm)")
    parser.add_argument("--query", action="append", default=[], help="a search question (repeatable)")
    parser.add_argument("--ask", default="", help="also time an Ask answer with meaning search off and on")
    parser.add_argument("--skip-build", action="store_true", help="skip the full index build timing")
    args = parser.parse_args()

    layer = add_apvis_to_path()
    from apvis_os import semantic
    from apvis_os.ask import AskConfig, AskService
    from apvis_os.ollama import OllamaClient
    from apvis_os.vault import Vault

    config = AskConfig.load()
    client = OllamaClient(config.ollama_url, timeout=10)
    installed = [m.name for m in client.models()]
    model = args.model or semantic.pick_model(installed)
    if not model:
        raise SystemExit("No embedding model installed. Switch on Settings > Local AI > Memory search, or run: "
                         "ollama pull nomic-embed-text")
    vault = Vault()
    notes = vault.notes()
    out: dict = {"label": args.label, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "apvis_layer": layer,
                 "machine": {"cpu": platform.processor() or platform.machine(), "cores": os.cpu_count(),
                             "python": platform.python_version()},
                 "embed_model": model, "vault_notes": len(notes), "ram_before": ram_snapshot(client)}
    try:
        out["machine"]["cpu"] = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                                     if line.startswith("model name"))
    except (OSError, StopIteration):
        pass
    print(f"APVIS layer: {layer}\nEmbedding model: {model}; vault notes: {len(notes)}")

    with tempfile.TemporaryDirectory() as tmp:
        index = semantic.SemanticIndex(client, model, Path(tmp) / "measure.sqlite")
        # Cold/warm load of the embedding model itself.
        t = time.perf_counter()
        client.embed(model, ["warm-up"], keep_alive=semantic.EMBED_KEEP_ALIVE)
        out["embed_first_call_s"] = round(time.perf_counter() - t, 3)
        t = time.perf_counter()
        client.embed(model, ["a short sentence about the wifi router"], keep_alive=semantic.EMBED_KEEP_ALIVE)
        out["embed_one_short_s"] = round(time.perf_counter() - t, 3)
        if not args.skip_build and notes:
            result = index.sync(vault)
            out["build"] = {**result.to_dict(), "per_note_s": round(result.seconds / max(1, result.embedded), 3),
                            "per_chunk_s": round(result.seconds / max(1, result.chunks), 3)}
            print(f"Index build: {result.embedded} notes, {result.chunks} chunks in {result.seconds}s")
        out["ram_after_embed"] = ram_snapshot(client)

        queries = args.query or ["what is my wifi password", "when is the car due", "what did I decide about models"]
        out["search"] = []
        for q in queries:
            t = time.perf_counter()
            kw = vault.search(q, limit=5)
            kw_s = time.perf_counter() - t
            semantic._CACHE.clear()
            t = time.perf_counter()
            raw = index.query(q, limit=5, timeout=None)
            first_s = time.perf_counter() - t
            t = time.perf_counter()
            info: dict = {}
            hy = semantic.hybrid_search(vault, q, 5, index, info)
            hy_s = time.perf_counter() - t
            row = {"query": q, "keyword_s": round(kw_s, 3), "semantic_cold_s": round(first_s, 3), "hybrid_s": round(hy_s, 3),
                   "mode": info.get("mode"), "keyword_top": [n.title for _, n in kw[:3]],
                   "hybrid_top": [[n.title, s] for s, n in hy[:3]],
                   "raw_cosine": [[p, round(c, 3)] for c, p in raw]}
            out["search"].append(row)
            print(f"\nQ: {q}\n  keyword {row['keyword_s']}s -> {row['keyword_top']}\n  hybrid  {row['hybrid_s']}s -> {row['hybrid_top']}"
                  f"\n  raw cosine: {row['raw_cosine']}")

    if args.ask:
        out["real_index"] = semantic.SemanticIndex(client, model).status()
        if not out["real_index"].get("ready"):
            print("\nNote: Home hasn't built your meaning index yet (switch on Memory search and wait for "
                  "'notes read'), so the 'on' Ask below can only use keywords.")
        out["ask"] = {}
        for label, on in (("off", False), ("on", True)):
            cfg = AskConfig.load()
            cfg.semantic_memory = on
            service = AskService(cfg)
            result = service.ask(args.ask, role="fast")          # fixed role: no cache, no router, same model
            out["ask"][label] = {"first_word_s": result.first_token_s, "total_s": result.total_s, "model": result.model,
                                 "notes_used": result.notes_used, "status": result.status}
            print(f"\nAsk with meaning search {label}: first word {result.first_token_s}s, total {result.total_s}s, "
                  f"notes used {result.notes_used}")
    out["ram_end"] = ram_snapshot(client)
    for key in ("ram_before", "ram_after_embed", "ram_end"):
        r = out[key]
        print(f"\nRAM {key}: used {r['used_mb']} MB of {r['total_mb']} MB, available {r['available_mb']} MB; "
              f"Home {r['home_rss_mb']} MB, browser {r['browser_rss_mb']} MB, Ollama {r['ollama_rss_mb']} MB; loaded {r['ollama_loaded']}")
    path = Path.home() / f"apvis-m1-{args.label}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
