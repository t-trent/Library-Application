# Library Database Application
# Mini Project - CMPT354 - Database Systems I
# Group 52 (Trent Carlson, Harry Kim)

from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

DATABASE = 'library.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)  # Waits up to 10 seconds if the database is locked
    conn.row_factory = sqlite3.Row
    return conn

# Home page: a menu for the operations
@app.route('/')
def index():
    return render_template('index.html')

# Find an item in the library
@app.route('/find_item', methods=['GET'])
def find_item():
    # Define allowed item types
    item_types = ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game']
    
    # Get parameters from the URL query string
    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'title')  # default sort by title
    sort_order = request.args.get('sort_order', 'asc')  # default ascending
    filter_type = request.args.get('filter_type', '')
    
    # Map the sort_by values to actual database columns safely
    order_column = {
        'id': 'item_id',
        'title': 'title',
        'type': 'item_type'
    }.get(sort_by, 'title')
    
    # Build the filtering clause and base parameters for the query
    filter_clause = ""
    params = ['%' + search_term + '%']
    if filter_type:
        filter_clause = " AND item_type = ?"
        params.append(filter_type)
    
    # Query for Available Items:
    # Items whose item_id does not appear in a Borrowings row with return_date IS NULL.
    available_query = f"""
        SELECT * FROM Items
        WHERE title LIKE ? {filter_clause}
          AND item_id NOT IN (
              SELECT item_id FROM Borrowings WHERE return_date IS NULL
          )
        ORDER BY {order_column} {sort_order.upper()}
    """
    
    # Query for Unavailable Items:
    # Items that are currently borrowed (return_date IS NULL)
    unavailable_query = f"""
        SELECT DISTINCT Items.* FROM Items
        JOIN Borrowings ON Items.item_id = Borrowings.item_id
        WHERE title LIKE ? {filter_clause}
          AND Borrowings.return_date IS NULL
        ORDER BY {order_column} {sort_order.upper()}
    """
    
    conn = get_db_connection()
    available_items = conn.execute(available_query, params).fetchall()
    unavailable_items = conn.execute(unavailable_query, params).fetchall()
    conn.close()
    
    return render_template('find_item.html',
                           available_items=available_items,
                           unavailable_items=unavailable_items,
                           search_term=search_term,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           filter_type=filter_type,
                           item_types=item_types)

# Borrow an item from the library
@app.route('/borrow_item', methods=['GET', 'POST'])
def borrow_item():
    conn = get_db_connection()
    success_message = None  # This will hold our success message if set
    error_message = None # This will hold our error message if set
    
    if request.method == 'POST':
        item_id = request.form['item_id']
        person_id = request.form['person_id']
        personnel_id = request.form['personnel_id']
        borrow_date_str = request.form['borrow_date']
        
        # Parse the borrow date and compute the due date (14 days later)
        try:
            borrow_date = datetime.strptime(borrow_date_str, '%Y-%m-%d')
            due_date = borrow_date + timedelta(days=14)
            due_date_str = due_date.strftime('%Y-%m-%d')
        except ValueError:
            error_message = 'Invalid borrow date format. Please use YYYY-MM-DD.'
        
        if error_message is None:
            try:
                conn.execute('''
                    INSERT INTO Borrowings (item_id, person_id, personnel_id, borrow_date, due_date, return_date)
                    VALUES (?, ?, ?, ?, ?, NULL)
                ''', (item_id, person_id, personnel_id, borrow_date_str, due_date_str))
                conn.commit()
                success_message = (f"Item [ID {item_id}] borrowed successfully by Person [ID {person_id}]. "
                                   f"Personnel [ID: {personnel_id}] assisted. Due date is {due_date_str}.")
            except Exception as e:
                # Roll back any changes and set an error message
                conn.rollback()
                error_message = f"An error occurred. Ensure the item is available and the person ID is valid."
    
    # Whether GET or after POST, load the dropdown options:
    available_items = conn.execute("""
        SELECT * FROM Items
        WHERE item_id NOT IN (
            SELECT item_id FROM Borrowings WHERE return_date IS NULL
        )
        ORDER BY title
    """).fetchall()
    
    people = conn.execute("SELECT person_id, name FROM People ORDER BY name").fetchall()
    
    librarians = conn.execute("""
        SELECT P.person_id, P.name, Pe.role
        FROM Personnel Pe
        JOIN People P ON Pe.person_id = P.person_id
        ORDER BY P.name
    """).fetchall()
    
    conn.close()
    
    return render_template('borrow_item.html',
                           available_items=available_items,
                           people=people,
                           librarians=librarians,
                           success_message=success_message,
                           error_message=error_message)



