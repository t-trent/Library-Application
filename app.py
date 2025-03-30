# Library Database Application
# Mini Project - CMPT354 - Database Systems I
# Group 52 (Trent Carlson, Harry Kim)

from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

DATABASE = 'library.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)  # Waits up to 10 seconds if the database is locked
    conn.row_factory = sqlite3.Row
    return conn

# Home page: a menu for the operations
@app.route('/')
def index():
    return render_template('index.html')

# 1. Find an item in the library
@app.route('/find_item', methods=['GET'])
def find_item():
    # Define allowed item types
    item_types = ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game']
    
    # Get parameters from the URL query string
    search_term = request.args.get('search_term', '')
    sort_by = request.args.get('sort_by', 'title')  # default sort by title
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
        ORDER BY {order_column}
    """
    
    # Query for Unavailable Items:
    # Items that are currently borrowed (return_date IS NULL)
    unavailable_query = f"""
        SELECT DISTINCT Items.* FROM Items
        JOIN Borrowings ON Items.item_id = Borrowings.item_id
        WHERE title LIKE ? {filter_clause}
          AND Borrowings.return_date IS NULL
        ORDER BY {order_column}
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
                           filter_type=filter_type,
                           item_types=item_types)


# 2. Borrow an item from the library
@app.route('/borrow_item', methods=['GET', 'POST'])
def borrow_item():
    conn = get_db_connection()
    success_message = None  # This will hold our success message if set
    
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
            success_message = 'Invalid borrow date format. Please use YYYY-MM-DD.'
            # Continue to load the dropdown options below
            
        if success_message is None:
            conn.execute('''
                INSERT INTO Borrowings (item_id, person_id, personnel_id, borrow_date, due_date, return_date)
                VALUES (?, ?, ?, ?, ?, NULL)
            ''', (item_id, person_id, personnel_id, borrow_date_str, due_date_str))
            conn.commit()
            success_message = (f"Item ID {item_id} borrowed successfully by Person ID {person_id}. "
                               f"Librarian (ID: {personnel_id}) assisted. Due date is {due_date_str}.")
    
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
                           success_message=success_message)


# 3. Return a borrowed item
@app.route('/return_item', methods=['GET', 'POST'])
def return_item():
    success_message = None
    conn = get_db_connection()
    
    if request.method == 'POST':
        borrowing_id = request.form['borrowing_id']
        return_date = request.form['return_date']
        
        # Update the Borrowings record to mark it as returned
        conn.execute('UPDATE Borrowings SET return_date = ? WHERE borrowing_id = ?', (return_date, borrowing_id))
        conn.commit()
        success_message = f"Borrowing ID {borrowing_id} was successfully returned on {return_date}."
    
    # Query active borrowings (where return_date is NULL)
    active_borrowings = conn.execute("SELECT * FROM Borrowings WHERE return_date IS NULL").fetchall()
    conn.close()
    
    return render_template('return_item.html', active_borrowings=active_borrowings, success_message=success_message)

# 4. Donate an item to the library
@app.route('/donate_item', methods=['GET', 'POST'])
def donate_item():
    success_message = None
    # Define the allowed item types
    item_types = ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game']
    
    if request.method == 'POST':
        item_type = request.form['item_type']
        title = request.form['title']
        
        conn = get_db_connection()
        # Get the current highest item_id from the Items table
        cursor = conn.execute("SELECT MAX(item_id) FROM Items")
        max_id_row = cursor.fetchone()
        max_id = max_id_row[0] if max_id_row[0] is not None else 0
        new_item_id = max_id + 1

        # Insert the new item with the new item_id
        conn.execute('INSERT INTO Items (item_id, item_type, title) VALUES (?, ?, ?)',
                     (new_item_id, item_type, title))
        conn.commit()
        conn.close()
        
        success_message = f"Item '{title}' (ID: {new_item_id}) of type '{item_type}' donated successfully."
    
    return render_template('donate_item.html', item_types=item_types, success_message=success_message)


