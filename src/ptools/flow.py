"""Pythonic FP-flavored workflow engine.

:command:`ptools flow` reads values from stdin (typically one per line),
evaluates Python expressions against each value using the
:class:`~ptools.lib.flow.runner.FlowRunner`, and emits the results in the
requested output flavor (JSON, YAML, raw Python, etc.).

The module defines the top-level CLI subcommands - :command:`collect`,
:command:`dict`, :command:`exec`, :command:`filter`, :command:`foreach`,
:command:`group`, :command:`json`, :command:`patch`, :command:`range`,
:command:`read`, :command:`reduce`, :command:`sort`, :command:`unique`,
and :command:`while` - all of which share a common expression-evaluation
pipeline and output formatting layer.
"""

import click
import builtins
import re

from ptools.lib.flow.values import StreamValue, OutputValue
from ptools.lib.flow.runner import FlowRunner
from ptools.lib.flow.decorators import (
    output_flavor,
    debug_scope,
    flow_expression,
)
from ptools.lib.flow.utils import stream, create_global_scope, yield_scope

globals = create_global_scope()
Runner = FlowRunner(globals=globals)


@click.group()
def cli():
    """Pythonic FP-flavored workflow engine.

    \b
    Example:
      $ ptools flow range 1 4
      1
      2
      3
    """
    pass


@click.command()
def read():
    """Read from stdin and print the StreamValue representation.


    Example::
      $ printf '{"a": 1}\\n' | ptools flow read
      {'a': 1} (type: AttributeDict)
    """
    for flow_value in stream():
        click.echo(f"{flow_value} (type: {type(flow_value.value).__name__})")


@click.command()
@click.option(
    "--multiline",
    "-m",
    is_flag=True,
    default=False,
    help="Read all lines as a single JSON array.",
)
@output_flavor.decorate()
def json(flavor, multiline):
    """Read JSON objects.

    \b
    Example:
      $ printf '{"a":1}\\n{"a":2}\\n' | ptools flow json --flavor json
      [
        {
          "a": 1
        },
        {
          "a": 2
        }
      ]
    """
    import json
    import sys

    if multiline:
        results = json.load(sys.stdin)
    else:
        results = [json.loads(line) for line in sys.stdin if line.strip()]
    click.echo(f"{OutputValue(flavor=flavor).format(results)}")


@click.command()
@click.option(
    "--multiline",
    "-m",
    is_flag=True,
    default=False,
    help="Read all lines as a single JSON array.",
)
@output_flavor.decorate()
def _dict(flavor, multiline):
    """Read Python dictionaries.

    \b
    Example:
      $ printf "{'a': 1}\\n{'a': 2}\\n" | ptools flow dict --flavor json
      [
        {
          "a": 1
        },
        {
          "a": 2
        }
      ]
    """
    import sys

    if multiline:
        results = eval(sys.stdin.read())
    else:
        results = [eval(line) for line in sys.stdin if line.strip()]
    click.echo(f"{OutputValue(flavor=flavor).format(results)}")


@click.command()
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
def collect(expression, flavor, debug):
    """Apply a Python expression to each streamed input line.

    \b
    Example:
      $ printf '1\\n2\\n3\\n' | ptools flow collect 'x * 2'
      2
      4
      6
    """
    output = OutputValue(flavor=flavor)
    results = []
    for result, _ in Runner.run(expression, debug=debug):
        results.append(result)
    click.echo(output.format(results))


@click.command()
@click.argument("start", type=int)
@click.argument("end", type=int)
@click.argument("step", type=int, default=1, required=False)
@output_flavor.decorate()
def frange(start, end, step, flavor):
    """Generate a range of numbers from start to end-1.

    \b
    Example:
      $ ptools flow range 1 5
      1
      2
      3
      4
    """
    output = OutputValue(flavor=flavor)
    result = list(range(start, end, step))
    click.echo(output.format(result))


@click.command()
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
def filter(expression, flavor, debug):
    """Filter streamed input lines based on a Python expression.

    \b
    Example:
      $ printf '1\\n2\\n3\\n4\\n' | ptools flow filter 'x % 2 == 0'
      2
      4
    """
    output = OutputValue(flavor=flavor)
    results = []
    for result, fv in Runner.run(expression, debug=debug):
        if result:
            results.append(fv.value)
    click.echo(output.format(results))


@click.command()
@flow_expression.decorate()
@click.option(
    "--accumulator", "-a", default=None, help="Initial value for the accumulator."
)
@debug_scope.decorate()
@output_flavor.decorate()
def reduce(expression, accumulator, flavor, debug):
    """Reduce streamed input lines based on a Python expression.
    [T, U](acc: T | None, x: U) -> Any

    \b
    Example:
      $ printf '1\\n2\\n3\\n' | ptools flow reduce 'acc + x' --accumulator 0
      6
    """
    accumulator = StreamValue(accumulator).value if accumulator is not None else None
    output = OutputValue(flavor=flavor)

    for flow_value in stream():
        try:
            for scope in yield_scope(flow_value):
                scope = {**scope, "acc": accumulator}
                if debug:
                    import sys
                    from ptools.utils.print import fdebug

                    sys.stderr.write(
                        fdebug(
                            "Runtime Debug Info",
                            expression=expression,
                            local_scope=scope,
                        )
                        + "\n",
                    )
                accumulator = eval(expression, globals, scope)
        except Exception as e:
            import sys

            sys.stderr.write(f"Error: {e}\n")

    click.echo(f"{output.format(accumulator)}")


