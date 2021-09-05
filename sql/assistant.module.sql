--
-- Schooner - Simple Course Management System
-- assistant.module.sql / Course assistants and work queues
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Placeholder with 'assistant' table.
--  2021-08-22  Evaluation tables and functions.
--  2021-08-23  Fixes for 'core' schema.
--
\echo 'Creating schema assistant'
DROP SCHEMA IF EXISTS assistant CASCADE;
CREATE SCHEMA assistant;
GRANT USAGE ON SCHEMA assistant TO "www-data";
GRANT USAGE ON SCHEMA assistant TO schooner_dev;


\echo '=== assistant.assistant'
CREATE TABLE assistant.assistant
(
    course_id           VARCHAR(32)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, uid),
    FOREIGN KEY (course_id)
        REFERENCES core.course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
GRANT ALL PRIVILEGES ON assistant.assistant TO schooner_dev;
GRANT SELECT ON assistant.assistant TO "www-data";

COMMENT ON TABLE assistant.assistant IS
'Assistants for each course implementation.';
COMMENT ON COLUMN assistant.assistant.status IS
'UTU ID/username of the assistant.';
COMMENT ON COLUMN assistant.assistant.status IS
'Assistant can be temporarily set to inactive status to avoid assigning exercise evaluations into his work queue.';
COMMENT ON COLUMN assistant.assistant.name IS
'For being "nice" and because assistant information may not exist elsewhere.';


