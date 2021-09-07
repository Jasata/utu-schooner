#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
#
# routes.py - Flask Application routes
#   2019-12-07  Initial version
#   2019-12-23  Add /sso endpoints
#   2019-12-25  Add /api/publish endpoint
#   2020-09-07  Add /api/file/upload
#   2020-09-09  Add /api/file/flow  (Flow.js GET, POST upload endpoint)
#   2020-09-12  Add /sse/flow-upload-status
#   2020-09-23  Clean obsolete code
#   2021-08-17  Modified for Schooner / PostgreSQL
#   2021-08-23  Added /register.html handler
#
#
#   This Python module only defines the routes, which the application.py
#   includes directly into itself.
#   Most of actual work is implemented in the API modules.
#
import os
from schooner.db.assistant.Evaluation import Evaluation
from schooner.db import assistant
import sys
import time
import json
import flask
import logging
import datetime

# These are the only four items so common that they can be referred without
# the 'flask.' prefix, and reader still knows what they are.
from flask          import request
from flask          import Response
from flask          import g
from flask          import session

from application    import app, sso

# ApiException classes, data classes
import api

from schooner.db.core       import Course
from schooner.db.core       import CourseList
from schooner.db.core       import Assignment
from schooner.ui.teacher    import Assets

# Pylint doesn't understand app.logger ...so we disable all these warnings
# pylint: disable=maybe-no-member


#
# Debug log-function
#       Store HTTP request path and the rule that triggered.
#
def log_request(request):
    app.logger.debug(
        f"Debug={str(app.debug)}, Auth={str(sso.is_authenticated)} :: {request.method} '{request.path}' (rule: '{request.url_rule.rule}')"
    )


###############################################################################
#
# REST API ENDPOINTS (routes)
#
###############################################################################


###############################################################################
#
# SSO API endpoints for Single Sign-On implementation
#
@app.route('/api/sso', methods=['GET'], strict_slashes = False)
def sso_state():
    """Returns a sigle item JSON: { "role": "[anonymous|student|teacher]" }. This also implicitly indicates the authentication state (anonymous = not authenticated)."""
    app.logger.debug(
        f"SSO STATE QUERY: session.UID = {session.get('UID', '(does not exist)')}, session.ROLE = {session.get('ROLE', 'does not exist')}' sso.roleJSON = {sso.roleJSON}"
    )
    return sso.roleJSON, 200


@app.route('/api/sso/login', methods=['GET'], strict_slashes = False)
def sso_login():
    """This is the landing URI from SSO login page. SSO REST API is re-queried and session is updated accordingly. Finally, 'destination' URL parameter is used to redirect the broser to the final location - persumably the page from where the "login" link/button was pressed."""
    sso.login(force = True)
    destination = request.args.get(
        'destination',
        default = '/index.html',
        type = str
    )
    return flask.redirect(destination, code = 302)


@app.route('/api/sso/logout', methods=['GET'], strict_slashes = False)
def sso_logout():
    """This endpoint sets UID to None and ROLE to 'anonymous' in the session, thus effectively logging the user out."""
    app.logger.debug(
        f"BEFORE sso.logout(): session.UID = {session.get('UID', '(does not exist)')}, session.ROLE = {session.get('ROLE', 'does not exist')}"
    )
    sso.logout()
    app.logger.debug(
        f"AFTER sso.logout(): session.UID = {session.get('UID', '(does not exist)')}, session.ROLE = {session.get('ROLE', 'does not exist')}"
    )
    return "OK", 200


###############################################################################
#
# Catch-all for non-existent API requests
#
@app.route('/api', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])
@app.route('/api/', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])
def api_not_implemented(path = ''):
    """Catch-all route for '/api*' access attempts that do not match any defined routes.
    "405 Method Not Allowed" JSON reply is returned."""
    log_request(request)
    try:
        raise api.MethodNotAllowed(
            "Requested API endpoint ('{}') does not exist!"
            .format("/api/" + path)
        )
    except Exception as e:
        return api.exception_response(e)



###############################################################################
#
# /sys
# System / development URIs
#
#       These routes are to be grouped under '/sys' path, with the notable
#       exception of '/api.html', because that serves the API listing as HTML
#       and because the API documentation is very central to this particular
#       solution.
#
#

