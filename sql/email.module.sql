--
-- Schooner - Simple Course Management System
-- email.module.sql / Email messages schema, PostgreSQL version
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-23  Initial version.
--  2021-08-24  Fix GRANT on email.template.
--  2021-08-25  Restructured attachment storage.
--  2021-08-28  jtd_submission_rec() and jtd_course_welcome_rec().
--
\echo 'Creating schema email'
DROP SCHEMA IF EXISTS email CASCADE;
CREATE SCHEMA email;
GRANT USAGE ON SCHEMA email TO "www-data";
GRANT USAGE ON SCHEMA email TO schooner_dev;


\echo '=== email.message'
CREATE TABLE email.message
(
    message_id          INTEGER         GENERATED ALWAYS AS IDENTITY,
    course_id           VARCHAR(16)     NULL,
    uid                 VARCHAR(10)     NULL,
    mimetype            VARCHAR(10)     NOT NULL DEFAULT 'text/plain',
    priority            VARCHAR(6)      NOT NULL DEFAULT 'normal',
    sent_from           VARCHAR(64)     NOT NULL,
    sent_to             VARCHAR(10000)  NOT NULL,
    subject             VARCHAR(255)    NOT NULL,
    body                VARCHAR(65536)  NULL,
    retry_count         INTEGER         NOT NULL DEFAULT 3,
    state               VARCHAR(8)      NOT NULL DEFAULT 'queued',
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by          TEXT            NOT NULL DEFAULT CURRENT_USER,
    sent_at             TIMESTAMP       NULL,
    PRIMARY KEY (message_id),
    FOREIGN KEY (course_id, uid)
        REFERENCES core.enrollee (course_id, uid)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT message_state_chk
        CHECK (state IN ('queued', 'failed', 'sent')),
    CONSTRAINT message_mimetype_chk
        CHECK (mimetype IN ('text/plain', 'text/html')),
    CONSTRAINT message_priority_chk
        CHECK (priority IN ('low', 'normal', 'high'))
);
GRANT ALL PRIVILEGES ON email.message TO schooner_dev;
GRANT SELECT, INSERT, UPDATE ON email.message TO "www-data";

COMMENT ON TABLE email.message IS
'Email cron job visits this table periodically to see .sent_at IS NULL rows (not yet sent) and sends them out.';
COMMENT ON COLUMN email.message.course_id IS
'Together with "uid", an optional reference that links the email to an enrolled student.';
COMMENT ON COLUMN email.message.uid IS
'Together with "course_id", an optional reference that links the email to an enrolled student.';
COMMENT ON COLUMN email.message.mimetype IS
'MIME type of the message text. Either ''text/plain'' or ''text/html''';
COMMENT ON COLUMN email.message.sent_from IS
'This should always be the course''s RT queue address, e.g., "dte20068@utu.fi".';
COMMENT ON COLUMN email.message.sent_to IS
'Single recipient or comma separated list of email address. Maximum local part (before @) is 64 characters and maximum domain part is 255 characters.';
COMMENT ON COLUMN email.message.state IS
'All emails that have yet-to-be-sent are in state = ''queued''. Ignoring transient errors, the email cron job will set handled records either as ''failed'' (non-transient error) or ''sent'' if successfully sent.';

\echo '=== email.message_bru()'
CREATE OR REPLACE FUNCTION email.message_bru()
    RETURNS TRIGGER
    LANGUAGE PLPGSQL
AS $$
BEGIN
    IF OLD.state = 'queued' AND NEW.state = 'sent' THEN
        NEW.sent_at = CURRENT_TIMESTAMP;
    END IF;
    IF OLD.state = 'queued' AND NEW.retry_count < 1 THEN
        NEW.state = 'failed';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER message_bru
    BEFORE UPDATE
    ON email.message
    FOR EACH ROW
    EXECUTE PROCEDURE email.message_bru();




