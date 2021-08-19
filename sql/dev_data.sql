--
-- Schooner - Simple Course Management System
-- dev_data.sql / Development and testing data set
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-19  Initial version.
--

-- Future DTE20068 (2022)
INSERT INTO course
VALUES
(
'DTE20068-3003',
'DTE20068',
'Embedded Microprocessor Systems',
'2022-10-25',
'2022-12-20',
'0-5/60',
'Future implementation.'
);

INSERT INTO assignment
VALUES
(
    'T01',
    'DTE20068-3003',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    '2022-10-30',
    NULL
),
(
    'T02',
    'DTE20068-3003',
    'VM Workshop',
    'Component Kit distribution',
    NULL,
    1,
    1,
    '2022-10-27',
    NULL
),
(
    'E01',
    'DTE20068-3003',
    'Week 2 Exercise',
    'Blink a LED',
    'HUBBOT',
    40,
    NULL,
    '2022-11-07',
    NULL
),
(
    'E02',
    'DTE20068-3003',
    'Week 3 Exercise',
    'Read ADC',
    'HUBBOT',
    60,
    NULL,
    '2022-11-14',
    NULL
),
(
    'E03',
    'DTE20068-3003',
    'Week 4 Exercise',
    'ISR & Timer',
    'HUBBOT',
    80,
    NULL,
    '2022-11-21',
    NULL
),
(
    'E04',
    'DTE20068-3003',
    'Week 5 Exercise',
    'Servo and PID',
    'HUBBOT',
    100,
    NULL,
    '2022-11-28',
    NULL
),
(
    'E05',
    'DTE20068-3003',
    'Week 6 Exercise',
    'FreeRTOS',
    'HUBBOT',
    100,
    NULL,
    '2022-12-05',
    NULL
),
(
    'E06',
    'DTE20068-3003',
    'Week 7 Exercise',
    'Run for the hills!',
    'HUBBOT',
    120,
    NULL,
    '2022-12-12',
    NULL
),
(
    'Q01',
    'DTE20068-3003',
    'Week 1 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-10-31',
    NULL
),
(
    'Q02',
    'DTE20068-3003',
    'Week 2 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-11-07',
    NULL
),
(
    'Q03',
    'DTE20068-3003',
    'Week 3 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-11-14',
    NULL
),
(
    'Q04',
    'DTE20068-3003',
    'Week 4 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-11-21',
    NULL
),
(
    'Q05',
    'DTE20068-3003',
    'Week 5 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-11-28',
    NULL
),
(
    'Q06',
    'DTE20068-3003',
    'Week 6 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-12-05',
    NULL
),
(
    'Q07',
    'DTE20068-3003',
    'Week 7 Quizz',
    NULL,
    'APLUS',
    35,
    NULL,
    '2022-12-12',
    NULL
),
(
    'T03',
    'DTE20068-3003',
    'Component kit return',
    'Course grade cannot be sent to Peppi until loan equipment has been returned.',
    NULL,
    8,
    8,
    '2022-12-12',
    NULL
),
(
    'EXM',
    'DTE20068-3003',
    'Exam',
    'exam.utu.fi exam, based on weekly quizzes',
    NULL,
    245,
    147,
    '2022-12-12',
    NULL
);



-- For Dummies course
INSERT INTO course
VALUES
(
'DTE20000-3002',
'DTE20000',
'For Dummies course',
'2021-08-01',
'2022-10-01',
'0-5/60',
'For Dummies. Made by a Dummy.'
);


INSERT INTO assignment
VALUES
(
    'T01',
    'DTE20000-3002',
    'GitHub Account Registration',
    'Student must register the GitHub account that will be used to submit the exercises in this course.',
    'HUBREG',
    1,
    1,
    '2021-08-25',
    NULL
),
(
    'T02',
    'DTE20000-3002',
    'First Lecture',
    'Mandatory first lecture of the course.',
    NULL,
    1,
    1,
    '2021-08-03',
    NULL
),
(
    'E01',
    'DTE20000-3002',
    'First exercise, mandatory',
    'Write Hello World',
    'HUBBOT',
    40,
    20,
    '2021-08-24',
    NULL
),
(
    'E02',
    'DTE20000-3002',
    'Second exercise, optional',
    'Write ROT13 encoder/decoder',
    'HUBBOT',
    60,
    NULL,
    '2021-09-04',
    NULL
),
(
    'EXM',
    'DTE20000-3002',
    'Exam',
    'exam.utu.fi exam',
    NULL,
    220,
    140,
    '2021-11-21',
    NULL
);

-- For Dummies course
INSERT INTO course
VALUES
(
'DTE20002-3002',
'DTE20002',
'Poems and haikus for modern programmer',
'2021-08-01',
'2022-11-01',
'F-P/50',
'Become proficient in poems and haikus to gain additional edge when competing for job opportunities.'
);

INSERT INTO assignment
VALUES
(
    'T01',
    'DTE20002-3002',
    'First meeting',
    'Participants will create classical and modern poems.',
    NULL,
    40,
    40,
    '2021-08-05',
    NULL
),
(
    'T02',
    'DTE20002-3002',
    'Second meeting',
    'In this session, each participant will write 4 haikus and whisper them into the wind.',
    NULL,
    40,
    40,
    '2021-08-12',
    NULL
);


--
-- Enrollments
--
INSERT INTO enrollee
(
    course_id,
    uid,
    studentid,
    email,
    lastname,
    firstname
)
VALUES
(
    'DTE20068-3002',
    'tumipo',
    506523,
    'tumipo@utu.fi',
    'Polvinen',
    'Tuisku'
),
(
    'DTE20000-3002',
    'tumipo',
    506523,
    'tumipo@utu.fi',
    'Polvinen',
    'Tuisku'
),
(
    'DTE20002-3002',
    'tumipo',
    506523,
    'tumipo@utu.fi',
    'Polvinen',
    'Tuisku'
),
(
    'DTE20068-3002',
    'jasata',
    52493,
    'jasata@utu.fi',
    'Tammi',
    'Jani'
),
(
    'DTE20000-3002',
    'jasata',
    52493,
    'jasata@utu.fi',
    'Tammi',
    'Jani'
),
(
    'DTE20002-3002',
    'jasata',
    52493,
    'jasata@utu.fi',
    'Tammi',
    'Jani'
);



--
-- Submissions
--
INSERT INTO submission
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
(
    'T01',
    'DTE20068-3002',
    'jasata',
    'Zorro',
    'draft',
    NULL,
    NULL
),
(
    'T02',
    'DTE20068-3002',
    'jasata',
    'KIT:001',
    'accepted',
    'www-data',
    1
),
(
    'T02',
    'DTE20068-3002',
    'tumipo',
    'KIT:002',
    'accepted',
    'www-data',
    1
),
(
    'Q02',
    'DTE20068-3002',
    'tumipo',
    'retrieved-from-aplus',
    'accepted',
    'www-data',
    33
);

