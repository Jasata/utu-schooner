#!/bin/env python3
import os
from schooner.db.core.Assignment import Assignment
import psycopg

class GitAssignment(Assignment):
    """Git Assignment dictionary with .directive attribute, which is a separate dictionary that loads JSON data from column 'directives' over default directive values."""


    class Course(dict):
        def __init__(self, cursor, course_id: str):
            self.cursor = cursor
            SQL = """
            SELECT      *
            FROM        core.course
            WHERE       course_id = %(course_id)s
            """
            cursor.execute(SQL, locals())
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )


    # Default/seed key: values that get updated after being copied for an object instance
    default_directives = {
        "fetch" : {
            "trigger"   : {
                "type"      : "file",
                "path"      : "/",
                "pattern"   : "READY*"
            },
            "notify-on-failure" : True,
            "notify-on-success" : True
        },
        # Because git does not retrieve partial repositories, additional step is provided
        # which removes unwanted content. List of patterns, white- or blacklist.
        # Operation will be applied to the local cloned repository
        "prune" : {
            "type"  : "whitelist",
            "list"  : [ "*" ]
        },
        # Test -phase contains yet-to-be-determined automated testing sequences.
        # The may include such as: coding standard compliance scanning, compile tests,
        # container-based execution with input/output criteria.
        # THIS PART WILL NOT BE PART OF SCHOONER, but as an external service
        # API and implementation are left for future
        "test" : {
            "TBA" : "TBA"
        },
        # Evaluate -phase is inteded for course assistants to review things that
        # cannot reasobably be automated. This should be a list of evaluation
        # criteria that can be parsed into a check-list into the evaluation page.
        "evaluate" : [
            {
                "TBA" : "TBA"
            }
        ]
    }

    def __init__(self, cursor, course_id: str, assignment_id: str):
        super().__init__(cursor, course_id, assignment_id)
        # self.cursor = cursor
        # SQL = """
        # SELECT      *
        # FROM        core.assignment
        # WHERE       course_id = %(course_id)s
        #             AND
        #             assignment_id = %(assignment_id)s
        # """
        # if self.cursor.execute(SQL, locals()).rowcount:
        #     self.update(
        #         dict(
        #             zip(
        #                 [key[0] for key in cursor.description],
        #                 cursor.fetchone()
        #             )
        #         )
        #     )
        # else:
        #     raise ValueError(
        #         f"Assignment ('{course_id}', '{assignment_id}') not found!"
        #     )
        # Create directives attribute-dictionary
        import copy
        import json
        self.directive = copy.deepcopy(GitAssignment.default_directives)
        jsonstring = self.get("directives", None)
        if jsonstring:
            self.directive.update(json.loads(jsonstring))
        # Create sub-objects
        self.course = GitAssignment.Course(cursor, self['course_id'])


    def triggers(self, contents: list) -> bool:
        """Returns list of files/directories specified by directives.fetch.trigger. Normal outcome is that there is either none, or one. Multiple is considered as a logical error - one of them has to be identified as the intended submission. These are details that the caller must deal with."""
        # NOTE: This does NOT have the capability to traverse Git repository tree.
        #       All triggers must, for now, exist in the repository root.
        import fnmatch
        trigs = []
        for item in list(contents):
            if (self.directive['fetch']['trigger']['type'] == "any" or
                self.directive['fetch']['trigger']['type'] == item['type']):
                # print(
                #     "Type match! Matching ",
                #     item['path'],
                #     self.directive['fetch']['trigger']['pattern']
                # )
                if fnmatch.fnmatch(
                    item['path'],
                    self.directive['fetch']['trigger']['pattern']
                ):
                    # print("Pattern match!", self.directive['fetch']['trigger']['pattern'], item['path'])
                    # Add to the list of triggering items
                    trigs.append(
                        {
                            k : item[k]
                            for k
                            in set(item).intersection(
                                ('name', 'path', 'type', 'size')
                            )
                        }
                    )
        return trigs



if __name__ == '__main__':

    with psycopg.connect(f"dbname=schooner").cursor() as cursor:
        gas = GitAssignment(cursor, 'DTEK0068-3002', 'E01')
        print(gas.course['github_account'])


# EOF