# Return a borrowed item
@app.route('/return_item', methods=['GET', 'POST'])
def return_item():
    success_message = None
    error_message = None
    conn = get_db_connection()
    
    if request.method == 'POST':
        borrowing_id = request.form['borrowing_id']
        return_date = request.form['return_date']
        
        try:
            # Update the Borrowings record to mark it as returned
            conn.execute('UPDATE Borrowings SET return_date = ? WHERE borrowing_id = ?', (return_date, borrowing_id))
            conn.commit()
            success_message = f"Borrowing ID {borrowing_id} was successfully returned on {return_date}."
        except Exception as e:
            conn.rollback()
            error_message = f"An error occurred while returning the item. Ensure the return date is on or after the borrow date."
    
    # Query active borrowings (where return_date is NULL)
    active_borrowings = conn.execute("SELECT * FROM Borrowings WHERE return_date IS NULL").fetchall()
    conn.close()
    
    return render_template('return_item.html', active_borrowings=active_borrowings, success_message=success_message, error_message=error_message)


# Donate an item to the library
@app.route('/donate_item', methods=['GET', 'POST'])
def donate_item():
    success_message = None
    error_message = None
    # Define the allowed item types
    item_types = ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game']
    
    if request.method == 'POST':
        item_type = request.form['item_type']
        title = request.form['title']
        
        conn = get_db_connection()
        try:
            # Get the current highest candidate_item_id from the FutureItems table
            cursor = conn.execute("SELECT MAX(candidate_item_id) FROM FutureItems")
            max_id_row = cursor.fetchone()
            max_id = max_id_row[0] if max_id_row[0] is not None else 0
            new_candidate_item_id = max_id + 1

            # Insert the new donated item into the FutureItems table
            conn.execute(
                'INSERT INTO FutureItems (candidate_item_id, item_type, title) VALUES (?, ?, ?)',
                (new_candidate_item_id, item_type, title)
            )
            conn.commit()
            success_message = f"Future item '{title}' [Candidate ID: {new_candidate_item_id}] of type '{item_type}' donated successfully. We may add this to the library after review."
        except Exception as e:
            conn.rollback()
            error_message = f"An error occurred while donating the item. Ensure the item type is valid."
        finally:
            conn.close()
    
    return render_template('donate_item.html', item_types=item_types, success_message=success_message, error_message=error_message)


# Find an event in the library
@app.route('/find_event', methods=['GET'])
def find_event():
    # Get parameters from query string (with defaults)
    search_term     = request.args.get('search_term', '')
    filter_audience = request.args.get('filter_audience', '')
    filter_room     = request.args.get('filter_room', '')
    filter_attendee = request.args.get('filter_attendee', '')
    sort_by         = request.args.get('sort_by', 'date')   # default sort by date
    sort_order      = request.args.get('sort_order', 'asc')   # default ascending

    # Get dropdown options from the database
    conn = get_db_connection()
    audience_types = conn.execute("SELECT DISTINCT audience_type FROM Audiences ORDER BY audience_type").fetchall()
    social_rooms = conn.execute("SELECT DISTINCT room_name FROM SocialRooms ORDER BY room_name").fetchall()
    people_dropdown = conn.execute("SELECT person_id, name FROM People ORDER BY name").fetchall()

    # Build the base query
    query = """
        SELECT 
            E.event_id,
            E.name,
            E.event_date,
            E.description,
            SR.room_name,
            GROUP_CONCAT(DISTINCT A.audience_type) AS audiences,
            GROUP_CONCAT(DISTINCT Att.name) AS attendees
        FROM Events E
        LEFT JOIN SocialRooms SR ON E.room_id = SR.room_id
        LEFT JOIN EventAudiences EA ON E.event_id = EA.event_id
        LEFT JOIN Audiences A ON EA.audience_id = A.audience_id
        LEFT JOIN Attending Atnd ON E.event_id = Atnd.event_id
        LEFT JOIN People Att ON Atnd.person_id = Att.person_id
        WHERE E.name LIKE ?
    """
    params = ['%' + search_term + '%']

    # Apply filters if provided
    if filter_room:
        query += " AND SR.room_name = ?"
        params.append(filter_room)
    if filter_audience:
        query += " AND A.audience_type = ?"
        params.append(filter_audience)
    if filter_attendee:
        query += " AND EXISTS (SELECT 1 FROM Attending Atnd2 WHERE Atnd2.event_id = E.event_id AND Atnd2.person_id = ?)"
        params.append(filter_attendee)

    query += " GROUP BY E.event_id, E.name, E.event_date, E.description, SR.room_name "

    # Map sort_by options to database columns
    sort_columns = {
        'id': 'E.event_id',
        'name': 'E.name',
        'date': 'E.event_date',
        'room': 'SR.room_name'
    }
    order_column = sort_columns.get(sort_by, 'E.event_date')
    order_clause = f" ORDER BY {order_column} {sort_order.upper()}"

    full_query = query + order_clause
    events = conn.execute(full_query, params).fetchall()
    conn.close()

    return render_template(
        'find_event.html',
        events=events,
        search_term=search_term,
        filter_audience=filter_audience,
        filter_room=filter_room,
        filter_attendee=filter_attendee,
        sort_by=sort_by,
        sort_order=sort_order,
        audience_types=audience_types,
        social_rooms=social_rooms,
        people_dropdown=people_dropdown
    )

