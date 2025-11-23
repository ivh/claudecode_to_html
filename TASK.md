# main goal

a script, python or other, that takes session logs from Claude Code (CC) and converts them into HTML.

## example data

* a06171f9-5f33-4258-84e1-4dc70e84c6dd.jsonl an example session log. all input files will have this format.
* Screenshot* two example screenshhots of how it looks on CC web.
* CCweb_example.html and CCweb_example_files/ , the saved web page of CC that should contain useful routines to render the session. Ignore the left half of the page and session management, only the session part itself is needed.

## requirements

* the output should be a single html-file, named like the input but ending .jsonl exchanged to .html
* all javascript should be inlined.
* the script does not need to be self-contained, can e.g. read js files or templates to make the output.
* the html should look similar to the screenshots, i.e. compact with unnecessary information skipped, file reads hiden, and long diffs shortened but expandable.
