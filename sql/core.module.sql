--
-- Schooner - Simple Course Management System
-- core.module.sql / Core table structure, PostgreSQL version
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--  2021-08-17  Updated.
--  2021-08-19  .github_account and .github_repository in enrollee.
--  2021-08-20  BIGINT PKs changed to INT.
--  2021-08-22  SERIAL changed to INTEGER GENERATED ALWAYS AS IDENTITY.
--  2021-08-23  Schema changed to 'core'.
--  2021-08-24  Add core.course: .email, .github_accout, and .github_accesstoken.
--  2021-08-25  Add core.course.enrollment_message.
--
-- Execute as 'schooner' (for ownership)
--
\echo 'Creating schema core'
DROP SCHEMA IF EXISTS core CASCADE;
CREATE SCHEMA core;
GRANT USAGE ON SCHEMA core TO "www-data";
GRANT USAGE ON SCHEMA core TO schooner_dev;

-- https://www.postgresql.org/docs/9.1/datatype-enum.html
CREATE TYPE active_t AS ENUM ('active', 'inactive');


--
-- Admin-privileged users
--
\echo '=== core.admin'
CREATE TABLE core.admin
(
    uid                 VARCHAR(10)     NOT NULL PRIMARY KEY,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active'
);
GRANT ALL PRIVILEGES ON core.admin TO schooner_dev;
GRANT SELECT ON core.admin TO "www-data";

COMMENT ON TABLE core.admin IS
'Table lists all SSO IDs that are granted administrator privileges in this system. Used by the web application SSO authentication module. NOTE: To-be swapped out for system.account and added with list of roles (instead of current three-tier model).';
COMMENT ON COLUMN core.admin.uid IS
'UTU SSO ID (aka. the login)';


--
-- Grading systems
--
\echo '=== core.gradesys'
CREATE TABLE core.gradesys
(
    gradesys_id         VARCHAR(8)      NOT NULL PRIMARY KEY,
    name                VARCHAR(64)     NOT NULL
);
GRANT ALL PRIVILEGES ON core.gradesys TO schooner_dev;
GRANT SELECT ON core.gradesys TO "www-data";

COMMENT ON TABLE core.gradesys IS
'Grading systems by name. See gradesys_criteria table for associated marks and required score percentages.';

INSERT INTO core.gradesys
VALUES
('0-5/60', 'Grades 0-5. Score of 60% is required to pass.'),
('0-5/50', 'Grades 0-5. Score of 50% is required to pass.'),
('F-P/60', 'FAIL/PASS. Score of 60% is required to pass.'),
('F-P/50', 'FAIL/PASS. Score of 50% is required to pass.');


