from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from sqlalchemy import extract
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein_geheimer_schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stechuhr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class RegistrationForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    confirm_password = PasswordField('Passwort bestätigen', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('Vorname', validators=[DataRequired()])
    last_name = StringField('Nachname', validators=[DataRequired()])
    submit = SubmitField('Registrieren')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)

class StempelEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('stempel_events', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    with app.app_context():
        # Holen Sie alle Benutzer und ihre letzten Stempelereignisse
        users = User.query.all()
        user_statuses = []

        for user in users:
            last_stempel_event = StempelEvent.query.filter_by(user=user).order_by(StempelEvent.timestamp.desc()).first()

            if last_stempel_event:
                # Benutzer hat Stempelereignisse
                if last_stempel_event.event_type == 'Stempeln':
                    user_status = {'user': user, 'status': 'Eingestempelt'}
                elif last_stempel_event.event_type == 'Ausstempeln':
                    user_status = {'user': user, 'status': 'Ausgestempelt'}
            else:
                # Benutzer hat keine Stempelereignisse
                user_status = {'user': user, 'status': 'Ausgestempelt'}

            user_statuses.append(user_status)

        return render_template('home.html', user_statuses=user_statuses)


@app.route('/login')
def login():
    with app.app_context():
        user = User.query.first()
        if user:
            login_user(user)
            flash('Erfolgreich eingeloggt!', 'success')
            return redirect(url_for('stechuhr'))
        else:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    with app.app_context():
        logout_user()
        flash('Erfolgreich ausgeloggt!', 'success')
        return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    with app.app_context():
        form = RegistrationForm()
        if request.method == 'POST' and form.validate_on_submit():
            new_user = User(
                username=form.username.data,
                password=form.password.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Erfolgreich registriert! Jetzt kannst du dich einloggen.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html', form=form)

@app.route('/stechuhr', methods=['GET', 'POST'])
@login_required
def stechuhr():
    with app.app_context():
        stempel_events = StempelEvent.query.filter_by(user=current_user).all()

        form = RegistrationForm()

        if request.method == 'POST':
            if 'einstempeln' in request.form:
                stempel_event = StempelEvent(event_type='Einstempeln', user=current_user)
                db.session.add(stempel_event)
                db.session.commit()
                flash('Erfolgreich eingestempelt!', 'success')
            elif 'ausstempeln' in request.form:
                stempel_event = StempelEvent(event_type='Ausstempeln', user=current_user)
                db.session.add(stempel_event)
                db.session.commit()
                flash('Erfolgreich ausgestempelt!', 'success')

            return redirect(url_for('stechuhr'))

        total_hours_this_week = get_total_hours_this_week(current_user)

        return render_template('stechuhr.html', stempel_events=stempel_events,
                               total_hours_this_week=total_hours_this_week,
                               get_total_hours_this_week=get_total_hours_this_week, form=form)


def get_total_hours_this_week(user):
    current_week = datetime.now().isocalendar()[1]
    stempel_events = StempelEvent.query.filter(
        extract('week', StempelEvent.timestamp) == current_week,
        StempelEvent.user == user
    ).all()

    if not stempel_events:
        return 0

    total_hours = sum((event.timestamp - stempel_events[index - 1].timestamp).total_seconds() / 3600
                      for index, event in enumerate(stempel_events) if index > 0 and event.event_type == 'Stempeln')

    return total_hours

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
