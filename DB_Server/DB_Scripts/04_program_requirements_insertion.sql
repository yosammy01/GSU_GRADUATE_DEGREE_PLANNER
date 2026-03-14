-- ==============================================================================
-- Populate Requirements and link them to the Program
-- ==============================================================================

-- Insert foundational requirements
INSERT IGNORE INTO Requirements (requirement_name, minimum_grade) VALUES
('Foundation Coursework', 'B'),
('Research Training Course', 'B'),
('Graduate-Level Coursework', 'B'),
('Thesis Option', 'B'),
('Project Option', 'B'),
('Course Only Option', 'B'),
('Graduate Assistants Requirements', 'B');

-- Link requirements to the Computer Science MS program
INSERT IGNORE INTO Program_Has_Requirements (major, degree, requirement_name) VALUES
('Computer Science', 'MS', 'Foundation Coursework'),
('Computer Science', 'MS', 'Research Training Course'),
('Computer Science', 'MS', 'Graduate-Level Coursework'),
('Computer Science', 'MS', 'Thesis Option'),
('Computer Science', 'MS', 'Project Option'),
('Computer Science', 'MS', 'Course Only Option'),
('Computer Science', 'MS', 'Graduate Assistants Requirements');