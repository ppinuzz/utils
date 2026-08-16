# Collection of user-defined utilities

Collection of various CLI utilities I've created over the years


## List of utilities

Each utility can be run with
```bash
python <utility-name>.py
```
and has a manpage accessible with the `-h` or `--help` flag.


| Utility          | Purpose                                                                                 |
|------------------|-----------------------------------------------------------------------------------------|
| `cleanbib`       | Clean BibTeX files, removing double braces `{{ }}` in titles  	                         |
| `downdiary`      | Download diary notes from Google Keep and save them as one or more Markdown/LaTeX files |


## TO DOs

- `downdiary`
	- Fix problem when multiple Greek letters are in sequence (e.g. `Δβ`)
	- Fix bullet points