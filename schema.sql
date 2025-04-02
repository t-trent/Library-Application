-- Items table
CREATE TABLE Items (
    item_id INTEGER PRIMARY KEY,
    item_type TEXT,
    title TEXT
    CHECK (item_type IN ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game'])
);

-- FutureItems table
CREATE TABLE FutureItems (
    candidate_item_id INTEGER PRIMARY KEY,
    item_type TEXT,
    title TEXT
    CHECK (item_type IN ['Book', 'DVD', 'Scientific Journal', 'Audiobook', 'Magazine', 'Newspaper', 'eBook', 'CD', 'Record', 'Video Game']
);

-- People table
CREATE TABLE People (
    person_id INTEGER PRIMARY KEY,
    name TEXT
);

-- Borrowings table
CREATE TABLE BorrowingsNew (
    borrowing_id INTEGER PRIMARY KEY,
    item_id INTEGER,
    person_id INTEGER,
    personnel_id INTEGER,
    borrow_date TEXT,
    due_date TEXT,
    return_date TEXT,
    FOREIGN KEY (item_id) REFERENCES Items(item_id),
    FOREIGN KEY (person_id) REFERENCES People(person_id),
    FOREIGN KEY (personnel_id) REFERENCES Personnel(person_id)
    CHECK (return_date IS NULL OR return_date >= borrow_date) -- Ensure return_date is after borrow_date
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
    FOREIGN KEY (borrowing_id) REFERENCES Borrowings(borrowing_id)
    CHECK (paid_status IN (0, 1)) -- 0 for unpaid, 1 for paid
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
    FOREIGN KEY (person_id) REFERENCES People(person_id)
    CHECK (role IN ['Librarian', 'Assistant Librarian', 'Volunteer']) -- Ensure role is one of the specified values
);

-- Help requests table
CREATE TABLE HelpRequests (
    request_id INTEGER PRIMARY KEY,
    person_id INTEGER,
    personnel_id INTEGER,
    status INTEGER,
    FOREIGN KEY (person_id) REFERENCES People(person_id)
    FOREIGN KEY (personnel_id) REFERENCES Personnel(person_id)
    CHECK (status IN [0, 1]) -- Ensure status is either 'Open' or 'Closed' (0 for Open, 1 for Closed)
);

