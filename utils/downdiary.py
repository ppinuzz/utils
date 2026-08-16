#!/usr/bin/env python3
"""
Download diary entries from Google Keep and print them to file.

@author: Andrea Pinardi <andreapinardi319@gmail.com>
"""

import argparse
from pathlib import Path
from dataclasses import dataclass
import datetime
import gkeepapi
import gpsoauth
import yaml
import re
from textwrap import dedent


#%% UTILITY FUNCTIONS

@dataclass
class DiaryNote:
    """Dataclass representing a diary entry in Google Keep."""
    
    date: datetime.date
    title: str
    text: str


def download_diary(mail: str, master_token: str, label: str, 
                   verbose: bool = False) -> list[DiaryNote]:
    """
    Download diary entries from Google Keep.

    Parameters
    ----------
    mail : str
        Google account email.
    master_token : str
        Master token used to access the Google account.
    label : str
        Label identifying the diary entries (e.g. "Diary 2024").
    verbose : bool, optional
        Whether to print a verbose output. The default is False.

    Returns
    -------
    entries : list[DiaryNote]
        Diary entries sorted from oldest (1st) to newest (last).

    """
    
    _print_msg('Authenticating to access Google Keep...', verbose)
    GoogleKeep = gkeepapi.Keep()
    GoogleKeep.authenticate(mail, master_token)
    _print_msg(f'Accessing diary entries labelled as "{label}"...', verbose)
    diary_label = GoogleKeep.findLabel(label)
    diary = GoogleKeep.find(labels=[diary_label])
    entries = []
    # one or more digits
    year = int(re.search(r'\d+', label)[0])
    months = {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 
              'giugno': 6, 'luglio': 7, 'agosto': 8, 'settembre': 9, 
              'ottobre': 10, 'novembre': 11, 'dicembre': 12}
    for entry in diary:
        title = entry.title.lower()
        month = [months[name] for name in months if name in title][0]
        day = int(re.search(r'\d+', title).group())
        
        note = DiaryNote(date=datetime.date(year, month, day),
                         title=title,
                         text=entry.text)
        entries.append(note)
    
    _print_msg(f'Read {len(entries)} diary entries', verbose)
    
    # sort the list from oldest (1st) to newest (last)
    entries.sort(key=lambda entry: entry.date)
    
    return entries