# Register for an event in the library
@app.route('/register_event', methods=['GET', 'POST'])
def register_event():
    success_message = None
    error_message = None
    conn = get_db_connection()
    
    # Query events and people to populate dropdown menus
    events = conn.execute("SELECT event_id, name FROM Events ORDER BY name").fetchall()
    people = conn.execute("SELECT person_id, name FROM People ORDER BY name").fetchall()
    
    if request.method == 'POST':
        event_id = request.form['event_id']
        person_id = request.form['person_id']
        
        try:
            # Insert registration into Attending table
            conn.execute('INSERT INTO Attending (event_id, person_id) VALUES (?, ?)', (event_id, person_id))
            conn.commit()
            success_message = f"Registered person [ID: {person_id}] for event [ID: {event_id}] successfully."
        except Exception as e:
            conn.rollback()
            error_message = f"An error occurred while registering for the event. Ensure you are not already registered."
    
    conn.close()
    return render_template('register_event.html', events=events, people=people,
                           success_message=success_message, error_message=error_message)

# Volunteer for the library
@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    message = None
    conn = get_db_connection()
    
    # Get all people who are NOT already in the Personnel table
    people = conn.execute(
        "SELECT person_id, name FROM People WHERE person_id NOT IN (SELECT person_id FROM Personnel) ORDER BY name"
    ).fetchall()
    
    if request.method == 'POST':
        person_id = request.form['person_id']
        # Automatically assign the role "Volunteer"
        role = "Volunteer"
        conn.execute('INSERT INTO Personnel (person_id, role) VALUES (?, ?)', (person_id, role))
        conn.commit()
        message = f"Volunteer registration successful. Person ID {person_id} have been assigned the role 'Volunteer'."
    
    conn.close()
    return render_template('volunteer.html', people=people, message=message)


# Ask for help from a librarian
@app.route('/ask_help', methods=['GET', 'POST'])
def ask_help():
    success_message = None
    conn = get_db_connection()
    
    # Fetch eligible people: those in People not already in Personnel.
    people = conn.execute(
        "SELECT person_id, name FROM People WHERE person_id NOT IN (SELECT person_id FROM Personnel) ORDER BY name"
    ).fetchall()
    
    if request.method == 'POST':
        person_id = request.form['person_id']
        question = request.form['question']
        
        # Get next request_id from HelpRequests table
        cursor = conn.execute("SELECT MAX(request_id) FROM HelpRequests")
        max_id_row = cursor.fetchone()
        max_id = max_id_row[0] if max_id_row[0] is not None else 0
        new_request_id = max_id + 1
        
        # Insert the new help request
        conn.execute('''
            INSERT INTO HelpRequests (request_id, status, message, person_id)
            VALUES (?, ?, ?, ?)
        ''', (new_request_id, 0, question, person_id))
        conn.commit()
        
        success_message = 'Your help request has been received and is pending review.'
    
    conn.close()
    return render_template('ask_help.html', people=people, success_message=success_message)


