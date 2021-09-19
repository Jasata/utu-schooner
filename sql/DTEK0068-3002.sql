--
-- Schooner - Simple Course Management System
-- DTEK0068-3002.sql / Course instance for P2/2021
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--  2021-08-22  Updated for assignment.retries.
--  2021-08-25  Updated DTE2 -> DTEK & new columns.
--  2021-09-01  Updated for ASSETMGR.
--

\echo '=== INSERT''ing DTEK0068-3002...'
INSERT INTO core.course
(
    course_id,
    code,
    name,
    email,
    github_account,
    github_accesstoken,
    enrollment_message,
    opens,
    closes,
    gradesys_id,
    description
)
VALUES
(
    'DTEK0068-3002',
    'DTEK0068',
    'Embedded Microprocessor Systems',
    'dtek0068@utu.fi',
    'DTEK0068',
    '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',
    'DTEK0068-3002_WELCOME',
    '2021-10-25',
    '2021-12-19',
    '0-5/60',
    'Exercise privilege is automatically earned once total of 355 points has been earned.

    Passing the course requires:
    - 60% of the total course points (600 points).
    - Attendance at VM Workshop (27.10.2021).
    - 60% score in the exam.
    - Component kit has been returned.'
);

INSERT INTO core.assignment
(
    assignment_id,
    course_id,
    name,
    description,
    handler,
    points,
    pass,
    retries,
    deadline,
    latepenalty,
    evaluation
)
VALUES
(
    'T01',
    'DTEK0068-3002',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2021-10-30',
    NULL,
    DEFAULT
),
(
    'T02',
    'DTEK0068-3002',
    'Component Kit Loan',
    'Component Kit lending. A ''draft'' submission registers the kit ID for loan and once returned, the submission is set to ''accepted''',
    'ASSETMGR',
    1,
    1,
    NULL,
    '2021-12-17',
    NULL,
    'last'
),
(
    'E01',
    'DTEK0068-3002',
    'Week 2 Exercise',
    'Blink a LED',
    'HUBBOT',
    40,
    NULL,
    0,
    '2021-11-07',
    NULL,
    DEFAULT
),
(
    'E02',
    'DTEK0068-3002',
    'Week 3 Exercise',
    'Read ADC',
    'HUBBOT',
    60,
    NULL,
    0,
    '2021-11-14',
    NULL,
    DEFAULT
),
(
    'E03',
    'DTEK0068-3002',
    'Week 4 Exercise',
    'ISR & Timer',
    'HUBBOT',
    80,
    NULL,
    0,
    '2021-11-21',
    NULL,
    DEFAULT
),
(
    'E04',
    'DTEK0068-3002',
    'Week 5 Exercise',
    'Servo and PID',
    'HUBBOT',
    100,
    NULL,
    0,
    '2021-11-28',
    NULL,
    DEFAULT
),
(
    'E05',
    'DTEK0068-3002',
    'Week 6 Exercise',
    'FreeRTOS',
    'HUBBOT',
    100,
    NULL,
    0,
    '2021-12-05',
    NULL,
    DEFAULT
),
(
    'E06',
    'DTEK0068-3002',
    'Week 7 Exercise',
    'Run for the hills!',
    'HUBBOT',
    120,
    NULL,
    0,
    '2021-12-12',
    NULL,
    DEFAULT
),
(
    'Q01',
    'DTEK0068-3002',
    'Week 1 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-10-31',
    NULL,
    DEFAULT
),
(
    'Q02',
    'DTEK0068-3002',
    'Week 2 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-07',
    NULL,
    DEFAULT
),
(
    'Q03',
    'DTEK0068-3002',
    'Week 3 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-14',
    NULL,
    DEFAULT
),
(
    'Q04',
    'DTEK0068-3002',
    'Week 4 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-21',
    NULL,
    DEFAULT
),
(
    'Q05',
    'DTEK0068-3002',
    'Week 5 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-28',
    NULL,
    DEFAULT
),
(
    'Q06',
    'DTEK0068-3002',
    'Week 6 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-12-05',
    NULL,
    DEFAULT
),
(
    'Q07',
    'DTEK0068-3002',
    'Week 7 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-12-12',
    NULL,
    DEFAULT
),
(
    'EXM',
    'DTEK0068-3002',
    'Exam',
    'exam.utu.fi exam, based on weekly quizzes',
    NULL,
    245,
    147,
    2,
    '2021-12-12',
    NULL,
    'best'
);

INSERT INTO email.template
VALUES
(
    'DTEK0068-3002_WELCOME',
    DEFAULT,
    'high',
    'IMPORTANT! Required tasks before Wednesday!',
    'Welcome to {{ course_code }} {{ course_name }}

VERY IMPORTANT: Number of tasks must be completed before the mandatory VM Workshop this Wednesday!

Due to the corona situation, just like last year, course will be rendered mostly as self-study remote teaching. This message should give you all the necessary information to get started on this course, so please read this carefully.

This course has only one mandatory face-to-face attendance. You must attend to the VM Workshop & component kit distribution event this Wednesday! Failure to attend will result in losing the course seat.

NOTE: There will be no lecture on this Tuesday. First event is the Wednesday VM Workshop.

Schedule for VM Workshop is very tight, please try not to be late.

Regards,
{{ course_code }}
{{ course_email }}',
    DEFAULT,
    NULL
);

-- EOF