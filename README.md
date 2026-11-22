# Clinic Reception Chatbot

A Flask-based clinic virtual receptionist demo that can answer FAQ questions, book/cancel/check appointments, and show lab results for logged-in patients.

## How to run

```bash
cd clinic_chatbot
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python run.py
```

Then open http://127.0.0.1:5000

## Seed/reset database

```bash
python run.py --seed
```

## Demo login

Use:

- Patient no: `P002`
- Password: `test1234`