\echo '=== email.attachment'
CREATE TABLE email.attachment
(
    attachment_id       INTEGER         GENERATED ALWAYS AS IDENTITY,
    name                VARCHAR(255)    NOT NULL,
    content             BYTEA           NOT NULL,
    PRIMARY KEY (attachment_id)
);
GRANT ALL PRIVILEGES ON email.attachment TO schooner_dev;
GRANT SELECT, INSERT ON email.attachment TO "www-data";

COMMENT ON TABLE email.attachment IS
'An attachment is often used by multiple messages and possibly multiple templates. For this reason, updating this table is strictly forbidden.';
COMMENT ON COLUMN email.attachment.name IS
'Filename of the attachment';
COMMENT ON COLUMN email.attachment.content IS
'Binary content of the attachment.';




\echo '=== email.template'
CREATE TABLE email.template
(
    template_id         VARCHAR(64)     NOT NULL,
    mimetype            VARCHAR(10)     NOT NULL DEFAULT 'text/plain',
    priority            VARCHAR(6)      NOT NULL DEFAULT 'normal',
    subject             VARCHAR(255)    NOT NULL,
    body                VARCHAR(65536)  NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified            TIMESTAMP       NULL,
    PRIMARY KEY (template_id),
    CONSTRAINT template_uppercase_id_chk
        CHECK (UPPER(template_id) = template_id),
    CONSTRAINT template_mimetype_chk
        CHECK (mimetype IN ('text/plain', 'text/html')),
    CONSTRAINT template_priority_chk
        CHECK (priority IN ('low', 'normal', 'high'))
);
GRANT ALL PRIVILEGES ON email.template TO schooner_dev;
GRANT SELECT ON email.template TO "www-data";

COMMENT ON TABLE email.template IS
'Templates are parsed as Jinja2. Mostly intended for automated email messages.';
COMMENT ON COLUMN email.template.template_id IS
'Descriptive short label that identifies the template.';


\echo '=== email.template_bru()'
CREATE OR REPLACE FUNCTION email.template_bru()
    RETURNS TRIGGER
    LANGUAGE PLPGSQL
AS $$
BEGIN
    NEW.modified = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER template_bru
    BEFORE UPDATE
    ON email.template
    FOR EACH ROW
    EXECUTE PROCEDURE email.template_bru();




