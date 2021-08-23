--
-- Schooner - Simple Course Management System
-- assistant.dev_data.sql / Development and testing data set
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-20  Initial version.
--

INSERT INTO assistant.assistant
(
    course_id,
    assistant_uid,
    name
)
VALUES
(
    'DTE20068-3002',
    'jasata',
    'Jani Tammi'
),
(
    'DTE20068-3002',
    'tumipo',
    'Tuisku Polvinen'
);

DO $$
DECLARE
    v_submission_id     INT;
BEGIN
    INSERT INTO submission
    VALUES
    (
        DEFAULT,
        'E02',
        'DTE20068-3002',
        'jasata',
        'Prööt prööt',
        DEFAULT,
        NULL,
        'draft',
        NULL,
        NULL,
        NULL,
        NULL
    )
    RETURNING   submission_id
    INTO        v_submission_id;
    PERFORM     assistant.evaluation_begin('jasata', v_submission_id);
END;
$$;



DROP FUNCTION assistant.test;
CREATE OR REPLACE FUNCTION
assistant.test(
    in_submission_id  INT
)
    RETURNS VARCHAR(10)
    LANGUAGE PLPGSQL
    VOLATILE
    STRICT
AS $$
DECLARE
    v_row           RECORD;
BEGIN
    SELECT      *
    FROM        assistant.evaluation
    WHERE       submission_id = in_submission_id
    INTO        v_row;
    IF FOUND THEN
        RAISE NOTICE 'Evaluation record exists';
    ELSE
        RAISE NOTICE 'Evaluation record does not exist';
    END IF;
    RETURN v_row.assistant_uid;
END
$$;




INSERT INTO assistant.evaluation
VALUES (1, 'DTE20068-3002', 'jasata', CURRENT_TIMESTAMP, NULL);

-- EOF