# View all currently borrowed items
@app.route('/view_borrowings', methods=['GET'])
def view_borrowings():
    conn = get_db_connection()

    # Get sorting and filtering parameters from the query string
    sort_by = request.args.get('sort_by', 'title') 
    sort_order = request.args.get('sort_order', 'asc')
    filter_status = request.args.get('filter_status', 'all')
    filter_fines = request.args.get('filter_fines', 'all')  # New fine filter parameter

    allowed_filters = ['all', 'returned', 'not_returned']
    if filter_status not in allowed_filters:
        filter_status = 'all'

    # Define the sortable columns and their display names
    sortable_columns_db = {
        'borrowing_id': 'B.borrowing_id',
        'item_id': 'B.item_id',
        'title': 'I.title',
        'item_type': 'I.item_type',
        'person_id': 'B.person_id',
        'borrower_name': 'P.name',
        'borrow_date': 'B.borrow_date',
        'fine_amount': 'total_fine_amount'
    }
    sortable_options_display = {
        'borrowing_id': 'Borrowing ID',
        'item_id': 'Item ID',
        'title': 'Title',
        'item_type': 'Type',
        'person_id': 'Borrower ID',
        'borrower_name': 'Borrower Name',
        'borrow_date': 'Borrow Date',
        'fine_amount': 'Total Fine Amount'
    }

    if sort_by not in sortable_columns_db:
        sort_by = 'title'
    if sort_order.lower() not in ['asc', 'desc']:
        sort_order = 'asc'
    sql_sort_column = sortable_columns_db[sort_by]

    # Build the base query with additional aggregates for fines
    base_query = """
        SELECT 
            B.borrowing_id, 
            B.item_id, 
            I.title, 
            I.item_type, 
            B.person_id, 
            P.name AS borrower_name, 
            B.borrow_date, 
            B.due_date, 
            COALESCE(B.return_date, 'Not Returned') AS return_date_display,
            B.return_date,
            COALESCE(SUM(F.amount), 0) AS total_fine_amount,
            SUM(CASE WHEN F.paid_status = '0' THEN F.amount ELSE 0 END) AS total_unpaid_fines,
            SUM(CASE WHEN F.paid_status = '1' THEN F.amount ELSE 0 END) AS total_paid_fines,
            GROUP_CONCAT(F.fine_id || '|' || F.amount || '|' || F.paid_status) AS fines,
            personnel_subquery.personnel_name
        FROM Borrowings B
        JOIN Items I ON B.item_id = I.item_id
        JOIN People P ON B.person_id = P.person_id
        LEFT JOIN Fines F ON B.borrowing_id = F.borrowing_id
        LEFT JOIN (
        SELECT person_id, name AS personnel_name
        FROM People
    ) AS personnel_subquery ON B.personnel_id = personnel_subquery.person_id
    """
    
    # Build the WHERE clause for return status filtering
    where_clause = ""
    if filter_status == 'returned':
        where_clause = "WHERE B.return_date IS NOT NULL"
    elif filter_status == 'not_returned':
        where_clause = "WHERE B.return_date IS NULL"
    
    # Grouping clause (must include all non-aggregated columns)
    group_clause = """
        GROUP BY 
            B.borrowing_id, B.item_id, I.title, I.item_type, 
            B.person_id, P.name, B.borrow_date, B.due_date, B.return_date
    """
    
    # Build a HAVING clause for fines filtering
    having_clause = "HAVING 1=1"
    if filter_fines == 'with_fines':
        having_clause += " AND total_fine_amount > 0"
    elif filter_fines == 'unpaid_fines':
        having_clause += " AND total_unpaid_fines > 0"
    elif filter_fines == 'paid_fines':
        having_clause += " AND total_paid_fines > 0"
    
    # Build the ORDER BY clause based on sort parameters
    order_clause = f"ORDER BY {sql_sort_column} {sort_order.upper()}"

    # Combine all clauses into one query
    query = f"{base_query} {where_clause} {group_clause} {having_clause} {order_clause}"
    
    borrowings = conn.execute(query).fetchall()
    conn.close()

    return render_template(
        'view_borrowings.html', 
        borrowings=borrowings,
        sortable_options=sortable_options_display,
        current_sort_by=sort_by,
        current_sort_order=sort_order,
        current_filter_status=filter_status,
        current_filter_fines=filter_fines  # Pass the current fines filter to the template
    )

