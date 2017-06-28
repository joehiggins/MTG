import pandas as pd
import json
import os
import time

#import collection
collection_directory = 'C:\\Users\\Joe\\Documents\\MTG\\'
collection_file = '20170625 my_collection.csv'
# import list of collection, aggregate to card name level (squashes foils/sets), then match
collection = pd.read_csv(collection_directory + collection_file)
collection = collection.groupby('Card')['Quantity'].sum()
collection = pd.DataFrame(collection)
#Add basic lands to collection
basic_lands = pd.DataFrame([['Forest',99], ['Mountain',99], ['Island',99], ['Plains',99], ['Swamp',99]]).set_index(0)
basic_lands = basic_lands.rename(columns={1: "Quantity"})
collection = collection.append(basic_lands)

#allocate output dataframe
output_columns = [
    'deck_name',
    'archetype',
    'url',
    'pct_cost_owned',
    'pct_pokedex_owned',
    'pct_cards_owned',
    'cost_owned',
    'cost_total',
    'pokedex_owned',
    'pokedex_total',
    'cards_owned',
    'cards_total'
]
output = pd.DataFrame(columns = output_columns)

#declare useful functions
def get_df_of_cards_in_type(card_type):
    cards_df = pd.DataFrame(list_of_card_groups[card_type])
    cards_df['card_type'] = card_type
    cards_df_with_good_column_names = cards_df.rename(columns={'deck-col-qty': 'how_many_the_deck_needs', 'deck-col-card': 'name', 'deck-col-price': 'price'})
    return cards_df_with_good_column_names

def get_how_many_you_have(row):
    return collection.loc[row['name'], 'Quantity'] if row['name'] in collection.index else 0

def get_how_many_you_need(row):
    return max(row['how_many_the_deck_needs'] - row['how_many_you_have'], 0)

def get_cost_to_complete_deck_requirements(row):
    return row['how_many_you_need'] * row['unit_price']

def get_value_of_cards_you_have(row):
    return (row['how_many_the_deck_needs'] - row['how_many_you_need']) * row['unit_price']

def division_by_zero_to_zero(a, b):
    if b == 0:
        return 0
    else:
        return a/b

#Loop through every file
directory = 'C:\\Users\\Joe\\Documents\\MTG\\MTG Goldfish Decks\\'
count = 0
number_of_decks = len(os.listdir(directory))

for filename in os.listdir(directory):
    if filename.endswith(".json"): 
        #print(os.path.join(directory, filename))

        start_time = time.time()
        
        json_file = directory + filename
        
        with open(json_file) as data_file:
            json_data = json.load(data_file)
        
        deck_number = list(json_data.keys())[0]
        deck_object = json_data[deck_number]
        list_of_card_groups = deck_object['list']
        
        card_type_dfs = map(get_df_of_cards_in_type, list_of_card_groups.keys())
        deck_df = pd.concat(card_type_dfs)
        deck_df['how_many_the_deck_needs'] = pd.to_numeric(deck_df['how_many_the_deck_needs'])
        
        #Skip if user didn't enter real cards and no price info available (e.g., https://www.mtggoldfish.com/deck/378046#paper):
        if 'price' not in deck_df:
            continue 
        
        deck_df['price'] = pd.to_numeric(deck_df['price'].str.replace(',','').fillna(0))
        deck_df['unit_price'] = deck_df['price'] / deck_df['how_many_the_deck_needs']
        
        deck_df['how_many_you_have'] = deck_df.apply(get_how_many_you_have, axis=1)
        deck_df['how_many_you_need'] = deck_df.apply(get_how_many_you_need, axis=1)
        cards_you_have = deck_df[deck_df['how_many_you_have'] > 0]        
        
        deck_df['value_of_cards_you_have'] = deck_df.apply(get_value_of_cards_you_have, axis=1)
        deck_df['cost_to_complete_deck_requirements'] = deck_df.apply(get_cost_to_complete_deck_requirements, axis=1)
        
        deck_name = deck_object['description']['deck_name']
        archetype = deck_object['description']['archetype']
        
        cost_owned = deck_df['value_of_cards_you_have'].sum()
        cost_total = deck_df['cost_to_complete_deck_requirements'].sum()
        pct_cost_owned = division_by_zero_to_zero(cost_owned, cost_total)
        
        cards_owned = deck_df['how_many_the_deck_needs'].where(deck_df['how_many_you_have'] > 0, 0).sum()
        cards_total = deck_df['how_many_the_deck_needs'].sum()
        pct_cards_owned = division_by_zero_to_zero(cards_owned, cards_total)
        
        pokedex_owned = len(cards_you_have)
        pokedex_total = len(deck_df)
        pct_pokedex_owned = division_by_zero_to_zero(pokedex_owned, pokedex_total)
        
        summary = pd.DataFrame(data=[[
            deck_name,
            archetype,
            deck_number,
            pct_cost_owned,
            pct_pokedex_owned,
            pct_cards_owned,
            cost_owned,
            cost_total,
            pokedex_owned,
            pokedex_total,
            cards_owned,
            cards_total
        ]],columns = output_columns)
        
        #output = output.append(summary)
        output, summary = output.align(summary, axis=1)
        output = pd.concat([output, summary])
                
        end_time = time.time()
        
        if count%100 == 0:
            print('Percent Complete: ' + str('{:.2%}'.format(count/number_of_decks)) + '  (' + str(count) + '/'+ str(number_of_decks) + ')  Time Diff: ' + str('{:.2}'.format(end_time - start_time)))
            
        count += 1
        
        continue
    else:
        continue

output.to_csv(collection_directory+'all_deck_summary_stats2.csv', encoding = 'utf-8')