# Context-Aware-AI-chatbot-for-clinic

Clinic Reception Chatbot
A virtual receptionist for a medical clinic, built as my final-year BSc Computer Science project (graded 79%, First). Patients can chat to it to book, cancel and check appointments, view their lab results after logging in, and get answers to common clinic questions, so reception staff spend less time on routine requests.

Why I built it
While waiting in a hospital, I watched the reception desk struggle with a long queue of bookings, general questions and lab-result enquiries. Most of those requests follow the same few patterns, so I built an assistant that can handle them and hand anything else over to a person.

What it can do
Understand what the user wants: 11 intents, including book, cancel, reschedule or check an appointment, lab results, clinic information, symptom questions, and asking for a human.
Book appointments through a short conversation: asks for the doctor or department, the date and time (understands phrases like "next Monday 2pm"), and the patient's name, then confirms before saving.
Cancel and check appointments for logged-in patients.
Show lab results securely: results are only shown after the patient logs in with their patient number and password.
Answer clinic FAQs using semantic search over a small knowledge base, so it only answers from trusted information.
Stay safe with medical questions: it doesn't diagnose; it suggests booking an appointment and adds a disclaimer.
Admin page listing doctors and appointments for reception staff.
How it works
Intent recognition: a pretrained sentence-transformer (all-MiniLM-L6-v2) embeds the user's message and compares it with example phrases for each intent using cosine similarity. Messages below a confidence threshold fall back to the FAQ search.
FAQ retrieval (retrieval-augmented answers): FAQ questions are embedded once at start-up; each query returns the closest stored answer only if the similarity score is high enough, otherwise the bot asks the user to rephrase.
Dialogue state: each chat session keeps its own history and "slots" (doctor, date, name, confirmation), so multi-step conversations like booking work naturally.
Entity extraction: date and time parsing with dateparser, plus rules for doctor names, departments, names and yes/no answers.
Data: a SQLite database with tables for doctors, patients, appointments, lab results and a chat log. Passwords are hashed with bcrypt.
Runs locally: after the embedding model is downloaded once, everything runs on the local machine, so patient data never leaves it.
Tech stack
Python, Flask, SQLite, sentence-transformers, scikit-learn, NumPy, dateparser, bcrypt, HTML/CSS/JavaScript.

Project structure
clinic_chatbot/
├── app.py              # Flask app and API routes (/api/chat, /api/login, /admin)
├── run.py              # Entry point; --seed resets the demo database
├── chatbot/
│   ├── engine.py       # Orchestrates intents, flows and replies
│   ├── intents.py      # Semantic intent classifier
│   ├── retriever.py    # Semantic FAQ retriever
│   ├── nlu.py          # Date, doctor, department, name and yes/no extraction
│   └── context.py      # Per-session conversation state
├── database/
│   ├── models.py       # SQLite schema and queries
│   └── seed.py         # Sample doctors, patients, appointments, lab results
├── knowledge_base/faqs.json
├── templates/          # Chat page and admin page
└── static/             # CSS and JavaScript for the chat interface
How to run
cd clinic_chatbot
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python run.py
Then open http://127.0.0.1:5000. To reset the demo database: python run.py --seed.

Demo login: patient number P002, password test1234.

Limitations and next steps
This is a demo with sample data, not a production medical system.
The admin page has no login yet.
Conversation state is kept in memory, so it resets when the server restarts.
Next steps: add admin authentication, store the chat log for analysis, and add automated tests for the intent classifier and booking flow.