# View future items
@app.route('/view_future_items', methods=['GET'])
def view_future_items():
    # Define allowed item types (adjust as needed)
    item_types = ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game']
    
    # Get parameters from the URL query string
    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'title')  # default sort by title
    sort_order = request.args.get('sort_order', 'asc')  # default ascending
    filter_type = request.args.get('filter_type', '')
    
    # Map the sort_by values to actual database columns safely
    order_column = {
        'id': 'candidate_item_id',
        'title': 'title',
        'item_type': 'item_type'
    }.get(sort_by, 'title')
    
    # Build filtering clause and parameters for the query
    filter_clause = ""
    params = ['%' + search_term + '%']
    if filter_type:
        filter_clause = " AND item_type = ?"
        params.append(filter_type)
    
    query = f"""
        SELECT * FROM FutureItems
        WHERE title LIKE ? {filter_clause}
        ORDER BY {order_column} {sort_order.upper()}
    """
    
    conn = get_db_connection()
    future_items = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('view_future_items.html',
                           future_items=future_items,
                           search_term=search_term,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           filter_type=filter_type,
                           item_types=item_types)


# Renew bookings
@app.route('/renew_item', methods=['GET', 'POST'])
def renew_item():
    conn = get_db_connection()
    success_message = None  # Initialize success message
    error_message = None    # Initialize error message

    if request.method == 'POST':
        borrowing_id = request.form['borrowing_id']
        personnel_id = request.form['personnel_id']
        new_due_date_str = request.form['new_due_date']

        try:
            # Update the borrowing with new due date and personnel
            conn.execute('''
                UPDATE Borrowings
                SET due_date = ?, personnel_id = ?
                WHERE borrowing_id = ?
            ''', (new_due_date_str, personnel_id, borrowing_id))
            conn.commit()

            success_message = "Renewal successful! The new due date has been set."

        except Exception as e:
            error_message = "Error renewing item. Please make sure the new due date is not before the borrow date."
    
    # Get current borrowings
    borrowings = conn.execute("""
        SELECT B.borrowing_id, I.title, I.item_type, B.person_id AS borrower_id, 
               P.name AS borrower_name, B.due_date
        FROM Borrowings B
        JOIN People P ON B.person_id = P.person_id
        JOIN Items I ON B.item_id = I.item_id
        WHERE B.return_date IS NULL
    """).fetchall()

    # Get available librarians
    librarians = conn.execute("""
        SELECT P.person_id, P.name, Pe.role
        FROM Personnel Pe
        JOIN People P ON Pe.person_id = P.person_id
        ORDER BY P.name
    """).fetchall()

    conn.close()

    return render_template('renew_item.html', 
                           borrowings=borrowings, 
                           librarians=librarians, 
                           success_message=success_message,
                           error_message=error_message)

# Pay a Fine
@app.route('/pay_fine', methods=['GET', 'POST'])
def pay_fine():
    conn = get_db_connection()
    success_message = None  # Initialize success message
    error_message = None    # Initialize error message

    if request.method == 'POST':
        fine_id = request.form['fine_id']

        try:
            # Check if a fine exists for the selected fine_id and is not already paid
            fine = conn.execute("""
                SELECT amount FROM Fines WHERE fine_id = ? AND paid_status = 0
            """, (fine_id,)).fetchone()

            if fine:
                # Mark the fine as paid
                conn.execute("""
                    UPDATE Fines
                    SET paid_status = 1
                    WHERE fine_id = ?
                """, (fine_id,))
                conn.commit()
                success_message = f"Fine of ${fine['amount']} has been successfully paid!"
            else:
                error_message = "Error paying fine. Make sure the fine hasn't already been paid."
        except Exception as e:
            conn.rollback()
            error_message = "Error paying fine. Make sure the fine exists and hasn't already been paid."

    # Get outstanding fines
    fines = conn.execute("""
        SELECT F.fine_id, I.title, I.item_type, P.name AS borrower_name, F.amount AS fine_amount
        FROM Fines F
        JOIN Borrowings B ON F.borrowing_id = B.borrowing_id
        JOIN People P ON B.person_id = P.person_id
        JOIN Items I ON B.item_id = I.item_id
        WHERE F.paid_status = 0
    """).fetchall()

    conn.close()

    return render_template('pay_fine.html', fines=fines, success_message=success_message, error_message=error_message)

