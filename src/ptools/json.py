import click
import ptools.utils.require as require
from ptools.utils.files import resolve_input
from ptools.utils.print import FormatUtils

import json
import sys
from functools import wraps

def read_json(json_string):
    if not json_string:
        click.echo(FormatUtils.error("No JSON input provided."), err=True)
        sys.exit(1)
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        click.echo(FormatUtils.error(f"Invalid JSON input: {e}"), err=True)
        sys.exit(1)

@require.library('pandas', prompt_install=True)
def json_to_pd(data):
    # pylint: disable=import-outside-toplevel
    import pandas as pd
    if isinstance(data, dict):
        return pd.DataFrame([data])
    elif isinstance(data, list):
        return pd.DataFrame(data)
    else:
        click.echo(FormatUtils.error("JSON input must be an object or an array of objects."), err=True)
        sys.exit(1)

def output_result(result, output_path):
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            click.echo(FormatUtils.success(f"Output written to {output_path}"))
        except Exception as e:
            click.echo(FormatUtils.error(f"Failed to write output to {output_path}: {e}"), err=True)
            sys.exit(1)
    else:
        click.echo(result)

@click.group()
def cli():
    pass

@click.command()
@resolve_input
@click.option('--separator', '-s', default=',', help='CSV separator character.')
@click.option('--na-rep', default='', help='Representation for missing data.')
@click.option('--float-format', default=None, help='Format string for floating point numbers.')
@click.option('--header/--no-header', default=True, help='Whether to write out the column names.')
@click.option('--index/--no-index', default=False, help='Whether to write row names (index).')
@click.option('--index-label', default=None, help='Column label for index column(s).')
@click.option('--mode', default='w', type=click.Choice(['w', 'x', 'a']), help='File mode to use when writing the output file.')
@click.option('--encoding', default='utf-8', help='Encoding to use in the output file.')
@click.option('--compression', default='infer', help='Compression mode to use for the output file.')
@click.option('--quoting', default=None, type=click.Choice(['all', 'minimal', 'nonnumeric', 'none']), help='Quoting option to use.')
@click.option('--quotechar', default='"', help='Character used to quote fields.')
@click.option('--lineterminator', default=None, help='Newline character or character sequence to use in the output file.')
@click.option('--chunksize', default=None, type=int, help='Number of rows to write at a time.')
@click.option('--date-format', default=None, help='Format string for datetime objects.')
@click.option('--doublequote/--no-doublequote', default=True, help=
'Control quoting of quotechar inside a field.')
@click.option('--escapechar', default=None, help='Character used to escape sep and quotechar when appropriate.')
@click.option('--decimal', default='.', help='Character recognized as decimal separator.')
@click.option('--output', '-o', 'output_path', help="Path to output CSV file", default=None, required=False)
@require.library('pandas', prompt_install=True)
def to_csv(source_type, content, separator, na_rep, float_format, header, index,
           index_label, mode, encoding, compression, quoting, quotechar, lineterminator,
           chunksize, date_format, doublequote, escapechar, decimal, output_path):
    """Convert JSON input to CSV format."""
    import pandas as pd


    json_string = content
    data = read_json(json_string)
    df = json_to_pd(data)

    csv = df.to_csv(
        sep=separator,
        na_rep=na_rep,
        float_format=float_format,
        header=header,
        index=index,
        index_label=index_label,
        mode=mode,
        encoding=encoding,
        compression=compression,
        quoting={'all': 1, 'minimal': 0, 'nonnumeric': 2, 'none': 3}.get(quoting, None),
        quotechar=quotechar,
        lineterminator=lineterminator,
        chunksize=chunksize,
        date_format=date_format,
        doublequote=doublequote,
        escapechar=escapechar,
        decimal=decimal
    )
    output_result(csv, output_path)

cli.add_command(to_csv, name='to-csv')