\echo '=== email.attached'
CREATE TABLE email.attached
(
    attachment_id       INTEGER         NOT NULL,
    message_id          INTEGER         NULL,
    template_id         VARCHAR(64)     NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attachment_id, message_id, template_id),
    FOREIGN KEY (attachment_id)
        REFERENCES email.attachment (attachment_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    FOREIGN KEY (message_id)
        REFERENCES email.message (message_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (template_id)
        REFERENCES email.template (template_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT included_in_message_or_template_chk
        CHECK (
            message_id IS NULL AND template_id IS NOT NULL
            OR
            message_id IS NOT NULL AND template_id IS NULL
        )
);
GRANT ALL PRIVILEGES ON email.attached TO schooner_dev;
GRANT SELECT, INSERT, DELETE ON email.attached TO "www-data";




\echo '=== VIEW email.attachment_usage'
CREATE OR REPLACE VIEW email.attachment_usage AS
SELECT      name,
            LENGTH(content) AS size,
            COUNT(message_id) AS message_use_count,
            COUNT(template_id) AS template_use_count
FROM        email.attachment
            LEFT OUTER JOIN email.attached
            ON (attachment.attachment_id = attached.attachment_id)
GROUP BY    name,
            size;
GRANT ALL PRIVILEGES ON email.attachment_usage TO schooner_dev;
GRANT SELECT ON email.attachment_usage TO "www-data";



CREATE OR REPLACE FUNCTION email.sendqueue()
    RETURNS SETOF email.message
    LANGUAGE PLPGSQL
AS $$
BEGIN
    RETURN QUERY
        WITH decrement_retry_count AS (
            UPDATE      email.message
            SET         retry_count = retry_count - 1
            WHERE       state != 'sent'
                        AND
                        retry_count > 0
            RETURNING   *
        )
        SELECT * FROM decrement_retry_count;
    RETURN;
END;
$$;
-- NO GRANTS TO ANYONE! This one will decrement retry count and
-- must be called only by the mailbot.py

COMMENT ON FUNCTION email.sendqueue IS
'Table of all ''queued'' messages that had retries left. IMPORTANT! This function decrements all retry_count values before yielding the table. Do not call unless you mean to send the messages!';


INSERT INTO email.template
(
    template_id,
    mimetype,
    priority,
    subject,
    body
)
VALUES
(
    'HUBREG',
    'text/plain',
    'normal',
    'Your GitHub account registration was successful!',
    'Matching collaborator invitation was found and your GitHub account {{ enrollee.github_account }} has been successfully registered. Your execises will be automatically retrieved from repository: {{ enrollee.github_repository }}.

Should you, for whatever reason, need to change your GitHub account or repository, you can always revisit https://schooner.utu.fi/register.html and issue a new registration. Just remember to make the corresponding collaborator invitation as well.

Regards,

{{ course.code }}
{{ course.email }}'
);



\echo '=== email.jtd_*'
--
-- Jinja Template Data
--
--      Functions standardizing the data when parsing Jinja email.template's.
--      Data entities are written as table/row PLPGSQL functions. All functions
--      return a TABLE, but uniquely identifiable entities do so with a single
--      row only.
--
--      jtd_<entity name>_rec()     Function returning a single row (record)
--                                  or raises an exception if not found.
--      jtd_<entity name>_tbl()     Funtion returns zero to N rows.
--
--      Column naming is specific in JTD_* functions. Each will be prefixed
--      with the table name (plus underscore) from where the data originates
--      from, even if a function is called.
--
--      Some conceptual renaming can be made. For example, the course.opens and
--      course.closes are called course_start and course_end, respectively.
--
CREATE OR REPLACE FUNCTION email.jtd_submission_rec(
    in_submission_id    INTEGER
)
    RETURNS TABLE
    (
        course_id                   VARCHAR,
        course_code                 VARCHAR,
        course_name                 VARCHAR,
        course_email                VARCHAR,
        course_github_account       VARCHAR,
        course_start                TIMESTAMP,
        course_end                  TIMESTAMP,
        enrollee_uid                VARCHAR,
        enrollee_studentid          VARCHAR,
        enrollee_lastname           VARCHAR,
        enrollee_firstname          VARCHAR,
        enrollee_email              VARCHAR,
        enrollee_notifications      VARCHAR,
        enrollee_github_account     VARCHAR,
        enrollee_github_repository  VARCHAR,
        enrollee_status             VARCHAR,
        assignment_id               VARCHAR,
        assignment_name             VARCHAR,
        assignment_handler          VARCHAR,
        assignment_max_score        INTEGER,
        assignment_score_to_pass    INTEGER,
        assignment_retries          INTEGER,
        assignment_deadline         DATE,
        assignment_latepenalty      NUMERIC,
        assignment_softdeadline     DATE,
        submission_id               INTEGER,
        submission_content          VARCHAR,
        submission_submitted        TIMESTAMP,
        submission_accepted         TIMESTAMP,
        submission_state            VARCHAR,
        submission_evaluator        VARCHAR,
        submission_score            INTEGER,
        submission_feedback         VARCHAR,
        submission_adjusted_score   NUMERIC
    )
    LANGUAGE PLPGSQL
AS $$
BEGIN
    RETURN QUERY
        SELECT      course.course_id,
                    course.code AS course_code,
                    course.name AS course_name,
                    course.email AS course_email,
                    course.github_account AS course_github_account,
                    course.opens AS course_start,
                    course.closes AS course_end,
                    enrollee.uid AS enrollee_uid,
                    enrollee.studentid AS enrollee_studentid,
                    enrollee.lastname AS enrollee_lastname,
                    enrollee.firstname AS enrollee_firstname,
                    enrollee.email AS enrollee_email,
                    enrollee.notifications AS enrollee_notifications,
                    enrollee.github_account AS enrollee_github_account,
                    enrollee.github_repository AS enrollee_github_repository,
                    enrollee.status::VARCHAR AS enrollee_status,
                    assignment.assignment_id,
                    assignment.name AS assignment_name,
                    assignment.handler AS assignment_handler,
                    assignment.points AS assignment_max_score,
                    assignment.pass AS assignment_score_to_pass,
                    assignment.retries AS assignment_retries,
                    assignment.deadline AS assignment_deadline,
                    assignment.latepenalty AS assignment_latepenalty,
                    core.submission_last_retrieval_date(assignment.deadline, assignment.latepenalty) AS assignment_softdeadline,
                    submission.submission_id,
                    submission.content AS submission_content,
                    submission.submitted AS submission_submitted,
                    submission.accepted AS submission_accepted,
                    submission.state AS submission_state,
                    submission.evaluator AS submission_evaluator,
                    submission.score AS submission_score,
                    submission.feedback AS submission_feedback,
                    core.submission_adjusted_score(submission.submission_id) AS submission_adjusted_score
        FROM        core.enrollee
                    INNER JOIN core.submission
                    ON (
                        enrollee.course_id = submission.course_id
                        AND
                        enrollee.uid = submission.uid
                    )
                    INNER JOIN core.assignment
                    ON (
                        submission.course_id = assignment.course_id
                        AND
                        submission.assignment_id = assignment.assignment_id
                    )
                    INNER JOIN core.course
                    ON (assignment.course_id = course.course_id)
        WHERE       submission.submission_id = in_submission_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Submission #% not found!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_FOUND';
    END IF;
    RETURN;
END;
$$;
GRANT EXECUTE ON FUNCTION email.jtd_submission_rec TO "www-data";
GRANT EXECUTE ON FUNCTION email.jtd_submission_rec TO schooner_dev;



CREATE OR REPLACE FUNCTION email.jtd_course_welcome_rec(
    in_course_id        VARCHAR
)
    RETURNS TABLE
    (
        course_id                   VARCHAR,
        course_code                 VARCHAR,
        course_name                 VARCHAR,
        course_email                VARCHAR,
        course_github_account       VARCHAR,
        course_start                TIMESTAMP,
        course_end                  TIMESTAMP,
        course_description          VARCHAR
    )
    LANGUAGE PLPGSQL
AS $$
-- So, why not just a SELECT?
-- This function will be expanded to contain information about the first
-- lecture / event, once the data structures will be added for those (2022).
-- Until then, this is more of a placeholder...
BEGIN
    RETURN QUERY
        SELECT      course.course_id,
                    course.code AS course_code,
                    course.name AS course_name,
                    course.email AS course_email,
                    course.github_account AS course_github_account,
                    course.opens AS course_start,
                    course.closes AS course_end,
                    course.description AS course_description
        FROM        core.course
                    LEFT OUTER JOIN (
                        SELECT      *
                        FROM        core.assignment
                        WHERE       assignment.course_id = in_course_id
                                    AND
                                    assignment.assignment_id = 'T01'
                    ) assignment
                    ON (course.course_id = assignment.course_id)
        WHERE       course.course_id = in_course_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Course ''%'' not found!', in_course_id
            USING HINT = 'COURSE_NOT_FOUND';
    END IF;
    RETURN;
END;
$$;
GRANT EXECUTE ON FUNCTION email.jtd_course_welcome_rec TO "www-data";
GRANT EXECUTE ON FUNCTION email.jtd_course_welcome_rec TO schooner_dev;


-- EOF