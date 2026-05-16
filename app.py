from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = "bloodapp"
ADMIN_USERNAME = "Teja@1234"
ADMIN_PASSWORD = "Dharmateja@1234"


# ---------------- DATABASE CONNECTION ----------------

def connect_db():

    conn = sqlite3.connect("database.db")

    conn.row_factory = sqlite3.Row

    return conn


# ---------------- CREATE TABLES ----------------

def create_tables():

    conn = connect_db()

    cur = conn.cursor()

    # USERS TABLE

    cur.execute("""

    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT,

        age INTEGER,

        gender TEXT,

        blood TEXT,

        phone TEXT,

        pincode TEXT,

        password TEXT,

        status TEXT,

        last_donated TEXT,

        next_eligible_date TEXT,

        total_donations INTEGER

    )

    """)

    # REQUESTS TABLE

    cur.execute("""

    CREATE TABLE IF NOT EXISTS requests (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        requester_id INTEGER,

        blood TEXT,

        amount INTEGER,

        required_date TEXT,

        required_time TEXT,

        pincode TEXT,

        status TEXT

    )

    """)

    # ACCEPTED REQUESTS TABLE

    cur.execute("""

    CREATE TABLE IF NOT EXISTS accepted_requests (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        request_id INTEGER,

        donor_id INTEGER,

        donated_amount INTEGER,

        status TEXT,

        accepted_time TEXT

    )

    """)

    conn.commit()

    conn.close()


create_tables()


# ---------------- HOME ----------------

@app.route('/')
def home():

    return render_template('index.html')