def print_diary(diary: list[DiaryNote], style: str, merge: bool = False, 
                verbose: bool = False) -> None:
    """
    Print diary entries to a Markdown or a LaTeX file.

    Parameters
    ----------
    diary : list[DiaryNote]
        List of all the diary entries, each saved as a DiaryNote dataclass.
    style : str
        Either 'Markdown' or 'LaTeX'.
    merge : bool, optional
        Whether to merge all the entries in a single file or keep them separate. 
        The default is False.
    verbose : bool, optional
        Whether to print a verbose output. The default is False.

    Raises
    ------
    ValueError
        If the style is unknown.

    """
    
    year = diary[0].date.year
    year_dir = Path.cwd() / str(year)
    _print_msg(f'Creating year directory \n\t{year_dir.resolve()}', verbose)
    year_dir.mkdir(exist_ok=True)
    
    style = style.lower()
    match style:
        case 'markdown':
            template_entry = '# {}\n\n{}'
            template_diary = '## {}\n\n{}'
            text_diary = f'# {year}\n\n'
            file_ext = '.md'
            closing_block = ''
        case 'latex':
            # dedent removes indentation if all lines are indented of the same
            # amount => remove the first empty line (\n) with lstrip()
            template_entry = dedent(rf"""
                                    % !TEX encoding = UTF-8 
                                    % !TEX TS-program = pdflatex
                                    % !TEX spellcheck = it-IT
                                    % !TEX root = {year}.tex
                                    """).lstrip()
            # '{{' is interpreted as a literal '{' by .format()
            template_entry = (template_entry + '\n\n' 
                              + r'\section*{{' '{}' + '}}\n{}')
            file_ext = '.tex'
            preamble = dedent(r"""
                              % !TEX encoding = UTF-8 
                              % !TEX TS-program = pdflatex
                              % !TEX spellcheck = it-IT
                              % !BIB TS-program = bibtex
                              
                              \documentclass[a4paper]{article}
                              \usepackage[T1]{fontenc}
                              \usepackage[utf8]{inputenc}
                              \usepackage[italian]{babel}
                              \usepackage{microtype}
                              % euro symbol
                              \usepackage{eurosym}
                              % greek letters not in math mode
                              \usepackage{textcomp}
                              % IF QUOTES ARE NOT SET AS ``...'' IN TEXSTUDIO (or OVERLEAF is used)
                              % LaTeX reproduces "..." verbatim (like ''...'') instead of using the mirrored version
                              % use csquotes package to avoid typing them explicitely as ``...''
                              \usepackage[italian=quotes]{csquotes}
                              \MakeOuterQuote{"}
                              % remove paragraph indent
                              \setlength{\parindent}{0pt}
                              
                              \begin{document}""").lstrip()
            preamble += '\n'
            preamble += r'\title{' + f'Diario {year}' + '}'
            preamble += '\n'
            preamble += r'\maketitle'
            preamble += '\n\n'
            text_diary = preamble
            template_diary = r'\section*{{' + '{}' + '}}\n{}'
            closing_block = r'\end{document}'
        case _:
            raise ValueError(f"Unknown style '{style}'")
    
    
    for entry in diary:
        _print_msg(f'Writing to file diary entry {entry.date}', verbose)
        # normalise trailing whitespaces 
        note_text = entry.text.rstrip() + '\n\n\n'
        # restore capital letter to 1st word
        note_title = entry.title[0].upper() + entry.title[1:]
        # and remove trailing whitespaces
        note_title = note_title.rstrip()
        # fix text to adapt it to LaTeX (e.g. '&' -> '\&')
        if style == 'latex':
            note_text = _fix_latex_text(note_text)
            problem = _check_latex_text(note_text)
            if problem is not None:
                print(f'Problem to be fixed in note {entry.date}: {problem}')
        
        if not merge:
            text = template_entry.format(note_title, note_text)
            # specify encoding to avoid errors with accents
            with open(year_dir/f'{entry.date}{file_ext}', 'w', encoding='utf-8') as file:
                file.write(text)
            
            if style == 'latex':
                text_diary += r'\input{' + f'{entry.date}' + '}\n'
        else:
            text_diary += template_diary.format(note_title, note_text)
    
    text_diary += closing_block 
    
    # a "main" file is required only when using LaTeX and when writing diary
    # entries in Markdown as a single merged document
    if style != 'markdown' or (style == 'markdown' and merge):
        with open(year_dir/f'{year}{file_ext}', 'w', encoding='utf-8') as file:
            file.write(text_diary)
    
    if style == 'latex':
        _create_latexmkrc(year_dir/f'{year}{file_ext}', verbose)


def get_master_token(email: str, oauth_token: str, android_id: str) -> dict[str, str]:
    """
    Get Google master token to access Google API.

    Parameters
    ----------
    email : str
        Google account email.
    oauth_token : str
        Authentication token ``oauth_token``, obtained following 
        ``https://github.com/simon-weber/gpsoauth#alternative-flow``.
    android_id : str
        16-character hex Android ID (e.g. any 16-char hex number).

    Raises
    ------
    RuntimeError
        If authentication failed.

    Returns
    -------
    auth_data : dict[str, str]
        Authentication data: email, Android ID and master token.

    """

    # following 
    # https://github.com/simon-weber/gpsoauth#alternative-flow    
    response = gpsoauth.exchange_token(email, oauth_token, android_id)
    if 'Token' not in response:
        raise RuntimeError(f'Authentication failed: {response}')

    # should start with 'aas_et/...'
    master_token = response['Token']
    print(f'Email           : {email}')
    print(f'Master token    : {master_token}')
    
    # directory from which this script is run (i.e. CWD)
    token_file = Path.cwd() / 'master_token.yaml'
    auth_data = {'email': email,
                 'master_token': master_token,
                 'android_id': android_id
                 }
    print(f'Saving master token to \n\t{token_file.resolve()}')
    with open(token_file, 'w') as file:
        yaml.safe_dump(auth_data, file)
    
    return auth_data



