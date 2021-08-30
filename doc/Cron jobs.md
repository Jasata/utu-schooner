# Cron Jobs

Current plan is to run all background tasks as local user `schooner` and use local IDENT authentication when accessing the database.

## Assuming schooner identity

- Gain super user privileges with `ksu`.
- Switch to `schooner`: `su - schooner`.

## Edit crontab

As local user: `crontab -e`  
As root: `crontab -e -u schooner`

- Add line: `MAILTO="dtek0068@utu.fi"`  
  _...or otherwise all cron messages are sent to schooner@utu.fi, which does not exist._
- Add the jobs
  - `mailbot.py` every 5 minutes
  - `hubreg.py` every minute
  - `hubbot.py` at 00:05 daily _(allow five minutes just in case system clocks are not super accurate)._

```crontab
* * * * * /var/www/schooner.utu.fi/cron.job/mailbot.py 2>&1
* * * * * /var/www/schooner.utu.fi/cron.job/hubreg.py 2>&1
5 0 * * * /var/www/schooner.utu.fi/cron.job/hubbot.py 2>&1
```  


## Importing local package from Cron job

Basically, it is as simple as adding a search path, but getting it **reliably** from the executing script file is little messy:
```python
# Add parent directory to the search path
# But not as the zero index... because it could be important for 3rd party
# code that may rely on sys.path documentation conformance:
#
#       As initialized upon program startup, the first item of this list,
#       path[0], is the directory containing the script that was used to
#       invoke the Python interpreter.
#
sys.path.insert(
    1,
    os.path.normpath(
        os.path.join(
            os.path.dirname(
                os.path.realpath(
                    os.path.join(
                        os.getcwd(),
                        os.path.expanduser(__file__)
                    )
                )
            ),
            ".." # Parent directory (relative to this script)
        )
    )
)
```
The above example works for `{web-root}/cron.job/*` scripts, allowing them to import from `{web-root}/schooner` package:
```
from schooner.util import AppConfig
```

Good reading on imports: [Chris Yeh's Guide to Python import Statements](https://chrisyeh96.github.io/2017/08/08/definitive-guide-python-imports.html#basics-of-the-python-import-and-syspath)

