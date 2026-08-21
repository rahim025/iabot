import os
import json
from flask import Flask, request, Response, render_template, redirect, url_for, jsonify, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from anthropic import Anthropic

from models import db, User, Conversation, Message
from config_models import AVAILABLE_MODELS, DEFAULT_MODEL

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-moi-en-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///chatbot.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Connecte-toi pour accéder à l'assistant."

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = (
    "Tu es Donia, un assistant IA utile, honnête et rapide, créée par Rahim Batchabi. "
    "Si on te demande qui t'a créée, réponds que c'est Rahim Batchabi. "
    "Réponds de façon claire et concise, en français par défaut sauf si l'utilisateur écrit dans une autre langue.\n\n"
    "Tu es particulièrement compétent en mathématiques, à tous les niveaux : primaire, collège, lycée "
    "(algèbre, géométrie, trigonométrie, fonctions, probabilités) et supérieur (analyse, algèbre linéaire, "
    "statistiques, calcul différentiel et intégral, etc.). Pour chaque exercice :\n"
    "- Donne toujours les étapes de résolution détaillées, pas seulement le résultat final\n"
    "- Utilise la notation LaTeX pour les formules : $...$ pour les formules en ligne, $$...$$ pour les formules isolées\n"
    "- Adapte le niveau d'explication à la question posée (vocabulaire plus simple pour un élève, plus technique pour un étudiant)\n"
    "- Vérifie ton résultat quand c'est possible\n\n"
    "Plus généralement, tu peux aider à résoudre toute sorte de problème (logique, code, rédaction, science, etc.) "
    "en structurant ta réponse étape par étape quand le sujet est complexe."
)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------- Authentification ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Nom d'utilisateur et mot de passe requis.")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur est déjà pris.")
            return redirect(url_for("register"))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Identifiants incorrects.")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------- Pages ----------

@app.route("/")
@login_required
def index():
    conversations = (
        Conversation.query.filter_by(user_id=current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return render_template(
        "index.html", conversations=conversations, models=AVAILABLE_MODELS,
        default_model=DEFAULT_MODEL,
    )


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


# ---------- API conversations ----------

@app.route("/api/conversations/<int:conv_id>/messages")
@login_required
def get_messages(conv_id):
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first_or_404()
    return jsonify([{"role": m.role, "content": m.content} for m in conv.messages])


@app.route("/api/conversations/new", methods=["POST"])
@login_required
def new_conversation():
    data = request.get_json(force=True) or {}
    model = data.get("model", DEFAULT_MODEL)
    conv = Conversation(user_id=current_user.id, model=model)
    db.session.add(conv)
    db.session.commit()
    return jsonify({"id": conv.id, "title": conv.title, "model": conv.model})


@app.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
@login_required
def delete_conversation(conv_id):
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first_or_404()
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"ok": True})


# ---------- Export PDF ----------

@app.route("/api/conversations/<int:conv_id>/export-pdf")
@login_required
def export_pdf(conv_id):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from xml.sax.saxutils import escape

    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first_or_404()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=16)
    user_style = ParagraphStyle(
        "UserStyle", parent=styles["Normal"], fontSize=11, textColor="#4F6EF7",
        spaceBefore=14, spaceAfter=4, alignment=TA_LEFT,
    )
    bot_style = ParagraphStyle(
        "BotStyle", parent=styles["Normal"], fontSize=11, spaceAfter=4, leading=16,
    )

    story = [Paragraph(escape(conv.title or "Conversation Donia"), title_style), Spacer(1, 12)]

    for msg in conv.messages:
        label = "Vous" if msg.role == "user" else "Donia"
        style = user_style if msg.role == "user" else bot_style
        text = escape(msg.content).replace("\n", "<br/>")
        story.append(Paragraph(f"<b>{label} :</b><br/>{text}", style))

    doc.build(story)
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{conv.title or "conversation"}.pdf"'},
    )


# ---------- Chat (streaming) ----------

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(force=True)
    user_message = (data.get("message") or "").strip()
    conv_id = data.get("conversation_id")

    if not user_message:
        return jsonify({"error": "Message vide"}), 400

    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first_or_404()

    # Sauvegarde le message utilisateur
    db.session.add(Message(conversation_id=conv.id, role="user", content=user_message))
    if conv.title == "Nouvelle conversation":
        conv.title = user_message[:50]
    db.session.commit()

    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    model = conv.model or DEFAULT_MODEL

    def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=history,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'chunk': text})}\n\n"

            with app.app_context():
                db.session.add(Message(conversation_id=conv.id, role="assistant", content=full_response))
                db.session.commit()
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
