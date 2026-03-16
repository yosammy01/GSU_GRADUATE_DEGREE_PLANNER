-- ==============================================================================
-- Core Entities (Parent Tables)
-- These must be created first before any foreign keys can reference them.
-- ==============================================================================
USE gsu_catalog;

CREATE TABLE Student (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE Program (
    major VARCHAR(255),
    degree VARCHAR(255),
    PRIMARY KEY (major, degree)
);

CREATE TABLE Requirements (
    requirement_name VARCHAR(255) PRIMARY KEY,
    minimum_grade VARCHAR(2)
);

CREATE TABLE Class_Groupings (
    grouping_id INT AUTO_INCREMENT PRIMARY KEY,
    grouping_name VARCHAR(255),
    credits INT
);

CREATE TABLE Class_Grouping_Elements (
    grouping_id INT,
    class_prefix VARCHAR(10),
    min_class_number INT,
    max_class_number INT,
    PRIMARY KEY (grouping_id, class_prefix, min_class_number, max_class_number),
    FOREIGN KEY (grouping_id) REFERENCES Class_Groupings(grouping_id) ON DELETE CASCADE
);

CREATE TABLE Plan (
    plan_id VARCHAR(50) PRIMARY KEY,
    major VARCHAR(255),
    degree VARCHAR(255),
    FOREIGN KEY (major, degree) REFERENCES Program(major, degree) ON DELETE SET NULL
);

CREATE TABLE Class (
    class_prefix VARCHAR(10),
    class_number VARCHAR(20),
    PRIMARY KEY (class_prefix, class_number)
);

CREATE TABLE Class_Catalog (
    class_prefix VARCHAR(10),
    graduate_class_number VARCHAR(20),
    class_title VARCHAR(255),
    credits INT,
    PRIMARY KEY (class_prefix, graduate_class_number)
);

-- ==============================================================================
-- Junction Tables (Associative Entities)
-- These tables enforce the relationships between the core entities.
-- ==============================================================================

CREATE TABLE Student_Part_Of_Program (
    id VARCHAR(50),
    major VARCHAR(255),
    degree VARCHAR(255),
    PRIMARY KEY (id, major, degree),
    FOREIGN KEY (id) REFERENCES Student(id) ON DELETE CASCADE,
    FOREIGN KEY (major, degree) REFERENCES Program(major, degree) ON DELETE CASCADE
);

CREATE TABLE Program_Has_Requirements (
    major VARCHAR(255),
    degree VARCHAR(255),
    requirement_name VARCHAR(255),
    PRIMARY KEY (major, degree, requirement_name),
    FOREIGN KEY (major, degree) REFERENCES Program(major, degree) ON DELETE CASCADE,
    FOREIGN KEY (requirement_name) REFERENCES Requirements(requirement_name) ON DELETE CASCADE
);

CREATE TABLE Requirements_Composed_Of_Class_Groupings (
    requirement_name VARCHAR(255),
    grouping_id INT,
    PRIMARY KEY (requirement_name, grouping_id),
    FOREIGN KEY (requirement_name) REFERENCES Requirements(requirement_name) ON DELETE CASCADE,
    FOREIGN KEY (grouping_id) REFERENCES Class_Groupings(grouping_id) ON DELETE CASCADE
);

CREATE TABLE Student_Plans_Plan (
    id VARCHAR(50),
    plan_id VARCHAR(50),
    PRIMARY KEY (id, plan_id),
    FOREIGN KEY (id) REFERENCES Student(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES Plan(plan_id) ON DELETE CASCADE
);

CREATE TABLE Plan_Requires_Class (
    plan_id VARCHAR(50),
    class_prefix VARCHAR(10),
    class_number VARCHAR(20),
    requirement_name VARCHAR(255) NOT NULL,
    taken_planned BOOLEAN,
    grade VARCHAR(2),
    semester VARCHAR(50),
    year INT,
    credits INT,
    PRIMARY KEY (plan_id, class_prefix, class_number),
    FOREIGN KEY (plan_id) REFERENCES Plan(plan_id) ON DELETE CASCADE,
    FOREIGN KEY (class_prefix, class_number) REFERENCES Class(class_prefix, class_number) ON DELETE CASCADE,
    FOREIGN KEY (requirement_name) REFERENCES Requirements(requirement_name) ON DELETE CASCADE
);

CREATE TABLE Class_Taken_From_Class_Catalog (
    class_prefix VARCHAR(10),
    class_number VARCHAR(20),
    catalog_class_prefix VARCHAR(10),
    graduate_class_number VARCHAR(20),
    PRIMARY KEY (class_prefix, class_number),
    FOREIGN KEY (class_prefix, class_number) REFERENCES Class(class_prefix, class_number) ON DELETE CASCADE,
    FOREIGN KEY (catalog_class_prefix, graduate_class_number) REFERENCES Class_Catalog(class_prefix, graduate_class_number) ON DELETE CASCADE
);

CREATE TABLE Class_Catalog_Prerequisites (
    class_prefix VARCHAR(10),
    graduate_class_number VARCHAR(20),
    prereq_prefix VARCHAR(10),
    prereq_graduate_class_number VARCHAR(20),
    PRIMARY KEY (class_prefix, graduate_class_number, prereq_prefix, prereq_graduate_class_number),
    FOREIGN KEY (class_prefix, graduate_class_number) REFERENCES Class_Catalog(class_prefix, graduate_class_number) ON DELETE CASCADE,
    FOREIGN KEY (prereq_prefix, prereq_graduate_class_number) REFERENCES Class_Catalog(class_prefix, graduate_class_number) ON DELETE CASCADE
);