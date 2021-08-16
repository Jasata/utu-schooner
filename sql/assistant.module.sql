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
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active',
    FOREIGN KEY (course_id)
    REFERENCES course (course_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
    CONSTRAINT assistant_course_unq
    UNIQUE (course_id, uid)
);

COMMENT ON TABLE assistant IS
'Assigns "uid" as an assistant to a course.';
COMMENT ON COLUMN assistant.status IS
'Assistant can be temporarily set to inactive status to avoid assigning exercise evaluations into his work queue.';

