#!/usr/bin/env python
'''
tichy_diktat

Text diktátu na vstupe (kódovanie UTF-8) prevedie na PDF, ktorý po vytlačení
žiak "vyrieši". Vďaka tomu ho môže vypracovať samostatne a v jemu vyhovujúcom
tempe.

Po vytlačení výstupu je (v predvolenom režime) úlohou žiaka:
 - čiarou spojiť písmená v slovách a zároveň sa pritom rozhodnúť medzi
    - použitím tvrdého/mäkkého i
    - znelou/neznelou spoluhláskou
 - zakrúžkovať písmeno, ktoré má byť správne písané veľkým (vlastné mená a pod)

Po spustení sa zobrazí výzva na zadanie textu, ten je možné napr. skopírovať
cez schránku (clipboard). Vstup je ukončený Ctrl-D. Výstupom je:
 diktat.pdf        - súbor so zadaním pre žiaka
 diktat.solved.pdf - súbor s riešením (pôvodný text)

Možnosti spustenia:

tichy_diktat.py [-h] [-d] [-Y] [-S] [-W] [-o OUTPUT_FILE]

Export textu do diktatu v PDF formáte

  -h, --help      show this help message and exit
  -d              Ladiace správy
  -Y              Netestovať y/i
  -S              Netestovať spodobovanie
  -W              Užšie medzery medzi slovami
  -o OUTPUT_FILE  Názov výstupného súboru (bez prípony)

Potrebné:
  - jinja2 (príprava .tex súboru)
  - xelatex (generovanie PDF)

Pro tip:
  Šetrite lesy a kúpte si grafický tablet.

Známe problémy:
  - vygenerovaný .tex súbor je prakticky needitovateľný (PR vítané)


                                  https://github.com/jose1711/tichy_diktat
'''

from jinja2 import Environment, FileSystemLoader
import argparse
import re
import subprocess
import logging
import sys


def multiple_replace(dict, text):
    # Create a regular expression    from the dictionary keys
    regex = re.compile("(%s)" % "|".join(map(re.escape, dict.keys())), flags=re.I)

    # For each match, look-up corresponding value in dictionary
    return regex.sub(get_replacement, text) 


def get_replacement(m):
    ''' return a proper replacement '''
    try:
        lookup = char_map[m.string[m.start():m.end()]]
    except KeyError:
        lookup = char_map[(m.string[m.start():m.end()]).lower()].upper().replace('ATOP', 'atop')
    return lookup


def atop(first, second):
    return '${0} \\atop {1}$'.format(first, second)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export textu do diktatu v PDF formáte')
    parser.add_argument('-d', action='store_true', dest='debug_mode', default=False, help='Ladiace správy')
    parser.add_argument('-Y', action='store_true', dest='no_yi', default=False, help='Netestovať y/i')
    parser.add_argument('-S', action='store_true', dest='no_spodobovanie', default=False, help='Netestovať spodobovanie')
    parser.add_argument('-W', action='store_true', dest='no_wide_spaces', default=False, help='Užšie medzery medzi slovami')
    parser.add_argument('-o', nargs=1, dest='output_file', default=['diktat'], help='Názov výstupného súboru (bez prípony)')
    args = parser.parse_args()

    if args.debug_mode:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug('Vstup: {}'.format(args))

    output_file = args.output_file[0] + '.tex'
    output_file_plain = args.output_file[0] + '.txt'
    output_file_solved = args.output_file[0] + '.solved.txt'
    input_string = ''
    print('Ukonči vstup Ctrl+D')
    
    while True:
        try:
            _ = input()
        except EOFError as e:
            break
        input_string += _ + '\n\n'
    
    logging.info('Vstup uložený do {0}'.format(output_file_plain))
    input_string_solved = input_string
    
    with open(output_file_plain, 'w') as f:
        f.write(input_string)
    
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    
    template = env.get_template('tichy_diktat.j2')
    
    spodobovanie_map = { "dz": atop('dz', 'c'),
                         "dž": atop('dž', 'č'),
                         "b": atop('b', 'p'),
                         "p": atop('b', 'p'),
                         "d": atop('d', 't'),
                         "t": atop('d', 't'),
                         "ď": atop('ď', 'ť'),
                         "ť": atop('ď', 'ť'),
                         "g": atop('g', 'k'),
                         "k": atop('g', 'k'),
                         "h": atop('h', 'ch'),
                         "ch": atop('h', 'ch'),
                         "z": atop('z', 's'),
                         "s": atop('z', 's'),
                         "ž": atop('ž', 'š'),
                         "š": atop('ž', 'š'),
                         "v": '$\\overset{v}{\\underset{f}{u}}$',
                         "f": '$\\overset{v}{\\underset{f}{u}}$',
                         "u": '$\\overset{v}{\\underset{f}{u}}$',
                         "V": '$\\overset{V}{\\underset{F}{U}}$',
                         "F": '$\\overset{V}{\\underset{F}{U}}$',
                         "U": '$\\overset{V}{\\underset{F}{U}}$' }
    yi_map = { "i": atop('i', 'y'),
                         "y": atop('i', 'y'),
                         "í": atop('í', 'ý'),
                         "ý": atop('í', 'ý') }

    space_map = { " ": ' \hspace{5mm}' }

    input_string = re.sub(r'[^. ] *[A-ZÁÉÍÓÚĎŤŇĽŠČŽ]', lambda n: n.group().lower(), input_string)
    input_string = re.sub(r'^.', lambda n: n.group().upper(), input_string, flags=re.M)

    char_map = {}
    if not args.no_spodobovanie:
        char_map.update(spodobovanie_map)

    if not args.no_yi:
        char_map.update(yi_map)

    if not args.no_wide_spaces:
        char_map.update(space_map)

    input_string = multiple_replace(char_map, input_string)

    output = template.render(text=input_string)
    output_solved = template.render(text=input_string_solved)

    logging.debug('Zapisujem súbor so zadaním do {}'.format(output_file))
    with open(output_file, 'w') as f:
        f.write(output)

    logging.debug('Zapisujem súbor s riešením do {}'.format(output_file_solved))
    with open(output_file_solved, 'w') as f:
        f.write(output_solved)

    logging.debug('Volám xelatex pre súbor so zadaním')
    logging.debug(subprocess.call(['xelatex', output_file]))
    logging.debug('Volám xelatex pre súbor s riešením')
    logging.debug(subprocess.call(['xelatex', output_file_solved]))
