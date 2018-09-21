from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from moz_sql_parser import parse, format
import pyparsing
from six import string_types

from gsheetsdb.exceptions import NotSupportedError, ProgrammingError


def replace(obj, replacements):
    """
    Modify parsed query recursively in place.

    """
    if isinstance(obj, list):
        for i, value in enumerate(obj):
            if isinstance(value, string_types) and value in replacements:
                obj[i] = replacements[value]
            elif isinstance(value, (list, dict)):
                replace(value, replacements)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, string_types) and value in replacements:
                obj[key] = replacements[value]
            elif isinstance(value, list):
                replace(value, replacements)
            elif isinstance(value, dict) and 'literal' not in value:
                replace(value, replacements)


def remove_aliases(parsed_query):
    select = parsed_query['select']
    if isinstance(select, dict):
        select = [select]

    for clause in select:
        if 'name' in clause:
            del clause['name']


def unalias_orderby(parsed_query):
    if not 'orderby' in parsed_query:
        return 

    select = parsed_query['select']
    if isinstance(select, dict):
        select = [select]

    alias_to_value = {
        clause['name']: clause['value']
        for clause in select
        if isinstance(clause, dict) and 'name' in clause
    }

    for k, v in parsed_query['orderby'].items():
        if isinstance(v, string_types) and v in alias_to_value:
            parsed_query['orderby'][k] = alias_to_value[v]


def extract_column_aliases(sql):
    try:
        parsed_query = parse(sql)
    except pyparsing.ParseException as e:
        raise ProgrammingError(format_error(sql, e.lineno, e.col, str(e)))

    select = parsed_query['select']
    if isinstance(select, dict):
        select = [select]

    aliases = []
    for clause in select:
        if isinstance(clause, dict):
            aliases.append(clause.get('name'))
        else:
            aliases.append(None)

    return aliases


def format_error(query, line, column, detailed_message):
    msg = query.split('\n')[:line]
    msg.append('{indent}^'.format(indent=' ' * (column - 1)))
    msg.append(detailed_message)
    return '\n'.join(msg)


def translate(sql, column_map):
    try:
        parsed_query = parse(sql)
    except pyparsing.ParseException as e:
        raise ProgrammingError(format_error(sql, e.lineno, e.col, str(e)))
    print(parsed_query)

    # HAVING is not supported
    if 'having' in parsed_query:
        raise NotSupportedError('HAVING not supported')

    from_ = parsed_query.pop('from')
    if not isinstance(from_, string_types):
        raise NotSupportedError('FROM should be a URL')

    unalias_orderby(parsed_query)
    remove_aliases(parsed_query)
    replace(parsed_query, column_map)

    return format(parsed_query)
