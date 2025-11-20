import click

import os
import pathlib

from ptools.utils.print import FormatUtils
from ptools.utils.config import ConfigFile
from ptools.utils.decorator_compistor import DecoratorCompositor

from pydantic import BaseModel, model_validator
from itertools import groupby
from jinja2 import Template, Environment, meta

config = ConfigFile('touch', quiet=True, format="yaml")

@click.group(name='touch')
def cli():
    """UNIX touch powered with Jinja2 templates"""
    pass

class FileNameOptions(BaseModel):
    dir_okay: bool = False
    file_arg: str = None
    extension: str = ".txt"
    allow_empty_extension: bool = False
    allow_arbitrary_extension: bool = True

    @model_validator(mode='before')
    def validate(cls, values):
        dir_okay = values.get('dir_okay', False)
        file_okay = values.get('file_okay', True)
        file_arg = values.get('file_arg', None)

        if dir_okay and not file_okay and not file_arg:
            raise ValueError("file_arg must be provided when dir_okay is True and file_okay is False")

        if file_arg is None:
            file_arg = "{dir}/output.txt"

        values['file_arg'] = file_arg
        return values

class TouchItem(BaseModel):
    command: str
    commands: list = []
    group: str = "default"
    description: str
    template: Template = None
    template_string: str
    arguments: dict = {}
    file_name_options: FileNameOptions = FileNameOptions()

    model_config = {
        'arbitrary_types_allowed': True
    }

    def __init__(self, **data):
        data['file_name_options'] = FileNameOptions(**data.get('file_name_options', {}))
        super().__init__(**data)

    def model_post_init(self, context):
        super().model_post_init(context)

        env = Environment()
        parsed_content = env.parse(self.template_string)
        undeclared_variables = meta.find_undeclared_variables(parsed_content)

        self.arguments = {**{arg: "<value>" for arg in undeclared_variables}, **self.arguments}
        self.template = Template(self.template_string)


values = sorted(config.get('values', []), key=lambda x: x.get('group', 'default'))

def set_extension(filepath: pathlib.Path, opts: FileNameOptions):
    filename = filepath.name
    has_extension = filepath.suffix != ''
    has_the_required_extension = filename.endswith(opts.extension)

    if not opts.allow_empty_extension and not has_extension:
        filename += opts.extension
    elif not opts.allow_arbitrary_extension and not has_the_required_extension:
        filename = filename[:-len(opts.extension)] + opts.extension

    return filepath.with_name(filename)

for item in values:
  obj = TouchItem(**item)
  fopts = obj.file_name_options

  arguments = DecoratorCompositor.from_list([
    click.option(
      '--{}'.format(arg_name),
      type=str,
      required=False,
      help=f"{arg_help}"
    )
    for arg_name, arg_help in obj.arguments.items()
  ])

  @cli.command(name=obj.command, help=obj.description)
  @click.argument('output', type=click.Path(exists=False, file_okay=True, dir_okay=fopts.dir_okay), required=True)
  @arguments.decorate()
  def touch_command(output, **kwargs):
      args = {k: v for k, v in kwargs.items() if v is not None}
      output = pathlib.Path(output)

      # Can we use dirs?
      if output.is_dir() and not fopts.dir_okay:
          raise click.BadParameter(
            f"The output path '{output}' is a directory, but dir_okay in the command configurator is set to False."
        )

      # After this, filename is guaranteed to be a file
      if output.is_dir():
        filename = args.get(fopts.file_arg, "output.txt")
        output = output / filename

      # Set extension rules
      final_output = set_extension(output, fopts)
      final_output.parent.mkdir(parents=True, exist_ok=True)
      args['file_stem'] = final_output.stem
      args['file_suffix'] = final_output.suffix
      args['file_path'] = str(final_output)
      args['file_name'] = final_output.name

      try:
          rendered_content = obj.template.render(**args)
          with open(final_output, 'w') as f:
              f.write(rendered_content)
          FormatUtils.success(f"File '{final_output}' has been created/updated successfully.")
      except Exception as e:
          FormatUtils.error(f"An error occurred while creating/updating the file '{final_output}': {e}")
