--
-- Schooner - Simple Course Management System
-- email.module.sql / Email messages schema, PostgreSQL version
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-23  Initial version.
--  2021-08-24  Fix GRANT on email.template.
--  2021-08-25  Restructured attachment storage.
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
    sent_to             VARCHAR(320)    NOT NULL,
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
'Single recipient email address. Maximum local part (before @) is 64 characters and maximum domain part is 255 characters.';
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
-- EOF