# ---------------- REGISTER ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']

        age = int(request.form['age'])

        gender = request.form['gender']

        blood = request.form['blood']

        phone = request.form['phone']

        pincode = request.form['pincode']

        password = request.form['password']

        if age < 18 or age > 65:

            return "Age must be between 18 and 65"

        conn = connect_db()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO users (

            name,
            age,
            gender,
            blood,
            phone,
            pincode,
            password,
            status,
            total_donations

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            name,
            age,
            gender,
            blood,
            phone,
            pincode,
            password,
            "ACTIVE",
            0

        ))

        conn.commit()

        conn.close()

        return redirect('/login')

    return render_template('register.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        phone = request.form['phone']

        password = request.form['password']

        conn = connect_db()

        cur = conn.cursor()

        cur.execute("""

        SELECT * FROM users

        WHERE phone=? AND password=?

        """, (phone, password))

        user = cur.fetchone()

        conn.close()

        if user:

            session['user_id'] = user['id']

            return redirect('/profile')

        else:

            return "Invalid Login"

    return render_template('login.html')


# ---------------- PROFILE ----------------

@app.route('/profile')
def profile():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = connect_db()
    cur = conn.cursor()

    # USER DETAILS
    cur.execute("""

    SELECT * FROM users
    WHERE id=?

    """, (user_id,))

    user = cur.fetchone()

    # MY RAISED REQUESTS
    cur.execute("""

    SELECT * FROM requests
    WHERE requester_id=?
    ORDER BY id DESC

    """, (user_id,))

    requests_data = cur.fetchall()

    # WHO ACCEPTED MY REQUESTS
    cur.execute("""

    SELECT
        accepted_requests.*,
        users.name AS donor_name,
        users.phone AS donor_phone,
        requests.blood

    FROM accepted_requests

    JOIN users
    ON accepted_requests.donor_id = users.id

    JOIN requests
    ON accepted_requests.request_id = requests.id

    WHERE requests.requester_id=?

    ORDER BY accepted_requests.id DESC

    """, (user_id,))

    accepted_for_me = cur.fetchall()

    # REQUESTS I ACCEPTED
    cur.execute("""

    SELECT
        accepted_requests.*,
        users.name AS requester_name,
        requests.blood

    FROM accepted_requests

    JOIN requests
    ON accepted_requests.request_id = requests.id

    JOIN users
    ON requests.requester_id = users.id

    WHERE accepted_requests.donor_id=?

    ORDER BY accepted_requests.id DESC

    """, (user_id,))

    my_accepts = cur.fetchall()

    conn.close()

    return render_template(

        'profile.html',

        user=user,
        requests_data=requests_data,
        accepted_for_me=accepted_for_me,
        my_accepts=my_accepts

    )

# ---------------- RAISE REQUEST ----------------

@app.route('/request', methods=['GET', 'POST'])
def request_blood():

    if 'user_id' not in session:

        return redirect('/login')

    if request.method == 'POST':

        blood = request.form['blood']

        amount = request.form['amount']

        required_date = request.form['required_date']

        required_time = request.form['required_time']
        time_period = request.form['time_period']

        required_time = required_time + " " + time_period

        pincode = request.form['pincode']

        user_id = session['user_id']

        conn = connect_db()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO requests (

            requester_id,
            blood,
            amount,
            required_date,
            required_time,
            pincode,
            status

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)

        """, (

            user_id,
            blood,
            amount,
            required_date,
            required_time,
            pincode,
            "OPEN"

        ))

        conn.commit()

        conn.close()

        return redirect('/status')

    return render_template('request.html')


# ---------------- STATUS ----------------

@app.route('/status')
def status():

    if 'user_id' not in session:

        return redirect('/login')

    user_id = session['user_id']

    conn = connect_db()

    cur = conn.cursor()

    cur.execute("""

    SELECT * FROM requests

    WHERE requester_id=?

    ORDER BY id DESC

    """, (user_id,))

    requests_data = cur.fetchall()

    conn.close()

    return render_template(

        'status.html',

        requests_data=requests_data

    )



# ---------------- DONORS ----------------

@app.route('/donors/<int:request_id>')
def donors(request_id):

    if 'user_id' not in session:
        return redirect('/login')

    conn = connect_db()
    cur = conn.cursor()

    # GET REQUEST
    cur.execute("""

    SELECT * FROM requests
    WHERE id=?

    """, (request_id,))

    request_data = cur.fetchone()

    if not request_data:
        conn.close()
        return "Request Not Found"

    # SAFE PINCODE
    request_pincode = request_data['pincode'] if 'pincode' in request_data.keys() else ""

    # GET MATCHING DONORS
    cur.execute("""

    SELECT * FROM users

    WHERE blood=?
    AND status='ACTIVE'
    AND id != ?

    """, (

        request_data['blood'],
        request_data['requester_id']

    ))

    matched_donors = cur.fetchall()

    conn.close()

    return render_template(

        'donors.html',

        matched_donors=matched_donors,

        request_data=request_data

    )


# ---------------- ACCEPT REQUEST ----------------

@app.route('/accept/<int:request_id>/<int:donor_id>', methods=['POST'])
def accept(request_id, donor_id):

    donated_amount = request.form['donated_amount']

    conn = connect_db()

    cur = conn.cursor()

    cur.execute("""

    INSERT INTO accepted_requests (

        request_id,
        donor_id,
        donated_amount,
        status,
        accepted_time

    )

    VALUES (?, ?, ?, ?, ?)

    """, (

        request_id,
        donor_id,
        donated_amount,
        "ACCEPTED",
        str(datetime.now())

    ))

    conn.commit()

    conn.close()

    return redirect('/notifications')


# ---------------- COMPLETE REQUEST ----------------

@app.route('/complete_request/<int:request_id>')
def complete_request(request_id):

    conn = connect_db()
    cur = conn.cursor()

    # GET ACCEPTED DONORS
    cur.execute("""

    SELECT * FROM accepted_requests
    WHERE request_id=?

    """, (request_id,))

    accepted = cur.fetchall()

    for donor in accepted:

        donor_id = donor['donor_id']

        # GET USER
        cur.execute("""

        SELECT * FROM users
        WHERE id=?

        """, (donor_id,))

        user = cur.fetchone()

        donation_date = datetime.now()

        # FORMAT DATE
        formatted_last = donation_date.strftime("%d-%b-%Y")

        # COOLDOWN
        if user['gender'] == 'Female':
            next_date = donation_date + timedelta(days=120)
        else:
            next_date = donation_date + timedelta(days=90)

        formatted_next = next_date.strftime("%d-%b-%Y")

        # UPDATE USER
        cur.execute("""

        UPDATE users

        SET
            status=?,
            last_donated=?,
            next_eligible_date=?,
            total_donations=total_donations+1

        WHERE id=?

        """, (

            "INACTIVE",
            formatted_last,
            formatted_next,
            donor_id

        ))

        # UPDATE ACCEPTED STATUS
        cur.execute("""

        UPDATE accepted_requests

        SET status=?

        WHERE request_id=? AND donor_id=?

        """, (

            "COMPLETED",
            request_id,
            donor_id

        ))

    # COMPLETE REQUEST
    cur.execute("""

    UPDATE requests

    SET status='COMPLETED'

    WHERE id=?

    """, (request_id,))

    conn.commit()
    conn.close()

    return redirect('/status')


# ---------------- NOTIFICATIONS ----------------

@app.route('/notifications')
def notifications():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    conn = connect_db()
    cur = conn.cursor()

    # GET CURRENT USER
    cur.execute("""

    SELECT * FROM users
    WHERE id=?

    """, (user_id,))

    user = cur.fetchone()

    # GET MATCHING REQUESTS
    cur.execute("""

    SELECT
        requests.*,
        users.name AS requester_name,

        (
            SELECT status
            FROM accepted_requests
            WHERE accepted_requests.request_id = requests.id
            AND accepted_requests.donor_id = ?
            LIMIT 1
        ) AS accept_status

    FROM requests

    JOIN users
    ON requests.requester_id = users.id

    WHERE requests.blood=?
    AND requests.status='OPEN'
    AND requests.requester_id != ?

    ORDER BY requests.id DESC

    """, (

        user_id,
        user['blood'],
        user_id

    ))

    notifications = cur.fetchall()

    conn.close()

    return render_template(

        'notifications.html',

        notifications=notifications,
        user=user

    )


# ---------------- DELETE REQUEST ----------------

@app.route('/delete_request/<int:request_id>')
def delete_request(request_id):

    conn = connect_db()

    cur = conn.cursor()

    cur.execute("""

    DELETE FROM requests

    WHERE id=?

    """, (request_id,))

    conn.commit()

    conn.close()

    return redirect('/status')


# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

# ---------------- ADMIN LOGIN ----------------

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

            session['admin'] = True

            return redirect('/admin_dashboard')

        else:

            return "Invalid Admin Login"

    return render_template('admin.html')


# ---------------- ADMIN DASHBOARD ----------------

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect('/admin')

    conn = connect_db()
    cur = conn.cursor()

    # TOTAL USERS
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    # TOTAL REQUESTS
    cur.execute("SELECT COUNT(*) FROM requests")
    total_requests = cur.fetchone()[0]

    # COMPLETED REQUESTS
    cur.execute("""

    SELECT COUNT(*)
    FROM requests
    WHERE status='COMPLETED'

    """)

    completed_requests = cur.fetchone()[0]

    # ACTIVE DONORS
    cur.execute("""

    SELECT COUNT(*)
    FROM users
    WHERE status='ACTIVE'

    """)

    active_donors = cur.fetchone()[0]

    # ALL USERS
    cur.execute("""

    SELECT * FROM users
    ORDER BY id DESC

    """)

    users = cur.fetchall()

    # ALL REQUESTS
    cur.execute("""

    SELECT requests.*, users.name

    FROM requests

    JOIN users
    ON requests.requester_id = users.id

    ORDER BY requests.id DESC

    """)

    requests_data = cur.fetchall()

    conn.close()

    return render_template(

        'admin_dashboard.html',

        total_users=total_users,
        total_requests=total_requests,
        completed_requests=completed_requests,
        active_donors=active_donors,
        users=users,
        requests_data=requests_data

    )


# ---------------- ADMIN LOGOUT ----------------

@app.route('/admin_logout')
def admin_logout():

    session.pop('admin', None)

    return redirect('/admin')

@app.route('/reset_db')
def reset_db():
    import os

    if os.path.exists("database.db"):
        os.remove("database.db")

    db.create_all()

    return "Database Fully Reset Successfully"


# ---------------- RUN APP ----------------

if __name__ == '__main__':

    app.run(debug=True)