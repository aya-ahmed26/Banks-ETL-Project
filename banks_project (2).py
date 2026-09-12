from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime





def log_progress(message):
    ''' This function logs the mentioned message of a given stage of the
    code execution to a log file. Function returns nothing'''

    timestamp_format = '%Y-%h-%d-%H:%M:%S'
    now = datetime.now()
    timestamp = now.strftime(timestamp_format)

    with open('./code_log.txt', 'a') as f:
        f.write(timestamp + ' : ' + message + '\n')


def extract(url, table_attribs):
    ''' This function aims to extract the required
    information from the website and save it to a data frame. The
    function returns the data frame for further processing. '''

    page = requests.get(url).text
    data = BeautifulSoup(page, 'html.parser')

    tables = data.find_all('table')

    df = pd.DataFrame(columns=table_attribs)

    for table in tables:

        headers = table.find_all('th')
        header_text = [
            header.get_text(" ", strip=True)
            for header in headers
        ]

        if any('Market cap' in header for header in header_text):

            rows = table.find_all('tr')

            for row in rows[1:]:

                col = row.find_all(['td', 'th'])

                if len(col) >= 3:

                    name = col[1].get_text(" ", strip=True)
                    market_cap = col[2].get_text(" ", strip=True)

                    market_cap = market_cap.replace(',', '')
                    market_cap = ''.join(
                        char for char in market_cap
                        if char.isdigit() or char == '.'
                    )

                    if market_cap:
                        data_dict = {
                            'Name': name,
                            'MC_USD_Billion': float(market_cap)
                        }

                        df = pd.concat(
                            [df, pd.DataFrame([data_dict])],
                            ignore_index=True
                        )

            break

    return df


def transform(df, csv_path):
    ''' This function accesses the CSV file for exchange rate
    information, and adds three columns to the data frame, each
    containing the transformed version of Market Cap column to
    respective currencies'''

    exchange_rate = pd.read_csv(csv_path)

    exchange_rate = exchange_rate.set_index('Currency').to_dict()['Rate']

    gbp_rate = float(exchange_rate['GBP'])
    eur_rate = float(exchange_rate['EUR'])
    inr_rate = float(exchange_rate['INR'])

    df['MC_GBP_Billion'] = [
        np.round(x * gbp_rate, 2)
        for x in df['MC_USD_Billion']
    ]

    df['MC_EUR_Billion'] = [
        np.round(x * eur_rate, 2)
        for x in df['MC_USD_Billion']
    ]

    df['MC_INR_Billion'] = [
        np.round(x * inr_rate, 2)
        for x in df['MC_USD_Billion']
    ]

    return df



def load_to_csv(df, output_path):
    ''' This function saves the final data frame to a CSV file
    in the provided path. Function returns nothing.'''

    df.to_csv(output_path, index=False)
    log_progress('Data saved to CSV file')


def load_to_db(df, sql_connection, table_name):
    ''' This function saves the final data frame to a database
    table with the provided name. Function returns nothing.'''

    df.to_sql(
        table_name,
        sql_connection,
        if_exists='replace',
        index=False
    )
    log_progress('Data loaded to Database as a table, Executing queries')



def run_query(query_statement, sql_connection):
    ''' This function runs the query on the database table
    and prints the output on the terminal. Function returns nothing.'''

    print(query_statement)

    result = pd.read_sql_query(
        query_statement,
        sql_connection
    )

    print(result)

    log_progress('Query executed: ' + query_statement)
# MAIN PROCESS

url = 'https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks'

exchange_rate_csv = './exchange_rate.csv'

table_attribs = ['Name', 'MC_USD_Billion']

output_path = './Largest_banks_data.csv'

db_name = 'Banks.db'

table_name = 'Largest_banks'


#  Log preliminaries
log_progress('Preliminaries complete. Initiating ETL process')


#  Extract
df = extract(url, table_attribs)

log_progress('Data extraction complete. Initiating Transformation process')


#  Transform
df = transform(df, exchange_rate_csv)

print(df)

# Print the 5th largest bank's EUR market capitalization
print(df['MC_EUR_Billion'][4])

log_progress('Data transformation complete. Initiating Loading process')


# Load to CSV
load_to_csv(df, output_path)




# Load to Database
sql_connection = sqlite3.connect(db_name)

log_progress('SQL Connection initiated')

load_to_db(df, sql_connection, table_name)




# Run Queries

run_query(
    'SELECT * FROM Largest_banks',
    sql_connection
)

run_query(
    'SELECT AVG(MC_GBP_Billion) FROM Largest_banks',
    sql_connection
)

run_query(
    'SELECT Name FROM Largest_banks LIMIT 5',
    sql_connection
)

log_progress('Process Complete')


# Close Database Connection
sql_connection.close()

log_progress('Server Connection closed')
