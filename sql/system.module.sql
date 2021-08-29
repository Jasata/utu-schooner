--
-- Schooner - Simple Course Management System
-- system.module.sql / Core table structure, PostgreSQL version
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-29  Initial version.
--
-- Execute as 'schooner' (for ownership)
--
\echo 'Creating schema system'
DROP SCHEMA IF EXISTS system CASCADE;
CREATE SCHEMA system;
GRANT USAGE ON SCHEMA system TO "www-data";
GRANT USAGE ON SCHEMA system TO schooner_dev;


--
-- System log
--
\echo '=== system.log'
CREATE TABLE system.log
(
    created         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    name            VARCHAR(32)     NOT NULL,
    level           VARCHAR(10)     NOT NULL,
    message         VARCHAR(1000)   NOT NULL,
    source          VARCHAR(100)    NULL
);
GRANT ALL PRIVILEGES ON system.log TO schooner_dev;
GRANT SELECT ON system.log TO "www-data";

COMMENT ON TABLE system.log IS
'For custom Python logging handler, but can be used for other logging as well.';
COMMENT ON COLUMN system.log.name IS
'Name of the logger (logging.getLogger("myNameIs"))';
COMMENT ON COLUMN system.log.source IS
'Optional ''file:line function()'' information where the log message was emitted from.';




\echo '=== system.role'
CREATE TABLE system.role
(
    role_id         VARCHAR(16)     NOT NULL,
    PRIMARY KEY (role_id)
);
GRANT ALL PRIVILEGES ON system.role TO schooner_dev;
GRANT SELECT ON system.role TO "www-data";

COMMENT ON TABLE system.role IS
'List of system roles. Should have at least: ADMIN, TEACHER, and ASSISTANT. Student role is unnecessary, because all SSO authenticated users are considered to be students anyway.';

INSERT INTO system.role
VALUES ('ADMIN'), ('TEACHER'), ('ASSISTANT');




\echo '=== system.account'
CREATE TABLE system.account
(
    uid             VARCHAR(10)     NOT NULL,
    role_id         VARCHAR(16)     NOT NULL,
    created         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (uid, role_id),
    FOREIGN KEY (role_id)
        REFERENCES system.role (role_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
GRANT ALL PRIVILEGES ON system.account TO schooner_dev;
GRANT SELECT ON system.account TO "www-data";

COMMENT ON TABLE system.account IS
'Replaces core.admin as the datasource for SSO mechanism... in 2022.';
COMMENT ON COLUMN system.account.uid IS
'Login ID from SSO. Also known as UTU ID.';

-- EOF