--
-- Evaluations
--
--  States:
--      1) Assistant undertakes submission's evaluation
--          started IS NOT NULL AND ended IS NULL
--      2) Assistant completes evaluation
--          started IS NOT NULL AND ended IS NOT NULL
\echo '=== assistant.evaluation'
CREATE TABLE assistant.evaluation
(
    submission_id       INT             NOT NULL PRIMARY KEY,
    course_id           VARCHAR(32)     NOT NULL,
    uid                 VARCHAR(10)     NOT NULL,
    started             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended               TIMESTAMP       NULL,
    FOREIGN KEY (submission_id)
        REFERENCES core.submission (submission_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (course_id, uid)
        REFERENCES assistant.assistant (course_id, uid)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT evaluation_ended_chk
        CHECK (
            ended IS NULL
            OR
            ended > started
        )
);
GRANT ALL PRIVILEGES ON assistant.evaluation TO schooner_dev;
GRANT SELECT ON assistant.evaluation TO "www-data";

COMMENT ON TABLE assistant.evaluation IS
'This table is inserted with a row when the evaluation of a submission begins, and it is updated with the .ended once the evaluation is complete. For work queue management, not having a row in this table means that the submission is available for evaluation, having a row without .ended value means that evaluation is in progress and having .ended value means that the submission has been evaluated.';
COMMENT ON COLUMN assistant.evaluation.uid IS
'User ID of the assistant.';


\echo '=== assistant.accesstoken'
CREATE TABLE assistant.accesstoken
(
    submission_id       INT         NOT NULL,
    token               INT         NOT NULL,
    expires             TIMESTAMP   NOT NULL,
    FOREIGN KEY (submission_id)
        REFERENCES core.submission (submission_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT accesstoken_pk
        PRIMARY KEY (submission_id),
    CONSTRAINT accesstoken_expires_chk
        CHECK (expires > CURRENT_TIMESTAMP)
);
GRANT ALL PRIVILEGES ON assistant.accesstoken TO schooner_dev;
GRANT SELECT ON assistant.accesstoken TO "www-data";

COMMENT ON TABLE assistant.accesstoken IS
'Time-limited download access tokens.';
COMMENT ON COLUMN assistant.accesstoken.expires IS
'Datetime until the token is valid.';

--
-- Pseudo encrypt - For generating non-colliding unique pseudo-random values
--
-- SELECT x, pseudo_encrypt(x) FROM generate_series(1, 12) AS x;
\echo '=== assistant.pseudo_encrypt()'
CREATE OR REPLACE FUNCTION
assistant.pseudo_encrypt(
    value   INT
)
    RETURNS INT
    LANGUAGE PLPGSQL
    IMMUTABLE
    STRICT
AS $$
DECLARE
    l1 INT;
    l2 INT;
    r1 INT;
    r2 INT;
    i  INT := 0;
BEGIN
    l1 := (value >> 16) & 65535;
    r1 := value & 65535;
    WHILE i < 3
    LOOP
        l2 := r1;
        r2 := l1 # ((((1366 * r1 + 150889) % 714025) / 714025.0) * 32767)::INT;
        l1 := l2;
        r1 := r2;
        i  := i + 1;
    END LOOP;
    RETURN ((r1 << 16) + l1);
END;
$$;
GRANT EXECUTE ON FUNCTION assistant.pseudo_encrypt(INT) TO "www-data";
GRANT EXECUTE ON FUNCTION assistant.pseudo_encrypt(INT) TO schooner_dev;

COMMENT ON FUNCTION assistant.pseudo_encrypt(INT) IS
'Produces an integer output that is uniquely associated to its integer input (by a mathematical permutation), but looks random at the same time, with zero collision. This is useful to communicate numbers generated sequentially without revealing their ordinal position in the sequence (for ticket numbers, URLs shorteners, promo codes...).

The permutation property is a consequence of the function being a Feistel network; see http://en.wikipedia.org/wiki/Feistel_cipher

Source: https://wiki.postgresql.org/wiki/Pseudo_encrypt';



--
-- Workqueue management functions
--
\echo '=== assistant.evaluation_begin()'
CREATE OR REPLACE FUNCTION
assistant.evaluation_begin(
    in_uid              VARCHAR(10),
    in_submission_id    INTEGER
)
    RETURNS INTEGER
    LANGUAGE PLPGSQL
    SECURITY DEFINER
    VOLATILE
    CALLED ON NULL INPUT
AS $$
-- Prerequisites:
--  1)  Assistant is registered for the same course as the submission is for
--  2)  Assistant is in 'active' status
--  3)  Evaluation record either...
--      3.1)    [START] Does not exists ...or...
--      3.2)    [RESTART] Existing evaluation record:
--              - is not closed (.ended IS NULL) and 
--              - belongs to the same assistant
--  4)  The submission exists
--  5)  Submission is in 'draft' state
--
-- This function creates (up updates) an evaluation record and generates
-- a time-limited access token that instructs the Flask endpoint to
-- allow submission downloads with the token.
--
-- [START]
--  - Evaluation record and accesstoken records are created.
-- [RESTART]
--  - evaluation.started is updated with CURRENT_TIMESTAMP
--  - accesstoken.expires is updated
--
DECLARE
    r_submission        RECORD;
    r_assistant         RECORD;
    r_evaluation        RECORD;
    v_accesstoken       INTEGER;
    v_token_duration    TIME;