#
# Flask Application Configuration
#
@app.route('/sys/cfg', methods=['GET'])
def show_flask_config():
    """Middleware (Flask application) configuration. Sensitive entries are
    censored."""
    # Allow output only when debugging AND when the user is authenticated
    if not sso.is_authenticated or not app.debug:
        return api.response((404, {'error': 'Permission Denied'}))
    log_request(request)
    try:
        cfg = {}
        for key in app.config:
            cfg[key] = app.config[key]
        # Censor sensitive values
        for key in cfg:
            if key in ('SECRET_KEY', 'MYSQL_DATABASE_PASSWORD'):
                cfg[key] = '<CENSORED>'
        return api.response((200, cfg))
    except Exception as e:
        return api.exception_response(e)



#
# API listing
#
#       Serves two routes: '/sys/api' and 'api.html'. First returns the listing
#       in JSON format and the second serves a HTML table of the same data.
#
#   NOTES:
#           - Built-in route '/static' is ignored.
#           - Implicit methods 'HEAD' and 'OPTIONS' are hidden.
#             That's not the correct way about doing this, but since this
#             implementation does not use either of them, we can skip this
#             issue and just hide them.
#
#   See also:
#   https://stackoverflow.com/questions/13317536/get-a-list-of-all-routes-defined-in-the-app
#
@app.route('/api.html', methods=['GET'])
@app.route('/sys/api', methods=['GET'])
def api_doc():
    """JSON API Documentation.
    Generates API document from the available endpoints. This functionality
    relies on PEP 257 (https://www.python.org/dev/peps/pep-0257/) convention
    for docstrings and Flask micro framework route ('rule') mapping to
    generate basic information listing on all the available REST API functions.
    This call takes no arguments.
    
    GET /sys/api
    
    List of API endpoints is returned in JSON.
    
    GET /api.html
    
    The README.md from /api is prefixed to HTML content. List of API endpoints
    is included as a table."""
    def htmldoc(docstring):
        """Some HTML formatting for docstrings."""
        result = None
        if docstring:
            docstring = docstring.replace('<', '&lt;').replace('>', '&gt;')
            result = "<br/>".join(docstring.split('\n')) + "<br/>"
        return result
    try:
        log_request(request)
        eplist = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                allowed = [method for method in rule.methods if method not in ('HEAD', 'OPTIONS')]
                methods = ','.join(allowed)

                eplist.append({
                    'service'   : rule.endpoint,
                    'methods'   : methods,
                    'endpoint'  : str(rule),
                    'doc'       : app.view_functions[rule.endpoint].__doc__
                })


        #
        # Sort eplist based on 'endpoint'
        #
        eplist = sorted(eplist, key=lambda k: k['endpoint'])


        if 'api.html' in request.url_rule.rule:
            try:
                from ext.markdown2 import markdown
                with open('api/README.md') as f:
                    readme = markdown(f.read(), extras=["tables"])
            except:
                app.logger.exception("Unable to process 'api/README.md'")
                readme = ''
            html =  "<!DOCTYPE html><html><head><title>API Listing</title>"
            html += "<link rel='stylesheet' href='/css/api.css'>"
            # substitute for favicon
            html += "<link rel='icon' href='data:;base64,iVBORw0KGgo='>"
            html += "</head><body>"
            html += readme
            html += "<h2>List of Flask routes and Endpoints</h2>"
            html += "<table class='endpointTable'><tr><th>Service</th><th>Methods</th><th>Endpoint</th><th>Documentation</th></tr>"
            for row in eplist:
                html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>" \
                        .format(
                            row['service'],
                            row['methods'],
                            row['endpoint'].replace('<', '&lt;').replace('>', '&gt;'),
                            htmldoc(row['doc'])
                        )
            html += "</table></body></html>"
            # Create Request object
            response = app.response_class(
                response    = html,
                status      = 200,
                mimetype    = 'text/html'
            )
            return response
        else:
            return api.response((200, {'endpoints': eplist}))
    except Exception as e:
        return api.exception_response(e)



