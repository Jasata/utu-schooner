#!/usr/bin/env python3
#
#
import os
from http.server    import HTTPServer, BaseHTTPRequestHandler
import urllib
from urllib.parse   import urlparse, parse_qs
import shutil
import json

PORT            = 8080
LOCALTMP        = "/tmp/"
SRVURI          = "https://schooner.utu.fi/exercise"
MPLABXPROJDIR   = "/home/aplus/MPLABXProject"

HTML_TOKEN_MISSING = """
<!DOCTYPE html>
<html>
  <head>
    <title>Missing Access Token</title>
  </head>
  <body>
    <h1>Request did not specify access token!</h1>
    <p>
    Service cannot complete the requested action because without the access token.
    </p>
  </body>
</html>
"""

def report() -> str:
    return """<!DOCTYPE html>
<html>
  <head>
    <title>Nothing to report!</title>
  </head>
  <body>
    <h1>Nothing to report</h1>
  </body>
</html>
    """




def fetch(token: str) -> str:
    import gzip
    import tarfile
    import cgi
    import urllib.request
    url = f"{SRVURI}?token={token}"
    # Retrieve exercise using the token
    with urllib.request.urlopen(url) as response:
        _, params = cgi.parse_header(response.headers.get('Content-Disposition', ''))
        localfile = '/tmp/' + params['filename']
        #submission_id = response.headers.get('X-SubmissionID', '(not specified)')
        redirect_url = response.headers.get('X-Redirect', 'https://schooner.utu.fi')
        print("=" * 80)
        print("params", str(params), "localfile", localfile)
        # Delete localfile, if exists
        try:
            os.ulink(localfile)
        except:
            pass
        # Uncompress response into (temporary) localfile
        with    gzip.GzipFile(fileobj=response) as uncompressed, \
                open(localfile, 'wb') as tar_file:
            tar_file.write(uncompressed.read())
    # Extract tar archive into the project directory
    with tarfile.open(localfile) as tar:
        tar.extractall(MPLABXPROJDIR)
    os.remove(localfile)
    return redirect_url





class FetchHandler(BaseHTTPRequestHandler):


    def _send_html(self, payload: str):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(payload.encode('UTF-8'))


    def _send_json(self, payload: dict):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('UTF-8'))


    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()


    def do_GET(self):
        # Valid URL *can* have more than one '?'
        print("self.path =", self.path)
        if self.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        path, qstr = tuple(self.path.split("?", 1))
        # Dict where values are lists (even if with only one value)
        params = parse_qs(qstr)

        if path == "/fetch":
            if 'token' not in params:
                self._send_html(
                    HTML_TOKEN_MISSING
                )
            else:
                try:
                    redirect_url = fetch(params['token'][0])
                except Exception as e:
                    url = f"{SRVURI}?token={params['token'][0]}"
                    self._send_html(
                        f"""
                        <html>
                        <body>
                        <b>Process of downloading and extracting the exercises was not successful!</b><br>
                        Please download the exercise manuall from <a href="{url}">{url}</a> and extract
                        it to '{MPLABXPROJDIR}'<br>
                        <br>
                        Exception:<br>
                        {str(e)}
                        """
                    )
                else:
                    # Redirect back to schooner
                    self.send_response(302)
                    self.send_header(
                        'Location',
                        redirect_url
                    )
                    self.end_headers()

                finally:
                    return

        elif path == "/report":
            self._send_html(
                report()
            )
        else:
            # Complaint response
            self.send_response(405)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"405 Method Not Allowed")

        return




if __name__ == "__main__":

    httpd = HTTPServer(('', PORT), FetchHandler)
    print("Serving on port {}".format(PORT))
    httpd.serve_forever()


# EOF