BEGIN
    -- Query token duration from config
    SELECT      access_token_duration
    FROM        system.config
    WHERE       rowlock = TRUE
    INTO        v_token_duration;
    IF NOT FOUND THEN
        RAISE EXCEPTION
        'ERROR: Configuration table ''system.config'' is empty!'
        USING HINT = 'CONFIG_ERROR';
    END IF;
    -- LOCK submission row
    PERFORM     *
    FROM        core.submission
    WHERE       submission_id = in_submission_id
    FOR UPDATE;
    -- LOCK evaluation table
    LOCK TABLE assistant.evaluation IN ACCESS EXCLUSIVE MODE;

    -- Submission must exist and be in 'draft' state
    SELECT      *
    FROM        core.submission
    WHERE       submission_id = in_submission_id
    INTO        r_submission;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Submission (%) does not exist!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_FOUND';
    ELSIF r_submission.state != 'draft' THEN
        RAISE EXCEPTION
            'Submission (%) is not in ''draft'' state!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_DRAFT';
    END IF;

    -- Assistant must be working for the same course as the submission is for
    SELECT      *
    FROM        assistant.assistant
    WHERE       uid = in_uid
                AND
                course_id = r_submission.course_id
    INTO        r_assistant;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not registered for course (''%'')!',
            in_uid, r_submission.course_id
            USING HINT = 'ASSISTANT_NOT_REGISTERED';
    ELSIF r_assistant.status != 'active' THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not active!', in_uid
            USING HINT = 'ASSISTANT_NOT_ACTIVE';
    END IF;

    -- Evaluation record either does not exist or 
    -- belongs to the same assistant and is not closed
    SELECT      *
    FROM        assistant.evaluation
    WHERE       submission_id = in_submission_id
    INTO        r_evaluation;
    IF NOT FOUND THEN
        INSERT INTO assistant.evaluation
        (
            submission_id,
            course_id,
            uid
        )
        VALUES
        (
            in_submission_id,
            r_submission.course_id,
            in_uid
        );
    ELSE
        IF r_evaluation.ended IS NOT NULL THEN
            RAISE EXCEPTION
            'Evaluation for submission (%) is already completed!',
            in_submission_id
            USING HINT = 'EVALUATION_COMPLETED';
        ELSIF r_evaluation.uid != in_uid THEN
            RAISE EXCEPTION
            'Evaluation for submission (%) belongs to another assistant (''%'')',
            in_submission_id, r_evaluation.uid
            USING HINT = 'EVALUATION_OWNER';
        END IF;
        -- Update assistant.evaluation.started
        UPDATE  assistant.evaluation
        SET     started = CURRENT_TIMESTAMP
        WHERE   submission_id = in_submission_id;
    END IF;

    --
    -- Generate or update non-colliding access token with expiry datetime
    --
    INSERT INTO assistant.accesstoken
    (
        submission_id,
        token,
        expires
    )
    VALUES
    (
        in_submission_id,
        assistant.pseudo_encrypt(in_submission_id),
        CURRENT_TIMESTAMP + v_token_duration
    )
    ON CONFLICT (submission_id)
    DO UPDATE SET
        expires = CURRENT_TIMESTAMP + v_token_duration
    RETURNING token
    INTO v_accesstoken;
    RETURN v_accesstoken;
END;
$$;
GRANT EXECUTE ON FUNCTION assistant.evaluation_begin TO "www-data";
GRANT EXECUTE ON FUNCTION assistant.evaluation_begin TO schooner_dev;


\echo '=== assistant.evaluation_close()'
CREATE OR REPLACE FUNCTION
assistant.evaluation_close(
    in_uid              VARCHAR(10),
    in_submission_id    INTEGER,
    in_score            INTEGER,
    in_feedback         TEXT,
    in_confidential     TEXT
)
    RETURNS TIME
    LANGUAGE PLPGSQL
    SECURITY DEFINER
    VOLATILE
    CALLED ON NULL INPUT
-- NOTE:    public.submission.state goes into 'rejected' ONLY if the submission
--          cannot be evaluated. For example, HUBBOT has found the required
--          directory in the repository and assumed that the submission is OK,
--          then proceeded to download it. It may turn out that the folder has
--          nothing to satisfy the given exercise. Perhaps no code files at all.
--          Such submissions will not receive 
AS $$
DECLARE
    r_submission        RECORD;
    r_assistant         RECORD;
    r_evaluation        RECORD;
    r_assignment        RECORD;
    v_row_count         INTEGER;
    v_closing_datetime  TIMESTAMP := CURRENT_TIMESTAMP;