#%% PRIVATE FUNCTIONS

def _print_msg(text: str, verbose: bool) -> None:
    if verbose:
        print(text)


def _fix_latex_text(text: str) -> str:
    # remove trailing whitespaces
    text = text.rstrip()
    
    # '&' converted to '\&'
    # find indices of all the occurences of those characters
    # https://stackoverflow.com/questions/3519565/find-the-indexes-of-all-regex-matches#comment110205339_3519601
    matches = re.finditer(r'[&%$_]', text)
    # FIXME: quando aggiungi/sostituisci dei pezzi, allunghi/accorci la stringa
    # => aggiorna gli indici, altrimenti continuerai a modificare test che ora
    # si trova nella posizione sbagliata
    shift = 0
    for char in matches:
        idx = char.start() + shift
        # the single '\' must be escaped, even if raw strings are used
        text = text[0:idx] + '\\' + text[idx:]
        # by adding a '\', all the following chars are shifted by 1 => keep
        # track of how many shifts you need, as all the matches use the
        # original unshifted indices
        shift += 1
    matches = re.finditer(r'[€μΔπρ≠εωνασΈίβ]', text)
    shift = 0
    # TODO: fix ancient Greek letters (e.g. Έ and ί)
    substitutions = {'€': r'\euro{}', 'μ': r'$\mu$', 'Δ': r'$\Delta$', 'π': r'$\pi$',
                     'ρ': r'$\rho$', '≠': r'$\neq$', 'ε': r'$\epsilon$', 
                     'ω': r'$\omega$', 'ν': r'$\nu$', 'α': r'$\alpha$', 
                     'σ': r'$\sigma$', 'Έ': r'\'E', 'ί': r'ì', 'β': r'$\beta$'}
    # remove € (-1) and add the code '\euro{}' (+7) => total: +6 shift
    shifts = {'€': 6, 'μ': 4, 'Δ': 6, 'π': 4, 'ρ': 5, '≠': 5, 'ε': 9, 'ω': 7, 
              'ν': 4, 'α': 7, 'σ': 7, 'Έ': 2, 'ί': 0, 'β': 6}
    for char in matches:
        matched_char = char.group()
        idx = char.start() + shift
        text = text[0:idx] + substitutions[matched_char] + text[idx+1:]
        shift += shifts[matched_char]
    
    # find text in between the *...*
    # => literal asterisk (\*) followed by any character (.) using a lazy match
    # (i.e. it won't match the 1st * with the last *, but only the 1st * with 
    # the 2nd *, and then the 3rd * with the 4th *, etc.), capturing what's in
    # between the *...*
    matches = re.finditer(r'\*(.*?)\*', text)
    shift = 0
    for emph in matches:
        # e.g. *my desk* is captured
        #   text[start] = '*'
        #   text[end] = '*'
        start = emph.start() + shift
        end = emph.end() + shift
        text = text[0:start] + r'\emph{' + text[start+1:end-1] + '} ' + text[end+1:]
        # add 7 characters, but remove 2 (the asterisks)
        shift += 5
    
    # replace hyphens with dashes
    # two possible scenarios:
    #   "lorem ipsum - dolor sit - amet"
    #   "lorem ipsum - dolor sit -, amet"   => more debatable
    # any whitespace (\s) followed by the hyphen (\-) and by either a comma or
    # a space
    matches = re.finditer(r'\s\-[,\s]', text)
    shift = 0
    for char in matches:
        # text[idx] = ' ', the space before the hyphen
        idx = char.start() + shift
        text = text[0:idx+1] + '-' + text[idx+1:]
        shift += 1
    
    # '\n\n' in the original text is meant to leave an empty line
    # match 2 or more \n: \n{n,2}
    matches = re.finditer(r'\n{2,}', text)
    shift = 0
    for char in matches:
        start = char.start() + shift
        end = char.end() + shift
        text = text[0:start+1] + r'\bigskip' + '\n' + text[end:]
        shift += 9 - (len(char.group())-1)
    
    # '\n' gets ignored in LaTeX, but '\n\n' doesn't
    # a \n NOT (!) preceded by another \n
    matches = re.finditer(r'(?<!\n)\n', text)
    shift = 0
    for char in matches:
        idx = char.start() + shift
        text = text[0:idx] + '\n' + text[idx:]
        shift += 1
    
    return text