\echo '=== core.gradesys_criteria'
CREATE TABLE core.gradesys_criteria
(
    gradesys_id         VARCHAR(8)      NOT NULL,
    mark                VARCHAR(10)     NOT NULL,
    score               NUMERIC(4,4)    NOT NULL,
    FOREIGN KEY (gradesys_id)
        REFERENCES core.gradesys (gradesys_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT grade_system_mark_unq
        UNIQUE (gradesys_id, mark)
);
GRANT ALL PRIVILEGES ON core.gradesys_criteria TO schooner_dev;
GRANT SELECT ON core.gradesys_criteria TO "www-data";

COMMENT ON TABLE core.gradesys_criteria IS
'Note that fail criteria is not recorded. If course points fail to reach any of the recorded criteria, it is a fail.';
COMMENT ON COLUMN core.gradesys_criteria.score IS
'Score percentage required to earn this mark.';
COMMENT ON COLUMN core.gradesys_criteria.mark IS
'Awarded grade. Commonly 0-5 or PASS/FAIL.';

INSERT INTO core.gradesys_criteria
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
\echo '=== core.course'
CREATE TABLE core.course
(
    course_id           VARCHAR(16)     NOT NULL PRIMARY KEY,
    code                VARCHAR(10)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    email               VARCHAR(64)     NULL,
    github_account      VARCHAR(40)     NULL,
    github_accesstoken  VARCHAR(255)    NULL,
    enrollment_message  VARCHAR(64)     NULL,
    opens               TIMESTAMP       NOT NULL,
    closes              TIMESTAMP       NULL,
    gradesys_id         VARCHAR(8)      NULL,
    description         VARCHAR(5000)   NULL,
    FOREIGN KEY (gradesys_id)
        REFERENCES core.gradesys (gradesys_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT course_begin_lte_end
        CHECK (closes IS NULL OR closes >= opens)
);
GRANT ALL PRIVILEGES ON core.course TO schooner_dev;
GRANT SELECT ON core.course TO "www-data";

COMMENT ON TABLE core.course IS
'Course instances (one per year/implementation). NOTE: Course total score is calculated from assignment table records.';
COMMENT ON COLUMN core.course.course_id IS
'Value should be the ID used in Peppi-system, "DTE20068-3002", for example.';
COMMENT ON COLUMN core.course.code IS
'Course code as it appears in Study Guide. "DTE20068", for example.';
COMMENT ON COLUMN core.course.name IS
'Course name as it appears in the Study Guid (in English).';
COMMENT ON COLUMN core.course.email IS
'The email address that will appear as sender in automated email messages.';
COMMENT ON COLUMN core.course.github_account IS
'GitHub account created for the course. Used to retrieve student repositories / exercises.';
COMMENT ON COLUMN core.course.github_accesstoken IS
'GitHub access token. Generated manually and stored here for GitHub API access use.';
COMMENT ON COLUMN core.course.enrollment_message IS
'Template id (email.template.template_id) which is used by enrollment mechanism to send a welcome message and/or instructions.';
COMMENT ON COLUMN core.course.opens IS
'Use period start date. Used to determine active/on-going courses.';
COMMENT ON COLUMN core.course.closes IS
'Can be set later. Used to determine active/on-going courses.';
COMMENT ON COLUMN core.course.gradesys_id IS
'Optional foreign key to gradesys -table to indicate which grading system the course uses.';
COMMENT ON COLUMN core.course.description IS
'Optional course description. There should not be much use for this field as all the pertinent information is made available in Moodle and/or APlus.';




--
-- Enrolled students
--
\echo '=== core.enrollee'
CREATE TABLE core.enrollee
(
    course_id           VARCHAR(16)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    studentid           VARCHAR(32)     NOT NULL,
    lastname            VARCHAR(32)     NOT NULL,
    firstname           VARCHAR(32)     NOT NULL,
    email               VARCHAR(64)     NULL,
    notifications       VARCHAR(10)     NOT NULL DEFAULT 'enabled',
    github_account      VARCHAR(40)     NULL,
    github_repository   VARCHAR(100)    NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, uid),
    FOREIGN KEY (course_id)
        REFERENCES core.course (course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT course_github_account_unq
        UNIQUE (course_id, github_account),
    CONSTRAINT course_studentid_unq
        UNIQUE (course_id, studentid),
    CONSTRAINT course_email_unq
        UNIQUE (course_id, email),
    CONSTRAINT enrollee_notifications_chk
        CHECK (notifications IN ('enabled', 'disabled'))
);
GRANT ALL PRIVILEGES ON core.enrollee TO schooner_dev;
GRANT SELECT, UPDATE ON core.enrollee TO "www-data";

COMMENT ON TABLE core.enrollee IS
'List of students enrolled to a course. NOTE: Redundant information for same student enrolled again, or in a different course, is accepted.';
COMMENT ON COLUMN core.enrollee.uid IS
'UTU ID, also known as the user name. The name used in the short email address.What is used to login to UTU SSO.';
COMMENT ON COLUMN core.enrollee.github_account IS
'Not NULL if account registration has been successfully handled. GitHub account name. Min: 1, max: 39, can contain: a-z A-Z 0-0 "-" but cannot start with dash character.';
COMMENT ON COLUMN core.enrollee.github_repository IS
'Not NULL if account registration has been successfully handled. GitHub maximum repository name length is 100 characters.';
COMMENT ON COLUMN core.enrollee.studentid IS
'Required to send grades. Possibly always numeric and up to 7 digits long. This solution acceptes strings up to 10 characters.';
COMMENT ON COLUMN core.enrollee.email IS
'Email should always be available from Peppi registration export, but this column may be NULL''ed, if student either does not want the email to be recorded, or prefers to make sure never to receive any notifications. Should mostly be {uid}@utu.fi';
COMMENT ON COLUMN core.enrollee.notifications IS
'Simple ''enabled''/''disabled'' setting that controls if the enrollee is sent automated notifications.';
COMMENT ON COLUMN core.enrollee.status IS
'Can be set to "inactive", if the student explicitly requests to be dropped from the course. Primarily used to enable/disable deadline email notifications.';



--
-- Assignment Handlers
--
\echo '=== core.handler'
CREATE TABLE core.handler
(
    code                VARCHAR(8)      NOT NULL PRIMARY KEY,
    name                VARCHAR(32)     NOT NULL UNIQUE,
    description         VARCHAR(5000)   NULL
);
GRANT ALL PRIVILEGES ON core.handler TO schooner_dev;
GRANT SELECT ON core.handler TO "www-data";

COMMENT ON TABLE core.handler IS
'Each type of a submission handling has its own code which allows background tasks and web forms to recognize assignments that they need to handle.';
COMMENT ON COLUMN core.handler.description IS
'Contents of this column should not be necessary to display to a student, but the explanations are likely very useful for a teacher who is recording the assignments.';

INSERT INTO core.handler
VALUES
('HUBREG',   'GitHub account registrations', 'Match registered Git accounts with pending collaborator invitations to complete the registration.'),
('HUBBOT',   'GitHub exercise retriever', 'Retrieve assignment submissions from Git repository on deadlines.'),
('APLUS',    'APlus Quizz score retriever', 'Scores are retrieved from APlus automatically.'),
('ASSETMGR', 'Asset Manager', 'Loaning assets / study materials (''draft'') and return tracking (''accepted'').');


--
-- Assignments (tasks, exercises, quizzes, exams, ...)
--
\echo '=== core.assignment'
CREATE TABLE core.assignment
(
    assignment_id       VARCHAR(16)     NOT NULL,
    course_id           VARCHAR(16)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    description         VARCHAR(5000)   NULL,
    handler             VARCHAR(8)      NULL,
    points              INTEGER         NOT NULL,
    pass                INTEGER         NULL,
    retries             INTEGER         NULL DEFAULT 0,
    deadline            DATE            NOT NULL,
    latepenalty         DECIMAL(3,3)    NULL,
    evaluation          VARCHAR(8)      NOT NULL DEFAULT 'best',
    PRIMARY KEY (assignment_id, course_id),
    FOREIGN KEY (course_id)
        REFERENCES core.course (course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (handler)
        REFERENCES core.handler (code)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT assignment_pass_lte_points
        CHECK (pass IS NULL OR pass <= points),
    CONSTRAINT assignment_retries_chk
        CHECK (retries IS NULL OR retries >= 0),
    CONSTRAINT assignment_latepenalty_chk
        CHECK (latepenalty IS NULL OR latepenalty > 0),
    CONSTRAINT assignment_evaluation_chk
        CHECK (evaluation IN ('first', 'last', 'best', 'worst'))
);
GRANT ALL PRIVILEGES ON core.assignment TO schooner_dev;
GRANT SELECT ON core.assignment TO "www-data";

COMMENT ON TABLE core.assignment IS
'Tasks, exercices, quizzes, exams, etc. Sum of points -column dictates the course total points.';
COMMENT ON COLUMN core.assignment.assignment_id IS
'For easier reading (the database directly, aka. debugging), use shorthand sumbols as T01 for tasks, Q01 for quizzes, E01 for exercises, etc.';
COMMENT ON COLUMN core.assignment.name IS
'Name of the assignment as it appears in the Moodle course description.';
COMMENT ON COLUMN core.assignment.handler IS
'NULL if submissions for this assignment are manually recorded. Otherwise, the code of the appropriate automation service (see "handler" table).';
COMMENT ON COLUMN core.assignment.points IS
'Maximum points that can be earned from the assignment.';
COMMENT ON COLUMN core.assignment.pass IS
'Minimum points to pass the assignment. Zero if any submission will do and NULL if the assignment is optional.';
COMMENT ON COLUMN core.assignment.retries IS
'Number of allowed retries after the first submission. Zero means no retries (only one submission allowed). NULL means unlimited.';
COMMENT ON COLUMN core.assignment.deadline IS
'NOTE: Current implementation ignores time part. Date during which the assignment must be submitted.';
COMMENT ON COLUMN core.assignment.latepenalty IS
'NULL if there is no soft-deadline. Otherwise, the penalty in percentages for each late day.';

-- Allow only one 'HUBREG' assignment per course
CREATE UNIQUE INDEX assignment_single_hubreg_idx
    ON core.assignment (course_id, handler)
    WHERE (handler = 'HUBREG');
COMMENT ON INDEX core.assignment_single_hubreg_idx IS
'Unique index ensuring that no course will have more than one ''HUBREG'' assignment.';


--
-- Calculate last submission retrieval date
--
\echo '=== core.submission_last_retrieval_date()'
CREATE OR REPLACE FUNCTION
core.submission_last_retrieval_date(
    in_deadline         DATE,
    in_penalty          NUMERIC
)
    RETURNS DATE
    LANGUAGE PLPGSQL
    SECURITY INVOKER
    VOLATILE
    CALLED ON NULL INPUT
AS $$
-- Assignment that has a deadline DATE X will be retrieved right after
-- midnight, or X + 1.
-- If the assignment has been defined with soft deadline (.latepenalty),
-- the number of additional days is calculated: 
BEGIN
    IF in_deadline IS NULL THEN
        RETURN NULL;
    ELSIF in_penalty IS NULL THEN
        RETURN in_deadline + 1;
    END IF;
    
    RETURN in_deadline + CEIL(1 / in_penalty)::INTEGER;
END;
$$;
GRANT EXECUTE ON FUNCTION core.submission_last_retrieval_date TO "www-data";
GRANT EXECUTE ON FUNCTION core.submission_last_retrieval_date TO schooner_dev;

-- select course_id, assignment_id, deadline, latepenalty, core.submission_last_retrieval_date(deadline::DATE, latepenalty::DECIMAL) from core.assignment;



--
-- Submission
--
\echo '=== core.submission'
CREATE TABLE core.submission
(
    submission_id       INTEGER         GENERATED ALWAYS AS IDENTITY,
    assignment_id       VARCHAR(16)     NOT NULL,
    course_id           VARCHAR(16)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    content             VARCHAR(255)    NOT NULL,
    submitted           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted            TIMESTAMP       NULL,
    state               VARCHAR(10)     NOT NULL DEFAULT 'draft',
    evaluator           VARCHAR(10)     NULL,
    score               INTEGER         NULL,
    feedback            VARCHAR(10000)  NULL,
    confidential        VARCHAR(5000)   NULL,
    PRIMARY KEY (submission_id),
    FOREIGN KEY (assignment_id, course_id)
        REFERENCES core.assignment (assignment_id, course_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (course_id, uid)
        REFERENCES core.enrollee (course_id, uid)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT submission_state_chk
        CHECK (state IN ('draft', 'rejected', 'accepted')),
    CONSTRAINT submission_evaluator_chk
        CHECK (
            (state = 'draft' AND evaluator IS NULL AND score IS NULL) OR
            (state != 'draft' AND evaluator IS NOT NULL AND score IS NOT NULL)
        ),
    CONSTRAINT submission_accepted_chk
        CHECK (accepted IS NULL OR accepted >= submitted)
);
GRANT ALL PRIVILEGES ON core.submission TO schooner_dev;
GRANT SELECT, INSERT, UPDATE ON core.submission TO "www-data";


COMMENT ON TABLE core.submission IS
'Number of submissions for each assignment defined by assignment.retries. Only ''draft'' state submissions may be updated.';
COMMENT ON COLUMN core.submission.content IS
'Submission content can be path to file(s), identifier, actual submission from student - depending on the type of assignment.';
COMMENT ON COLUMN core.submission.submitted IS
'Date and time of the submission. Important for (soft)deadline and score calculations.';
COMMENT ON COLUMN core.submission.accepted IS
'Date and time set when the submission state becomes ''accepted''';
COMMENT ON COLUMN core.submission.state IS
'One of "draft", "rejected", or "accepted". Draft means that the submission requires evaluation (both .evaluator and .score must be NULL) while rejected and accepted mean that the submission is handled/evaluated (.evaluator and .score must have values). NOTE that accepted/rejected does not concern itself with the assignment.pass (minimum required score). To be rejected, something in the submission must prevent normal evaluation and a new submission is required.';
COMMENT ON COLUMN core.submission.evaluator IS
'SSO ID or handler.code of the evaluator. Handler codes are in capital letters, SSO ID is in lower case.';
COMMENT ON COLUMN core.submission.score IS
'Given score for the submission. Database does not limit the maximum (assignment.points) - this is a design decision that allows bonus points to be awarded. Any enforcement is left for the application code.';
COMMENT ON COLUMN core.submission.feedback IS
'Personal feedback from the evaluator.';
COMMENT ON COLUMN core.submission.confidential IS
'Confidential notes shared between teachers and assistants. NOT SENT TO STUDENT!';

-- PostgreSQL does not support SQL triggers (surprisingly).
-- Each requires a trigger function...
\echo '=== core.submission_bru()'
CREATE OR REPLACE FUNCTION core.submission_bru()
    RETURNS TRIGGER
    LANGUAGE PLPGSQL
AS $$
BEGIN
    -- TODO: allow for NEW.evaluator IN admin
    IF OLD.state != 'draft' THEN
        RAISE EXCEPTION
        'Submission (%) is not in ''draft'' state and cannot be updated!',
        OLD.submission_id
        USING HINT = 'SUBMISSION_NOT_DRAFT';
    END IF;
    -- Draft becomes Accepted
    IF NEW.state = 'accepted' THEN
        NEW.accepted := CURRENT_TIMESTAMP;
        IF NEW.evaluator IS NULL THEN
            NEW.evaluator = CURRENT_USER;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER submission_bru
    BEFORE UPDATE
    ON core.submission
    FOR EACH ROW
    EXECUTE PROCEDURE core.submission_bru();



\echo '=== core.submission_bri()'
CREATE OR REPLACE FUNCTION core.submission_bri()
    RETURNS TRIGGER
    LANGUAGE PLPGSQL
AS $$
-- This trigger does not concern itself with deadlines.
-- Submissions past their deadlines are accepted.
-- Application code needs to deal with them accordingly.
DECLARE
    v_retries       INT;
    v_submissions   INT;
    v_drafts        INT;
BEGIN
    SELECT      assignment.retries
    FROM        core.assignment
    WHERE       assignment_id = NEW.assignment_id
                AND
                course_id = NEW.course_id
    INTO v_retries;
    SELECT      COUNT(submission_id),
                SUM(
                    CASE
                        WHEN state = 'draft' THEN 1
                        ELSE 0
                    END
                )
    FROM        core.submission
    WHERE       assignment_id = NEW.assignment_id
                AND
                course_id = NEW.course_id
                AND
                uid = NEW.uid
    INTO        v_submissions,
                v_drafts;
    IF v_retries IS NOT NULL THEN
        -- Enforce submission retry limit
        IF v_submissions > v_retries THEN
            RAISE EXCEPTION
                'Maximum number of submissions (%) already created for course (''%'') assignment (''%'') by enrollee (''%'')!',
                v_retries + 1, NEW.course_id, NEW.assignment_id, NEW.uid
                USING HINT = 'RETRIES_EXHAUSTED';
        END IF;
    END IF;
    -- Do not allow new submission while a 'draft' exists, regardless what the NEW.state is
    IF v_drafts > 0 THEN
        RAISE EXCEPTION
            'No new submissions are accepted while ''draft'' submission exists!'
            USING HINT = 'DRAFT_EXISTS';
    END IF;
    -- Enforce .accepted integrity
    IF NEW.state = 'accepted' THEN
        NEW.accepted := CURRENT_TIMESTAMP;
    ELSE
        NEW.accepted := NULL;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER submission_bri
    BEFORE INSERT
    ON core.submission
    FOR EACH ROW
    EXECUTE PROCEDURE core.submission_bri();

COMMENT ON TRIGGER submission_bri ON core.submission IS
'Trigger limits the number of submissions based on assignment.retries (NULL = unlimited). It also prevents inserting new submissions if ''draft'' exists. They must be evaluated into ''acceted'' or ''rejected'' before new can be entered.';


CREATE OR REPLACE PROCEDURE
core.register_github(
    in_submission_id        INTEGER,
    in_github_repository    VARCHAR(100)
)
    LANGUAGE PLPGSQL
    SECURITY INVOKER
AS $$
DECLARE
    r_assignment        RECORD;
    r_submission        RECORD;
BEGIN
    SELECT      *
    FROM        core.submission
    WHERE       submission_id = in_submission_id
    INTO        r_submission
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Submission (%) not found!',
            in_submission_id
            USING HINT = 'SUBMISSION_NOT_FOUND';
    ELSIF r_submission.state != 'draft' THEN
        RAISE EXCEPTION
            'Submission (%) state is ''%''. Only ''draft'' submission can be accepted!',
            in_submission_id, r_submission.state
            USING HINT = 'SUBMISSION_NOT_DRAFT';
    END IF;
    -- Locking two rows in two tables is not possible.
    -- This is the next best thing...
    PERFORM
    FROM        core.enrollee
    WHERE       uid = r_submission.uid
                AND
                course_id = r_submission.course_id
    FOR UPDATE;

    SELECT      *
    FROM        core.assignment
    WHERE       assignment_id = r_submission.assignment_id
                AND
                course_id = r_submission.course_id
    INTO        r_assignment;

    UPDATE      core.submission
    SET         state = 'accepted',
                evaluator = 'HUBREG',
                score = r_assignment.points
    WHERE       submission_id = in_submission_id;

    UPDATE      core.enrollee
    SET         github_account = r_submission.content,
                github_repository = in_github_repository
    WHERE       uid = r_submission.uid
                AND
                course_id = r_submission.course_id;

END;
$$;
GRANT EXECUTE ON PROCEDURE core.register_github TO "www-data";
GRANT EXECUTE ON PROCEDURE core.register_github TO schooner_dev;

\echo '=== core.submission_adjusted_score()'
CREATE OR REPLACE FUNCTION
core.submission_adjusted_score(
    in_submission_id    INTEGER
)
    RETURNS NUMERIC
    LANGUAGE PLPGSQL
    SECURITY INVOKER
    VOLATILE
    STRICT
AS $$
-- Compares assignment.deadline to submission.submitted and applies
-- latepenalty to the score.
-- There is no need to worry about multiple submissions because this
-- function deals with submission PK (caller's headache to pick the one).
-- NOTE: Hubbot will record submitted values as the last second of yesterday
-- because it runs exactly after midnight (after the deadline has been passed).
DECLARE
    r_submission        RECORD;
BEGIN
    IF in_submission_id IS NULL THEN
        RETURN NULL;
    END IF;
    SELECT      submission.submitted::DATE AS submitted,
                assignment.deadline,
                assignment.latepenalty,
                assignment.points AS max_score,
                submission.score,
                submission.state,
                submission.submitted::DATE - assignment.deadline AS days_late
    FROM        core.submission
                INNER JOIN core.assignment
                ON (
                    submission.assignment_id = assignment.assignment_id
                    AND
                    submission.course_id = assignment.course_id
                )
    WHERE       submission_id = in_submission_id
    INTO        r_submission;
    IF NOT FOUND THEN
        RETURN NULL;
    ELSIF r_submission.score IS NULL THEN
        RETURN NULL;
    ELSIF r_submission.days_late <= 0 THEN
        -- Not late, no adjustments
        RETURN r_submission.score;
    END IF;

    -- LATE submissions
    IF r_submission.latepenalty IS NULL THEN
        -- Late and no soft deadline => no points!
        RETURN 0;
    ELSIF r_submission.days_late * r_submission.latepenalty >= 1.0 THEN
        -- Too late for soft deadline
        RETURN 0;
    END IF;

    -- Is late and within soft deadline
    RETURN (
        r_submission.score * (
            1 - r_submission.days_late * r_submission.latepenalty
        )
    );
END;
$$;
GRANT EXECUTE ON FUNCTION core.submission_last_retrieval_date TO "www-data";
GRANT EXECUTE ON FUNCTION core.submission_last_retrieval_date TO schooner_dev;


-- call core.enrol('DTE20068-3002', 'dodo', '9137192', 'dodo@null', 'Do', 'Doris');
\echo '=== core.enrol()'
CREATE OR REPLACE PROCEDURE
core.enrol(
    in_course_id            VARCHAR(16),
    in_uid                  VARCHAR(10),
    in_student_id           VARCHAR(32),
    in_email                VARCHAR(64),
    in_lastname             VARCHAR(32),
    in_firstname            VARCHAR(32),
    in_update_existing      BOOLEAN DEFAULT FALSE
)
    LANGUAGE PLPGSQL
    SECURITY INVOKER
AS $$
BEGIN
    PERFORM     *
    FROM        core.enrollee
    WHERE       course_id = in_course_id
                AND
                uid = in_uid
    FOR UPDATE;
    IF NOT FOUND THEN
        INSERT INTO core.enrollee
        (
            course_id,
            uid,
            studentid,
            email,
            lastname,
            firstname
        )
        VALUES
        (
            in_course_id,
            in_uid,
            in_student_id,
            in_email,
            in_lastname,
            in_firstname
        );
    ELSE
        IF in_update_existing THEN
            UPDATE  core.enrollee
            SET     studentid   = in_student_id,
                    email       = in_email,
                    lastname    = in_lastname,
                    firstname   = in_firstname
            WHERE   course_id   = in_course_id
                    AND
                    uid         = in_uid;
        ELSE
            RAISE EXCEPTION
                'Enrollee (''%'', ''%'') already exists!',
                in_course_id, in_uid
                USING HINT = 'ENROLLEE_ALREDY_EXISTS';
        END IF;
    END IF;
END
$$;
GRANT EXECUTE ON PROCEDURE core.enrol TO schooner_dev;

COMMENT ON PROCEDURE core.enrol IS
'Creates (or updates) an enrollment for a single student.';


-- Last accepted submission
\echo '=== VIEW core.last_accepted_submission'
CREATE VIEW core.last_accepted_submission AS
SELECT      submission.submission_id,
            submission.course_id,
            submission.assignment_id,
            submission.uid,
            submission.submitted,
            submission.submitted::DATE - assignment.deadline AS days_late,
            assignment.latepenalty,
            submission.score,
            core.submission_adjusted_score(submission.submission_id) AS adjusted_score,
            assignment.points as max_score
FROM        core.submission
            INNER JOIN core.assignment
            ON (
            	submission.assignment_id = assignment.assignment_id
                AND
                submission.course_id = assignment.course_id
            )
WHERE       submitted = (
                SELECT      MAX(submitted)
                FROM        core.submission s
                WHERE       s.course_id = submission.course_id
                            AND
                            s.assignment_id = submission.assignment_id
                            AND
                            s.uid = submission.uid
                            AND
                            s.state = 'accepted'
            );
GRANT SELECT ON core.last_accepted_submission TO schooner_dev;
GRANT SELECT ON core.last_accepted_submission TO "www-data";

COMMENT ON VIEW core.last_accepted_submission IS
'Please note that this view WILL show unfavorable results for students, especially if there is an accepted submission after (soft) deadline (score will be zero). Consider using view core.best_accepted_submission.';



\echo '=== VIEW core.best_accepted_submission'
CREATE VIEW core.best_accepted_submission AS
SELECT      submission.submission_id,
            submission.course_id,
            submission.assignment_id,
            submission.uid,
            submission.submitted,
            submission.submitted::DATE - assignment.deadline AS days_late,
            assignment.latepenalty,
            submission.score,
            core.submission_adjusted_score(submission.submission_id) AS adjusted_score,
            assignment.points as max_score
FROM        core.submission
            INNER JOIN core.assignment
            ON (
                submission.assignment_id = assignment.assignment_id
                AND
                submission.course_id = assignment.course_id
            )
WHERE       submitted = (
                SELECT      MIN(submitted)
                FROM        core.submission s1
                WHERE       core.submission_adjusted_score(submission_id) = (
                                SELECT      MAX(core.submission_adjusted_score(submission_id))
                                FROM        core.submission s2
                                WHERE       s1.course_id = s2.course_id
                                            AND
                                            s1.assignment_id = s2.assignment_id
                                            AND
                                            s1.uid = s2.uid
                                            AND
                                            s2.state = 'accepted'
                            )
                            AND
                            submission.course_id = s1.course_id
                            AND
                            submission.assignment_id = s1.assignment_id
                            AND
                            submission.uid = s1.uid
                            AND
                            s1.state = 'accepted'
            );
GRANT SELECT ON core.best_accepted_submission TO schooner_dev;
GRANT SELECT ON core.best_accepted_submission TO "www-data";

COMMENT ON VIEW core.best_accepted_submission IS
'This view can be used to calculate course score. Adjusted score ensures that points cannot be accrued if the deadline or soft deadline has been missed.';


\echo '=== VIEW core.last_accepted_submission'
CREATE OR REPLACE VIEW core.ongoing_courses AS
SELECT      course.course_id,
            course.code,
            course.name,
            course.closes,
            count(enrollee.uid) AS n_enrolled
FROM        core.course
            LEFT OUTER JOIN core.enrollee
            ON (course.course_id = enrollee.course_id)
WHERE       course.opens <= CURRENT_TIMESTAMP
            AND
            (
                course.closes IS NULL
                OR
                course.closes >= CURRENT_TIMESTAMP
            )
GROUP BY    course.course_id,
            course.code,
            course.name,
            course.closes;
GRANT SELECT ON core.ongoing_courses TO schooner_dev;
GRANT SELECT ON core.ongoing_courses TO "www-data";



\echo '=== core.asset_claim()'
CREATE OR REPLACE FUNCTION
core.asset_claim(
    in_course_id        VARCHAR,
    in_assignment_id    VARCHAR,
    in_uid              VARCHAR,
    in_content          VARCHAR,
    in_confidential     VARCHAR DEFAULT NULL
)
    RETURNS INTEGER
    LANGUAGE PLPGSQL
    SECURITY INVOKER
    VOLATILE
    CALLED ON NULL INPUT
AS $$
-- Creates a 'draft' submission for a handler = 'ASSETMGR' assignment which
-- records (submission.content) the asset ID (if any).
-- Use asset_return() function to record (state = 'accepted') the return of
-- the loaned item(s).
-- Returns the submission_id of the created record.
DECLARE
    v_submission_id INTEGER;
    v_count         INTEGER;
BEGIN
    SELECT      submission.submission_id
    FROM        core.assignment
                LEFT OUTER JOIN (
                    SELECT      *
                    FROM        core.submission
                    WHERE       submission.state = 'draft'
                                AND
                                uid = in_uid
                ) submission
                ON (
                    assignment.course_id = submission.course_id
                    AND
                    assignment.assignment_id = submission.assignment_id
                )
    WHERE       assignment.course_id = in_course_id
                AND
                assignment.assignment_id = in_assignment_id
                AND
                assignment.handler = 'ASSETMGR'
    INTO        v_submission_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Asset assignment (''%'', ''%'') not found or has incorrect handler!',
            in_course_id, in_assignment_id
            USING HINT = 'ASSIGNMENT_NOT_FOUND';
    ELSEIF v_submission_id IS NOT NULL THEN
        RAISE EXCEPTION
            'Student (''%'') already has assets on loan (#%)!',
            in_uid, v_submission_id
            USING HINT = 'ASSETS_ALREADY_CLAIMED';
    END IF;
    -- create new record
    INSERT INTO core.submission
    (
        course_id,
        assignment_id,
        uid,
        content,
        confidential
    )
    VALUES
    (
        in_course_id,
        in_assignment_id,
        in_uid,
        in_content,
        in_confidential
    )
    RETURNING submission_id
    INTO v_submission_id;
    RETURN v_submission_id;
END;
$$;
GRANT EXECUTE ON FUNCTION core.asset_claim TO "www-data";
GRANT EXECUTE ON FUNCTION core.asset_claim TO schooner_dev;


\echo '=== core.asset_return()'
CREATE OR REPLACE PROCEDURE
core.asset_return(
    in_submission_id    INTEGER,
    in_feedback         VARCHAR DEFAULT NULL,
    in_confidential     VARCHAR DEFAULT NULL
)
    LANGUAGE PLPGSQL
    SECURITY INVOKER
AS $$
-- Sets 'draft' submission for a handler = 'ASSETMGR' assignment to
-- 'accepted' and credits it with assignment.score, unless deadline has
-- been passed.
DECLARE
    r_record    RECORD;
    v_points    INTEGER;
BEGIN
    SELECT      assignment.points,
                assignment.deadline
    FROM        core.submission
                INNER JOIN core.assignment
                ON (
                    submission.course_id = assignment.course_id
                    AND
                    submission.assignment_id = assignment.assignment_id
                )
    WHERE       submission.submission_id = in_submission_id
                AND
                assignment.handler = 'ASSETMGR'
    INTO        r_record;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Submission #% not found or has incorrect handler!',
            in_submission_id
            USING HINT = 'SUBMISSION_NOT_FOUND';
    ELSEIF r_record.deadline < CURRENT_TIMESTAMP THEN
        v_points = 0;
    ELSE
        v_points = r_record.points;
    END IF;
    UPDATE      core.submission
    SET         state = 'accepted',
                score = v_points,
                evaluator = CURRENT_USER,
                feedback = in_feedback,
                confidential = in_confidential
    WHERE       submission_id = in_submission_id;
END;
$$;
GRANT EXECUTE ON PROCEDURE core.asset_return TO "www-data";
GRANT EXECUTE ON PROCEDURE core.asset_return TO schooner_dev;




\echo '=== core.course_purge()'
CREATE OR REPLACE PROCEDURE
core.course_purge(
    in_course_id        VARCHAR
)
    LANGUAGE PLPGSQL
    SECURITY INVOKER
AS $$
-- Normally, a course -table record cannot be deleted when enrollee
-- table has referencing records (so that a course is not accidentally
-- deleted along with student course data).
-- This procedure will clean up all data related to the designated
-- course.
DECLARE
    r_enrollee      RECORD;
BEGIN
    -- Delete submissions
    FOR r_enrollee IN
        SELECT      uid
        FROM        core.enrollee
        WHERE       course_id = in_course_id
    LOOP
        DELETE
        FROM        core.submission
        WHERE       course_id = in_course_id
                    AND
                    uid = r_enrollee.uid;
    END LOOP;
    -- Delete enrollees
    DELETE
    FROM            core.enrollee
    WHERE           course_id = in_course_id;
    -- Delete assignment
    DELETE
    FROM            core.assignment
    WHERE           course_id = in_course_id;
    -- Delete course
    DELETE
    FROM            core.course
    WHERE           course_id = in_course_id;
END;
$$;
-- Grant noone any privileges - this must be executed as database owner.



-- EOF