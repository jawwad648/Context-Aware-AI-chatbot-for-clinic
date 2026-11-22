"""
ChatbotEngine - the orchestrator.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sentence_transformers import SentenceTransformer

from chatbot.context import ContextStore, ConversationState
from chatbot.intents import INTENT_EXAMPLES, IntentClassifier
from chatbot.nlu import (
    extract_datetime,
    extract_department,
    extract_doctor,
    extract_name,
    yes_no,
)
from chatbot.retriever import FaqRetriever
from database.models import (
    book_appointment,
    cancel_appointment_for_patient,
    get_appointments_for_patient,
    get_doctor_names,
    get_doctors_by_specialty,
    get_lab_results_for_patient,
    get_or_create_patient_by_name,
)

MODEL_NAME = os.environ.get("CLINIC_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base", "faqs.json")

DISCLAIMER = (
    " Please remember I'm an automated assistant; for any medical decision "
    "always consult a qualified doctor."
)


class ChatbotEngine:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        print(f"[chatbot] Loading encoder: {MODEL_NAME} ...")
        self.model = SentenceTransformer(MODEL_NAME)
        print("[chatbot] Building intent classifier ...")
        self.intents = IntentClassifier(self.model)
        print("[chatbot] Building FAQ retriever ...")
        self.faq = FaqRetriever(self.model, FAQ_PATH)
        self.ctx = ContextStore()
        print("[chatbot] Ready.")

    def handle(
        self,
        session_id: str,
        message: str,
        patient_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        state = self.ctx.get(session_id)
        state.add_user(message)

        if state.flow == "booking":
            reply = self._step_booking(state, message, patient_id)
        elif state.flow == "cancel":
            reply = self._step_cancel(state, message, patient_id)
        elif state.flow == "lab":
            reply = self._step_lab(state, message, patient_id)
        else:
            pred = self.intents.predict(message)
            state.last_intent = pred.intent
            state.last_confidence = pred.confidence

            if pred.confidence < IntentClassifier.MIN_CONFIDENCE:
                reply = self._route_fallback(state, message)
            else:
                reply = self._route(state, message, pred.intent, patient_id)

        state.add_bot(reply)
        return {
            "reply": reply,
            "intent": state.last_intent,
            "confidence": round(state.last_confidence, 3),
            "state": state.to_public_dict(),
        }

    def _route(
        self,
        state: ConversationState,
        message: str,
        intent: str,
        patient_id: Optional[int],
    ) -> str:
        if intent == "greeting":
            return (
                "Hello! I'm the virtual receptionist for the clinic. "
                "I can help you book or cancel appointments, check lab results, "
                "and answer general questions. How can I help?"
            )
        if intent == "goodbye":
            state.reset_flow()
            return "Goodbye, take care!"
        if intent == "thanks":
            return "You're welcome."
        if intent == "book_appointment":
            state.flow = "booking"
            state.slots = {}
            return self._step_booking(state, message, patient_id)
        if intent == "cancel_appointment":
            state.flow = "cancel"
            state.slots = {}
            return self._step_cancel(state, message, patient_id)
        if intent == "reschedule_appointment":
            return (
                "To reschedule, I'll cancel your existing appointment and book a "
                "new one. First, which appointment would you like to cancel? "
                "(please give the date)"
            )
        if intent == "check_appointment":
            return self._handle_check_appointment(patient_id)
        if intent == "lab_results":
            state.flow = "lab"
            state.slots = {}
            return self._step_lab(state, message, patient_id)
        if intent == "clinic_info":
            return self._route_fallback(state, message)
        if intent == "symptom_query":
            return (
                "I'm sorry you're not feeling well. I can give general information "
                "but I cannot diagnose. For acute symptoms please book an "
                "appointment or, in an emergency, call your local emergency "
                "number." + DISCLAIMER
            )
        if intent == "human_handoff":
            return (
                "No problem - a human receptionist will be with you shortly. "
                "In the meantime please tell me your name and reason for calling "
                "so I can pass it on."
            )
        return self._route_fallback(state, message)

    def _route_fallback(self, state: ConversationState, message: str) -> str:
        hit = self.faq.best(message)
        if hit:
            return hit.answer
        return (
            "I'm not sure I understood that. I can help with appointments, "
            "lab results, and general clinic information. Could you rephrase?"
        )

    def _step_booking(
        self,
        state: ConversationState,
        message: str,
        patient_id: Optional[int],
    ) -> str:
        slots = state.slots

        if yes_no(message) is False and "confirm" not in slots:
            state.reset_flow()
            return "OK, I've cancelled the booking request. Anything else?"

        if "doctor" not in slots and "department" not in slots:
            known = get_doctor_names(self.db_path)
            d = extract_doctor(message, known)
            if d:
                slots["doctor"] = d
            else:
                dept = extract_department(message)
                if dept:
                    slots["department"] = dept

        if "doctor" not in slots and "department" not in slots:
            doctors_preview = ", ".join(get_doctor_names(self.db_path)[:4]) + ", ..."
            return (
                "Sure, I can book you an appointment. "
                f"Which doctor or department would you like? "
                f"Available doctors include: {doctors_preview}"
            )

        if "doctor" not in slots and "department" in slots:
            candidates = get_doctors_by_specialty(self.db_path, slots["department"])
            if not candidates:
                state.reset_flow()
                return (
                    f"Sorry, we don't currently have a doctor in {slots['department']}. "
                    "Would you like to try another department?"
                )
            slots["doctor"] = candidates[0]

        if "when" not in slots:
            dt = extract_datetime(message)
            if dt and dt > datetime.now():
                slots["when"] = dt
            else:
                return (
                    f"Great - for Dr {slots['doctor']}, when would you like the "
                    "appointment? (e.g. 'tomorrow 10am' or 'next Monday 2pm')"
                )

        if "patient_id" not in slots:
            if patient_id is not None:
                slots["patient_id"] = patient_id
            else:
                name = extract_name(message)
                if name:
                    first, last = name
                    pid = get_or_create_patient_by_name(self.db_path, first, last)
                    slots["patient_id"] = pid
                    slots["patient_name"] = f"{first} {last}"
                else:
                    return (
                        "Could I have your full name please? "
                        "(for example: 'my name is Ayesha Khan')"
                    )

        if not slots.get("confirmed"):
            slots["confirmed"] = "pending"
            when = slots["when"].strftime("%A %d %b %Y at %H:%M")
            return (
                f"Just to confirm: appointment with Dr {slots['doctor']} on "
                f"{when}. Shall I book it? (yes/no)"
            )

        if slots.get("confirmed") == "pending":
            ans = yes_no(message)
            if ans is True:
                appt_id = book_appointment(
                    self.db_path,
                    patient_id=slots["patient_id"],
                    doctor_name=slots["doctor"],
                    when=slots["when"],
                )
                state.reset_flow()
                when = slots["when"].strftime("%A %d %b %Y at %H:%M")
                return (
                    f"Done! Your appointment with Dr {slots['doctor']} is "
                    f"confirmed for {when}. Booking reference #{appt_id}. "
                    "Anything else?"
                )
            if ans is False:
                state.reset_flow()
                return "No problem, I've cancelled the booking. Anything else?"
            return "Please answer yes or no - shall I book the appointment?"

        state.reset_flow()
        return "Sorry, I lost track. Shall we start again?"

    def _step_cancel(
        self,
        state: ConversationState,
        message: str,
        patient_id: Optional[int],
    ) -> str:
        if patient_id is None:
            state.reset_flow()
            return (
                "To cancel an appointment I first need to verify your identity. "
                "Please log in using the sidebar on the left."
            )

        slots = state.slots
        if "when" not in slots:
            dt = extract_datetime(message)
            if dt is None:
                upcoming = get_appointments_for_patient(self.db_path, patient_id)
                if not upcoming:
                    state.reset_flow()
                    return "You don't have any upcoming appointments to cancel."
                lines = [
                    f"- {a['date']} with Dr {a['doctor']} (ref #{a['id']})"
                    for a in upcoming[:5]
                ]
                return (
                    "Which appointment would you like to cancel?\n" + "\n".join(lines)
                )
            slots["when"] = dt

        ok = cancel_appointment_for_patient(
            self.db_path, patient_id=patient_id, when=slots["when"]
        )
        state.reset_flow()
        if ok:
            return "Your appointment has been cancelled. Anything else?"
        return (
            "I couldn't find an appointment matching that time. "
            "Could you double-check the date?"
        )

    def _step_lab(
        self,
        state: ConversationState,
        message: str,
        patient_id: Optional[int],
    ) -> str:
        if patient_id is None:
            state.reset_flow()
            return (
                "Lab results are private. Please log in using the sidebar "
                "(patient number + password) and I'll pull them up for you."
            )

        results = get_lab_results_for_patient(self.db_path, patient_id)
        state.reset_flow()
        if not results:
            return "Good news - there are no pending lab results on your file."
        lines = []
        for r in results[:10]:
            status = "READY" if r["ready"] else "pending"
            lines.append(
                f"- {r['date']}: {r['test']} ({status}) "
                + (f"- result: {r['result']}" if r["ready"] else "")
            )
        return (
            "Here is a summary of your lab results:\n"
            + "\n".join(lines)
            + DISCLAIMER
        )

    def _handle_check_appointment(self, patient_id: Optional[int]) -> str:
        if patient_id is None:
            return (
                "Please log in (sidebar) so I can look up your appointments securely."
            )
        ap = get_appointments_for_patient(self.db_path, patient_id)
        if not ap:
            return "You have no upcoming appointments."
        lines = [f"- {a['date']} with Dr {a['doctor']} (ref #{a['id']})" for a in ap[:5]]
        return "Here are your upcoming appointments:\n" + "\n".join(lines)
