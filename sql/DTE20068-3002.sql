--
-- Schooner - Simple Course Management System
-- DTE20068-3002.sql / Course instance for P2/2021
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--  2021-08-22  Updated for assignment.retries.
--

INSERT INTO core.course
VALUES
(
'DTE20068-3002',
'DTE20068',
'Embedded Microprocessor Systems',
'2021-10-25',
'2021-12-20',
'0-5/60',
'Exercise privilege is automatically earned once total of 355 points has been earned.

Passing the course requires:
- 60% of the total course points (600 points).
- Attendance at VM Workshop (27.10.2021).
- 60% score in the exam.
- Component kit has been returned.'
);

INSERT INTO core.assignment
VALUES
(
    'T01',
    'DTE20068-3002',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2021-10-30',
    NULL
),
(
    'T02',
    'DTE20068-3002',
    'VM Workshop',
    'Component Kit distribution',
    NULL,
    1,
    1,
    0,
    '2021-10-27',
    NULL
),
(
    'E01',
    'DTE20068-3002',
    'Week 2 Exercise',
    'Blink a LED',
    'HUBBOT',
    40,
    NULL,
    0,
    '2021-11-07',
    NULL
),
(
    'E02',
    'DTE20068-3002',
    'Week 3 Exercise',
    'Read ADC',
    'HUBBOT',
    60,
    NULL,
    0,
    '2021-11-14',
    NULL
),
(
    'E03',
    'DTE20068-3002',
    'Week 4 Exercise',
    'ISR & Timer',
    'HUBBOT',
    80,
    NULL,
    0,
    '2021-11-21',
    NULL
),
(
    'E04',
    'DTE20068-3002',
    'Week 5 Exercise',
    'Servo and PID',
    'HUBBOT',
    100,
    NULL,
    0,
    '2021-11-28',
    NULL
),
(
    'E05',
    'DTE20068-3002',
    'Week 6 Exercise',
    'FreeRTOS',
    'HUBBOT',
    100,
    NULL,
    0,
    '2021-12-05',
    NULL
),
(
    'E06',
    'DTE20068-3002',
    'Week 7 Exercise',
    'Run for the hills!',
    'HUBBOT',
    120,
    NULL,
    0,
    '2021-12-12',
    NULL
),
(
    'Q01',
    'DTE20068-3002',
    'Week 1 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-10-31',
    NULL
),
(
    'Q02',
    'DTE20068-3002',
    'Week 2 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-07',
    NULL
),
(
    'Q03',
    'DTE20068-3002',
    'Week 3 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-14',
    NULL
),
(
    'Q04',
    'DTE20068-3002',
    'Week 4 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-21',
    NULL
),
(
    'Q05',
    'DTE20068-3002',
    'Week 5 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-11-28',
    NULL
),
(
    'Q06',
    'DTE20068-3002',
    'Week 6 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-12-05',
    NULL
),
(
    'Q07',
    'DTE20068-3002',
    'Week 7 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2021-12-12',
    NULL
),
(
    'T03',
    'DTE20068-3002',
    'Component kit return',
    'Course grade cannot be sent to Peppi until loan equipment has been returned.',
    NULL,
    8,
    8,
    0,
    '2021-12-12',
    NULL
),
(
    'EXM',
    'DTE20068-3002',
    'Exam',
    'exam.utu.fi exam, based on weekly quizzes',
    NULL,
    245,
    147,
    2,
    '2021-12-12',
    NULL
);