@app.route('/find_event', methods=['GET'])
def find_event():
    # Get query parameters (with defaults)
    search_term    = request.args.get('search_term', '')
    filter_audience = request.args.get('filter_audience', '')
    filter_room    = request.args.get('filter_room', '')
    sort_by        = request.args.get('sort_by', 'date_asc')  # default sort: date ascending
    filter_attendee = request.args.get('filter_attendee', '')
    
    # Allowed filter options for audiences and social rooms
    audience_types_list = ["Seniors", "Teens", "Children", "Young Adults", "Families", 
                             "Academics", "Hobbyists", "Students", "Artists", "Tech Enthusiasts"]
    social_room_names = ["Maple Hall", "Sunset Room", "Heritage Lounge", "Cedar Commons", 
                         "The Learning Loft", "Innovation Nook", "Oak Room", "Skyview Gallery", 
                         "Community Studio", "The Nest"]
    
    # Query for all People for the attendee dropdown
    conn = get_db_connection()
    people_dropdown = conn.execute("SELECT person_id, name FROM People ORDER BY name").fetchall()

    # Build the base query.
    # Note: We join Attending (Atnd) and People (Att) to get the names of the attendees.
    query = """
        SELECT 
            E.event_id, 
            E.name, 
            E.event_date, 
            E.description, 
            SR.room_name,
            GROUP_CONCAT(DISTINCT A.audience_type) as audiences,
            GROUP_CONCAT(DISTINCT Att.name) as attendees
        FROM Events E
        LEFT JOIN SocialRooms SR ON E.social_room_id = SR.social_room_id
        LEFT JOIN EventAudiences EA ON E.event_id = EA.event_id
        LEFT JOIN Audiences A ON EA.audience_id = A.audience_id
        LEFT JOIN Attending Atnd ON E.event_id = Atnd.event_id
        LEFT JOIN People Att ON Atnd.person_id = Att.person_id
        WHERE E.name LIKE ?
    """
    params = ['%' + search_term + '%']
    
    # Apply filter for social room if provided
    if filter_room:
        query += " AND SR.room_name = ?"
        params.append(filter_room)
    
    # Apply filter for audience type if provided
    if filter_audience:
        query += " AND A.audience_type = ?"
        params.append(filter_audience)
    
    # Apply filter for a specific attendee: ensure the event has at least one attendee with that person_id.
    if filter_attendee:
        query += " AND EXISTS (SELECT 1 FROM Attending Atnd2 WHERE Atnd2.event_id = E.event_id AND Atnd2.person_id = ?)"
        params.append(filter_attendee)
    
    query += " GROUP BY E.event_id, E.name, E.event_date, E.description, SR.room_name "
    
    # Determine sort order based on sort_by parameter
    if sort_by == "date_asc":
        query += " ORDER BY E.event_date ASC"
    elif sort_by == "date_desc":
        query += " ORDER BY E.event_date DESC"
    elif sort_by == "title":
        query += " ORDER BY E.name"
    elif sort_by == "id":
        query += " ORDER BY E.event_id"
    else:
        query += " ORDER BY E.event_date ASC"  # fallback default

    events = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('find_event.html',
                           events=events,
                           search_term=search_term,
                           filter_audience=filter_audience,
                           filter_room=filter_room,
                           sort_by=sort_by,
                           filter_attendee=filter_attendee,
                           audience_types_list=audience_types_list,
                           social_room_names=social_room_names,
                           people_dropdown=people_dropdown)




# 6. Register for an event in the library
@app.route('/register_event', methods=['GET', 'POST'])
def register_event():
    message = None
    conn = get_db_connection()
    
    # Query events and people to populate dropdown menus
    events = conn.execute("SELECT event_id, name FROM Events ORDER BY name").fetchall()
    people = conn.execute("SELECT person_id, name FROM People ORDER BY name").fetchall()
    
    if request.method == 'POST':
        event_id = request.form['event_id']
        person_id = request.form['person_id']
        
        # Insert registration into Attending table
        conn.execute('INSERT INTO Attending (event_id, person_id) VALUES (?, ?)', (event_id, person_id))
        conn.commit()
        message = f"Registered person ID {person_id} for event ID {event_id} successfully."
    
    conn.close()
    return render_template('register_event.html', events=events, people=people, message=message)

# 7. Volunteer for the library
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


# 8. Ask for help from a librarian
@app.route('/ask_help', methods=['GET', 'POST'])
def ask_help():
    if request.method == 'POST':
        person_id = request.form['person_id']
        question = request.form['question']
        # You might record this in a separate table or simply email someone
        flash('Your help request has been received.')
        return redirect(url_for('index'))
    return render_template('ask_help.html')

if __name__ == '__main__':
    app.run(debug=True)

