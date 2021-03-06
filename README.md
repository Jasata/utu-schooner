# Schooner - Simple Course Management System

Simple enrollment roster that manages deadlines, tasks, and scoring.

## Dependencies

Current version of `setup.py` is NON-FUNCTIONAL and needs to be re-written!

- PostgreSQL (tested with version 11)
- Psycopg3 (PostgreSQL connector, pre-release version dev2)

## Design Goals

 - **Simplicity and minimal effort** (in implementation, site structure, usage...). And where not achievable, good and clear documentation.
 - Minimal dependencies.
 - **Two-step principle**. All actions (primary use cases) should be accomplished in no more than two clicks. One to choose the relevant subpage, another to open a folding information container (if necessary).
 - **Integration-friendly Architecture**. Basically meaning that the backend is a REST API and none of the client pages are dynamically parsed.


## Functional Specifications (project goals)

Parenthesis document status for RC1 (version 0.4.0)

- UTU SSO authentication. (**OK**)
- Student can register GitHub account name. (**OK**)
- Student can view course progress and score. (NOK)
- Model course curriculum in "requirements". (Mostly OK, as _Assignments_)
- Exam privilege tracking (when earned, date and time recorded). (NOK)
- Free-form text for each student-course-year allowing special considerations. (NOK)
- Can import ViLLE/A+ quizz scores. (NOK)
- Can import exam.utu.fi exports. (NOK)
- MS Teams integration, automatic course group addition, messages, etc. (NOK)
- Asset (component kit) management (**OK**)
- Automated notifications and per-student notification settings (very basic)
- Assistant workqueue system (**OK**)
- Assistant Virtual Machine / submission evaluation transfers (**OK**)
- Student score calculator and grader (NOK)

## GDPR

Database stores personal information and GDPR policy compliance document will be created, outlining responsible persons and practises, as required by the directive.

## Third-party components

Frontend
 - [Bootstrap 4.3.1](https://getbootstrap.com/docs/4.3/getting-started/introduction/)
 - [JQuery 3.4.1](https://jquery.com/download/)
 - [Font Awesome 4.7.0](https://fontawesome.com/v4.7.0/) (because that is the last free version)
 - [Datatables 1.10.20](https://datatables.net/) for download page tables
 - [CardTabs 1.0](https://github.com/blekerfeld/CardTabs) for tabulated content
 - [JSONForm](https://github.com/jsonform/jsonform) for VM details edit
 
Backend
- Nginx ver.1.14.0+
- Python 3.6.8+ (Ubuntu Server 18.04.3 LTS, offered by IT-Services)
- Flask 1.1.1+ (2021-08-16, version: 2.0.1 is the newest)
- UWSGI 2.0.15+
- PostgreSQL 11.12+
- Psycopg3 dev2 (will be updated to release version, when it is released)