def _check_latex_text(text: str) -> str | None:
    
    # default: no problem
    problem = None
    matches = re.findall(r'"', text)
    if len(matches)%2 != 0:
        problem = f'The are some mismatched quotes: found {len(matches)} " in the text'
    
    return problem


def _create_latexmkrc(mainfile: Path, verbose: bool = False) -> None:
    
    # main file (e.g. '2024.tex') depends on the year of the diary
    text = dedent(f"""
    # latexmkrc FILE TO COMPILE LaTeX CODE BY RUNNING latexmk ON THE TERMINAL
    
    # list of options used by Overleaf in its LatexMk "system-wide" file:
    # https://www.overleaf.com/learn/how-to/How_does_Overleaf_compile_my_project%3F
    
    # Main compilation command
    #   -interaction=nonstopmode    try to compile without pausing for user interaction in case of errors
    #   -synctex=1                  generate a synchronization file to go from source code to PDF and vice versa in an IDE (e.g., TeXstudio)
    #   %O                          placeholder for optional compilation flags when calling latexmk
    #   %S                          placeholder for the name of the LaTeX source file
    $pdflatex = 'pdflatex -interaction=nonstopmode -synctex=1 %O %S';
    
    
    # Specify the output to be a .pdf 
    # (https://mg.readthedocs.io/latexmk.html#local-configuration-files):
    $pdf_mode = 1;
        
    # Specify the main file (if not specified, all the .tex files in the CWD will be used - in this case, there's no difference)
    @default_files = ('{mainfile.name}');
    
    # Run BibTeX whenever a change in the .aux file occurs (to keep References updated)
    $bibtex_use = 2;
    
    # Clean these files before compilation (list of extensions)
    $clean_ext = 'aux acn acr alg bbl bcf blg glo gls glsdefs idx ist lof lot nlg nlo nls out run.xml sta synctex.gz toc';
    
    # Copied from Overleaf's default LatexMk
    # https://www.overleaf.com/learn/how-to/How_does_Overleaf_compile_my_project%3F
    """).lstrip()
    
    text += dedent(r"""
    # makeindex
    @ist = glob("*.ist");
    if (scalar(@ist) > 0) {
            $makeindex = "makeindex -s $ist[0] %O -o %D %S";
    }
    
    # If you want to move .cls, .sty and .bst files in other folders:
        # https://www.overleaf.com/learn/latex/Questions/I_have_a_lot_of_.cls%2C_.sty%2C_.bst_files%2C_and_I_want_to_put_them_in_a_folder_to_keep_my_project_uncluttered._But_my_project_is_not_finding_them_to_compile_correctly
        
    # Standard line to signify the end of the script
    1;
    """).lstrip()
    
    latexmkrc = mainfile.parent / 'latexmkrc'
    _print_msg(f'Writing latexmkrc file to \n\t{latexmkrc.resolve()}', verbose)
    with open(latexmkrc, 'w') as file:
        file.write(text)


