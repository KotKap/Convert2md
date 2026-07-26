#!/usr/bin/env python3
"""Run the local Convert2MD graphical interface."""

from pathlib import Path

from dotenv import load_dotenv
import uvicorn


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parent / ".env")
    uvicorn.run("src.web_api:create_web_app", host="127.0.0.1", port=8000,
                reload=False, factory=True)
