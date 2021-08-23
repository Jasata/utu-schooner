# Schooner Database

PK/FK types and values have been designed with readability in mind. Normally, all key values would be integers and entirely separate from data (for obvious reasons), but this implementation has no development budget and will thus only receive the basic student and course assistant interfaces. All admin work will be done by using a DB browser and/or by issuing manual DML SQL sentences, and they will directly benefit from these choices.

## Schema Modules

Structure for database (`schooner`) has been split into three parts for easier management of development:

- Core structure, containing course instance data (grading system, assignments) and enrollee data (limited personal details and submissions to assignments).
- Assistant module, consisting of structures to manage evaluation work queues.
- Rule and Conditions. Yet-to-be started portion, which will model conditions that can prevent progressing in the course until certain tasks or score criteria have been satisfied.

## Roles

Current implementation uses only `schooner` role.

## Unsigned Integers

PostgreSQL has none. Use of `DOMAIN` is suggested:
```sql
CREATE DOMAIN uint AS INT4
   CONSTRAINT uint_not_negative_chk
   CHECK (VALUE IS NULL OR VALUE >= 0);
```
But that doesn't seem to work as adverticed:
```sql
SELECT (-1::uint);
 ?column? 
----------
       -1
(1 row)
```
**Our solution:** We will use table constraints to enforce intended value ranges.

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


## Rules and Conditions Module
TODO:
1) Exam privilege tracking (should be based on rules/conditions)
2) Rules and conditions.  
   Example rule 1: "exam privilege"  
   T01 OK, score >= 355  
   Example rule 2: "pass course"  
   T02 OK, X00 OK, SUM(E01...E06) > 250, SUM(Q01...Q07) > 100, course score >= 600