#12: Pay a Fine
@app.route('/pay_fine', methods=['GET', 'POST'])
def pay_fine():
    conn = get_db_connection()
    success_message = None  # Initialize success message

    if request.method == 'POST':
        fine_id = request.form['fine_id']

        try:
            # Check if a fine exists for the selected fine_id
            fine = conn.execute("""
                SELECT amount FROM Fines WHERE fine_id = ? AND paid_status = 0
            """, (fine_id,)).fetchone()

            if fine:
                # Mark the fine as paid
                conn.execute("""
                    UPDATE Fines
                    SET paid_status = 1
                    WHERE fine_id = ?
                """, (fine_id,))
                conn.commit()

                success_message = f"Fine of ${fine['amount']} has been successfully paid!"

        except Exception as e:
            success_message = f"Error: {str(e)}"

    # Get outstanding fines
    fines = conn.execute("""
        SELECT F.fine_id, I.title, I.item_type, P.name AS borrower_name, F.amount AS fine_amount
        FROM Fines F
        JOIN Borrowings B ON F.borrowing_id = B.borrowing_id
        JOIN People P ON B.person_id = P.person_id
        JOIN Items I ON B.item_id = I.item_id
        WHERE F.paid_status = 0
    """).fetchall()

    conn.close()

    return render_template('pay_fine.html', fines=fines, success_message=success_message)


# Respond to help requests
@app.route('/respond_help', methods=['GET', 'POST'])
def respond_help():
    conn = get_db_connection()

    # --- Handle updates (POST) for a single help request ---
    if request.method == 'POST':
        request_id = request.form['request_id']
        # Convert empty personnel selection to None.
        new_personnel_id = request.form.get('personnel_id') or None  
        new_status = request.form['status']  # Expect "0" (Open) or "1" (Closed)
        conn.execute("""
            UPDATE HelpRequests
            SET personnel_id = ?, status = ?
            WHERE request_id = ?
        """, (new_personnel_id, new_status, request_id))
        conn.commit()

    # --- Filtering and Sorting Controls (GET) ---
    filter_status = request.args.get('filter_status', 'all')  # "all", "open", "closed"
    filter_sender = request.args.get('filter_sender', '')
    filter_helper = request.args.get('filter_helper', '')
    sort_by = request.args.get('sort_by', 'request_id')  # default sort by request_id
    sort_order = request.args.get('sort_order', 'asc')     # default ascending

    # Map allowed sort options to actual columns.
    sort_columns = {
        'request_id': 'HR.request_id',
        'person_id': 'HR.person_id',
        'person_name': 'Sender.name',
        'personnel_id': 'HR.personnel_id',
        'personnel_name': 'Helper.name',
        'status': 'HR.status'
    }
    order_column = sort_columns.get(sort_by, 'HR.request_id')

    # Build the base query.
    # Join People table twice: once for sender and once for helper.
    # Also join Personnel (as Per) to get the helper’s role.
    query = """
        SELECT 
            HR.request_id, 
            HR.person_id, 
            Sender.name AS person_name, 
            HR.personnel_id, 
            Helper.name AS personnel_name,
            Per.role AS personnel_role,
            HR.message,
            HR.status
        FROM HelpRequests HR
        JOIN People Sender ON HR.person_id = Sender.person_id
        LEFT JOIN Personnel Per ON HR.personnel_id = Per.person_id
        LEFT JOIN People Helper ON HR.personnel_id = Helper.person_id
        WHERE 1=1
    """
    params = []
    if filter_status == 'open':
        query += " AND HR.status = 0"
    elif filter_status == 'closed':
        query += " AND HR.status = 1"
    if filter_sender:
        query += " AND HR.person_id = ?"
        params.append(filter_sender)
    if filter_helper:
        query += " AND HR.personnel_id = ?"
        params.append(filter_helper)
    
    query += f" ORDER BY {order_column} {sort_order.upper()}"

    requests_list = conn.execute(query, params).fetchall()

    # --- Fetch options for filtering ---
    # For sender filtering: only People who are NOT in Personnel.
    senders = conn.execute("""
        SELECT person_id, name 
        FROM People 
        WHERE person_id NOT IN (SELECT person_id FROM Personnel)
        ORDER BY name
    """).fetchall()
    # For helper filtering: only those in Personnel (join to People to get name and role)
    helpers = conn.execute("""
        SELECT Per.person_id, P.name, Per.role
        FROM Personnel Per
        JOIN People P ON Per.person_id = P.person_id
        ORDER BY P.name
    """).fetchall()
    # For inline update dropdown (all helpers with their role)
    personnel_options = helpers

    conn.close()

    return render_template('respond_help.html',
                           requests_list=requests_list,
                           filter_status=filter_status,
                           filter_sender=filter_sender,
                           filter_helper=filter_helper,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           senders=senders,
                           helpers=helpers,
                           personnel_options=personnel_options)

if __name__ == '__main__':
    app.run(debug=True)

