"""WSGI entry point for the ``api`` process: ``gunicorn wsgi:app``."""

from app import create_app

app = create_app()