BEGIN
    -- LOCK submission row
    PERFORM     *
    FROM        core.submission
    WHERE       submission_id = in_submission_id
    FOR UPDATE;
    -- LOCK evaluation table
    LOCK TABLE assistant.evaluation IN ACCESS EXCLUSIVE MODE;

    -- Submission must exist and be in 'draft' state
    SELECT      *
    FROM        core.submission
    WHERE       submission_id = in_submission_id
    INTO        r_submission;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Submission (%) does not exist!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_FOUND';
    ELSIF r_submission.state != 'draft' THEN
        RAISE EXCEPTION
            'Submission (%) is not in ''draft'' state!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_DRAFT';
    END IF;

    -- Assistant must be working for the same course as the submission is for
    SELECT      *
    FROM        assistant.assistant
    WHERE       uid = in_uid
                AND
                course_id = r_submission.course_id
    INTO        r_assistant;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not registered for course (''%'')!',
            in_uid, r_submission.course_id
            USING HINT = 'ASSISTANT_NOT_REGISTERED';
    ELSIF r_assistant.status != 'active' THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not active!', in_uid
            USING HINT = 'ASSISTANT_NOT_ACTIVE';
    END IF;

    -- Evaluation record must exist, not be closed, and
    -- belong to the same assistant
    SELECT      *
    FROM        assistant.evaluation
    WHERE       submission_id = in_submission_id
    INTO        r_evaluation;
    IF NOT FOUND THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) has not been started!',
        in_submission_id
        USING HINT = 'EVALUATION_NOT_STARTED';
    ELSIF r_evaluation.ended IS NOT NULL THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) is already completed!',
        in_submission_id
        USING HINT = 'EVALUATION_COMPLETED';
    ELSIF r_evaluation.uid != in_uid THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) belongs to another assistant (''%'')',
        in_submission_id, r_evaluation.uid
        USING HINT = 'EVALUATION_OWNER';
    END IF;

    -- Check given score against assignment maximum
    SELECT      *
    FROM        core.assignment
    WHERE       assignment_id = r_submission.assignment_id
                AND
                course_id = r_submission.course_id
    INTO r_assignment;
    IF in_score > r_assignment.points THEN
        RAISE EXCEPTION
        'Submission (%) cannot be awarded more points (%) than the assignment (''%'', ''%'') maximum (%) defines!',
        in_submission_id, in_score, r_assignment.assignment_id, r_assignment.course_id, r_assignment.points
        USING HINT = 'EVALUATION_SCORE_EXCEEDED';
    ELSIF in_score < 0 THEN
        RAISE EXCEPTION
        'Submission (%) cannot be awarded with negative points!',
        in_submission_id
        USING HINT = 'EVALUATION_SCORE_NEGATIVE';
    END IF;

    --
    -- Update submission and evaluation, remove access token
    --
    UPDATE  core.submission
    SET     state           = 'accepted',
            evaluator       = in_uid,
            score           = in_score,
            feedback        = in_feedback,
            confidential    = in_confidential
    WHERE   submission_id = in_submission_id;
    -- Paranoia check, because this is vitally important part
    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    IF v_row_count < 1 THEN
        RAISE EXCEPTION
        'Somehow, UPDATE did not affect a any rows! submission_id: %',
        in_submission_id
        USING HINT = 'IMPOSSIBLE_ERROR';
    ELSIF v_row_count > 1 THEN
        RAISE EXCEPTION
        'Somehow, UPDATE affected more than a single row! submission_id: %',
        in_submission_id
        USING HINT = 'IMPOSSIBLE_ERROR';
    END IF;

    UPDATE  assistant.evaluation
    SET     ended = v_closing_datetime
    WHERE   submission_id = in_submission_id;

    DELETE
    FROM    assistant.accesstoken
    WHERE   submission_id = in_submission_id;

    --
    -- Return time spent on evaluation
    --
    RETURN v_closing_datetime - r_evaluation.started;

END
$$;
GRANT EXECUTE ON FUNCTION assistant.evaluation_close TO "www-data";
GRANT EXECUTE ON FUNCTION assistant.evaluation_close TO schooner_dev;


\echo '=== assistant.evaluation_reject()'
CREATE OR REPLACE FUNCTION
assistant.evaluation_reject(
    in_uid              VARCHAR(10),
    in_submission_id    INTEGER,
    in_feedback         TEXT,
    in_confidential     TEXT
)
    RETURNS TIME
    LANGUAGE PLPGSQL
    SECURITY DEFINER
    VOLATILE
    CALLED ON NULL INPUT
