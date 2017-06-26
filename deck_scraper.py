# -*- coding: utf-8 -*-
"""
Created on Sun May 14 11:45:37 2017

@author: Joe
"""

import os
import json
import requests
import time
import errno
from functools import reduce
from bs4 import BeautifulSoup
from collections import defaultdict


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

# directory the we will dump the files into
# TODO: JCH have this be dynamic file path so it works on other machines
output_directory = 'decks'
mkdir_p(output_directory)

# Construct the First URL to request
baseURL = 'https://www.mtggoldfish.com/deck/'
start = 321262  # 258216 is the true start number and is the earliest deck I found
finish = 645533  # determined by looking at most recently uploaded deck: https://www.mtggoldfish.com/deck/custom/standard#paper 
endURL = '#paper'

for i in range(start, finish + 1):
    deck_num = i
    URL = baseURL + str(deck_num) + endURL

    # Get the page
    print("Requesting:          " + URL)
    page = requests.get(URL)
    contents = page.content
    soup = BeautifulSoup(contents, 'html.parser')

    # Check if the URL was valid, if it either:
    #   i got throttled keep trying again
    #   500
    #   502: bad gateway
    #   404: doesn't exist
    #   or the URL failed because the deck is private and redirected to https://www.mtggoldfish.com/metagame#paper
    #   empty deck causes table object not to exist

    # TODO: JCH rather than look for all the ways it can fail, should look for what indicates success and move forward only if finding that
    if soup.text == "Throttled\n":
        print("            Currently throttled")
        print("            Will try " + URL + " again in 1 minute")
        time.sleep(30)
        print("            Will try " + URL + " again in 30 seconds")
        time.sleep(20)
        print("            Will try " + URL + " again in 10 seconds")
        time.sleep(10)
        i += -1
        continue
    elif hasattr(soup.find('title'), 'text') and soup.text == "\n\n\nOops! | MTGGoldfish (500)\n\n    body{text-align:center;position:absolute;top:50%;margin:0;margin-top:-275px;width:100%;}\n    h2,h3{color:#555;font:bold 200% sans-serif; padding: 10px;}\n    p{color:#777;font:normal 150% sans-serif; padding: 10px;}\n    img{max-width: 100%; display:block; margin: 0 auto; height: auto;}\n  \n\n\n\n\nOops! Something went wrong!\nWe've been notified about this issue and we'll take a look at it shortly.\n    In the meantime, please try another page on mtggoldfish.\n\n\n":
        print("            Error:    500")
        continue
    elif hasattr(soup.find('title'), 'text') and soup.text == "\n502 Bad Gateway\n\n502 Bad Gateway\nnginx/1.8.0\n\n\n":
        print("            Error:    502")
        continue
    elif hasattr(soup.find('title'), 'text') and soup.find('title').text == 'Oops! Page not found! | MTGGoldfish (404)':
        print("            Error:    404")
        continue
    elif soup.find('meta', content="https://www.mtggoldfish.com/metagame"):
        print("            Error:    URL redirected to main page")
        continue
    elif soup.find('td', attrs='deck-header').text.strip() == "0 Cards Total":
        print("            Error: Some scrub entered an empty deck... wtf")
        continue

    # Find the elements we are about with beautiful soup
    title = soup.find('h2', attrs={"class": "deck-view-title"})
    description = soup.find('div', attrs={"class": "deck-view-description"})
    paper_tab = soup.find('div', attrs={"id": "tab-paper"})
    deck_table = paper_tab.find('table', attrs={"class": "deck-view-deck-table"})

    # get the deck description
    deck_name = ''
    author = ''
    if len([line for line in title.text.strip().split("\n") if line]) == 2:
        deck_name, author = [line for line in title.text.strip().split("\n") if line]

    user = ''
    archetype = ''
    if len([line for line in description.text.strip().split("\n") if line]) == 2:
        play_format, submit_date = [line for line in description.text.strip().split("\n") if line]
    elif len([line for line in description.text.strip().split("\n") if line]) == 3:
        user, play_format, submit_date = [line for line in description.text.strip().split("\n") if line]
    elif len([line for line in description.text.strip().split("\n") if line]) == 4:
        user, play_format, submit_date, archetype = [line for line in description.text.strip().split("\n") if line]
    output_description = {
        'deck_name': deck_name,
        'author': author,
        'user': user,
        'format': play_format,
        'archetype': archetype,
        'date': submit_date,
        'url': URL
    }

    # get the decklist
    deck_list = defaultdict(list)
    rows = deck_table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        card = {}

        # if the <td> is a section divider, grab it (e.g., creatures, spells...)
        if len(cols) == 1 and str.find(str(cols[0]), 'Total') < 0:
            cols = [ele.text.strip() for ele in cols]
            section = cols[len(cols) - 1]
            newlineLocation = str.find(section, '\n')
            section = section[0:newlineLocation]

        # if the <td> is a card, get [name, quantity, price] and add it to the section (e.g., 2 dark ritual at 1.00 added the spells section)
        elif len(cols) > 1:
            fields = [ele.get('class')[0] for ele in cols]
            cards = [ele.text.strip() for ele in cols]

            deck_list_entry = dict(zip(fields, cards))
            deck_list_entry = {field: card for field, card in deck_list_entry.items() if card}

            deck_list[section].append(deck_list_entry)

    # Dictionaries --> JSON
    deck = {
        str(deck_num): {
            'description': output_description,
            'list': dict(deck_list)
        }
    }

    deck_json = json.dumps(deck, ensure_ascii=False)
    # https://support.microsoft.com/en-us/help/905231/information-about-the-characters-that-you-cannot-use-in-site-names,-folder-names,-and-file-names-in-sharepoint
    deck_name_replacements = [
        ['/', '-FSLASH-'],
        ['|', '-PIPE-'],
        ['?', '-QUESTION-'],
        ['~', '-TILDE-'],
        ['#', '-POUND-'],
        ['%', '-PERCENT-'],
        ['&', '-AMPERSAND-'],
        ['*', '-ASTERISK-'],
        ['{', '-LBRACE-'],
        ['}', '-RBRACE-'],
        ['\\', '-BSLASH-'],
        [':', '-COLON-'],
        ['<', '-LANGLE-'],
        ['>', '-RANGLE-'],
        ['+', '-PLUS-'],
        ['\"', '-2QUOTE-'],
        ['\'', '-1QUOTE-'],
        ['\n', '-NEWLINE-'],
        ['\t', '-TAB-'],
        ['\r', '-RETURN-']
    ]

    safe_deck_name_for_saving_to_file = reduce((lambda x, y: x.replace(y[0], y[1])), deck_name_replacements, deck_name)
    file_name = output_directory + '/' + safe_deck_name_for_saving_to_file + "_" + str(deck_num) + ".json"
    with open(file_name, 'w') as out_file:
        json.dump(deck, out_file)

    print("            Success: wrote " + file_name)
    print("                     into  " + output_directory)
    # print(json.dumps(deck, ensure_ascii=False, indent=2, separators=(',', ': ')))
