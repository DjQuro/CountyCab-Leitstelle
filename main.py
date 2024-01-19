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
        return redirect(url_for('stechuhr'))


@app.route('/stechuhr', methods=['GET', 'POST'])
@login_required
def stechuhr():
    with app.app_context():
        stempel_events = StempelEvent.query.filter_by(user=current_user).all()

        form = RegistrationForm()  # Füge diese Zeile hinzu

        if request.method == 'POST':
            stempel_event = StempelEvent(event_type='Stempeln', user=current_user)
            db.session.add(stempel_event)
            db.session.commit()
            flash('Erfolgreich gestempelt!', 'success')
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

    # Wenn es keine Stempelereignisse gibt, setze den Wert auf 0
    if not stempel_events:
        return 0

    total_hours = sum((event.timestamp - stempel_events[index - 1].timestamp).total_seconds() / 3600
                      for index, event in enumerate(stempel_events) if index > 0 and event.event_type == 'Stempeln')

    return total_hours


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
