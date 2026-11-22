"""
Flask application factory for the Clinic Reception Chatbot.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request, session

from chatbot.engine import ChatbotEngine
from database.models import (
    authenticate_patient,
    get_all_appointments,
    get_all_doctors,
)


def create_app(db_path: str) -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = os.environ.get("CLINIC_SECRET_KEY", "change-me-in-prod-" + uuid.uuid4().hex)

    # Heavy model is loaded once at boot and kept in memory.
    engine = ChatbotEngine(db_path=db_path)
    app.config["ENGINE"] = engine
    app.config["DB_PATH"] = db_path

    @app.route("/")
    def index() -> str:
        if "session_id" not in session:
            session["session_id"] = uuid.uuid4().hex
        return render_template("index.html")

    @app.route("/admin")
    def admin() -> str:
        appointments = get_all_appointments(db_path)
        doctors = get_all_doctors(db_path)
        return render_template(
            "admin.html",
            appointments=appointments,
            doctors=doctors,
        )

    @app.route("/api/chat", methods=["POST"])
    def api_chat() -> Any:
        data: Dict[str, Any] = request.get_json(force=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Empty message"}), 400

        if "session_id" not in session:
            session["session_id"] = uuid.uuid4().hex

        session_id = session["session_id"]
        patient_id = session.get("patient_id")

        result = engine.handle(
            session_id=session_id,
            message=message,
            patient_id=patient_id,
        )
        return jsonify(
            {
                "reply": result["reply"],
                "intent": result.get("intent"),
                "confidence": result.get("confidence"),
                "state": result.get("state"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    @app.route("/api/login", methods=["POST"])
    def api_login() -> Any:
        data = request.get_json(force=True) or {}
        patient_no = (data.get("patient_no") or "").strip()
        password = (data.get("password") or "").strip()
        patient = authenticate_patient(db_path, patient_no, password)
        if not patient:
            return jsonify({"ok": False, "error": "Invalid credentials"}), 401
        session["patient_id"] = patient["id"]
        session["patient_name"] = patient["name"]
        return jsonify({"ok": True, "patient_name": patient["name"]})

    @app.route("/api/logout", methods=["POST"])
    def api_logout() -> Any:
        session.pop("patient_id", None)
        session.pop("patient_name", None)
        return jsonify({"ok": True})

    @app.route("/api/whoami")
    def api_whoami() -> Any:
        return jsonify(
            {
                "patient_id": session.get("patient_id"),
                "patient_name": session.get("patient_name"),
            }
        )

    return app
