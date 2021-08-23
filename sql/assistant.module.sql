--
-- Schooner - Simple Course Management System
-- assistant.module.sql / Course assistants and work queues
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Placeholder with 'assistant' table only.
--
DROP SCHEMA IF EXISTS assistant CASCADE;
CREATE SCHEMA assistant;
GRANT USAGE ON SCHEMA assistant TO "www-data";
GRANT USAGE ON SCHEMA assistant TO schooner_dev;

--
-- Assistant module configuration
--
CREATE TABLE assistant.config
(
    rowlock             BOOL            NOT NULL PRIMARY KEY DEFAULT TRUE,
    token_duration      TIME            NOT NULL DEFAULT '00:05:00',
    dummy               VARCHAR(10)     NOT NULL DEFAULT 'dummy',
    CONSTRAINT config_rowlock_chk
        CHECK (rowlock)
);
CREATE RULE assistant_config_delete
AS
    ON DELETE
    TO assistant.config
    DO INSTEAD NOTHING;
INSERT INTO assistant.config (rowlock) VALUES (TRUE);

GRANT ALL PRIVILEGES ON assistant.config TO schooner_dev;
GRANT SELECT ON assistant.config TO "www-data";

COMMENT ON TABLE assistant.config IS
'Configurations used by functions and procedures. You can only UPDATE this table.';
COMMENT ON COLUMN assistant.config.rowlock IS
'PK column which limits the number of rows to one.';
COMMENT ON COLUMN assistant.config.token_duration IS
'Time which is added to CURRENT_TIMESTAMP when accesstoken -table row is inserted.';

