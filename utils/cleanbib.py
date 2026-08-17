#!/usr/bin/env python3
"""
CLI tool to clean Bibtex bibliography.

@author: Andrea Pinardi <andreapinardi319@gmail.com>
"""

from pathlib import Path
import argparse


#%% FUNCTIONS

def clean_bibfile(bib_file: Path | str, clean_bib_file: Path | str, verbose: bool = True) -> None:
    """
    Clean BibTeX .bib file, removing double braces in from title field.

    Parameters
    ----------
    bib_file : Path or str
        Bibliography file.
    clean_bib_file : Path or str
        Output file where "cleaned" bib file is written.
    verbose : bool, optional
        Whether to print user messages. The default is True.

    Raises
    ------
    FileNotFoundError
        If the .bib file doesn't exist.

    """
    
    bib_file = Path(bib_file)
    if not bib_file.exists():
        raise FileNotFoundError(f'{bib_file.resolve()} does not exist')
    
    _print_msg("Removing double braces {{ }} from 'title' field in " + f'{bib_file.resolve()}',
               verbose)
    clean_bib = []
    with open(bib_file, 'r') as file:
        for line in file:
            # if title = {{My Sentence Case Title}}, the double braces will protect
            # it from being normalised to "My sentence case title" when needed
            # => remove them
            if line.startswith('title = {{'):
                line = line.replace('{{', '{')
                line = line.replace('}}', '}')
            clean_bib.append(line)
    
    clean_bib_file = Path(clean_bib_file)
    _print_msg(f'Writing clean bibliography file to {clean_bib_file.resolve()}', verbose)
    with open(clean_bib_file, 'w') as file:
        file.writelines(clean_bib)



#%% COMMAND LINE INTERFACE

# parse_args() takes a list of arguments to parse and parses them into an 
# argparse.Namespace object whose attributes are accessible using dot notation 
# => you can pass the arguments
#   - either manually as a list of strings, e.g.
#       args = parser.parse_args(['myinputfile.txt', 'myoutput.txt'])
#   - or by reading them from sys.argv[1:] (ignoring 0th element, as that is
#   always the name of the command) => default option
# since the default option is used when argv=None in the call to parse_args(),
# by including argv=None in the argument list I can:
#   - use the CLI as a regular CLI when called from the terminal
#   - call the CLI from within a Python script by explicitly passing the 
#   list of input arguments I'd use if I called it from the terminal, e.g.
#       read_cli_args(['myinputfile.txt', 'myoutput.txt'])
def read_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Parameters
    ----------
    argv : list[str] or None, optional
        List of input arguments to parse. If None, they will be read from 
        ``sys.argv[1:]``. The default is None.

    Returns
    -------
    args : argparse.Namespace
        Namespace containing the parsed command-line arguments.

    """
    # create parser
    parser = argparse.ArgumentParser(
                prog='cleanbib',
                description='Clean BibTeX files, removing double braces',
                # %(prog)s is used to include the program's name
                epilog='This is %(prog)s, version 1.0.0',
                # force the user to enter the exact long option's name
                # (otherwise, --a, --arg, --arg-long-name will be equivalent)
                allow_abbrev=False)
    # add a positional argument ("argument") IN THE RIGHT ORDER
    parser.add_argument('bibfile', help='original BibTeX file')
    
    # add an optional argument ("option/switch/flag")
    # whose flag is -v or --verbose indifferently
    # whose action means "store a True if the option is given by the user, 
    # otherwise set to False" (i.e. False is the default)
    parser.add_argument('-v', '--verbose', action='store_true', help='print verbose output')
    
    # parse the arguments passed to the function
    # (either from the terminal or explicitly calling this CLI function from
    # within another program)
    args = parser.parse_args(argv)

    return args


#%% PRIVATE FUNCTIONS

def _print_msg(text: str, verbose: bool) -> None:
    if verbose:
        print(text)


#%% APPLICATION ENTRY POINT

# same as above for the argv=None argument
def main(argv: list[str] | None = None) -> None:
    """
    Application entry point.

    Parameters
    ----------
    argv : list[str] or None, optional
        List of arguments passed to the command line utility. If None, they are
        read from the CLI; if not None, arguments and flags can be passed explicitly.
        The default is None.

    """
    
    args = read_cli_args(argv)
    bibfile = Path(args.bibfile)
    # keep the same parent directory as bibfile, and use a user-defined name
    outfile = bibfile.with_name(bibfile.stem + '_clean.bib')
    clean_bibfile(bibfile, outfile, verbose=args.verbose)


if __name__ == '__main__':
    main()