--
-- Schooner - Simple Course Management System
-- core.module.sql / Core table structure, PostgreSQL version
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--  2021-08-17  Updated.
--  2021-08-19  .github_account and .github_repository in enrollee.
--
-- Execute as 'schooner' (for ownership)

-- https://www.postgresql.org/docs/9.1/datatype-enum.html
CREATE TYPE active_t AS ENUM ('active', 'inactive');


--
-- Admin-privileged users
--
CREATE TABLE admin
(
    uid                 VARCHAR(10)     NOT NULL PRIMARY KEY,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active'
);
GRANT ALL PRIVILEGES ON admin TO schooner_dev;
GRANT SELECT ON admin TO "www-data";

COMMENT ON TABLE admin IS
'Table lists all SSO IDs that are granted administrator privileges in this system. Used by the web application SSO authentication module.';
COMMENT ON COLUMN admin.uid IS
'UTU SSO ID (aka. the login)';


--
-- Grading systems
--
CREATE TABLE gradesys
(
    gradesys_id         VARCHAR(8)      NOT NULL PRIMARY KEY,
    name                VARCHAR(64)     NOT NULL
);
GRANT ALL PRIVILEGES ON gradesys TO schooner_dev;
GRANT SELECT ON gradesys TO "www-data";

COMMENT ON TABLE gradesys IS
'Grading systems by name. See gradesys_criteria table for associated marks and required score percentages.';

INSERT INTO gradesys
VALUES
('0-5/60', 'Grades 0-5. Score of 60% is required to pass.'),
('0-5/50', 'Grades 0-5. Score of 50% is required to pass.'),
('F-P/60', 'FAIL/PASS. Score of 60% is required to pass.'),
('F-P/50', 'FAIL/PASS. Score of 50% is required to pass.');

