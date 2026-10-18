
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce(key, value):
    value = str(value)

    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return value.strip().lower() in ("true", "1", "yes", "on")

    return value


def normalize_key(key):
    key = key.strip().lower()

    if key == "num_workers":
        return "workers"

    return key


def apply_layer(config, layer, app_prefix=False):
    for raw_key, value in layer.items():
        if value is None:
            continue

        key = str(raw_key).strip().lower()

        if app_prefix:
            if not key.startswith("app_"):
                continue
            key = key[4:]

        key = normalize_key(key)

        if key in DEFAULTS:
            config[key] = coerce(key, value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    # 1. Environment-specific YAML
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = Path(f"config.{env_name}.yaml")

    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}
        apply_layer(config, yaml_config)

    # 2. .env file (NUM_WORKERS alias supported)
    env_file = dotenv_values(".env")
    apply_layer(config, env_file)

    # 3. OS-level APP_* environment variables
    apply_layer(config, os.environ, app_prefix=True)

    # 4. CLI overrides, highest precedence
    for item in set:
        key, separator, value = item.partition("=")

        if not separator:
            continue

        key = normalize_key(key)

        if key in DEFAULTS:
            config[key] = coerce(key, value)

    # Never reveal the actual secret
    config["api_key"] = "****"

    return config
