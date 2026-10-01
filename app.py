import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from services.ai_service import evaluate_answer, generate_questions
from services.json_service import append_record, update_record

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "development-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

TECHNOLOGIES = [
    "Python", "Java", "JavaScript", "HTML and CSS", "React", "SQL",
    "Data Structures", "Machine Learning",
]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
INTERVIEW_TYPES = ["Technical", "HR", "Mixed"]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/setup")
def setup():
    return render_template(
        "setup.html", technologies=TECHNOLOGIES, levels=LEVELS,
        interview_types=INTERVIEW_TYPES,
    )


@app.post("/start-interview")
def start_interview():
    name = request.form.get("student_name", "").strip()
    technology = request.form.get("technology", "")
    level = request.form.get("level", "")
    interview_type = request.form.get("interview_type", "")
    try:
        question_count = int(request.form.get("question_count", "5"))
    except ValueError:
        question_count = 0

    if not name or len(name) > 80:
        flash("Please enter a valid name.", "error")
    elif technology not in TECHNOLOGIES or level not in LEVELS or interview_type not in INTERVIEW_TYPES:
        flash("Please choose valid interview options.", "error")
    elif question_count not in range(3, 11):
        flash("Choose between 3 and 10 questions.", "error")
    else:
        interview_id = str(uuid.uuid4())
        questions = generate_questions(technology, level, interview_type, question_count)
        session["interview"] = {
            "id": interview_id, "student_name": name, "technology": technology,
            "level": level, "interview_type": interview_type, "questions": questions,
            "answers": [], "current_index": 0, "started_at": timestamp(),
        }
        append_record("interviews.json", session["interview"])
        return redirect(url_for("interview"))
    return redirect(url_for("setup"))


@app.route("/interview")
def interview():
    interview_data = session.get("interview")
    if not interview_data:
        return redirect(url_for("setup"))
    index = interview_data["current_index"]
    if index >= len(interview_data["questions"]):
        return redirect(url_for("finish_interview"))
    return render_template(
        "interview.html", interview=interview_data,
        question=interview_data["questions"][index], question_number=index + 1,
    )


@app.post("/submit-answer")
def submit_answer():
    interview_data = session.get("interview")
    answer = request.form.get("answer", "").strip()
    if not interview_data:
        return redirect(url_for("setup"))
    if not answer or len(answer) > 5000:
        flash("Please enter an answer before continuing.", "error")
        return redirect(url_for("interview"))

    index = interview_data["current_index"]
    question = interview_data["questions"][index]
    feedback = evaluate_answer(question, answer, interview_data["technology"], interview_data["level"])
    interview_data["answers"].append({"question": question, "answer": answer, "feedback": feedback})
    interview_data["current_index"] += 1
    session["interview"] = interview_data
    if interview_data["current_index"] >= len(interview_data["questions"]):
        return redirect(url_for("finish_interview"))
    return redirect(url_for("interview"))


@app.route("/finish-interview")
def finish_interview():
    interview_data = session.get("interview")
    if not interview_data or not interview_data["answers"]:
        return redirect(url_for("setup"))
    scores = [item["feedback"]["score"] for item in interview_data["answers"]]
    total = round(sum(scores) / len(scores))
    result = {
        "id": interview_data["id"], "student_name": interview_data["student_name"],
        "technology": interview_data["technology"], "level": interview_data["level"],
        "interview_type": interview_data["interview_type"], "score": total,
        "completed_at": timestamp(), "answers": interview_data["answers"],
    }
    append_record("results.json", result)
    update_record("interviews.json", interview_data["id"], {"completed_at": result["completed_at"], "score": total})
    session.pop("interview", None)
    return redirect(url_for("result", interview_id=result["id"]))


@app.get("/result/<interview_id>")
def result(interview_id):
    from services.json_service import find_record
    result_data = find_record("results.json", interview_id)
    if not result_data:
        flash("That result could not be found.", "error")
        return redirect(url_for("index"))
    return render_template("result.html", result=result_data)


@app.get("/api/result/<interview_id>")
def download_result(interview_id):
    from services.json_service import find_record
    result_data = find_record("results.json", interview_id)
    if not result_data:
        return jsonify({"error": "Result not found"}), 404
    return jsonify(result_data)


if __name__ == "__main__":
    app.run(debug=True)