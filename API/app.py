from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from datetime import datetime
from pathlib import Path
import json
import os
import re
import hashlib
from dotenv import load_dotenv
from werkzeug.utils import secure_filename


# Load environment variables from repo root .env if present
repo_root = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=repo_root / '.env')


app = Flask(__name__)
CORS(app)

# Ensure Database folder exists and use a repo-relative SQLite file
db_dir = repo_root / 'Database'
db_dir.mkdir(parents=True, exist_ok=True)
db_path = db_dir / 'complaints.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path.as_posix()}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Uploads directory (local prototype storage)
UPLOAD_DIR = repo_root / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    train_number = db.Column(db.String(64), nullable=True)
    coach = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(128), nullable=True)
    subcategory = db.Column(db.String(128), nullable=True)
    severity = db.Column(db.String(32), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    department = db.Column(db.String(128), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)  # JSON string
    status = db.Column(db.String(64), default='Pending')
    group_key = db.Column(db.String(128), nullable=True, index=True)
    occurrences = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'train_number': self.train_number,
            'coach': self.coach,
            'description': self.description,
            'image_path': self.image_path,
            'category': self.category,
            'subcategory': self.subcategory,
            'severity': self.severity,
            'summary': self.summary,
            'department': self.department,
            'confidence': self.confidence,
            'extracted_text': json.loads(self.extracted_text) if self.extracted_text else [],
            'status': self.status,
            'group_key': self.group_key,
            'occurrences': self.occurrences,
        }


def analyze_payload(description, train_number=None, coach=None, image_path=None):
    """
    Placeholder AI analysis. Replace with Gemini calls later.
    Returns a dict matching the recommended structured AI output.
    """
    # Very small heuristic stub: detect keywords
    text = (description or '').lower()
    if 'ac' in text or 'air' in text or 'cool' in text:
        category = 'AC_ELECTRICAL'
        subcategory = 'AC_NOT_WORKING'
        severity = 'HIGH'
        department = 'Electrical'
    elif 'clean' in text or 'toilet' in text or 'water' in text:
        category = 'CLEANLINESS'
        subcategory = 'GENERAL_CLEANLINESS'
        severity = 'MEDIUM'
        department = 'Housekeeping'
    else:
        category = 'OTHER'
        subcategory = 'UNSPECIFIED'
        severity = 'LOW'
        department = 'General'

    summary = description.strip()[:400]
    confidence = 0.65
    extracted_text = []

    return {
        'category': category,
        'subcategory': subcategory,
        'severity': severity,
        'summary': summary,
        'coach': coach,
        'detected_objects': [],
        'extracted_text': extracted_text,
        'missing_information': [],
        'confidence': confidence,
        'department': department,
    }


def compute_group_key(description: str, train_number: str | None, coach: str | None, category: str | None, subcategory: str | None) -> str:
    """Create a deterministic short fingerprint for grouping similar complaints.

    This normalizes description, appends train/coach/category, and returns a
    sha256 hex digest (shortened to 32 chars for readability).
    """
    parts = []
    if description:
        # normalize: lowercase, remove non-alphanumeric, collapse whitespace
        text = description.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        parts.append(text)
    if train_number:
        parts.append(str(train_number).strip().lower())
    if coach:
        parts.append(str(coach).strip().lower())
    if category:
        parts.append(str(category).strip().lower())
    if subcategory:
        parts.append(str(subcategory).strip().lower())

    key_material = "|".join(parts)
    digest = hashlib.sha256(key_material.encode('utf-8')).hexdigest()
    return digest[:32]


def ensure_db():
    db.create_all()
    # create index for group_key if it doesn't exist (improves recurring-group queries)
    try:
        db.session.execute(text('CREATE INDEX IF NOT EXISTS ix_complaint_group_key ON complaint (group_key);'))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route('/api/complaints', methods=['POST'])
def create_complaint():
    # Support both JSON and multipart/form-data (for image uploads)
    data = {}
    if request.is_json:
        data = request.get_json() or {}
        image_file = None
    else:
        # form data
        data = request.form.to_dict()
        image_file = request.files.get('image')

    description = data.get('description')
    if not description:
        return jsonify({'error': 'description is required'}), 400

    train_number = data.get('train_number')
    coach = data.get('coach')
    image_path = data.get('image_path')

    # handle file upload if provided
    if image_file:
        filename = f"{int(datetime.utcnow().timestamp())}_{secure_filename(image_file.filename)}"
        saved_path = UPLOAD_DIR / filename
        image_file.save(saved_path)
        # store relative path that frontend can request from /uploads/<filename>
        image_path = f"uploads/{filename}"

    ai = analyze_payload(description, train_number, coach, image_path)

    # compute deterministic group key to identify recurring/duplicate complaints
    group_key = compute_group_key(
        description,
        train_number,
        coach,
        ai.get('category'),
        ai.get('subcategory'),
    )

    c = Complaint(
        train_number=train_number,
        coach=coach,
        description=description,
        image_path=image_path,
        category=ai.get('category'),
        subcategory=ai.get('subcategory'),
        severity=ai.get('severity'),
        summary=ai.get('summary'),
        department=ai.get('department'),
        confidence=ai.get('confidence'),
        extracted_text=json.dumps(ai.get('extracted_text') or []),
        group_key=group_key,
        occurrences=1,
    )
    db.session.add(c)
    db.session.commit()

    # update occurrences count for this group across existing rows
    count = Complaint.query.filter_by(group_key=group_key).count()
    if count > 1:
        Complaint.query.filter_by(group_key=group_key).update({'occurrences': count})
        db.session.commit()

    return jsonify(c.to_dict()), 201


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve uploaded files from the local uploads directory (prototype only)
    return send_from_directory(UPLOAD_DIR.as_posix(), filename)


@app.route('/api/complaints', methods=['GET'])
def list_complaints():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return jsonify([c.to_dict() for c in complaints])


@app.route('/api/complaints/<int:cid>', methods=['GET'])
def get_complaint(cid):
    c = Complaint.query.get(cid)
    if not c:
        return jsonify({'error': 'not found'}), 404
    return jsonify(c.to_dict())


@app.route('/api/complaints/<int:cid>', methods=['PATCH'])
def patch_complaint(cid):
    c = Complaint.query.get(cid)
    if not c:
        return jsonify({'error': 'not found'}), 404
    data = request.get_json() or {}
    allowed = ['status', 'department', 'category', 'subcategory', 'severity', 'summary']
    changed = False
    for k in allowed:
        if k in data:
            setattr(c, k, data[k])
            changed = True
    if changed:
        db.session.commit()
    return jsonify(c.to_dict())


if __name__ == '__main__':
    # ensure DB and indexes exist before serving
    with app.app_context():
        ensure_db()
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