CREATE TABLE assistant.assistant
(
    course_id           VARCHAR(32)     NOT NULL,
    assistant_uid       VARCHAR(10)     NOT NULL,
    name                VARCHAR(64)     NOT NULL,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active',
    PRIMARY KEY (course_id, assistant_uid),
    FOREIGN KEY (course_id)
        REFERENCES public.course (course_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT assistant_course_unq
        UNIQUE (course_id, assistant_uid)
);
GRANT ALL PRIVILEGES ON assistant.assistant TO schooner_dev;
GRANT SELECT ON assistant.assistant TO "www-data";

COMMENT ON TABLE assistant.assistant IS
'Assistants for each course implementation.';
COMMENT ON COLUMN assistant.assistant.status IS
'UTU ID/username of the assistant.':
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
CREATE TABLE assistant.evaluation
(
    submission_id       INT             NOT NULL PRIMARY KEY,
    course_id           VARCHAR(32)     NOT NULL,
    assistant_uid       VARCHAR(10)     NOT NULL,
    started             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended               TIMESTAMP       NULL,
    FOREIGN KEY (submission_id)
        REFERENCES submission (submission_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (course_id, assistant_uid)
        REFERENCES assistant.assistant (course_id, assistant_uid)
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
-- INSERT removed, functions run as SECURITY DEFINER

COMMENT ON TABLE assistant.evaluation IS
'This table is inserted with a row when the evaluation of a submission begins, and it is updated with the .ended once the evaluation is complete. For work queue management, not having a row in this table means that the submission is available for evaluation, having a row without .ended value means that evaluation is in progress and having .ended value means that the submission has been evaluated.';
COMMENT ON COLUMN assistant.evaluation.assistant_uid IS
'User ID of the assistant.';


CREATE TABLE assistant.accesstoken
(
    submission_id       INT         NOT NULL,
    token               INT         NOT NULL,
    expires             TIMESTAMP   NOT NULL,
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
CREATE OR REPLACE FUNCTION
assistant.evaluation_begin(
    in_assistant_uid    VARCHAR(10),
    in_submission_id    INT
)
    RETURNS INT
    LANGUAGE PLPGSQL
    SECURITY DEFINER
    VOLATILE
    STRICT
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
    v_accesstoken       INT;
    v_token_duration    TIME;
BEGIN
    -- Query token duration from config
    SELECT      token_duration
    FROM        assistant.config
    WHERE       rowlock = TRUE
    INTO        v_token_duration;
    IF NOT FOUND THEN
        RAISE EXCEPTION
        'ERROR: Configuration table ''assistant.config'' is empty!'
        USING HINT = 'CONFIG_ERROR';
    END IF;
    -- LOCK submission row
    PERFORM     *
    FROM        submission
    WHERE       submission_id = in_submission_id
    FOR UPDATE;
    -- LOCK evaluation table
    LOCK TABLE assistant.evaluation IN ACCESS EXCLUSIVE MODE;

    -- Submission must exist and be in 'draft' state
    SELECT      *
    FROM        submission
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
    WHERE       assistant_uid = in_assistant_uid
                AND
                course_id = r_submission.course_id
    INTO        r_assistant;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not registered for course (''%'')!',
            in_assistant_uid, r_submission.course_id
            USING HINT = 'ASSISTANT_NOT_REGISTERED';
    ELSIF r_assistant.status != 'active' THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not active!', in_assistant_uid
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
            assistant_uid
        )
        VALUES
        (
            in_submission_id,
            r_submission.course_id,
            in_assistant_uid
        );
    ELSE
        IF r_evaluation.ended IS NOT NULL THEN
            RAISE EXCEPTION
            'Evaluation for submission (%) is already completed!',
            in_submission_id
            USING HINT = 'EVALUATION_COMPLETED';
        ELSIF r_evaluation.assistant_uid != in_assistant_uid THEN
            RAISE EXCEPTION
            'Evaluation for submission (%) belongs to another assistant (''%'')',
            in_submission_id, r_evaluation.assistant_uid
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



CREATE OR REPLACE FUNCTION
assistant.evaluation_close(
    in_assistant_uid    VARCHAR(10),
    in_submission_id    INT,
    in_score            INT,
    in_feedback         TEXT,
    in_confidential     TEXT
)
    RETURNS TIME
    LANGUAGE PLPGSQL
    SECURITY DEFINER
    VOLATILE
    STRICT
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
    v_row_count         INT;
    v_closing_datetime  TIMESTAMP := CURRENT_TIMESTAMP;
BEGIN
    -- LOCK submission row
    PERFORM     *
    FROM        submission
    WHERE       submission_id = in_submission_id
    FOR UPDATE;
    -- LOCK evaluation table
    LOCK TABLE assistant.evaluation IN ACCESS EXCLUSIVE MODE;

    -- Submission must exist and be in 'draft' state
    SELECT      *
    FROM        submission
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
    WHERE       assistant_uid = in_assistant_uid
                AND
                course_id = r_submission.course_id
    INTO        r_assistant;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not registered for course (''%'')!',
            in_assistant_uid, r_submission.course_id
            USING HINT = 'ASSISTANT_NOT_REGISTERED';
    ELSIF r_assistant.status != 'active' THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not active!', in_assistant_uid
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
    ELSIF r_evaluation.assistant_uid != in_assistant_uid THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) belongs to another assistant (''%'')',
        in_submission_id, r_evaluation.assistant_uid
        USING HINT = 'EVALUATION_OWNER';
    END IF;

    -- Check given score against assignment maximum
    SELECT      *
    FROM        assignment
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
    UPDATE  submission
    SET     state           = 'accepted',
            evaluator       = in_assistant_uid,
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



CREATE OR REPLACE FUNCTION
assistant.evaluation_reject(
    in_assistant_uid    VARCHAR(10),
    in_submission_id    INT,
    in_feedback         TEXT,
    in_confidential     TEXT
)
    RETURNS TIME
    LANGUAGE PLPGSQL
    SECURITY DEFINER
    VOLATILE
    STRICT
AS $$
DECLARE
    r_submission        RECORD;
    r_assistant         RECORD;
    r_evaluation        RECORD;
    v_row_count         INT;
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
--    WHERE       assistant_uid = in_assistant_uid
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
    FROM        submission
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
    ELSIF r_evaluation.assistant_uid != in_assistant_uid THEN
        RAISE EXCEPTION
        'Evaluation for submission (%) belongs to another assistant (''%'')',
        in_submission_id, r_evaluation.assistant_uid
        USING HINT = 'EVALUATION_OWNER';
    END IF;

    -- Assistant must be working for the same course as the submission is for
    SELECT      *
    FROM        assistant.assistant
    WHERE       assistant_uid = in_assistant_uid
                AND
                course_id = r_submission.course_id
    INTO        r_assistant;
    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not registered for course (''%'')!',
            in_assistant_uid, r_submission.course_id
            USING HINT = 'ASSISTANT_NOT_REGISTERED';
    ELSIF r_assistant.status != 'active' THEN
        RAISE EXCEPTION
            'Assistant (''%'') is not active!', in_assistant_uid
            USING HINT = 'ASSISTANT_NOT_ACTIVE';
    END IF;

    --
    -- Update submission and evaluation, remove access token
    --
    UPDATE  submission
    SET     state           = 'rejected',
            evaluator       = in_assistant_uid,
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


-- EOF