###############################################################################
#
# Dynamic pages
#
@app.route('/material_loan.html', methods=['GET'])
def material_loan_get():
    if not sso.is_admin:
        return flask.render_template(
            "internal_error.jinja",
            title = "Permission Denied",
            message = "Admin privileges are required to access this page."
        )
    
    args = {
        'course_id'     : request.args.get('cid'),
        'assignment_id' : request.args.get('aid'),
        'title'         : 'Teaching Material Loan',
        'uid'           : sso.uid
    }
    try:
        if not args['uid']:
            return flask.render_template(
                'please_login.jinja',
                **args
            )
        elif not args['course_id'] or not args['assignment_id']:
            # Choose assignment to work with
            assignments = Assets.assignments(
                g.db.cursor(),
                active_courses = True
            )
            app.logger.debug(
                f"Number of asset assignments: {len(assignments)}"
            )
            return flask.render_template(
                'choose_assignment.jinja',
                assignments = assignments,
                **args
            )
        else:
            # Render edit/enter view
            return flask.render_template(
                'material_loan.jinja',
                course = Course(
                    g.db.cursor(),
                    course_id = args['course_id']
                ),
                assignment = Assignment(
                    g.db.cursor(),
                    course_id = args['course_id'],
                    assignment_id = args['assignment_id']
                ),
                loans = Assets(
                    g.db.cursor(),
                    args['course_id'],
                    args['assignment_id']
                ).sort('lastname'),
                **args
            )


    except Exception as e:
        app.logger.exception(str(e))
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )



@app.route('/material_return.html', methods=['POST'])
def material_return_post():
    # Expects:
    #       form['cid']             submission.course_id
    #       form['aid']             submission.assignment_id
    #       form['uid']             submission.uid
    requiredkeys = ["cid", "aid", "uid"]
    try:
        # Require authenticated session
        if not sso.is_admin:
            raise Exception(
                f"Session must be authenticated to an admin account!"
            )
        # process FORM data
        issues = []
        data = request.form.to_dict(flat = True)
        for key in requiredkeys:
            if key not in data:
                issues.append(
                    f"Form does not contain key '{key}'"
                )
        if issues:
            raise ValueError(
                f"Malformed POST data: {', '.join(issues)}: {str(data)}"
            )
    except Exception as e:
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )
    # Application logic
    try:
        #
        # Save submitted loan
        #
        app.logger.debug(str(data))
        with g.db.cursor() as cursor:
            # Returns created submission_id, but we ignore it
            Assets.receive_cua(
                cursor, data['cid'], data['aid'], data['uid']
            )
        return flask.redirect(
            f"/material_loan.html?cid={data['cid']}&aid={data['aid']}"
        )
    except Exception as e:
        app.logger.exception(f"Unable to handle material return registration! {str(e)}")
        return flask.render_template(
            'internal_error.jinja',
            title = "Material Return Registration Error",
            message = str(e)
        )



@app.route('/material_loan.html', methods=['POST'])
def material_loan_post():
    # Expects:
    #       form['cid']             submission.course_id
    #       form['aid']             submission.assignment_id
    #       form['uid']             submission.uid
    #       form['item_id']         submission.content
    requiredkeys = ["cid", "aid", "uid", "item_id"]
    try:
        # Require authenticated session
        if not sso.is_admin:
            raise ValueError(
                f"Session must be authenticated to an admin account!"
            )
        # process FORM data
        issues = []
        data = request.form.to_dict(flat = True)
        for key in requiredkeys:
            if key not in data:
                issues.append(
                    f"Form does not contain key '{key}'"
                )
        if issues:
            raise ValueError(
                f"Malformed POST data: {', '.join(issues)}: {str(data)}"
            )
        data['item_id'] = data['item_id'].strip()
        if len(data['item_id']) < 1:
            raise ValueError(
                f"Submitted item id cannot be empty!"
            )
    except Exception as e:
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )
    # Application logic
    try:
        #
        # Save submitted loan
        #
        app.logger.debug(str(data))
        with g.db.cursor() as cursor:
            # Returns created submission_id, but we ignore it
            id = Assets.loan(
                cursor, data['cid'], data['aid'], data['uid'], data['item_id']
            )
            app.logger.error(f"Created submission #{id}")
        return flask.redirect(
            f"/material_loan.html?cid={data['cid']}&aid={data['aid']}"
        )
    except Exception as e:
        # TODO: Log exception somewhere we can SEE it! Like... log -table?
        app.logger.exception(f"Unable to handle material loan registration! {str(e)}")
        return flask.render_template(
            'internal_error.jinja',
            title = "Material Loan Registration Error",
            message = str(e)
        )