@click.command()
@flow_expression.decorate()
@output_flavor.decorate()
def exec(expression, flavor):
    """Execute a Python expression with access to the global scope.

    \b
    Example:
      $ ptools flow exec 'sum(range(4))'
      6
    """
    try:
        result = eval(expression, globals)
        click.echo(f"{OutputValue(flavor=flavor).format(result)}")
    except Exception as e:
        click.echo(f"Error: {e}")


@click.command()
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
def unique(expression, flavor, debug):
    """Yield unique items from the stream based on a Python expression.

    \b
    Example:
      $ printf '1\\n1\\n2\\n' | ptools flow unique 'x'
      1
      2
    """
    seen = set()
    output = OutputValue(flavor=flavor)
    results = []

    for result, fv in Runner.run(expression, debug=debug):
        key = result
        if key not in seen:
            seen.add(key)
            results.append(fv.value)

    click.echo(output.format(results))


@click.command()
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
@click.option(
    "--compare",
    type=click.Choice(["abc", "123"]),
    default=None,
    help='The comparison method to use for sorting (e.g., "abc" for alphabetical, "123" for numerical).',
)
@click.option(
    "--order",
    type=click.Choice(["asc", "desc"]),
    default="asc",
    help="The sort order (ascending or descending).",
)
def sort(expression, flavor, debug, compare, order):
    """Sort items from the stream based on a Python expression.

    \b
    Example:
      $ printf '3\\n1\\n2\\n' | ptools flow sort 'x' --compare 123
      1
      2
      3
    """
    output = OutputValue(flavor=flavor)
    values = []

    sort_fn = lambda x: x[0]
    match compare:
        case "abc":
            sort_fn = lambda x: str(x[0])
        case "123":
            sort_fn = lambda x: float(x[0])

    for result, fv in Runner.run(expression, debug=debug):
        values.append((result, fv.value))

    values.sort(key=sort_fn, reverse=(order == "desc"))
    results = [fv for _, fv in values]

    click.echo(output.format(results))


@click.command()
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
def group(expression, flavor, debug):
    """Group items from the stream based on a Python expression.

    \b
    Example:
      $ printf '1\\n2\\n3\\n4\\n' | ptools flow group 'x % 2' --flavor json
      {
        "1": [
          1,
          3
        ],
        "0": [
          2,
          4
        ]
      }
    """
    from collections import defaultdict

    groups = defaultdict(list)

    for result, fv in Runner.run(expression, debug=debug):
        key = result
        groups[key].append(fv.value)

    click.echo(OutputValue(flavor=flavor).format(builtins.dict(groups)))


@click.command()
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
def foreach(expression, flavor, debug):
    """Foreach loop over items generated from each streamed input line.

    \b
    Example:
      $ printf '1\\n2\\n3\\n' | ptools flow foreach 'x * 10'
      10
      20
      30
    """
    output = OutputValue(flavor=flavor)

    for result, _ in Runner.run(expression, debug=debug):
        if (
            result is not None
            and not (isinstance(result, list) and len(result) == 0)
            and not (isinstance(result, str) and result.strip() == "")
        ):
            click.echo(f"{output.format(result)}")


@click.command()
@flow_expression.decorate()
@click.option("--initial", "-i", default=None, help="Initial value for the x variable.")
@click.option(
    "--condition", "-c", default="True", help="Loop condition as a Python expression."
)
@click.option(
    "--update-on-none",
    is_flag=True,
    default=False,
    help="Continue updating x even if the expression returns None.",
)
@click.option(
    "--output-last/--output-all",
    is_flag=True,
    default=True,
    help="Output only the final result after the loop ends.",
)
@output_flavor.decorate()
@debug_scope.decorate()
def while_loop(
    expression, initial, condition, update_on_none, flavor, debug, output_last
):
    """While loop executing a Python expression as long as the condition is true.

    \b
    Example:
      $ ptools flow while 'x + 1' --initial 0 --condition 'x < 3'
      3
    """
    output = OutputValue(flavor=flavor)

    for result, _, is_last in Runner.run_while(
        expression,
        initial=initial,
        condition=condition,
        update_on_none=update_on_none,
        debug=debug,
    ):
        if not output_last or is_last:
            click.echo(f"{output.format(result)}")


