-- ==============================================================================
-- 1. Populate the Class_Groupings Table
-- This defines the specific classes or "ranges" of classes that fulfill requirements.
-- ==============================================================================

INSERT INTO Class_Groupings (grouping_id, grouping_name, credits) VALUES
-- Foundation Classes
(1, 'MATH 2211', 4),
(2, 'MATH 2212', 4),
(3, 'CSC 2510', 3),
(4, 'CSC 2720', 3),
(5, 'CSC 3210 or 6210', 3),
(6, 'CSC 6320', 4),
(7, 'CSC 6330, 6340, or 6510', 4),
(8, 'CSC 6350', 4),
(9, 'CSC 6520', 4),
-- Research & Seminar Classes
(10, 'CSC 8900', 1),
(11, 'CSC 8901', 1),
(12, 'CSC 8920', 2),
-- Variable Credit Research/Projects
(13, 'CSC 8930', 0),
(14, 'CSC 8940', 0),
(15, 'CSC 8981', 0),
(16, 'CSC 8982', 0),
(17, 'CSC 8999', 0),
-- Broad Elective Ranges
(18, '8000-8999 Electives', 16),
(19, '6000-8999 Electives', 8),
(20, '6000-8999 Electives', 4),
(21, '8000-8999 Electives', 4);

-- ==============================================================================
-- 1.5. Populate the Class_Grouping_Elements Table
-- This defines the specific class numbers or ranges for each grouping.
-- ==============================================================================
INSERT INTO Class_Grouping_Elements (grouping_id, class_prefix, min_class_number, max_class_number) VALUES
(1, 'MATH', 2211, 2211),
(2, 'MATH', 2212, 2212),
(3, 'CSC', 2510, 2510),
(4, 'CSC', 2720, 2720),
(5, 'CSC', 3210, 3210),
(5, 'CSC', 6210, 6210),
(6, 'CSC', 6320, 6320),
(7, 'CSC', 6330, 6330),
(7, 'CSC', 6340, 6340),
(7, 'CSC', 6510, 6510),
(8, 'CSC', 6350, 6350),
(9, 'CSC', 6520, 6520),
(10, 'CSC', 8900, 8900),
(11, 'CSC', 8901, 8901),
(12, 'CSC', 8920, 8920),
(13, 'CSC', 8930, 8930),
(14, 'CSC', 8940, 8940),
(15, 'CSC', 8981, 8981),
(16, 'CSC', 8982, 8982),
(17, 'CSC', 8999, 8999),
(18, 'CSC', 8000, 8999),
(19, 'CSC', 6000, 8999),
(20, 'CSC', 6000, 8999),
(21, 'CSC', 8000, 8999);

-- ==============================================================================
-- 2. Populate the Requirements_Composed_Of_Class_Groupings Junction Table
-- This links the predefined requirements to the specific groupings/classes above.
-- ==============================================================================

INSERT INTO Requirements_Composed_Of_Class_Groupings (requirement_name, grouping_id) VALUES
-- Foundation Coursework
('Foundation Coursework', 1),
('Foundation Coursework', 2),
('Foundation Coursework', 3),
('Foundation Coursework', 4),
('Foundation Coursework', 5),
('Foundation Coursework', 6),
('Foundation Coursework', 7),
('Foundation Coursework', 8),
('Foundation Coursework', 9),

-- Research Training Course
('Research Training Course', 10),

-- Graduate-Level Coursework (The 24-hour elective buckets)
('Graduate-Level Coursework', 18),
('Graduate-Level Coursework', 19),

-- Thesis Option
('Thesis Option', 17),

-- Project Option
('Project Option', 13),
('Project Option', 14),

-- Course Only Option
('Course Only Option', 11),
('Course Only Option', 20),
('Course Only Option', 21);