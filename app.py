from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this_in_production'
app.config['USERS_FILE'] = 'users.json'
app.config['POLLS_FILE'] = 'polls.json'
app.config['VOTES_FILE'] = 'votes.json'

# Load data from JSON files
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

# Save data to JSON files
def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize data
users = load_data(app.config['USERS_FILE'])
polls = load_data(app.config['POLLS_FILE'])
votes = load_data(app.config['VOTES_FILE'])

# Add some sample data if empty
if not polls:
    polls = {
        "1": {
            "question": "Choose our next president?",
            "options": {
                "Imran Khan": 0,
                "Nawaz Sharif": 0,
                "Maryam Nawaz": 0
            },
            "created_at": "2025-08-27 23:13:17"
        }
    }
    save_data(polls, app.config['POLLS_FILE'])

@app.route("/")
def home():
    return render_template("home.html", polls=polls, user=session.get('user'))

@app.route("/about")
def about():
    return render_template("about.html", user=session.get('user'))

@app.route("/contact")
def contact():
    return render_template("contact.html", user=session.get('user'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        age = request.form.get("age")
        gender = request.form.get("gender")
        city = request.form.get("city")
        
        if not all([name, email, password, age, gender, city]):
            flash("Please fill out all fields!", "warning")
            return render_template("register.html")
        
        if email in users:
            flash("Email already registered!", "danger")
            return render_template("register.html")
        
        users[email] = {
            "name": name,
            "password": generate_password_hash(password),
            "age": age,
            "gender": gender,
            "city": city,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        save_data(users, app.config['USERS_FILE'])
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html", user=session.get('user'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if email in users and check_password_hash(users[email]["password"], password):
            session['user'] = {
                "email": email,
                "name": users[email]["name"],
                "age": users[email]["age"],
                "gender": users[email]["gender"],
                "city": users[email]["city"]
            }
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password!", "danger")
    
    return render_template("login.html", user=session.get('user'))

@app.route("/logout")
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/vote/<poll_id>", methods=["GET", "POST"])
def vote(poll_id):
    if 'user' not in session:
        flash("Please login to vote!", "warning")
        return redirect(url_for("login"))
    
    if poll_id not in polls:
        flash("Poll not found!", "danger")
        return redirect(url_for("home"))
    
    # Check if user already voted in this poll
    user_email = session['user']['email']
    if poll_id in votes and user_email in votes[poll_id]:
        flash("You have already voted in this poll!", "warning")
        return redirect(url_for("results", poll_id=poll_id))
    
    if request.method == "POST":
        selected_option = request.form.get("option")
        if selected_option and selected_option in polls[poll_id]["options"]:
            # Record the vote
            polls[poll_id]["options"][selected_option] += 1
            
            # Record who voted for what
            if poll_id not in votes:
                votes[poll_id] = {}
            
            votes[poll_id][user_email] = {
                "option": selected_option,
                "voted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_info": {
                    "name": session['user']['name'],
                    "age": session['user']['age'],
                    "gender": session['user']['gender'],
                    "city": session['user']['city']
                }
            }
            
            save_data(polls, app.config['POLLS_FILE'])
            save_data(votes, app.config['VOTES_FILE'])
            
            flash("Your vote has been recorded!", "success")
            return redirect(url_for("results", poll_id=poll_id))
        else:
            flash("Please select an option to vote!", "warning")
    
    return render_template("vote.html", poll=polls[poll_id], poll_id=poll_id, user=session.get('user'))

@app.route("/results/<poll_id>")
def results(poll_id):
    if poll_id not in polls:
        flash("Poll not found!", "danger")
        return redirect(url_for("home"))
    
    # Get voting details for this poll
    poll_votes = votes.get(poll_id, {})
    return render_template("results.html", poll=polls[poll_id], poll_id=poll_id, 
                          votes=poll_votes, user=session.get('user'))

@app.route("/voter_details/<poll_id>")
def voter_details(poll_id):
    if 'user' not in session:
        flash("Please login to view voter details!", "warning")
        return redirect(url_for("login"))
    
    if poll_id not in polls:
        flash("Poll not found!", "danger")
        return redirect(url_for("home"))
    
    # Get voting details for this poll
    poll_votes = votes.get(poll_id, {})
    return render_template("voter_details.html", poll=polls[poll_id], poll_id=poll_id, 
                          votes=poll_votes, user=session.get('user'))

@app.route("/create_poll", methods=["GET", "POST"])
def create_poll():
    if 'user' not in session:
        flash("Please login to create a poll!", "warning")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        question = request.form.get("question")
        options = request.form.get("options")
        
        if question and options:
            # Split options by comma and create a new poll
            options_list = [option.strip() for option in options.split(",") if option.strip()]
            
            if len(options_list) < 2:
                flash("Please provide at least 2 options!", "warning")
                return render_template("create_poll.html", user=session.get('user'))
            
            # Generate a unique ID for the poll
            new_poll_id = str(int(datetime.now().timestamp()))
            
            polls[new_poll_id] = {
                "question": question,
                "options": {option: 0 for option in options_list},
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": session['user']['email']
            }
            
            save_data(polls, app.config['POLLS_FILE'])
            flash("Poll created successfully!", "success")
            return redirect(url_for("home"))
        else:
            flash("Please fill out all fields!", "warning")
    
    return render_template("create_poll.html", user=session.get('user'))

@app.route("/delete_poll/<poll_id>")
def delete_poll(poll_id):
    if 'user' not in session:
        flash("Please login to delete a poll!", "warning")
        return redirect(url_for("login"))
    
    if poll_id in polls:
        # Check if user created this poll or is admin
        if polls[poll_id].get('created_by') == session['user']['email']:
            del polls[poll_id]
            # Also remove votes for this poll
            if poll_id in votes:
                del votes[poll_id]
            
            save_data(polls, app.config['POLLS_FILE'])
            save_data(votes, app.config['VOTES_FILE'])
            
            flash("Poll deleted successfully!", "success")
        else:
            flash("You can only delete polls that you created!", "danger")
    else:
        flash("Poll not found!", "danger")
    
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)