@app.route('/register.html', methods=['GET'])
def register_get():
    """Render page to enter GitHub account."""
    parameters = {
        'course_id' : request.args.get('cid'),
        'title'     : 'GitHub Account Registration',
        'uid'       : sso.uid,
        'assignment': ''
    }

    try:
        if not parameters['uid']:
            return flask.render_template(
                'please_login.jinja',
                **parameters
            )
        elif not parameters['course_id']:
            gitcourses = CourseList(
                g.db.cursor(),
                handler = 'HUBREG',
                uid = sso.uid,
                ongoing = True
            )
            parameters['msg_emptylist'] = """
            You do not seem to be enrolled in any on-going courses that require GitHub registration. If this is an error, please email your course / instructor.
            """
            parameters['message'] = """
            You are currently enrolled in more than one on-going courses with GitHub registration. Please choose which course you want to register your account for.
            """
            return flask.render_template(
                'choose_course.jinja',
                courselist = gitcourses,
                **parameters
            )
        else:
            # Render edit/enter view
            from schooner.api import GitRegistration
            return flask.render_template(
                'register.jinja',
                registration =  GitRegistration(
                    g.db.cursor(),
                    parameters['course_id'],
                    parameters['uid']
                ),
                **parameters
            )
    except Exception as e:
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )



@app.route('/register.html', methods=['POST'])
def register_post():
    """Accept GitHub account registration. This interface operates on 'draft' submissions, either creating one or updating an existing 'draft', but NEVER changing the submission state - that is for the HUBREG to do when it matches the enrollee-submitted GitHub account name and a pending collaborator invitation."""
    import string
    # Expects:
    #       form['cid']             course.course_id
    #       form['account_name']    enrollee.github_account
    requiredkeys = ("cid", "account_name")
    # GitHub allowed characters. We'll use it also for the course_id...
    allowedchars = list(
        string.ascii_lowercase +
        string.ascii_uppercase +
        string.digits +
        '.-_'
    )
    try:
        # Require authenticated session
        if not sso.is_authenticated:
            raise ValueError(
                f"Session must be authenticated to submit! Please login."
            )
        # process FORM data
        issues = []
        data = request.form.to_dict(flat = True)
        for key in requiredkeys:
            if key not in data:
                issues.append(
                    f"Form does not contain key '{key}'"
                )
        if issues:
            raise ValueError(
                f"Malformed POST data: {', '.join(issues)}"
            )
        # Strip characters not in allowedchars
        for key in data.keys():
            data[key] = "".join(c for c in data[key] if c in allowedchars)
        if len(data['account_name']) < 1:
            raise ValueError(
                f"Submitted account name cannot be empty!"
            )
        # Add SSO ID
        data['uid'] = sso.uid
    except Exception as e:
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )
    # Application logic
    try:
        # Get schooner.api.GitRegistration(cursor, enrollee)
        from schooner.api import GitRegistration
        reg = GitRegistration(
            g.db.cursor(),
            data['cid'],
            data['uid']
        )
        # If registration is not open (assignment.deadline passed)
        if not reg['github_registration_open'] == 'y':
            return flask.render_template(
                "internal_error.jinja",
                title = "Account registration is no longer open",
                message = f"""GitHub account registration assignment deadline ('{reg['deadline']}') for course '{reg['cid']}' has closed and no new submissions can be accepted."""
            )
        #
        # Save submitted account name
        #
        reg.register_account(
            data['account_name']
        )
        return flask.redirect(f"/register.html?cid={data['cid']}")
    except Exception as e:
        app.logger.exception(f"Unable to handle GitHub account registration! {str(e)}")
        return flask.render_template(
            'internal_error.jinja',
            title = "Registration Error",
            message = str(e)
        )






