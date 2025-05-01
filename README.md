# Flask Library Database Application

This project is a library web application built using Flask, Python, and SQLite for a Database Systems course. This involved defining and specifying the domain of the application, creating an Entity Relationship diagram, showing functional dependencies, analyzing our design for anomalies, normalizing data, converting our ERDs to table schemas in SQLite, populating our tables with realistic tuples, and building a database application.


## Table of Contents

- [The Team](#the-team)
- [Project Specification](#project-specification)
- [Database Schema](#database-schema)
- [E/R Diagram](#er-diagram)
- [Does the design allow anomalies?](#does-the-design-allow-anomalies)
  - [Functional Dependencies (FDs)](#functional-dependencies-fds)
  - [Normalization Note](#normalization-note)
- [SQL Schema](#sql-schema)
- [Database Application](#database-application)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Flask App](#running-the-flask-app)
- [Screenshots](#screenshots)

## The Team

- Trent Carlson
- Harry Kim

## Project Specification

This project models a comprehensive library system that manages a wide range of media, including print and digital books, magazines, scientific journals, CDs, and records. Users can borrow and return items, with fines applied for overdue returns. The system also supports library-hosted events such as book clubs, art shows, and film screenings—free to attend and tailored to specific audiences. Additional features include personnel management and record keeping for both current and prospective library materials.

## Database Schema

Primary keys are <b>bolded,</b> and foreign keys are <sup>superscripted.</sup>

Items = { <b>item_id</b>, item_type, title }

FutureItems = { <b>candidate_item_id</b>, item_type, title }

People = { <b>person_id</b>, name }

Personnel = { <b>person_id</b><sup>FK-People</sup>, role }

Borrowings = { <b>borrowing_id</b>, item_id<sup>FK-Items</sup>, person_id<sup>FK-People</sup>, personnel_id<sup>FK-People</sup>, borrow_date, due_date, return_date }

Fines = { <b>fine_id</b>, borrowing_id<sup>FK-Borrowings</sup>, amount, paid_status }

Events = { <b>event_id</b>, name, description, event_date, room_id<sup>FK-SocialRooms</sup> }

Attending = { <b>event_id</b><sup>FK-Events</sup>, <b>person_id</b><sup>FK-People</sup> }

SocialRooms = { <b>room_id</b>, room_name }

Audiences = { <b>audience_id</b>, audience_type }

EventAudiences = { <b>event_id</b><sup>FK-Events</sup>, <b>audience_id</b><sup>FK-Audiences</sup> }

PersonAudiences = { <b>person_id</b><sup>FK-People</sup>, <b>audience_id</b><sup>FK-Audiences</sup> }

HelpRequests = { <b>request_id</b>, <b>person_id</b><sup>FK-People</sup>, <b>personnel_id</b><sup>FK-Personnel</sup>, message }

## E/R Diagram

![ER Diagram](https://github.com/t-trent/Library-Application/blob/main/Library_ER_Diagram.png)

## Does the design allow anomalies?

### Functional Dependencies (FDs)

#### **Items**
- **FD:** `item_id → item_type, title`  
- **Explanation:** Each item has a unique ID, which determines its type and title. This allows individual tracking even for multiple copies of the same item.

#### **FutureItems**
- **FD:** `candidate_item_id → item_type, title`  
- **Explanation:** Ensures proposed new items are uniquely identifiable, preventing confusion with existing items.

#### **People**
- **FD:** `person_id → name`  
- **Explanation:** Each person is uniquely identified by an ID, which determines their name—important for handling duplicate names.

#### **Personnel**
- **FD:** `person_id → role`  
- **Explanation:** Since personnel are part of People, their roles are also uniquely determined by their ID, ensuring integrity and no redundancy.

#### **Borrowings**
- **FD:** `borrowing_id → borrow_date, due_date, return_date, item_id, person_id, personnel_id`  
- **Explanation:** A borrowing record’s ID determines all relevant details, linking it to an item, borrower, and staff.

#### **Fines**
- **FD:** `fine_id → amount, paid_status, borrowing_id`  
- **Explanation:** Each fine is uniquely identified and tied to a specific borrowing transaction.

#### **Events**
- **FD:** `event_id → name, description, event_date, room_id`  
- **Explanation:** Each event is uniquely defined by its ID, including where and when it takes place.

#### **Attending**
- **FD:** _No non-trivial functional dependencies_  
- **Explanation:** This is a many-to-many relationship table, so no single attribute functionally determines the other.

#### **SocialRooms**
- **FD:** `room_id → room_name`  
- **Explanation:** Each social room has a unique ID to eliminate confusion over names.

#### **Audiences**
- **FD:** `audience_id → audience_type`  
- **Explanation:** Each audience type is uniquely identified for consistent categorization.

#### **EventAudiences**
- **FD:** _No non-trivial functional dependencies_  
- **Explanation:** This join table relates events to their recommended audiences.

#### **PersonAudiences**
- **FD:** _No non-trivial functional dependencies_  
- **Explanation:** This join table relates people to the audience types relevant to them.

#### **HelpRequests**
- **FD:** `request_id → message, status, person_id, personnel_id`  
- **Explanation:** Each help request has a unique ID, determining all associated data, even when content might appear similar.

---

### Normalization Note

This schema avoids anomalies and is in **BCNF**. For all non-trivial functional dependencies `X → Y`, `X` is a superkey. Most determinants are primary keys (or candidate keys), and no partial dependencies exist due to careful decomposition.

---

## SQL Schema

```sql 
-- Items table
CREATE TABLE Items (
    item_id INTEGER PRIMARY KEY,
    item_type TEXT,
    title TEXT,
    CHECK (item_type IN ('Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game'));
);

-- FutureItems table
CREATE TABLE FutureItems (
    candidate_item_id INTEGER PRIMARY KEY,
    item_type TEXT,
    title TEXT,
    CHECK (item_type IN ('Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game'));
);

-- People table
CREATE TABLE People (
    person_id INTEGER PRIMARY KEY,
    name TEXT
);

-- Borrowings table
CREATE TABLE Borrowings (
    borrowing_id INTEGER PRIMARY KEY,
    item_id INTEGER,
    person_id INTEGER,
    personnel_id INTEGER,
    borrow_date TEXT,
    due_date TEXT,
    return_date TEXT,
    FOREIGN KEY (item_id) REFERENCES Items(item_id),
    FOREIGN KEY (person_id) REFERENCES People(person_id),
    FOREIGN KEY (personnel_id) REFERENCES Personnel(person_id),
    CHECK (return_date IS NULL OR return_date >= borrow_date), -- Ensure return_date is after borrow_date
    CHECK (due_date IS NULL OR due_date >= borrow_date) -- Ensure due_date is after borrow_date
);

-- Trigger to prevent double borrowing
CREATE TRIGGER trg_prevent_double_borrowing
BEFORE INSERT ON Borrowings
FOR EACH ROW
WHEN NEW.return_date IS NULL
BEGIN
    SELECT 
        CASE 
            WHEN EXISTS (SELECT 1 FROM Borrowings WHERE item_id = NEW.item_id AND return_date IS NULL)
            THEN RAISE(ABORT, 'This item is already borrowed and not yet returned.')
        END;
END;

-- Fines table
CREATE TABLE Fines (
    fine_id INTEGER PRIMARY KEY,
    borrowing_id INTEGER,
    amount REAL,
    paid_status INTEGER,
    FOREIGN KEY (borrowing_id) REFERENCES Borrowings(borrowing_id),
    CHECK (paid_status IN (0, 1)), -- 0 for unpaid, 1 for paid
    CHECK (amount IN (5, 15, 50)) -- Fixed fine amounts
);

-- SocialRooms table
CREATE TABLE SocialRooms (
    room_id INTEGER PRIMARY KEY,
    room_name TEXT
);

-- Events table
CREATE TABLE Events (
    event_id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    event_date TEXT,
    room_id INTEGER,
    FOREIGN KEY (room_id) REFERENCES SocialRooms(room_id)
);

-- Attending table
CREATE TABLE Attending (
    event_id INTEGER,
    person_id INTEGER,
    PRIMARY KEY (event_id, person_id), -- Composite primary key
    FOREIGN KEY (event_id) REFERENCES Events(event_id),
    FOREIGN KEY (person_id) REFERENCES People(person_id)
);

-- Audiences table
CREATE TABLE Audiences (
    audience_id INTEGER PRIMARY KEY,
    audience_type TEXT
);

-- EventAudiences table
CREATE TABLE EventAudiences (
    event_id INTEGER,
    audience_id INTEGER,
    PRIMARY KEY (event_id, audience_id), -- Composite primary key
    FOREIGN KEY (event_id) REFERENCES Events(event_id),
    FOREIGN KEY (audience_id) REFERENCES Audiences(audience_id)
);

-- PersonAudiences table
CREATE TABLE PersonAudiences (
    person_id INTEGER,
    audience_id INTEGER,
    PRIMARY KEY (person_id, audience_id),
    FOREIGN KEY (person_id) REFERENCES People(person_id),
    FOREIGN KEY (audience_id) REFERENCES Audiences(audience_id)
);

-- Personnel table
CREATE TABLE Personnel (
    person_id INTEGER PRIMARY KEY,
    role TEXT,
    FOREIGN KEY (person_id) REFERENCES People(person_id),
    CHECK (role IN ('Librarian', 'Assistant Librarian', 'Volunteer')) -- Ensure role is one of the specified values
);

-- Help requests table
CREATE TABLE HelpRequests (
    request_id INTEGER PRIMARY KEY,
    person_id INTEGER,
    personnel_id INTEGER,
    message TEXT,
    status INTEGER,
    FOREIGN KEY (person_id) REFERENCES People(person_id),
    FOREIGN KEY (personnel_id) REFERENCES Personnel(person_id),
    CHECK (status IN (0, 1)) -- Ensure status is either 'Open' or 'Closed' (0 for Open, 1 for Closed)
);
```

---

## Database Application

In our application, library users can:
-	Find an item in the library
-	Borrow an item from the library
-	Return a borrowed item
-	Donate an item to the library
-	Find an event in the library
-	Register for an event in the library
-	Volunteer for the library
-	Ask for help from a librarian
-	View borrowings & fines
-	View future items
-	Renew an item
-	Pay a fine
-	View & update help requests
-	Add a new person
-	Manage people


## Prerequisites

- Python 3.6 or higher
- `pip` (Python package manager)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/t-trent/CMPT-354-Mini-Project
   cd CMPT-354-Mini-Project
   ```

2. **Install Flask:**

   ```bash
   pip install flask
   ```

## Running the Flask App

To start the Flask application, run the following command:

```bash
python app.py
```

The app should now be running on [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

## Screenshots

Below are some screenshots of the web application. Bootstrap CSS was used for some light styling and for the navbar.

### Landing Page
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/landing-page.png)

### Find an Item
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/find-item.png)

### Borrow an Item
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/borrow-item.png)

### Find an Event
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/find-event.png)

### View Borrowings
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/view-borrowings.png)

### View & Update Help Requests
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/help-requests.png)

### Navbar
![](https://github.com/t-trent/Library-Application/blob/main/screenshots/hamburger-menu.png)
