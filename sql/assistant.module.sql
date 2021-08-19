--
-- Schooner - Simple Course Management System
-- assistant.module.sql / Course assistants and work queues
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Placeholder with 'assistant' table only.
--

CREATE TABLE assistant
(
    course_id           VARCHAR(32)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, uid),
    FOREIGN KEY (course_id)
        REFERENCES course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT assistant_course_unq
        UNIQUE (course_id, uid)
);
GRANT ALL PRIVILEGES ON assistant TO schooner_dev;
GRANT SELECT ON assistant TO "www-data";

COMMENT ON TABLE assistant IS
'Assistants for each course implementation.';
COMMENT ON COLUMN assistant.status IS
'Assistant can be temporarily set to inactive status to avoid assigning exercise evaluations into his work queue.';

CREATE TABLE evaluation
(
    submission_id       BIGINT          NOT NULL,
    course_id           VARCHAR(32)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    started             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended               TIMESTAMP       NULL,
    FOREIGN KEY (submission_id)
        REFERENCES submission (submission_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (course_id, uid)
        REFERENCES assistant (course_id, uid)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT evaluation_started_before_ended_chk
        CHECK (
            ended IS NULL
            OR
            ended > started
        )
);
GRANT ALL PRIVILEGES ON evaluation TO schooner_dev;
GRANT SELECT, INSERT ON evaluation TO "www-data";

COMMENT ON TABLE evaluation IS
'This table is inserted with a row when the evaluation of a submission begins, and it is updated with the .ended once the evaluation is complete. For work queue management, not having a row in this table means that the submission is available for evaluation, having a row without .ended value means that evaluation is in progress and having .ended value means that the submission has been evaluated.';
COMMENT ON COLUMN evaluation.uid IS
'User ID of the assistant.';
