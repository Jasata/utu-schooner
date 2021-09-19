--
-- Schooner - Simple Course Management System
-- core.dev_data.sql / Development and testing data set
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-19  Initial version.
--  2021-08-23  Changed to schema 'core'.
--  2021-08-31  Changed for assignment.evaluation.
--

-- Future DTE20068 (2022)
\echo '=== INSERT''ing core development data...'
INSERT INTO core.course
(
    course_id,
    code,
    name,
    email,
    enrollment_message,
    opens,
    closes,
    gradesys_id,
    description
)
VALUES
(
    'DTEK0068-3003',
    'DTEK0068',
    'Embedded Microprocessor Systems',
    'dtek0068@utu.fi',
    NULL,
    '2022-10-25',
    '2022-12-20',
    '0-5/60',
    'Future implementation.'
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
    'DTEK0068-3003',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2022-10-30',
    NULL,
    DEFAULT
),
(
    'T02',
    'DTEK0068-3003',
    'VM Workshop',
    'Component Kit distribution',
    NULL,
    1,
    1,
    0,
    '2022-10-27',
    NULL,
    'last'
),
(
    'E01',
    'DTEK0068-3003',
    'Week 2 Exercise',
    'Blink a LED',
    'HUBBOT',
    40,
    NULL,
    0,
    '2022-11-07',
    NULL,
    DEFAULT
),
(
    'E02',
    'DTEK0068-3003',
    'Week 3 Exercise',
    'Read ADC',
    'HUBBOT',
    60,
    NULL,
    0,
    '2022-11-14',
    NULL,
    DEFAULT
),
(
    'E03',
    'DTEK0068-3003',
    'Week 4 Exercise',
    'ISR & Timer',
    'HUBBOT',
    80,
    NULL,
    0,
    '2022-11-21',
    NULL,
    DEFAULT
),
(
    'E04',
    'DTEK0068-3003',
    'Week 5 Exercise',
    'Servo and PID',
    'HUBBOT',
    100,
    NULL,
    0,
    '2022-11-28',
    NULL,
    DEFAULT
),
(
    'E05',
    'DTEK0068-3003',
    'Week 6 Exercise',
    'FreeRTOS',
    'HUBBOT',
    100,
    NULL,
    0,
    '2022-12-05',
    NULL,
    DEFAULT
),
(
    'E06',
    'DTEK0068-3003',
    'Week 7 Exercise',
    'Run for the hills!',
    'HUBBOT',
    120,
    NULL,
    0,
    '2022-12-12',
    NULL,
    DEFAULT
),
(
    'Q01',
    'DTEK0068-3003',
    'Week 1 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-10-31',
    NULL,
    DEFAULT
),
(
    'Q02',
    'DTEK0068-3003',
    'Week 2 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-11-07',
    NULL,
    DEFAULT
),
(
    'Q03',
    'DTEK0068-3003',
    'Week 3 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-11-14',
    NULL,
    DEFAULT
),
(
    'Q04',
    'DTEK0068-3003',
    'Week 4 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-11-21',
    NULL,
    DEFAULT
),
(
    'Q05',
    'DTEK0068-3003',
    'Week 5 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-11-28',
    NULL,
    DEFAULT
),
(
    'Q06',
    'DTEK0068-3003',
    'Week 6 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-12-05',
    NULL,
    DEFAULT
),
(
    'Q07',
    'DTEK0068-3003',
    'Week 7 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    0,
    '2022-12-12',
    NULL,
    DEFAULT
),
(
    'EXM',
    'DTEK0068-3003',
    'Exam',
    'exam.utu.fi exam, based on weekly quizzes',
    NULL,
    245,
    147,
    2,
    '2022-12-12',
    NULL,
    'best'
);



-- For Dummies course
\echo 'DTEK0000-* PAST, ONGOING and FUTURE courses'
INSERT INTO core.course
(
    course_id,
    code,
    name,
    email,
    enrollment_message,
    opens,
    closes,
    gradesys_id,
    description
)
VALUES
(
    'DTEK0000-3000',
    'DTEK0000',
    'PAST course (2019)',
    NULL,
    NULL,
    '2019-10-25',
    '2019-12-18',
    '0-5/60',
    'For Dummies. Made by a Dummy.'
),
(
    'DTEK0000-3001',
    'DTEK0000',
    'PAST course (2020)',
    NULL,
    NULL,
    '2020-10-25',
    '2020-12-18',
    '0-5/60',
    'For Dummies. Made by a Dummy.'
),
(
    'DTEK0000-3002',
    'DTEK0000',
    'CURRENT course (2021)',
    NULL,
    NULL,
    '2021-08-25',
    '2021-12-18',
    '0-5/60',
    'For Dummies. Made by a Dummy.'
),
(
    'DTEK0000-3003',
    'DTEK0000',
    'FUTURE course (2022)',
    NULL,
    NULL,
    '2022-10-25',
    '2022-12-18',
    '0-5/60',
    'For Dummies. Made by a Dummy.'
),
(
    'DTEK0000-3004',
    'DTEK0000',
    'FUTURE course (2023)',
    NULL,
    NULL,
    '2023-10-25',
    '2023-12-18',
    '0-5/60',
    'For Dummies. Made by a Dummy.'
);

