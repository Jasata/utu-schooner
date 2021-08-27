__all__ = [
    "Course",
    "Enrollee",
    "Assignment",
    "Submission",
    "PendingGitHubRegistrations",
    "github_register"
]
# Table data-dictionaries
from .Course        import Course
from .Enrollee      import Enrollee
from .Assignment    import Assignment
from .Submission    import Submission

# Result set dictionaries
from .PendingGitHubRegistrations    import PendingGitHubRegistrations

# Functions
from .github_register               import github_register

