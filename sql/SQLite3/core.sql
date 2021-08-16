--
-- core.sql - Core database structures
--
--      PK/FK types and values have been designed with readability in mind.
--      Normally, all key values would be integers and entirely separate
--      from data (for blatantly obvious reasons), but this implementation
--      has no development budget and will thus only receive the basic
--      student and course assistant interfaces. All admin work is to be done
--      by using a DB browser and/or by issuing manual DML SQL sentences.
--
--  TODO:
--      1) Exam privilege tracking (should be based on rules/conditions)
--      2) Rules and conditions.
--          Example rule 1: "exam privilege"
--              T01 OK, score >= 355
--          Example rule 2: "pass course"
--              T02 OK, X00 OK, SUM(E01...E06) > 250, SUM(Q01...Q07) > 100, course score >= 600, 
--
--  2021-08-07  Initial structure.
--  2021-08-08  Redesign for simplicity and improved readability.
--


-- Required by SSO module to make a distinction between privileged (teacher)
-- and unprivileged (student) users.
-- status:      Controls the state of the teacher login role. If "inactive",
--              login credentials will be "student".
CREATE TABLE teacher
(
    uid                 TEXT        NOT NULL PRIMARY KEY,
    created             TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              TEXT        NOT NULL DEFAULT 'active',
    CHECK (status IN ('active', 'inactive'))
);

-- mark (F, 1, 2, 3, 4, 5) or (FAIL, PASS) - note that F/FAIL is not recorded.
-- score in percentages
CREATE TABLE grade
(
    system              TEXT        NOT NULL,
    mark                TEXT        NOT NULL,
    score               NUMERIC     NOT NULL
);


-- COURSE IMPLEMENTATION
-- 
-- course_id:   course.code || '-' || Peppi implementation ID
--              (e.g., "DTE20068-3002")
-- begin / end: Use period period start and end dates, unless
--              there is a reason not to do so.
-- NOTE: score maximum is summed from assignments!
CREATE TABLE course
(
    course_id           TEXT        NOT NULL PRIMARY KEY,
    code                TEXT        NOT NULL,
    name                TEXT        NOT NULL,
    begin               DATETIME    NOT NULL,
    end                 DATETIME    NULL,
    grade_system        TEXT        NULL,
    description         TEXT        NULL,
    FOREIGN KEY (grade_system) REFERENCES grade (system)
);

-- ASSISTANT
--
--  Controls who's work queue will be assigned with submissions to be reviewed.
CREATE TABLE assistant
(
    course_id           TEXT        NOT NULL,
    uid                 TEXT        NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, uid),
    CHECK (status IN ('active', 'inactive'))
)

-- Enrolled students
-- email:       If NULL, default to {uid}@utu.fi
-- studentid:   Required to send grades
-- status:      Primarily used to enable/disable deadline email notifications.
CREATE TABLE enrollee
(
    course_id           TEXT        NOT NULL,
    uid                 TEXT        NOT NULL,
    github              TEXT        NULL,
    studentid           TEXT        NOT NULL,
    email               TEXT        NULL,
    lastname            TEXT        NOT NULL,
    firstname           TEXT        NOT NULL,
    created             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              TEXT        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, uid),
    FOREIGN KEY (course_id) REFERENCES course (course_id),
    UNIQUE (course_id, github),
    UNIQUE (course_id, studentid),
    UNIQUE (course_id, email),
    CHECK (status IN ('active', 'inactive'))
);


-- assignment_id (examples):
-- "EX01" (Exercise 01), "QZ01" (Quizz 01), "TK01" (Task 01)... and so on
-- requirement: NULL if optional assignment
--              <n> min points to qualify
-- latepenalty: NULL if no soft-deadline, otherwise
--              percentage penalty per late day
CREATE TABLE assignment
(
    assignment_id       TEXT        NOT NULL,
    course_id           TEXT        NOT NULL,
    name                TEXT        NOT NULL,
    description         TEXT        NULL,
    points              INTEGER     NOT NULL,
    requirement         INTEGER     NULL,
    deadline            DATETIME    NOT NULL,
    latepenalty         NUMERIC     NULL,
    PRIMARY KEY (assignment_id, course_id),
    FOREIGN KEY (course_id) REFERENCES course (course_id),
    CHECK (latepenalty IS NULL OR (latepenalty > 0 AND latepenalty <= 1))
);

-- IMPORTANT: Must allow multiple submissions from each student!
-- Especially true for the exam
CREATE TABLE submission
(
    assignment_id       TEXT        NOT NULL,
    course_id           TEXT        NOT NULL,
    uid                 TEXT        NOT NULL,
    created             TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    score               INTEGER     NOT NULL,
    notes               TEXT        NULL,
    FOREIGN KEY (assignment_id, course_id) REFERENCES assignment (assignment_id, course_id),
    FOREIGN KEY (course_id, uid) REFERENCES enrollee (course_id, uid)
);