@click.command()
@click.argument("keys", type=str, required=True, nargs=1, metavar="KEYS")
@click.option(
    "--glob",
    "-g",
    is_flag=True,
    default=False,
    help="Enable wildcard (*) expansion in paths.",
)
@flow_expression.decorate()
@debug_scope.decorate()
@output_flavor.decorate()
def patch(keys, glob, expression, flavor, debug):
    """Patch values at dot/bracket paths in each streamed dict.

    KEYS is a comma-separated list of paths (e.g. "a.b,c[0]").
    The expression receives `x` (value at path), `k` (key), `m` (match string), and `obj` (root).

    With --glob, paths can contain `*` to iterate over dict keys or list indices.

    \b
    Example:
      $ printf '{"a": {"b": 1}, "c": [10]}\\n' | ptools flow patch 'a.b,c[0]' 'x + 1'
      {"a": {"b": 2}, "c": [11]}

      $ printf '{"a": {"x": 1, "y": 2}}\\n' | ptools flow patch -g 'a.*' 'x + 10'
      {"a": {"x": 11, "y": 12}}
    """
    import re

    output = OutputValue(flavor=flavor)
    raw_paths = [p.strip() for p in keys.split(",")]

    # Track segments per yield so we can recover them after Runner.run
    pending_segments = []

    def parse_segment(seg: str):
        indices = [int(i) for i in re.findall(r"\[(\d+)\]", seg)]
        name = re.sub(r"\[\d+\]", "", seg)
        return name, indices

    def resolve(obj, name, indices):
        target = getattr(obj, name, None) if not isinstance(obj, dict) else obj[name]
        for idx in indices:
            target = target[idx]
        return target

    def get_by_path(obj, segments):
        target = obj
        for name, indices in segments:
            target = resolve(target, name, indices)
        return target

    def set_by_path(obj, segments, value):
        parent = get_by_path(obj, segments[:-1]) if len(segments) > 1 else obj
        name, indices = segments[-1]

        if indices:
            container = (
                resolve(parent, name, indices[:-1])
                if len(indices) > 1
                else (
                    getattr(parent, name, None)
                    if not isinstance(parent, dict)
                    else parent[name]
                )
            )
            container[indices[-1]] = value
        elif isinstance(parent, dict):
            parent[name] = value
        else:
            setattr(parent, name, value)

    def expand_paths(obj, raw_path: str):
        parts = raw_path.split(".")

        if not glob or "*" not in parts:
            segments = [parse_segment(p) for p in parts]
            yield segments, parts[-1], raw_path
            return

        star_idx = parts.index("*")
        prefix = [parse_segment(p) for p in parts[:star_idx]]
        suffix = ".".join(parts[star_idx + 1 :])

        target = get_by_path(obj, prefix) if prefix else obj

        if isinstance(target, dict):
            items = list(target.keys())
        elif isinstance(target, (list, tuple)):
            items = list(range(len(target)))
        else:
            raise ValueError(f"Cannot glob over {type(target).__name__}")

        for item in items:
            if isinstance(target, dict):
                child_prefix = prefix + [(str(item), [])]
            else:
                if prefix:
                    last_name, last_indices = prefix[-1]
                    child_prefix = prefix[:-1] + [(last_name, last_indices + [item])]
                else:
                    child_prefix = [("", [item])]

            if suffix:
                # Recurse for nested globs like *.*
                child_obj = get_by_path(obj, child_prefix)
                if not isinstance(child_obj, (dict, list, tuple)):
                    continue  # skip scalars silently
                for segments, k, m in expand_paths(child_obj, suffix):
                    yield child_prefix + segments, k, raw_path
            else:
                yield child_prefix, item, raw_path

    def yield_patches(stream_value):
        obj = (
            stream_value.value
            if isinstance(stream_value, StreamValue)
            else stream_value
        )
        if not isinstance(obj, dict):
            raise ValueError(f"Expected dict, got {type(obj).__name__}")

        for raw_path in raw_paths:
            for segments, k, m in expand_paths(obj, raw_path):
                value = get_by_path(obj, segments)
                pending_segments.append(segments)
                yield {
                    "x": value,
                    "k": k,
                    "m": m,
                    "obj": obj,
                }

    seen_objects = []
    seg_idx = 0

    for result, flow_value in Runner.run(
        expression, debug=debug, yield_scope=yield_patches
    ):
        obj = flow_value.value
        segments = pending_segments[seg_idx]
        seg_idx += 1

        set_by_path(obj, segments, result)

        if obj not in seen_objects:
            seen_objects.append(obj)

    click.echo(
        output.format(seen_objects if len(seen_objects) != 1 else seen_objects[0])
    )


cli.add_command(read, name="read")
cli.add_command(collect, name="collect")
cli.add_command(frange, name="range")
cli.add_command(filter, name="filter")
cli.add_command(reduce, name="reduce")
cli.add_command(unique, name="unique")
cli.add_command(sort, name="sort")
cli.add_command(group, name="group")
cli.add_command(exec, name="exec")
cli.add_command(foreach, name="foreach")
cli.add_command(while_loop, name="while")
cli.add_command(json, name="json")
cli.add_command(_dict, name="dict")
cli.add_command(patch, name="patch")
