--
-- Course data for DTE20068-3002 (2021)
--

PRAGMA foreign_keys=1;


INSERT INTO course
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


-- Exercises 6x (=500), Quizzes 7x 35 (=245), Exam 245, Tasks 10 
INSERT INTO assignment
VALUES
('T01', 'DTE20068-3002', 'GitHub Account Registration', NULL, 1, 1, '2021-10-30', NULL),
('T02', 'DTE20068-3002', 'VM Workshop', 'Component Kit distribution', 5, 5, '2021-10-27', NULL),
('E01', 'DTE20068-3002', 'Week 2 Exercise', 'Blink a LED', 40, NULL, '2021-11-07', NULL),
('E02', 'DTE20068-3002', 'Week 3 Exercise', 'Read ADC', 60, NULL, '2021-11-14', NULL),
('E03', 'DTE20068-3002', 'Week 4 Exercise', 'ISR & Timer', 80, NULL, '2021-11-21', NULL),
('E04', 'DTE20068-3002', 'Week 5 Exercise', 'Servo and PID', 100, NULL, '2021-11-28', NULL),
('E05', 'DTE20068-3002', 'Week 6 Exercise', 'FreeRTOS', 100, NULL, '2021-12-05', NULL),
('E06', 'DTE20068-3002', 'Week 7 Exercise', 'Run for the hills!', 120, NULL, '2021-12-12', NULL),
('Q01', 'DTE20068-3002', 'Week 1 Quizz', NULL, 35, NULL, '2021-10-31', NULL),
('Q02', 'DTE20068-3002', 'Week 2 Quizz', NULL, 35, NULL, '2021-11-07', NULL),
('Q03', 'DTE20068-3002', 'Week 3 Quizz', NULL, 35, NULL, '2021-11-14', NULL),
('Q04', 'DTE20068-3002', 'Week 4 Quizz', NULL, 35, NULL, '2021-11-21', NULL),
('Q05', 'DTE20068-3002', 'Week 5 Quizz', NULL, 35, NULL, '2021-11-28', NULL),
('Q06', 'DTE20068-3002', 'Week 6 Quizz', NULL, 35, NULL, '2021-12-05', NULL),
('Q07', 'DTE20068-3002', 'Week 7 Quizz', NULL, 35, NULL, '2021-12-12', NULL),
('T03', 'DTE20068-3002', 'Component kit return', NULL, 5, 5, '2021-12-12', NULL),
('EXM', 'DTE20068-3002', 'Exam', 'exam.utu.fi exam, based on weekly quizzes', 245, 147, '2021-12-12', NULL);