AS $$
DECLARE
    r_submission        RECORD;
    r_assistant         RECORD;
    r_evaluation        RECORD;
    v_row_count         INTEGER;
    v_closing_datetime  TIMESTAMP := CURRENT_TIMESTAMP;
BEGIN
    -- LOCK submission row
--    PERFORM     *
--    FROM        submission
--    WHERE       submission_id = in_submission_id
--    FOR UPDATE;
--    IF NOT FOUND THEN
--        RAISE EXCEPTION
--        'Submission (%) not found!',
--        in_submission_id
--        USING HINT = 'SUBMISSION_NOT_FOUND';
--    END IF;
    -- LOCK evaluation table
--    PERFORM     *
--    FROM        assistant.evaluation
--    WHERE       uid = in_uid
--    FOR UPDATE;
--    IF NOT FOUND THEN
--        RAISE EXCEPTION
--        'Evaluation record for submission (%) not found!',
--        in_submission_id
--        USING HINT = 'EVALUATION_NOT_FOUND';
 --   END IF;
    -- Unlike .evaluation_beginning(), this routine does not need to lock the entire table
    -- LOCK TABLE assistant.evaluation IN ACCESS EXCLUSIVE MODE;

    -- Submission must exist and be in 'draft' state
    SELECT      *
    FROM        core.submission
    WHERE       submission_id = in_submission_id
    INTO        r_submission
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Submission (%) does not exist!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_FOUND';
    ELSIF r_submission.state != 'draft' THEN
        RAISE EXCEPTION
            'Submission (%) is not in ''draft'' state!', in_submission_id
            USING HINT = 'SUBMISSION_NOT_DRAFT';
    END IF;

    -- Evaluation record must exist, not be closed, and
    -- belong to the same assistant
    SELECT      *
    FROM        assistant.evaluation
    WHERE       submission_id = in_submission_id
    INTO        r_evaluation
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) has not been started!',
        in_submission_id
        USING HINT = 'EVALUATION_NOT_STARTED';
    ELSIF r_evaluation.ended IS NOT NULL THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) is already completed!',
        in_submission_id
        USING HINT = 'EVALUATION_COMPLETED';
    ELSIF r_evaluation.uid != in_uid THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) belongs to another assistant (''%'')',
        in_submission_id, r_evaluation.uid
        USING HINT = 'EVALUATION_OWNER';
    END IF;

    -- Assistant must be working for the same course as the submission is for
    SELECT      *
    FROM        assistant.assistant
    WHERE       uid = in_uid
                AND
                course_id = r_submission.course_id
    INTO        r_assistant;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not registered for course (''%'')!',
            in_uid, r_submission.course_id
            USING HINT = 'ASSISTANT_NOT_REGISTERED';
    ELSIF r_assistant.status != 'active' THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not active!', in_uid
            USING HINT = 'ASSISTANT_NOT_ACTIVE';
    END IF;

    --
    -- Update submission and evaluation, remove access token
    --
    UPDATE  core.submission
    SET     state           = 'rejected',
            evaluator       = in_uid,
            score           = 0,
            feedback        = in_feedback,
            confidential    = in_confidential
    WHERE   submission_id = in_submission_id;
    -- Paranoia check, because this is vitally important part
    GET DIAGNOSTICS v_row_count = ROW_COUNT;
    IF v_row_count < 1 THEN
        RAISE EXCEPTION
        'Somehow, UPDATE did not affect a any rows! submission_id: %',
        in_submission_id
        USING HINT = 'IMPOSSIBLE_ERROR';
    ELSIF v_row_count > 1 THEN
        RAISE EXCEPTION
        'Somehow, UPDATE affected more than a single row! submission_id: %',
        in_submission_id
        USING HINT = 'IMPOSSIBLE_ERROR';
    END IF;

    UPDATE  assistant.evaluation
    SET     ended = v_closing_datetime
    WHERE   submission_id = in_submission_id;

    DELETE
    FROM    assistant.accesstoken
    WHERE   submission_id = in_submission_id;

    --
    -- Return time spent on evaluation
    --
    RETURN v_closing_datetime - r_evaluation.started;

