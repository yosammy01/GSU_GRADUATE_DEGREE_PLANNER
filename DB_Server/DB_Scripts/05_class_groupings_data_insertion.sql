-- ==============================================================================
-- 1. Populate the Class_Groupings Table
-- This defines the specific classes or "ranges" of classes that fulfill requirements.
-- ==============================================================================

INSERT INTO Class_Groupings (class_prefix, graduate_range, credits) VALUES
-- Foundation Classes (Specific Numbers)
('MATH', '2211', 4),
('MATH', '2212', 4),
('CSC', '6210', 4),
('CSC', '6320', 4),
('CSC', '6330', 4), -- OR option 1
('CSC', '6340', 4), -- OR option 2
('CSC', '6510', 4), -- OR option 3
('CSC', '6350', 4),
('CSC', '6520', 4),

-- Research & Seminar Classes
('CSC', '8900', 1),
('CSC', '8901', 1),
('CSC', '8920', 2),

-- Variable Credit Research/Projects (Using 0 as our indicator)
('CSC', '8930', 0),
('CSC', '8940', 0),
('CSC', '8981', 0),
('CSC', '8982', 0),
('CSC', '8999', 0),

-- Broad Elective Ranges (Representing the Graduate-Level Coursework buckets)
-- The credits here reflect the total hours required by the bucket
('CSC', '8000-8999', 16), 
('CSC', '6000-9999', 8);

-- ==============================================================================
-- 2. Populate the Requirements_Composed_Of_Class_Groupings Junction Table
-- This links the predefined requirements to the specific groupings/classes above.
-- ==============================================================================

INSERT INTO Requirements_Composed_Of_Class_Groupings (requirement_name, class_prefix, graduate_range) VALUES
-- Foundation Coursework
('Foundation Coursework', 'MATH', '2211'),
('Foundation Coursework', 'MATH', '2212'),
('Foundation Coursework', 'CSC', '6210'),
('Foundation Coursework', 'CSC', '6320'),
('Foundation Coursework', 'CSC', '6330'),
('Foundation Coursework', 'CSC', '6340'),
('Foundation Coursework', 'CSC', '6510'),
('Foundation Coursework', 'CSC', '6350'),
('Foundation Coursework', 'CSC', '6520'),

-- Research Training Course
('Research Training Course', 'CSC', '8900'),

-- Graduate-Level Coursework (The 24-hour elective buckets)
('Graduate-Level Coursework', 'CSC', '8000-8999'),
('Graduate-Level Coursework', 'CSC', '6000-9999'),

-- Thesis Option
('Thesis Option', 'CSC', '8999'),

-- Project Option
('Project Option', 'CSC', '8930'),
('Project Option', 'CSC', '8940'),

-- Course Only Option
('Course Only Option', 'CSC', '8901'),

-- Graduate Assistants Requirements
('Graduate Assistants Requirements', 'CSC', '8920'),
('Graduate Assistants Requirements', 'CSC', '8981'),
('Graduate Assistants Requirements', 'CSC', '8982');