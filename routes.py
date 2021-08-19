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
#   2021-08-17  Modified for Schooner
#
#
#   This Python module only defines the routes, which the application.py
#   includes directly into itself.
#   Most of actual work is implemented in the API modules.
#
import os
import sys
import time
import json
import flask
import logging

# These are the only four items so common that they can be referred without
# the 'flask.' prefix, and reader still knows what they are.
from flask          import request
from flask          import Response
from flask          import g
from flask          import session

from application    import app, sso

# ApiException classes, data classes
import api

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
@app.route('/register.html', methods=['GET'])
def register_get():
    """Render page to enter GitHub account."""
    parameters = {
        'course_id' : request.args.get('cid'),
        'title'     : 'Register GitHub Account',
        'uid'       : sso.uid,
        'assignment': ''
    }

    if not parameters['uid']:
        return flask.render_template(
            'please_login.jinja',
            **parameters
        )
    elif not parameters['course_id']:
        gitcourses = api.Enrollee.gitcourseids(parameters['uid'])
        app.logger.debug(f"Git Courses: {str(gitcourses)}")
        return flask.render_template(
            'choose_course.jinja',
            courselist = gitcourses,
            **parameters
        )
    else:
        # Render edit/enter view
        return flask.render_template(
            'register.jinja',
            enrollee = api.Enrollee(parameters['course_id'], parameters['uid']),
            course = api.Course(parameters['course_id']),
            **parameters
        )


@app.route('/register.html', methods=['POST'])
def register_post():
    """Accept GitHub account registration."""
    try:
        course = api.GitHubAccountRegistration(
            flask.request.form['cid'],
            sso.uid
        )
        app.logger.info(
            f"Course ('{course.course_id}') is on-going: {str(course.is_ongoing)}")
    except Exception as e:
        # TODO: Log exception somewhere we can SEE it!
        app.logger.exception(f"Unable to handle GitHub registration! {str(e)}")
        return flask.render_template('server_error.jinja')



@app.route('/assistant/list.html', methods=['GET'])
def assistant_list_get():
    """List """
    # 1) Check authenticated session (sso.is_authenticated)
    # 2) Check is assistant (list of course_id's)
    # 3) Present list of queued submissions



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
    log_request(request)
    return flask.send_from_directory('html', path)



# EOF