@app.route('/notifications.html', methods=['GET'])
def notifications_get():
    """Enable / disable automated email notifications."""
    parameters = {
        'course_id' : request.args.get('cid'),
        'title'     : 'Enable or disable automated email notifications',
        'uid'       : sso.uid
    }

    try:
        if not parameters['uid']:
            return flask.render_template(
                'please_login.jinja',
                **parameters
            )
        elif not parameters['course_id']:
            mycourses = CourseList(
                g.db.cursor(),
                uid = parameters['uid'],
                ongoing = True
            )
            #app.logger.debug(f"My Courses: {str(mycourses)}")
            parameters['msg_emptylist'] = """
            You do not seem to be enrolled in any courses. If this is an error, please email your course / instructor.
            """
            parameters['message'] = """
            You are currently enrolled in more than one on-going course. Please choose which course you want to configure notification setting for.
            """
            return flask.render_template(
                'choose_course.jinja',
                courselist = mycourses,
                **parameters
            )
        else:
            #############################################################
            # Render edit/enter view
            from schooner.db.core import Course
            from schooner.db.core import Enrollee
            return flask.render_template(
                'notification.jinja',
                course = Course(
                    g.db.cursor(),
                    parameters['course_id']
                ),
                enrollee = Enrollee(
                    g.db.cursor(),
                    parameters['course_id'],
                    parameters['uid']
                ),
                **parameters
            )
            #############################################################
    except Exception as e:
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )




@app.route('/notifications.html', methods=['POST'])
def notifications_post():
    """Accept notifications configuration from user."""
    # Expects:
    #       form['cid']             enrollee.course_id
    #       form['uid']             enrollee.uid
    requiredkeys = ("cid", "uid")
    # GitHub allowed characters. We'll use it also for the course_id...
    try:
        # Require authenticated session
        if not sso.is_authenticated:
            raise ValueError(
                f"Session must be authenticated to submit! Please login."
            )
        # process FORM data
        issues = []
        data = request.form.to_dict(flat = True)
        data['notifications'] = data.get('notifications', 'disabled')
        if data['notifications'] != 'disabled':
            data['notifications'] = 'enabled'
        #app.logger.info(str(data))
        for key in requiredkeys:
            if key not in data:
                issues.append(
                    f"Form does not contain key '{key}'"
                )
        if issues:
            raise ValueError(
                f"Malformed POST data: {', '.join(issues)}"
            )

    except Exception as e:
        return flask.render_template(
            "internal_error.jinja",
            title = "Internal Error",
            message = str(e)
        )
    # Application logic
    try:
        from schooner.db.core import Enrollee
        enrollee = Enrollee(
            g.db.cursor(),
            data['cid'],
            data['uid']
        )
        enrollee['notifications'] = data['notifications']
        #
        # Save submitted notifications configuration
        #
        enrollee.db_update()
        return flask.redirect(f"/notifications.html?cid={data['cid']}")
    except Exception as e:
        # TODO: Log exception somewhere we can SEE it! Like... log -table?
        app.logger.exception(f"Unable to handle notifications configuration! {str(e)}")
        return flask.render_template(
            'internal_error.jinja',
            title = "Internal Error",
            message = str(e)
        )


###############################################################################
#
# COURSE ASSISTANT
#
#
@app.route("/assistant.html", methods=['GET'])
def assistant_get():
    """Basic assistant page. TBA."""
    from schooner.db.assistant import Assistant, AssistantList
    try:
        if not sso.is_authenticated:
            raise Exception("Must be authenticated to access this view")
        if not Assistant.is_assistant(g.db.cursor(), sso.uid):
            raise Exception("You are not registed as an assistant!")
        return flask.render_template(
            'assistant_index.jinja',
            title = "Assistant Information",
            assistant_name = Assistant.get_name(g.db.cursor(), sso.uid),
            courselist = AssistantList(g.db.cursor(), uid = sso.uid)
        )
    except Exception as e:
        app.logger.exception(str(e))
        return flask.render_template(
            'internal_error.jinja',
            title = "Internal Error",
            message = str(e)
        )