CREATE TABLE gradesys_criteria
(
    gradesys_id         VARCHAR(8)      NOT NULL,
    mark                VARCHAR(10)     NOT NULL,
    score               NUMERIC(4,4)    NOT NULL,
    FOREIGN KEY (gradesys_id)
        REFERENCES gradesys (gradesys_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT grade_system_mark_unq
        UNIQUE (gradesys_id, mark)
);
GRANT ALL PRIVILEGES ON gradesys_criteria TO schooner_dev;
GRANT SELECT ON gradesys_criteria TO "www-data";

COMMENT ON TABLE gradesys_criteria IS
'Note that fail criteria is not recorded. If course points fail to reach any of the recorded criteria, it is a fail.';
COMMENT ON COLUMN gradesys_criteria.score IS
'Score percentage required to earn this mark.';
COMMENT ON COLUMN gradesys_criteria.mark IS
'Awarded grade. Commonly 0-5 or PASS/FAIL.';

INSERT INTO gradesys_criteria
VALUES
('0-5/60',  '5',    0.92),
('0-5/60',  '4',    0.84),
('0-5/60',  '3',    0.76),
('0-5/60',  '2',    0.68),
('0-5/60',  '1',    0.60),
('0-5/50',  '5',    0.90),
('0-5/50',  '4',    0.80),
('0-5/50',  '3',    0.70),
('0-5/50',  '2',    0.60),
('0-5/50',  '1',    0.50),
('F-P/60',  'PASS', 0.60),
('F-P/50',  'PASS', 0.50);




--
-- Course Implementation
-- 
CREATE TABLE course
(
    course_id           VARCHAR(16)     NOT NULL PRIMARY KEY,
    code                VARCHAR(10)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    opens               TIMESTAMP       NOT NULL,
    closes              TIMESTAMP       NULL,
    gradesys_id         VARCHAR(8)      NULL,
    description         VARCHAR(5000)   NULL,
    FOREIGN KEY (gradesys_id)
        REFERENCES gradesys (gradesys_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT course_begin_lte_end
        CHECK (closes IS NULL OR closes >= opens)
);
GRANT ALL PRIVILEGES ON course TO schooner_dev;
GRANT SELECT ON course TO "www-data";

COMMENT ON TABLE course IS
'Course instances (one per year/implementation). NOTE: Course total score is calculated from assignment table records.';
COMMENT ON COLUMN course.course_id IS
'Value should be the ID used in Peppi-system, "DTE20068-3002", for example.';
COMMENT ON COLUMN course.code IS
'Course code as it appears in Study Guide. "DTE20068", for example.';
COMMENT ON COLUMN course.name IS
'Course name as it appears in the Study Guid (in English).';
COMMENT ON COLUMN course.opens IS
'Use period start date. Used to determine active/on-going courses.';
COMMENT ON COLUMN course.closes IS
'Can be set later. Used to determine active/on-going courses.';
COMMENT ON COLUMN course.gradesys_id IS
'Optional foreign key to gradesys -table to indicate which grading system the course uses.';
COMMENT ON COLUMN course.description IS
'Optional course description. There should not be much use for this field as all the pertinent information is made available in Moodle and/or APlus.';




--
-- Enrolled students
--
CREATE TABLE enrollee
(
    course_id           VARCHAR(16)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    github_account      VARCHAR(40)     NULL,
    github_repository   VARCHAR(100)    NULL,
    studentid           VARCHAR(10)     NOT NULL,
    email               VARCHAR(64)     NULL,
    lastname            VARCHAR(32)     NOT NULL,
    firstname           VARCHAR(32)     NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, uid),
    FOREIGN KEY (course_id)
        REFERENCES course (course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT course_github_account_unq
        UNIQUE (course_id, github_account),
    CONSTRAINT course_studentid_unq
        UNIQUE (course_id, studentid),
    CONSTRAINT course_email_unq
        UNIQUE (course_id, email)
);
GRANT ALL PRIVILEGES ON enrollee TO schooner_dev;
GRANT SELECT ON enrollee TO "www-data";

COMMENT ON TABLE enrollee IS
'List of students enrolled to a course. NOTE: Redundant information for same student enrolled again, or in a different course, is accepted.';
COMMENT ON COLUMN enrollee.uid IS
'UTU ID, also known as the user name. The name used in the short email address.What is used to login to UTU SSO.';
COMMENT ON COLUMN enrollee.github_account IS
'Not NULL if account registration has been successfully handled. GitHub account name. Min: 1, max: 39, can contain: a-z A-Z 0-0 "-" but cannot start with dash character.';
COMMENT ON COLUMN enrollee.github_repository IS
'Not NULL if account registration has been successfully handled. GitHub maximum repository name length is 100 characters.';
COMMENT ON COLUMN enrollee.studentid IS
'Required to send grades. Possibly always numeric and up to 7 digits long. This solution acceptes strings up to 10 characters.';
COMMENT ON COLUMN enrollee.email IS
'Email should always be available from Peppi registration export, but this column may be NULL''ed, if student either does not want the email to be recorded, or prefers to make sure never to receive any notifications. Should mostly be {uid}@utu.fi';
COMMENT ON COLUMN enrollee.status IS
'Can be set to "inactive", if the student explicitly requests to be dropped from the course. Primarily used to enable/disable deadline email notifications.';





--
-- Assignment Handlers
--
CREATE TABLE handler
(
    code                VARCHAR(8)      NOT NULL PRIMARY KEY,
    name                VARCHAR(32)     NOT NULL UNIQUE,
    description         VARCHAR(5000)   NULL
);
GRANT ALL PRIVILEGES ON handler TO schooner_dev;
GRANT SELECT ON handler TO "www-data";

COMMENT ON TABLE handler IS
'Each type of a submission handling has its own code which allows background tasks and web forms to recognize assignments that they need to handle.';
COMMENT ON COLUMN handler.description IS
'Contents of this column should not be necessary to display to a student, but the explanations are likely very useful for a teacher who is recording the assignments.';

INSERT INTO handler
VALUES
('HUBREG', 'GitHub account registrations', NULL),
('HUBBOT', 'GitHub exercise retriever', NULL),
('APLUS', 'APlus Quizz score retriever', 'Scores are retrieved from APlus automatically.');


--
-- Assignments (tasks, exercises, quizzes, exams, ...)
--
CREATE TABLE assignment
(
    assignment_id       VARCHAR(8)      NOT NULL,
    course_id           VARCHAR(16)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    description         VARCHAR(5000)   NULL,
    handler             VARCHAR(8)      NULL,
    points              INTEGER         NOT NULL,
    pass                INTEGER         NULL,
    deadline            TIMESTAMP       NOT NULL,
    latepenalty         NUMERIC(2,2)    NULL,
    PRIMARY KEY (assignment_id, course_id),
    FOREIGN KEY (course_id)
        REFERENCES course (course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (handler)
        REFERENCES handler (code)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT assignment_pass_lte_points
        CHECK (pass IS NULL OR pass <= points)
);
-- Allow only one 'HUBREG' assignment per course
CREATE UNIQUE INDEX assignment_single_hubreg_idx
ON assignment (course_id, handler)
WHERE (handler = 'HUBREG');

GRANT ALL PRIVILEGES ON assignment TO schooner_dev;
GRANT SELECT ON assignment TO "www-data";

COMMENT ON TABLE assignment IS
'Tasks, exercices, quizzes, exams, etc. Sum of points -column dictates the course total points.';
COMMENT ON COLUMN assignment.assignment_id IS
'For easier reading (the database directly, aka. debugging), use shorthand sumbols as T01 for tasks, Q01 for quizzes, E01 for exercises, etc.';
COMMENT ON COLUMN assignment.name IS
'Name of the assignment as it appears in the Moodle course description.';
COMMENT ON COLUMN assignment.handler IS
'NULL if submissions for this assignment are manually recorded. Otherwise, the code of the appropriate automation service (see "handler" table).';
COMMENT ON COLUMN assignment.points IS
'Maximum points that can be earned from the assignment.';
COMMENT ON COLUMN assignment.pass IS
'Minimum points to pass the assignment. Zero if any submission will do and NULL if the assignment is optional.';
COMMENT ON COLUMN assignment.deadline IS
'NOTE: Current implementation ignores time part. Date during which the assignment must be submitted.';
COMMENT ON COLUMN assignment.latepenalty IS
'NULL if there is no soft-deadline. Otherwise, the penalty in percentages for each late day.';




--
-- Submission
--
CREATE TABLE submission
(
    submission_id       BIGSERIAL       PRIMARY KEY,
    assignment_id       VARCHAR(8)      NOT NULL,
    course_id           VARCHAR(16)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    content             VARCHAR(255)    NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified            TIMESTAMP       NULL,
    state               VARCHAR(10)     NOT NULL DEFAULT 'draft',
    evaluator           VARCHAR(10)     NULL,
    score               INTEGER         NULL,
    feedback            VARCHAR(10000)  NULL,
    confidential_notes  VARCHAR(5000)   NULL,
    FOREIGN KEY (assignment_id, course_id)
        REFERENCES assignment (assignment_id, course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (course_id, uid)
        REFERENCES enrollee (course_id, uid)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT submission_state_chk
        CHECK (state IN ('draft', 'rejected', 'accepted')),
    CONSTRAINT submission_evaluator_chk
        CHECK (
            (state = 'draft' AND evaluator IS NULL AND score IS NULL) OR
            (state != 'draft' AND evaluator IS NOT NULL AND score IS NOT NULL)
        )
);
GRANT ALL PRIVILEGES ON submission TO schooner_dev;
GRANT SELECT, INSERT, UPDATE ON submission TO "www-data";

COMMENT ON TABLE submission IS
'Table structure does not prevent multiple submissions for each assignment. This must be possible, especially for the exam and its three attempts.';
COMMENT ON COLUMN submission.content IS
'Submission content can be path to file(s), identifier, actual submission from student - depending on the type of assignment.';
COMMENT ON COLUMN submission.state IS
'One of values "draft", "rejected", "accepted". Draft means that the submission requires evaluation (both .evaluator and .score must be NULL) while rejected and accepted mean that the submission is handled/evaluated (.evaluator and .score must have values). NOTE that accepted/rejected does not concern itself with the assignment.pass (minimum required score). To be rejected, something in the submission must prevent normal evaluation and a new submission is required.';
COMMENT ON COLUMN submission.evaluator IS
'SSO ID or handler.code of the evaluator. Handler codes are in capital letters, SSO ID is in lower case.';
COMMENT ON COLUMN submission.score IS
'Given score for the submission. Database does not limit the maximum (assignment.points) - this is a design decision that allows bonus points to be awarded. Any enforcement is left for the application code.';
COMMENT ON COLUMN submission.feedback IS
'Personal feedback from the evaluator.';
COMMENT ON COLUMN submission.confidential_notes IS
'Confidential notes shared between teachers and assistants. NOT SENT TO STUDENT!';

-- PostgreSQL does not support SQL triggers (surprisingly).
-- Each requires a trigger function...
CREATE OR REPLACE FUNCTION trfnc_submission_bru()
    RETURNS TRIGGER
    LANGUAGE PLPGSQL
AS $$
BEGIN
    NEW.modified = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER submission_bru
    BEFORE UPDATE
    ON submission
    FOR EACH ROW
    EXECUTE PROCEDURE trfnc_submission_bru();




--
-- Emails
--
CREATE TABLE email
(
    email_id            BIGSERIAL       PRIMARY KEY,
    course_id           VARCHAR(16)     NULL,
    uid                 VARCHAR(10)     NULL,
    sent_from           VARCHAR(64)     NOT NULL,
    sent_to             VARCHAR(320)    NOT NULL,
    subject             VARCHAR(255)    NOT NULL,
    body                VARCHAR(65536)  NULL,
    state               VARCHAR(8)      NOT NULL DEFAULT 'queued',
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by          TEXT            NOT NULL DEFAULT CURRENT_USER,
    sent_at             TIMESTAMP       NULL,
    FOREIGN KEY (course_id, uid)
        REFERENCES enrollee (course_id, uid)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT email_state_chk
        CHECK (state IN ('queued', 'failed', 'sent'))
);
GRANT ALL PRIVILEGES ON email TO schooner_dev;
GRANT SELECT, INSERT ON email TO "www-data";

COMMENT ON TABLE email IS
'Email cron job visits this table periodically to see .sent_at IS NULL rows (not yet sent) and sends them out.';
COMMENT ON COLUMN email.course_id IS
'Together with "uid", an optional reference that links the email to an enrolled student.';
COMMENT ON COLUMN email.uid IS
'Together with "course_id", an optional reference that links the email to an enrolled student.';
COMMENT ON COLUMN email.sent_from IS
'This should always be the course''s RT queue address, e.g., "dte20068@utu.fi".';
COMMENT ON COLUMN email.sent_to IS
'Single recipient email address. Maximum local part (before @) is 64 characters and maximum domain part is 255 characters.';
COMMENT ON COLUMN email.state IS
'All emails that have yet-to-be-sent are in state = ''queued''. Ignoring transient errors, the email cron job will set handled records either as ''failed'' (non-transient error) or ''sent'' if successfully sent.';


CREATE TABLE email_attachment
(
    email_id            BIGINT          NOT NULL,
    name                VARCHAR(255)    NOT NULL,
    content             BYTEA           NOT NULL,
    FOREIGN KEY (email_id)
        REFERENCES email (email_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT email_attachment_name_unq
        UNIQUE (email_id, name)
);
GRANT ALL PRIVILEGES ON email_attachment TO schooner_dev;
GRANT SELECT, INSERT ON email_attachment TO "www-data";

COMMENT ON TABLE email_attachment IS
'An email message may contain zero to N attachments. Create both email and email_attachment records in a single transaction to prevent the email cron job from sending the message while the attachment(s) are being inserted.';
COMMENT ON COLUMN email_attachment.name IS
'Filename of the attachment';
COMMENT ON COLUMN email_attachment.content IS
'Binary content of the attachment. BUT IS TEXT BETTER, IF CONTENT IS ENCODED ANYWAY?';