--
-- Each of them shall have a basic set of assignments
--
\echo 'DTEK0000-* GitHub Account Registration Assignments'
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
    latepenalty
)
VALUES
(
    'T01',
    'DTEK0000-3000',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2019-12-18',
    NULL
),
(
    'T01',
    'DTEK0000-3001',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2020-12-18',
    NULL
),
(
    'T01',
    'DTEK0000-3002',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2021-12-18',
    NULL
),
(
    'T01',
    'DTEK0000-3003',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2021-12-18',
    NULL
),
(
    'T01',
    'DTEK0000-3004',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    NULL,
    '2021-12-18',
    NULL
);

\echo 'DTEK0000-* Asset loans'
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
    latepenalty
)
VALUES
('T02', 'DTEK0000-3000', 'Asset loan', 'Students sign for course material loan.', 'ASSETMGR', 1, 1, NULL, '2019-09-20', NULL),
('T02', 'DTEK0000-3001', 'Asset loan', 'Students sign for course material loan.', 'ASSETMGR', 1, 1, NULL, '2020-09-20', NULL),
('T02', 'DTEK0000-3002', 'Asset loan', 'Students sign for course material loan.', 'ASSETMGR', 1, 1, NULL, '2021-09-20', NULL),
('T02', 'DTEK0000-3003', 'Asset loan', 'Students sign for course material loan.', 'ASSETMGR', 1, 1, NULL, '2022-09-20', NULL),
('T02', 'DTEK0000-3004', 'Asset loan', 'Students sign for course material loan.', 'ASSETMGR', 1, 1, NULL, '2023-09-20', NULL);


\echo 'DTEK0000-* Weekly quizzes'
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
    latepenalty
)
VALUES
('Q01', 'DTEK0000-3000', 'First weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2019-09-07', NULL),
('Q01', 'DTEK0000-3001', 'First weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2020-09-07', NULL),
('Q01', 'DTEK0000-3002', 'First weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2021-09-07', NULL),
('Q01', 'DTEK0000-3003', 'First weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2022-09-07', NULL),
('Q01', 'DTEK0000-3004', 'First weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2023-09-07', NULL);

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
    latepenalty
)
VALUES
('Q02', 'DTEK0000-3000', 'Second weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2019-09-14', NULL),
('Q02', 'DTEK0000-3001', 'Second weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2020-09-14', NULL),
('Q02', 'DTEK0000-3002', 'Second weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2021-09-14', NULL),
('Q02', 'DTEK0000-3003', 'Second weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2022-09-14', NULL),
('Q02', 'DTEK0000-3004', 'Second weekly quiz', 'Visit ViLLE', 'APLUS', 40, 20, 2, '2023-09-14', NULL);


\echo 'DTEK0000-* Weekly execises'
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
    latepenalty
)
VALUES
('E01', 'DTEK0000-3000', 'First exercise', 'Hello World', 'HUBBOT', 40, 20, 2, '2019-09-07', NULL),
('E01', 'DTEK0000-3001', 'First exercise', 'Hello World', 'HUBBOT', 40, 20, 2, '2020-09-07', NULL),
('E01', 'DTEK0000-3002', 'First exercise', 'Hello World', 'HUBBOT', 40, 20, 2, '2021-09-07', NULL),
('E01', 'DTEK0000-3003', 'First exercise', 'Hello World', 'HUBBOT', 40, 20, 2, '2022-09-07', NULL),
('E01', 'DTEK0000-3004', 'First exercise', 'Hello World', 'HUBBOT', 40, 20, 2, '2023-09-07', NULL);


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
    latepenalty
)
VALUES
('E02', 'DTEK0000-3000', 'ROT13', 'encoder/decoder', 'HUBBOT', 60, NULL, 2, '2019-09-14', NULL),
('E02', 'DTEK0000-3001', 'ROT13', 'encoder/decoder', 'HUBBOT', 60, NULL, 2, '2020-09-14', NULL),
('E02', 'DTEK0000-3002', 'ROT13', 'encoder/decoder', 'HUBBOT', 60, NULL, 2, '2021-09-14', NULL),
('E02', 'DTEK0000-3003', 'ROT13', 'encoder/decoder', 'HUBBOT', 60, NULL, 2, '2022-09-14', NULL),
('E02', 'DTEK0000-3004', 'ROT13', 'encoder/decoder', 'HUBBOT', 60, NULL, 2, '2023-09-14', NULL);