@app.route("/assistant_workqueue.html", methods=['GET'])
def assistant_workqueue_get():
    from schooner.db.assistant  import CourseAssistant
    from schooner.api           import AssistantWorkqueue
    try:
        if not sso.is_authenticated:
            raise Exception("Must be authenticated to access this view")
        data = request.args.to_dict(flat = True)
        if 'cid' not in data:
            raise ValueError("Request query parameter 'cid' not found!")
        return flask.render_template(
            'assistant_workqueue.jinja',
            title = "Assistant Workqueue",
            assistant = CourseAssistant(
                g.db.cursor(),
                data['cid'],
                sso.uid
            ),
            queue = AssistantWorkqueue(
                g.db.cursor(),
                sso.uid,
                course_id = data['cid']
            ).sort('submitted')
        )
    except Exception as e:
        app.logger.exception(str(e))
        return flask.render_template(
            'internal_error.jinja',
            title = "Internal Error",
            message = str(e)
        )




@app.route('/assistant_evaluation.html', methods=['GET'])
def assistant_evaluation():
    """Assistant work-view where comments and feedback is written."""
    # IMPORTANT This view requires the evaluation to have been started
    #           (assistant.evaluation record exists) BUT NOT FINISHED!
    #           (assistant.evaluation.ended must be NULL ...AND
    #           core.submission.state must be 'draft')
    #           Accessing user (sso.uid) must also be the assistant who's
    #           uid has been registed into the evaluation record so that
    #           assistants won't mess up each other's evaluations by
    #           accident (or some kind...?)
    from schooner.db.assistant  import CourseAssistant
    from schooner.api           import AssignmentSubmission
    try:
        if not sso.is_authenticated:
            raise Exception("Must be authenticated to access this view")
        if not (sid := request.args.get('sid', None)):
            raise ValueError("Request query parameter 'sid' not found!")
        assistant  = CourseAssistant.create_from_submission_id(
            g.db.cursor(),
            sid
        )
        # When assistant information is retrieved by using submission_id,
        # it might be someone else than the currently authenticated one.
        if assistant['uid'] != sso.uid:
            raise Exception(
                f"You are not the evaluator for submission #{sid}! '{assistant['uid']}' has taken it."
            )
        # Check that the submission is open
        submission = AssignmentSubmission(
            g.db.cursor(),
            sid
        )
        if not submission['evaluation_started']:
            # This should not be possible after CourseAssistant.create_from_submission_id()
            raise Exception(
                f"This submission (#{sid}) does not have evaluation record (evaluation has not yet been started)!"
            )
        if submission['state'] != 'draft':
            raise Exception(
                f"This submission (#{sid}) is not in 'draft' state, but in '{submission['state']}'! Only 'draft' submission may be evaluated."
            )
        #
        # All checks should be now done. Present the evaluation form for the assistant.
        #
        return flask.render_template(
            'assistant_evaluation.jinja',
            title = "Submission evaluation",
            message = "Not yet implemented",
            submission = submission
        )
    except Exception as e:
        app.logger.exception(str(e))
        return flask.render_template(
            'internal_error.jinja',
            title = "Internal Error",
            message = str(e)
        )




@app.route('/assistant_evaluation_begin.html', methods=['POST'])
def assistant_start_evaluation_get():
    from schooner.db.core       import Submission
    from schooner.db.assistant  import CourseAssistant
    from schooner.db.assistant  import Evaluation
    from schooner.api           import AssistantWorkqueue
    # Required POST parameter(s): sid (submission_id)
    try:
        if not sso.is_authenticated:
            raise Exception("Must be authenticated to access this view")
        if not (cid := request.form.get('cid', None)):
            raise ValueError("FORM parameter 'Cid' not found!")
        # Check that the caller is course assistant (raises an exception if not)
        ass = CourseAssistant(g.db.cursor(), cid, sso.uid)
        if ass['open_submission_id']:
            raise Exception(
                f"Already evaluating submission #{ass['open_submission_id']}. Complete that before starting another."
            )

        queue = AssistantWorkqueue(
                g.db.cursor(),
                sso.uid,
                course_id = cid
            ).sort('submitted')
        if not queue:
            raise Exception("No more pending evaluations!")

        #
        # Preliminaries done
        #
        # Create empty
        evaluation = Evaluation(g.db.cursor())
        evaluation['submission_id'] = queue[0]['submission_id']
        evaluation['uid'] = sso.uid
        # Begin evaluation
        token = evaluation.begin()

        # Go and initiate local transfer at Assistant vm
        return flask.redirect(f"http://localhost:8080/fetch?token={token}")

    except Exception as e:
        app.logger.exception(str(e))
        return flask.render_template(
            'internal_error.jinja',
            title = "Internal Error",
            message = str(e)
        )




