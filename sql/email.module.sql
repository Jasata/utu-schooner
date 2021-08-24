--
-- Schooner - Simple Course Management System
-- email.module.sql / Email messages schema, PostgreSQL version
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-23  Initial version.
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
        CHECK (state IN ('queued', 'failed', 'sent'))
);
GRANT ALL PRIVILEGES ON email.message TO schooner_dev;
GRANT SELECT, INSERT, UPDATE ON email.message TO "www-data";

COMMENT ON TABLE email.message IS
'Email cron job visits this table periodically to see .sent_at IS NULL rows (not yet sent) and sends them out.';
COMMENT ON COLUMN email.message.course_id IS
'Together with "uid", an optional reference that links the email to an enrolled student.';
COMMENT ON COLUMN email.message.uid IS
'Together with "course_id", an optional reference that links the email to an enrolled student.';
COMMENT ON COLUMN email.message.sent_from IS
'This should always be the course''s RT queue address, e.g., "dte20068@utu.fi".';
COMMENT ON COLUMN email.message.sent_to IS
'Single recipient email address. Maximum local part (before @) is 64 characters and maximum domain part is 255 characters.';
COMMENT ON COLUMN email.message.state IS
'All emails that have yet-to-be-sent are in state = ''queued''. Ignoring transient errors, the email cron job will set handled records either as ''failed'' (non-transient error) or ''sent'' if successfully sent.';


\echo '=== email.attachment'
CREATE TABLE email.attachment
(
    message_id          INT             NOT NULL,
    name                VARCHAR(255)    NOT NULL,
    content             BYTEA           NOT NULL,
    FOREIGN KEY (message_id)
        REFERENCES email.message (message_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT attachment_name_unq
        UNIQUE (message_id, name)
);
GRANT ALL PRIVILEGES ON email.attachment TO schooner_dev;
GRANT SELECT, INSERT ON email.attachment TO "www-data";

COMMENT ON TABLE email.attachment IS
'An email message may contain zero to N attachments. Create both email and email_attachment records in a single transaction to prevent the email cron job from sending the message while the attachment(s) are being inserted.';
COMMENT ON COLUMN email.attachment.name IS
'Filename of the attachment';
COMMENT ON COLUMN email.attachment.content IS
'Binary content of the attachment. BUT IS TEXT BETTER, IF CONTENT IS ENCODED ANYWAY?';


\echo '=== email.template'
CREATE TABLE email.template
(
    code                VARCHAR(32)     NOT NULL,
    subject             VARCHAR(255)    NOT NULL,
    body                VARCHAR(65536)  NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code)
);
GRANT ALL PRIVILEGES ON email.attachment TO schooner_dev;
GRANT SELECT ON email.attachment TO "www-data";

COMMENT ON TABLE email.template IS
'Mostly intended for automated email messages. Replaceable tokens in braces (''{}''). Application defines they keys and values for tokens.';


\echo '=== email.template_attachment'
CREATE TABLE email.template_attachment
(
    code                VARCHAR(32)     NOT NULL,
    name                VARCHAR(255)    NOT NULL,
    content             BYTEA           NOT NULL,
    FOREIGN KEY (code)
        REFERENCES email.template
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT template_attachment_name_unq
        UNIQUE (code, name)
);
GRANT ALL PRIVILEGES ON email.template_attachment TO schooner_dev;
GRANT SELECT ON email.template_attachment TO "www-data";



-- EOF