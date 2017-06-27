import pandas as pd
import json

json_file = 'C:\\Users\\Joe\\Documents\\MTG\\MTG Goldfish Decks\\Sultai Delirium_591943.json'
collection_file = 'C:\\Users\\Joe\\Documents\\MTG\\20170625 my_collection.csv'

with open(json_file) as data_file:
    json_data = json.load(data_file)

deck_number = list(json_data.keys())[0]
deck_object = json_data[deck_number]
list_of_card_groups = deck_object['list']

def get_df_of_cards_in_type(card_type):
    cards_df = pd.DataFrame(list_of_card_groups[card_type])
    cards_df['card_type'] = card_type
    cards_df_with_good_column_names = cards_df.rename(columns={'deck-col-qty': 'how_many_the_deck_needs', 'deck-col-card': 'name', 'deck-col-price': 'price'})
    return cards_df_with_good_column_names

card_type_dfs = map(get_df_of_cards_in_type, list_of_card_groups.keys())
deck_df = pd.concat(card_type_dfs)
deck_df['how_many_the_deck_needs'] = pd.to_numeric(deck_df['how_many_the_deck_needs'])
deck_df['price'] = pd.to_numeric(deck_df['price'])
deck_df['unit_price'] = deck_df['price'] / deck_df['how_many_the_deck_needs']

# import list of collection, aggregate to card name level (squashes foils/sets), then match
collection = pd.read_csv(collection_file)
collection = collection.groupby('Card')['Quantity'].sum()
collection = pd.DataFrame(collection)
# to do: exclude basic lands?
basic_lands = ['Forest', 'Mountain', 'Island', 'Plains', 'Swamp']


def get_how_many_you_have(row):
    return collection.loc[row['name'], 'Quantity'] if row['name'] in collection.index else 0

deck_df['how_many_you_have'] = deck_df.apply(get_how_many_you_have, axis=1)
deck_df['how_many_you_need'] = deck_df['how_many_the_deck_needs'] - deck_df['how_many_you_have']

def get_cost_to_complete_deck_requirements(row):
    return (row['how_many_the_deck_needs'] - row['how_many_you_have']) * row['unit_price']

def get_value_of_cards_you_have(row):
    return row['how_many_you_have'] * row['unit_price']

deck_df['value_of_cards_you_have'] = deck_df.apply(get_value_of_cards_you_have, axis=1)
deck_df['cost_to_complete_deck_requirements'] = deck_df.apply(get_cost_to_complete_deck_requirements, axis=1)
print(deck_df)

cards_you_have = deck_df[deck_df['how_many_you_have'] > 0]
print('cards you have: ')
print(cards_you_have[['name', 'how_many_you_have', 'how_many_the_deck_needs']])
print('total value: ')
total_value_of_your_cards = deck_df['value_of_cards_you_have'].sum()
print(total_value_of_your_cards)

cards_you_need_to_buy = deck_df[deck_df['how_many_you_need'] > 0]
print('cards you need to buy:')
print(cards_you_need_to_buy[['name', 'how_many_you_need', 'unit_price']])
print('total cost: ')
total_cost_to_complete_the_deck = deck_df['cost_to_complete_deck_requirements'].sum()
print(total_cost_to_complete_the_deck)

print('percentage of the deck you own by value: ' + str(100 * total_value_of_your_cards / (total_value_of_your_cards + total_cost_to_complete_the_deck)))
print('deck owned by count: ' + str(deck_df['how_many_you_have'].sum()) + ' / ' + str(deck_df['how_many_the_deck_needs'].sum()))

print('pokedex fraction unlocked: ' + str(len(cards_you_have)) + ' / ' + str(len(deck_df)))