@app.route('/assistant_evaluation_cancel.html', methods=['POST'])
def assistant_evaluation_cancel():
    from schooner.db.assistant import Evaluation
    # Required POST parameter(s): sid (submission_id)
    try:
        if not sso.is_authenticated:
            raise Exception("Must be authenticated to access this view")
        if not (sid := request.form.get('sid', None)):
            raise ValueError("Request query parameter 'sid' not found!")
        # The following will raise ValueError if uid and submission_id do not match
        try:
            task = Evaluation(g.db.cursor(), sid)
        except ValueError:
            raise Exception(f"You are not registered as an assistant for the course in which submission #{sid} belongs to!") from None
        if task['ended']:
            raise Exception(f"Evaluation of submission #{sid} has been completed and cannot be cancelled!")
        # Checks are done, cancel
        task.cancel()
        # Redirect to workqueue page
        return flask.redirect(f"/assistant_workqueue.html?cid={task['course_id']}")
    except Exception as e:
        app.logger.exception(str(e))
        return flask.render_template(
            'internal_error.jinja',
            title = "Internal Error",
            message = str(e)
        )




@app.route('/assistant_evaluation_reject.html', methods=['POST'])
def assistant_evaluation_reject():
    return flask.render_template(
        'internal_error.jinja',
        title = "Not yet implemented",
        message = "Not yet implemented"
    )




@app.route('/assistant_evaluation_accept.html', methods=['POST'])
def assistant_evaluation_accept():
    return flask.render_template(
        'internal_error.jinja',
        title = "Not yet implemented",
        message = "Not yet implemented"
    )




@app.route("/exercise", methods=['GET'])
def exercise_get():
    """Download exercise archive with a time-limited access token."""
    from schooner.api           import ExerciseArchive
    from schooner.db.assistant  import AccessToken
    # Until there is a way to transger SSO cookie from assistant's browser
    # to the schooner-local-daemon, we cannot require authenticated sessions.
    #if not sso.is_authenticated:
    #    return (405, "Permission Denied. You must be logged")
    try:
        if not (token := request.args.get('token')):
            raise AccessToken.InvalidAccessToken(
                "Access token required and cannot be empty!"
            )
        # Create archive of the exercise
        archive = ExerciseArchive(g.db.cursor(), token)
        tmpfile = archive.create()

        # As of August 2012, the MIME type recommended in RFC 6713
        # is 'application/gzip'
        return flask.send_file(
            tmpfile,
            as_attachment=True,
            mimetype='application/gzip'
        )
        #return (f"Access: {tmpfile}", 200)
    except KeyError as e:
        app.logger.exception(str(e))
        return ("URI parameter 'token' required!", 400)
    except ExerciseArchive.InvalidAccessToken as e:
        app.logger.exception(str(e))
        return (f"{str(e)}", 404)   # 404 Not Found
    except Exception as e:
        app.logger.exception(f"{str(e)}")
        return (f"Internal server error - see logs!\n{str(e)}", 500)


###############################################################################
#
# Static content
#
#   NOTE:   Nginx can be configured (see /etc/nginx/nginx.conf) to serve
#           files of certain suffixes (images, css, js) which are deemed to
#           be always static.
#
#           Nginx file suffix configuration would be a never ending chase after
#           new files suffixes. It's not worth it in this application -
#           performance is not a vital concern.
#
#   This is an alternative (albeit little less efficient) approach:
#
#           Certain routes are setup to contain only static files and
#           'send_from_directory()' is used to simply hand out the content.
#           The function is designed to solve a security problems where
#           an attacker would try to use this to dig up .py files.
#           It will raise an error if the path leads to outside of a
#           particular directory.
#

#
# Catch-all for other paths (UI HTML files)
#
@app.route('/<path:path>', methods=['GET'])
# No-path case
@app.route('/', methods=['GET'])
def send_ui(path = 'index.html'):
    """Send static content (HTML/CSS/JS/images/...)."""
    #log_request(request)
    return flask.send_from_directory('html', path)



# EOF