#%% CLI

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
                prog='downdiary',
                description='Download diary notes from Google Keep',
                # %(prog)s is used to include the program's name
                epilog='This is %(prog)s, version 1.0.0',
                # force the user to enter the exact long option's name
                # (otherwise, --a, --arg, --arg-long-name will be equivalent)
                allow_abbrev=False)
    
    # subcommands are divided in groups, each command has a sub-parser and all
    # the subparsers of a single group are associated with this object
    subparsers = parser.add_subparsers(dest='auth_commands',
                                       title='subcommands',
                                       metavar='COMMAND',
                                       description='use -h, --help to access each subcommand manpage')
    
    # command to get master token
    getmtok_parser = subparsers.add_parser('getmtok',
                                    help='obtain Google master token for your account')
    getmtok_parser.add_argument('-e', '--email', help='account email')
    getmtok_parser.add_argument('-t', '--auth-tok', help='Google authentication token oauth_token')
    getmtok_parser.add_argument('-f', '--file', help='authentication data file (with email and oauth_token)')
    getmtok_parser.add_argument('-i', '--id', help='Android 16-char hex ID')
    

    parser.add_argument('-e', '--email', help='account email')
    parser.add_argument('-t', '--master-tok', help='Google master token')
    parser.add_argument('-f', '--file', help='authentication data file (with email and master token)')
    parser.add_argument('-l', '--label', help='diary label, between "..."')
    # add an optional argument ("option/switch/flag")
    # whose flag is -v or --verbose indifferently
    # whose action means "store a True if the option is given by the user, 
    # otherwise set to False" (i.e. False is the default)
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='print verbose output')
    parser.add_argument('-x', '--latex', action='store_true', 
                        help='create LaTeX output file')
    parser.add_argument('-m', '--markdown', action='store_true', 
                        help='create Markdown output file')
    parser.add_argument('-s', '--merge', action='store_true', 
                        help='merge all entries in a single file')
    
    
    # parse the arguments passed to the function
    # (either from the terminal or explicitly calling this CLI function from
    # within another program)
    args = parser.parse_args(argv)

    # check for incompatible options
    if args.auth_commands == 'getmtok':
        separated_args = (args.email is not None or args.auth_tok is not None or args.id is not None)
        if args.file is not None and separated_args:
            getmtok_parser.error('--file option cannot be combined with --email, --auth-tok or --id')
    
    if args.file is not None and (args.email is not None or args.master_tok is not None):
        parser.error('--file option cannot be combined with --email or --master-tok')

    return args
    


#%% APPLICATION ENTRY POINT

# same as above for the argv=None argument
def main(argv: list[str] | None = None):
    """
    Application entry point.

    Parameters
    ----------
    argv : list[str] or None, optional
        List of arguments passed to the command line utility. If None, they are
        read from the CLI; if not None, arguments and flags can be passed explicitly.
        The default is None.

    Raises
    ------
    ValueError
        If arguments are missing or wrong (e.g. invalid pairs).

    """
    args = read_cli_args(argv)
    
    # GET MASTER TOKEN
    if args.auth_commands == 'getmtok':
        if args.file is not None:
            auth_data_file = Path.cwd() / args.file
            with open(auth_data_file, 'r') as file:
                auth_data = yaml.safe_load(file)
                email = auth_data['email']
                oauth_token = auth_data['oauth_token']
                android_id = auth_data['android_id'] 
        elif args.email is not None and args.auth_tok is not None and args.id is not None:
            email = args.email
            oauth_token = args.auth_tok
            android_id = args.id
        else:
            raise ValueError('Wrong or missing arguments')
        
        get_master_token(email, oauth_token, android_id)
    else:
        # DOWNLOAD DIARY ENTRIES
        if args.file is not None:
            auth_data_file = Path(args.file)
            if args.verbose:
                print(f'Reading authentication info from \n\t{auth_data_file.resolve()}')
            with open(auth_data_file, 'r') as file:
                auth_data = yaml.safe_load(file)
                email = auth_data['email']
                master_token = auth_data['master_token']
        elif args.email is not None and args.master_tok is not None:
            email = args.email
            master_token = args.master_tok
        else:
            raise ValueError('Wrong or missing arguments')
        
        print('Executing routine to download diary entries from Google Keep...')
        if args.label is None:
            raise ValueError('Missing diary label')
        diary = download_diary(email, master_token, args.label, verbose=args.verbose)
        
        if args.markdown and args.latex:
            raise ValueError('Markdown and LaTeX options cannot be combined')
        elif args.markdown:
            style = 'Markdown'
        elif args.latex:
            style = 'LaTeX'
        else:
            raise ValueError('Missing output format')
        print(f'Formatting diary entries in {style}...')
        print_diary(diary, style, verbose=args.verbose, merge=args.merge)
        print('Writing finished')


if __name__ == '__main__':
    main()