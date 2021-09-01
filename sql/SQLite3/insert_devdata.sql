--
-- Development data
--
PRAGMA foreign_keys=1;



INSERT INTO enrollee
(course_id, uid, github, studentid, email, lastname, firstname)
VALUES
('DTE20068-3002', 'jasata', 'jasata', 59482, 'jasata@utu.fi', 'Jani', 'Tammi'),
('DTE20068-3002', 'tumipo', 'variski', 101010, 'tumipo@utu.fi', 'Tuisku', 'Polvinen');




INSERT INTO submission
(assignment_id, course_id, uid, score, notes)
VALUES
('T01', 'DTE20068-3002', 'jasata', 1, NULL),
('T01', 'DTE20068-3002', 'tumipo', 1, NULL),
('Q01', 'DTE20068-3002', 'tumipo', 34, NULL),
('Q01', 'DTE20068-3002', 'jasata', 27, NULL),
('E01', 'DTE20068-3002', 'jasata', 31, 'Coding standard ignored -5 p. Incorrect use of register -4 p.'),
('EXM', 'DTE20068-3002', 'jasata', 131, NULL),
('EXM', 'DTE20068-3002', 'jasata', 158, NULL);