END
$$;
GRANT EXECUTE ON FUNCTION assistant.evaluation_reject TO "www-data";
GRANT EXECUTE ON FUNCTION assistant.evaluation_reject TO schooner_dev;




\echo '=== assistant.accesstoken_validate()'
CREATE OR REPLACE FUNCTION
assistant.accesstoken_validate(
    in_accesstoken      INTEGER
)
    RETURNS INTEGER
    LANGUAGE PLPGSQL
    SECURITY INVOKER
    VOLATILE
    STRICT
AS $$
-- Returns NULL if the token is not valid.
-- If valid, returns submission_id.
DECLARE
    r_accesstoken       RECORD;
BEGIN
    SELECT      *
    FROM        assistant.accesstoken
    WHERE       token = in_accesstoken
    INTO        r_accesstoken;
    IF NOT FOUND THEN
        RETURN NULL;
    ELSEIF r_accesstoken.expires < CURRENT_TIMESTAMP THEN
        RETURN NULL;
    END IF;
    RETURN r_accesstoken.submission_id;
END;
$$;
GRANT EXECUTE ON FUNCTION assistant.evaluation_reject TO "www-data";
GRANT EXECUTE ON FUNCTION assistant.evaluation_reject TO schooner_dev;




\echo '=== assistant.workqueue()'
CREATE OR REPLACE FUNCTION assistant.workqueue(
    in_uid                  VARCHAR
)
    RETURNS TABLE
    (
        submission_id       INTEGER,
        lastname            VARCHAR,
        firstname           VARCHAR,
        course_id           VARCHAR,
        assignment_id       VARCHAR,
        assignment_name     VARCHAR,
        student_uid         VARCHAR,
        submitted           TIMESTAMP,
        deadline            DATE,
        evaluator_uid       VARCHAR,
        evaluator_name      VARCHAR,
        evaluation_started  TIMESTAMP
    )
    LANGUAGE PLPGSQL
    STRICT
AS $$
-- Returns all unevaluated HUBBOT assignment submissions for course(s) in which
-- the given assistant uid is registered as an active assistant.
BEGIN
    RETURN QUERY
        SELECT      submission.submission_id,
                    enrollee.lastname,
                    enrollee.firstname,
                    submission.course_id,
                    submission.assignment_id,
                    assignment.name AS assignment_name,
                    submission.uid,
                    submission.submitted,
                    assignment.deadline,
                    evaluation.uid AS evaluator_uid,
                    assistant.name AS evaluator_name,
                    evaluation.started AS evaluation_started
        FROM        core.submission
                    INNER JOIN core.assignment
                    ON (
                        submission.assignment_id = assignment.assignment_id 
                        AND
                        submission.course_id = assignment.course_id
                        AND
                        assignment.handler = 'HUBBOT'
                    )
                    INNER JOIN assistant.assistant
                    ON (
                        assistant.course_id = assignment.course_id
                        AND
                        assistant.uid = in_uid
                        AND
                        assistant.status = 'active'
                    )
                    LEFT OUTER JOIN assistant.evaluation
                    ON (submission.submission_id = evaluation.submission_id)
                    INNER JOIN core.enrollee
                    ON (
                        submission.course_id = enrollee.course_id
                        AND
                        submission.uid = enrollee.uid
                    )
        WHERE       submission.state = 'draft';
    RETURN;
END;
$$;
GRANT EXECUTE ON FUNCTION assistant.workqueue TO "www-data";
GRANT EXECUTE ON FUNCTION assistant.workqueue TO schooner_dev;

COMMENT ON FUNCTION assistant.workqueue IS
'Return a list of non-evaluated HUBBOT submissions for all courses that the assistant is signed for.';




-- EOF
