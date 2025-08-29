"""
Compatibility shim for Flask 3.x:
Restores a Flask-2 style `@app.before_first_request` decorator.

Usage:
    1) Save this file next to server.py
    2) Add `import flask_before_first_compat` as the FIRST import in server.py
       (before `from flask import Flask` or creating `app`)
"""

import flask
from typing import Callable

# Only patch if missing (Flask 3+)
if not hasattr(flask.Flask, "before_first_request"):
    def _before_first_request(self: flask.Flask, func: Callable):
        """
        Register a function to run once, right before handling the first request.
        We emulate the old behavior by injecting a before_request that runs once.
        """
        ran_flag = {"done": False}

        @self.before_request
        def _run_once():
            if not ran_flag["done"]:
                # Execute the original function in app context (as Flask did)
                func()
                ran_flag["done"] = True

        return func

    # Monkey-patch the class
    flask.Flask.before_first_request = _before_first_request  # type: ignore[attr-defined]