\echo 'DTEK0000-* Exam'
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
    latepenalty
)
VALUES
('EXM', 'DTEK0000-3000', 'Exam', 'exam.utu.fi exam', NULL, 220, 140, 2, '2019-12-31', NULL),
('EXM', 'DTEK0000-3001', 'Exam', 'exam.utu.fi exam', NULL, 220, 140, 2, '2020-12-31', NULL),
('EXM', 'DTEK0000-3002', 'Exam', 'exam.utu.fi exam', NULL, 220, 140, 2, '2021-12-31', NULL),
('EXM', 'DTEK0000-3003', 'Exam', 'exam.utu.fi exam', NULL, 220, 140, 2, '2022-12-31', NULL),
('EXM', 'DTEK0000-3004', 'Exam', 'exam.utu.fi exam', NULL, 220, 140, 2, '2023-12-31', NULL);






\echo 'DTEK0002-3002 Poems course'
INSERT INTO core.course
(
    course_id,
    code,
    name,
    email,
    enrollment_message,
    opens,
    closes,
    gradesys_id,
    description
)
VALUES
(
    'DTEK0002-3002',
    'DTEK0002',
    'Poems and haikus for modern programmer',
    NULL,
    NULL,
    '2021-08-01',
    '2022-11-01',
    'F-P/50',
    'Become proficient in poems and haikus to gain additional edge when competing for job opportunities.'
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
    latepenalty
)
VALUES
(
    'T01',
    'DTEK0002-3002',
    'First meeting',
    'Participants will create classical and modern poems.',
    NULL,
    40,
    40,
    0,
    '2021-08-05',
    NULL
),
(
    'T02',
    'DTEK0002-3002',
    'Second meeting',
    'In this session, each participant will write 4 haikus and whisper them into the wind.',
    NULL,
    40,
    40,
    0,
    '2021-08-12',
    NULL
),
('E01', 'DTEK0002-3002', 'First exercise', 'Hello Universe', 'HUBBOT', 40, 20, 2, '2019-09-06', 0.10),
('E02', 'DTEK0002-3002', 'Second exercise', 'Hello Infinity', 'HUBBOT', 40, 20, 2, '2020-09-07', 0.20);


--
-- Enrollments
--
\echo 'Enrolling developers (''jasata'',''tumipo'', ''_none_'')'
INSERT INTO core.enrollee
(
    course_id,
    uid,
    studentid,
    email,
    lastname,
    firstname
)
VALUES
('DTEK0000-3000', 'tumipo', 506523, 'tumipo@utu.fi', 'Polvinen', 'Tuisku'),
('DTEK0000-3001', 'tumipo', 506523, 'tumipo@utu.fi', 'Polvinen', 'Tuisku'),
('DTEK0000-3002', 'tumipo', 506523, 'tumipo@utu.fi', 'Polvinen', 'Tuisku'),
('DTEK0000-3003', 'tumipo', 506523, 'tumipo@utu.fi', 'Polvinen', 'Tuisku'),
('DTEK0000-3000', 'jasata', 52493,  'jasata@utu.fi', 'Tammi',    'Jani'),
('DTEK0000-3001', 'jasata', 52493,  'jasata@utu.fi', 'Tammi',    'Jani'),
('DTEK0000-3002', 'jasata', 52493,  'jasata@utu.fi', 'Tammi',    'Jani'),
('DTEK0000-3003', 'jasata', 52493,  'jasata@utu.fi', 'Tammi',    'Jani'),
('DTEK0000-3004', 'jasata', 52493,  'jasata@utu.fi', 'Tammi',    'Jani'),
('DTEK0000-3001', '_none_', 123456, '_none_@null',   'Noneof',   'Yourbusiness'),
('DTEK0000-3002', '_none_', 123456, '_none_@null',   'Noneof',   'Yourbusiness');


INSERT INTO core.enrollee
(
    course_id,
    uid,
    studentid,
    email,
    lastname,
    firstname
)
VALUES
('DTEK0002-3002', 'tumipo', 506523, 'tumipo@utu.fi', 'Polvinen', 'Tuisku'),
('DTEK0002-3002', 'jasata', 52493,  'jasata@utu.fi', 'Tammi',    'Jani'),
('DTEK0002-3002', '_none_', 123456, '_none_@null',   'Noneof',   'Yourbusiness');



--
-- Submissions
--
INSERT INTO core.submission
(
    assignment_id,
    course_id,
    uid,
    content,
    state,
    evaluator,
    score
)
VALUES
('T01', 'DTEK0000-3002', 'jasata', 'Zorro',   'draft',    NULL,       NULL),
('T02', 'DTEK0000-3002', 'jasata', '#001',    'draft',    NULL,       NULL),
('T02', 'DTEK0000-3002', 'tumipo', '#002',    'draft',    NULL,       NULL);


INSERT INTO core.submission
(
    assignment_id,
    course_id,
    uid,
    content,
    state,
    evaluator,
    score
)
VALUES
('E01', 'DTEK0000-3002', 'jasata', 'WHAT GOES HERE',   'draft',    NULL,       NULL),
('E02', 'DTEK0000-3002', 'jasata', 'I did a thing',    'draft',    NULL,       NULL),
('E02', 'DTEK0000-3002', 'tumipo', 'Cake',             'draft',    NULL,       NULL);

-- EOF
