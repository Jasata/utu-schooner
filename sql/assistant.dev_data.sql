--
-- Schooner - Simple Course Management System
-- assistant.dev_data.sql / Development and testing data set
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-20  Initial version.
--  2021-08-25  Adjusted for new course code.
--
\echo '=== INSERT''ing assistant development data...'
INSERT INTO assistant.assistant
(
    course_id,
    uid,
    name
)
VALUES
(
    'DTEK0068-3002',
    'jasata',
    'Jani Tammi'
),
(
    'DTEK0068-3002',
    'tumipo',
    'Tuisku Polvinen'
);

DO $$
DECLARE
    v_submission_id     INTEGER;
BEGIN
    INSERT INTO core.submission
    (
        assignment_id,
        course_id,
        uid,
        content
    )
    VALUES
    (
        'E02',
        'DTEK0068-3002',
        'jasata',
        'Prööt prööt'
    )
    RETURNING   submission_id
    INTO        v_submission_id;
    PERFORM     assistant.evaluation_begin('jasata', v_submission_id);
END;
$$;



-- EOF