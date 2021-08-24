# Schooner - Simple Course Management System

PK/FK types and values have been designed with readability in mind. Normally, all key values would be integers and entirely separate from data (for obvious reasons), but this implementation has no development budget and will thus only receive the basic student and course assistant interfaces. All admin work will be done by using a DB browser and/or by issuing manual DML SQL sentences, and they will directly benefit from these choices.

## Course Data

In addition to the obvious course attributes:
- **Email address**. Generally an RT queue where the course instructor and assistants can reply to student requests. This email is also used as a _sender_ for all the automated Schooner messages.
- **GitHub account**. Each course has its own GitHub account to which students send the collaboration invitations and which is used by the HUBBOT to retrieve execises.
- **GitHub access token**. Generated with the GitHub UI for allowing the cron jobs to access data / invitations under the GitHub account.

## Submission State

Design currently recognizes three (3) states:
1. `draft` which means that the evaluation is pending.  
   This mode is also used for various other things, such as:
   - Accepting the GitHub account name from the enrollee as a `draft` and once HUBREG background task has matched the given account name an bending collaborate invitation, will the submission be set as `accepted`.
   - Background task HUBBOT creates a `draft` submission when it detects the require content in enrollee's repository. These `draft` submissions are then picked up by course assistants for evaluation and grading. Once an assistant submits his feedback and points, the submission is set as `accepted`.
2. `accepted` submissions must have `.evaluator` (UID) and `.score` information. These are considered completed and should never be modified.
3. `rejected` submissions are such that for some reason cannot be evaluated / accepted. As of now (2021-08-21), there are no clearly defined uses yet.

## Submission retries

```sql
CREATE TABLE assignment
(
   retries        INTEGER     NULL DEFAULT 0,
   CONSTRAINT assignment_retries_chk
      CHECK (retries IS NULL OR retries >= 0)
);
```
**Meaning:**
- `NULL` signifies unlimited number of retries.
- `0` means that there are no retries.
- Other positive values indicate the number of allowed retries.

This will be enforced by `public.submission BEFORE INSERT` trigger.
- Assignment PK (`assignment_id`, `course_id`) paired with Enrollee PK (`course_id`, `uid`) is considered as identifying tuple.
- Trigger queries the number of submissions (`COUNT(submission_d)`) and number of `submission.state = 'draft'` submissions for the identifying tuple.
- Trigger queries `public.assignment.retries` value, and if not `NULL`...
   - If the `COUNT(submission_id)` is > `public.assignment.retries`, exception is raised (and the INSERT is rolled back).
- Trigger checks if there are `draft` submissions. If so, an exception raised - each submission must be completed before next can be entered.

## GitHub Account Registration

...uses submissions.

1. Student uses the web UI to create a `draft` submission containing his/her GitHub account name.
2. Cron job HUBREG executes on set intervals and scans for `draft` submissions for assignments that have _handler_ set as "HUBREG".
3. If a pending collaborator invitation is found for the pending (`draft`) registration submission, HUBREG executes `core.register_github` procedure which accepts the submission and updates enrollee account name and repository name fields.

- Student can modify the `draft` submission.  
  (_To fix a typo, for example._)
- If GitHub account has already been registered, and there is no `draft` submission pending, student can still create a new.  
  (_If the student has lost access to one account or has deleted and recreated the repository, for example. New collaborator invitation is still needed, obviously._)

## Rules and Conditions Module
TODO:
1) Exam privilege tracking (should be based on rules/conditions)
2) Rules and conditions.  
   Example rule 1: "exam privilege"  
   T01 OK, score >= 355  
   Example rule 2: "pass course"  
   T02 OK, X00 OK, SUM(E01...E06) > 250, SUM(Q01...Q07) > 100, course score >= 600
