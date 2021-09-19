#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# CourseAssistant.py - Data dictionary class for assistant.assistant
#   2021-09-07  Initial version.
#
#
# (2021-09-18)  Used currently in assistant's submission evaluation view,
#               in '/assistant_evaluation.html', assistant_evaluation().
#



class AssignmentSubmission(dict):

    SQL = """
        SELECT      submission.submission_id,
                    submission.assignment_id,
                    submission.course_id,
                    submission.uid,
                    submission.content,
                    submission.submitted,
                    submission.accepted,
                    submission.state,
                    submission.evaluator,
                    submission.score,
                    submission.feedback,
                    submission.confidential,
                    assignment.name AS assignment_name,
                    assignment.description AS assignment_description,
                    assignment.handler AS assignment_handler,
                    assignment.points AS assignment_max_points,
                    assignment.pass AS assignment_points_to_pass,
                    assignment.retries AS assignment_retries,
                    assignment.deadline AS assignment_deadline,
                    assignment.latepenalty AS assignment_latepenalty,
                    assignment.evaluation AS assignment_evaluation,
                    evaluation.started AS evaluation_started,
                    evaluation.ended AS evaluation_ended,
                    assistant.uid AS assistant_uid,
                    assistant.name AS assistant_name,
                    assistant.status AS assistant_status,
                    course.code AS course_code,
                    course.name AS course_name,
                    course.opens AS course_opens,
                    course.closes AS course_closes,
                    enrollee.studentid AS enrollee_studentid,
                    enrollee.lastname AS enrollee_lastname,
                    enrollee.firstname AS enrollee_firstname,
                    enrollee.email AS enrollee_email,
                    enrollee.status AS enrollee_status
        FROM        core.submission
                    INNER JOIN core.assignment
                    ON (
                        submission.course_id = assignment.course_id
                        AND
                        submission.assignment_id = assignment.assignment_id
                    )
                    LEFT OUTER JOIN assistant.evaluation
                    ON (
                        submission.submission_id = evaluation.submission_id
                    )
                    LEFT OUTER JOIN assistant.assistant
                    ON (
                        evaluation.course_id = assistant.course_id
                        AND
                        evaluation.uid = assistant.uid
                    )
                    INNER JOIN core.course
                    ON (
                        submission.course_id = course.course_id
                    )
                    INNER JOIN core.enrollee
                    ON (
                        submission.course_id = enrollee.course_id
                        AND
                        submission.uid = enrollee.uid
                    )
        WHERE       submission.submission_id = %(submission_id)s
    """

    def __init__(self, cursor, submission_id: int):
        self.cursor = cursor
        self['submission_id'] = submission_id
        self.__update_self()




    def __update_self(self):
        if self.cursor.execute(AssignmentSubmission.SQL, self).rowcount != 1:
            raise Exception(
                f"Submission #{self['submission_id']} not found!"
            )
        self.update(
                dict(
                    zip(
                        [key[0] for key in self.cursor.description],
                        self.cursor.fetchone()
                    )
                )
            )




# EOF