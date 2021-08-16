# Schooner Database

PK/FK types and values have been designed with readability in mind. Normally, all key values would be integers and entirely separate from data (for obvious reasons), but this implementation has no development budget and will thus only receive the basic student and course assistant interfaces. All admin work will be done by using a DB browser and/or by issuing manual DML SQL sentences, and they will directly benefit from these choices.

## Schema Modules

Structure for database (`schooner`) has been split into three parts for easier management of development:

- Core structure, containing course instance data (grading system, assignments) and enrollee data (limited personal details and submissions to assignments).
- Assistant module, consisting of structures to manage evaluation work queues.
- Rule and Conditions. Yet-to-be started portion, which will model conditions that can prevent progressing in the course until certain tasks or score criteria have been satisfied.

## Roles

Current implementation uses only `schooner` role.

## Rules and Conditions Module
TODO:
1) Exam privilege tracking (should be based on rules/conditions)
2) Rules and conditions.  
   Example rule 1: "exam privilege"  
   T01 OK, score >= 355  
   Example rule 2: "pass course"  
   T02 OK, X00 OK, SUM(E01...E06) > 250, SUM(Q01...Q07) > 100, course score >= 600
