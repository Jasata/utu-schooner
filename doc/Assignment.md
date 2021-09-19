# Assignment

A course can have zero to N assignments. Assignments come in types (2021, in `core.handler`):

1. `NULL` (undefined handler/type) are "manual" that require teacher input.
2. `HUBREG` assignments are handled by background process (`hubreg.py`).
3. `HUBBOT` are exercises returned via a Git repository (2021, GitHub).
4. `APLUS` assignments are external APlus exercises/quizzes (2021, not implemented).
5. `ASSETMGR` are for book-keeping equipment loan.

## Assignment Attributes

- `course_id`, `assignment_id` pair is a primary key which also links the assignment to a course.
- `name` (`VARCHAR(64)`) Short (up to 64 characters) name of the assignment.
- `description` (`TEXT`) Free-form text description of the assignment. Both `name`and `description` are inteded for student consumption and hold no functional role.
- `handler` (`VARCHAR(8)`) (to-be renamed as `type` in 2022). Types are listed above.
- `directives` (`TEXT`) is a JSON field that contains `type` specific instructions for the type-specific handlers. These are described in-depth below. **Directives field contains data/parameters/commands that are distinct for the assignment type and thus not shared among all assignments.**
- `points` (`INTEGER`) (to-be renamed as `max_score` in 2022) specified the maximum points that a submission for this assignment can be awarded.
- `pass` (`INTEGER`) (to-be renamed as `passing_score` in 2022) sets the required score for a submission to pass this assignment. It may be `NULL` to indicate that this assignment is optional (does not need to have a submission). Alternatively, it can have a value of zero (`0`) which is interpreted as a mandatory assignment (must have a submission), but has no score requirement.
- `retries` (`INTEGER`) indicates how many retries are allowed for the assignment. `NULL` value means unlimited submissions are allowed. Zero value (`0`) allows no retries (only one submission can be created). For example, `retries` value 2 allows two retries, thus the assignment can have up to three (3) submissions (the first submission + 2 retries).
- `opens` (`TIMESTAMP`) sets the date (and time) when the assignment opens for submissions. `NULL` value is allowed and then the course's open date is used instead.
- `deadline` (`DATE`) is the final date when submissions are accepted (for non-penalized score). `NULL` value is substituted with course's `closes`. If both are `NULL`, assignment is open for submissions indefinitely. If `deadline` is `2021-09-11`, all submissions until `2021-09-11 23:59:59` are accepted.
- `latepenalty` (`DECIMAL(3,3)`) Percentage, penalty per late day. Value `0.25` means that for each day after the `deadline` that amount will be deducted from the submission score. For example, if `deadline` is set as `2021-09-11` and `latepenalty` as `0.25` and the submission date is two days late (`2021-09-14`), submission score will be penalized 75%.
- `evaluation` (["`best`", "`first`", "`last`", "`worst`"]) Dictates which of the submissions are calculated into the course total.

**Notes:**
1. `latepenalty` cannot have a value unless `deadline` has been set.
2. `pass` must be `NULL` or at most as large as `points`.

# Types and Directives

## HUBBOT

Submissions of this type have four phases:

1. Fetch
2. Prune
3. Test
4. Evaluate

Each have a key in the directive JSON:
```JSON
{
    "fetch" : {
        "trigger" : [null | {file}],
        "notify-on-fail"  : true,
        "notify-on-success" : true
    },
    "prune" : {
        "type" : "whitelist",
        "list" : [{file}, ...]
    },
    "test" : {
        "TBD" : null
    },
    "evaluate" : {
        "TBD" : null
    }
}
```

_Phases / keys `test` and `evaluate` are left unspecified until they can have some kind of an implementation._

### The FILE object

Object / dictionary with only four attribues:
```JSON
{
    "type"      : "file" | "dir" | "any",
    "path"      : "/path/",
    "pattern"   : "Unix filename pattern"
}
```

Unix filename patterns are well known, very easy and have only four (4) special patterns:

| Pattern  | Meaning                                  |
|----------|------------------------------------------|
| `*`      | Matches everything                       |
| `?`      | Matches a single character               |
| `[seq]`  | Matches any character in `seq`           |
| `[!seq]` | Matches any character not in `seq`       |

To match meta characters (`*` or `?`), wrap them in brackets. For example:

- `"[?]"` matches `"?"`
- `([*])` matches `(*)` and so on...

**IMPORTANT: All matches are case insensitive!** This choice has been made because MacOS and Windows are case insensitive, and students using them can run into all kinds of trouble if triggering is case sensitive.

### Fetch Phase

Once the HUBBOT has determined that a fetch attempt can be made _(assignment is open for submissions, student has not exceeded retry count, there is no `draft` currently)_, a sub process is started.

1. Repository is queried to check that it exists and is accessible.
2. If `directives` JSON has ['fetch']['trigger'], and it is not `null`, it must be a file -object. If defined, repository is queried for contents and it is checked for a matching file. If found, cloning is "triggered".
3. If trigger is **not defined**, triggering file -object is generated from the `assignment_id`. For example, assignment `E01` would have trigger:
```JSON
{
    "type"      : "any",
    "path"      : "/",
    "pattern"   : "E01*"
}
```

