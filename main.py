import os
from pathlib import Path
from typing import List
import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

DEFAULTS = {"port": 8000, "workers": 1, "debug": False, "log_level": "info", "api_key": "default-secret-000"}
TYPES = {
    "port": int,
    "workers": int,
    "debug": lambda v: str(v).strip().lower() in {"true", "1", "yes", "on"},
    "log_level": str,
    "api_key": str,
}

def normalize_key(raw):
    key = str(raw).strip()
    if key.startswith("APP_"):
        key = key[4:]
    key = key.lower()
    return "workers" if key == "num_workers" else key

def apply_layer(config, values):
    for raw_key, value in values.items():
        key = normalize_key(raw_key)
        if value is not None and key in TYPES:
            config[key] = value

def build_config(overrides):
    config = dict(DEFAULTS)
    env_name = os.environ.get("APP_ENV", "development")
    path = Path(f"config.{env_name}.yaml")
    if path.exists():
        apply_layer(config, yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    apply_layer(config, dotenv_values(".env"))
    os_values = {k: v for k, v in os.environ.items() if k.startswith("APP_") and k != "APP_ENV"}
    apply_layer(config, os_values)
    cli = {}
    for item in overrides:
        if "=" in item:
            key, value = item.split("=", 1)
            cli[key] = value
    apply_layer(config, cli)
    result = {}
    for key, converter in TYPES.items():
        try:
            result[key] = converter(config[key])
        except (TypeError, ValueError):
            result[key] = DEFAULTS[key]
    result["api_key"] = "****"
    return result

app = FastAPI(title="eShopCo Configuration Health API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    return build_config(set)

@app.get("/")
def root():
    return {"service": "eshopco-config-api", "status": "ok"}
