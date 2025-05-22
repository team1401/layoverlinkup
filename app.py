import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///layoverlinkup.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    home_airport = db.Column(db.String(10))
    contact_info = db.Column(db.String(120))
    itineraries = db.relationship('Itinerary', backref='user', lazy=True)
    memberships = db.relationship('GroupMembership', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    memberships = db.relationship('GroupMembership', backref='group', lazy=True)
    itinerary_shares = db.relationship('ItineraryShare', backref='group', lazy=True)

class GroupMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Itinerary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    airline = db.Column(db.String(100))
    flight_number = db.Column(db.String(20))
    departure_airport = db.Column(db.String(10))
    arrival_airport = db.Column(db.String(10))
    departure_time = db.Column(db.DateTime)
    arrival_time = db.Column(db.DateTime)
    layover_airport = db.Column(db.String(10))
    layover_start = db.Column(db.DateTime)
    layover_end = db.Column(db.DateTime)
    shares = db.relationship('ItineraryShare', backref='itinerary', lazy=True)

class ItineraryShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey('itinerary.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

# --- Helpers ---

def create_match(it1, it2):
    if not (it1.layover_airport and it2.layover_airport):
        return None
    if it1.layover_airport != it2.layover_airport:
        return None
    latest_start = max(it1.layover_start, it2.layover_start)
    earliest_end = min(it1.layover_end, it2.layover_end)
    if latest_start < earliest_end:
        duration = (earliest_end - latest_start).total_seconds() / 60
        return {
            'airport': it1.layover_airport,
            'start': latest_start,
            'end': earliest_end,
            'duration': duration,
            'it1': it1,
            'it2': it2,
        }
    return None

def find_matches(user_id):
    matches = []
    user = User.query.get(user_id)
    if not user:
        return matches
    # iterate through groups user belongs to
    for membership in user.memberships:
        group = membership.group
        # get itineraries shared with this group
        group_itineraries = [share.itinerary for share in group.itinerary_shares]
        for i, it1 in enumerate(group_itineraries):
            for it2 in group_itineraries[i+1:]:
                match = create_match(it1, it2)
                if match:
                    matches.append({'group': group, **match})
    return matches

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    itineraries = user.itineraries
    matches = find_matches(user.id)
    return render_template('dashboard.html', user=user, itineraries=itineraries, matches=matches)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.home_airport = request.form['home_airport']
        user.contact_info = request.form['contact_info']
        db.session.commit()
        flash('Profile updated')
    return render_template('profile.html', user=user)

@app.route('/itinerary/new', methods=['GET', 'POST'])
def new_itinerary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        it = Itinerary(
            user_id=session['user_id'],
            airline=request.form['airline'],
            flight_number=request.form['flight_number'],
            departure_airport=request.form['departure_airport'],
            arrival_airport=request.form['arrival_airport'],
            departure_time=datetime.fromisoformat(request.form['departure_time']),
            arrival_time=datetime.fromisoformat(request.form['arrival_time']),
            layover_airport=request.form['layover_airport'] or None,
            layover_start=datetime.fromisoformat(request.form['layover_start']) if request.form['layover_start'] else None,
            layover_end=datetime.fromisoformat(request.form['layover_end']) if request.form['layover_end'] else None,
        )
        db.session.add(it)
        db.session.commit()
        flash('Itinerary added')
        return redirect(url_for('dashboard'))
    return render_template('new_itinerary.html')

@app.route('/groups')
def groups():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    owned_groups = Group.query.filter_by(owner_id=user.id).all()
    member_groups = [m.group for m in user.memberships]
    return render_template('groups.html', owned_groups=owned_groups, member_groups=member_groups)

@app.route('/group/new', methods=['GET', 'POST'])
def new_group():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        group = Group(name=name, owner_id=session['user_id'])
        db.session.add(group)
        db.session.add(GroupMembership(group=group, user_id=session['user_id']))
        db.session.commit()
        return redirect(url_for('groups'))
    return render_template('new_group.html')

@app.route('/group/<int:group_id>', methods=['GET', 'POST'])
def group_detail(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    group = Group.query.get_or_404(group_id)
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.add(GroupMembership(group=group, user=user))
            db.session.commit()
        else:
            flash('User not found')
    itineraries = [share.itinerary for share in group.itinerary_shares]
    return render_template('group_detail.html', group=group, itineraries=itineraries)

@app.route('/share_itinerary/<int:itinerary_id>', methods=['GET', 'POST'])
def share_itinerary(itinerary_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    if itinerary.user_id != session['user_id']:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        group_id = int(request.form['group_id'])
        db.session.add(ItineraryShare(itinerary_id=itinerary_id, group_id=group_id))
        db.session.commit()
        return redirect(url_for('dashboard'))
    groups = [m.group for m in User.query.get(session['user_id']).memberships]
    return render_template('share_itinerary.html', itinerary=itinerary, groups=groups)

@app.route('/initdb')
def initdb():
    db.create_all()
    return 'Database initialized'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
