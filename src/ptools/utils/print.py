import os
from typing import Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel
import humanize
from typing import List

from ptools.utils.files import KnownExtensions

PTOOLS_DEFAULT_BRACKET_CHAR = os.environ.get('BRACKET_CHAR', '[]')
PTOOLS_DEFAULT_FILL_CHAR = os.environ.get('FILL_CHAR', '█')
PTOOLS_DEFAULT_EMPTY_CHAR = os.environ.get('EMPTY_CHAR', '-')

@dataclass
class ASCIIEscapes:
    BLACK: str = "\033[30m"
    RED: str = "\033[91m"
    GREEN: str = "\033[92m"
    YELLOW: str = "\033[93m"
    BLUE: str = "\033[94m"
    MAGENTA: str = "\033[95m"
    CYAN: str = "\033[96m"

    BG_BLACK: str = "\033[40m"
    BG_RED: str = "\033[41m"
    BG_GREEN: str = "\033[42m"
    BG_YELLOW: str = "\033[43m"
    BG_BLUE: str = "\033[44m"
    BG_MAGENTA: str = "\033[45m"
    BG_CYAN: str = "\033[46m"


    BOLD: str = "\033[1m"
    ITALIC: str = "\033[3m"

    RESET: str = "\033[0m"

    @staticmethod
    def wrap(text: str, code: str) -> str:
        lines = text.splitlines()
        wrapped_lines = [f"{code}{line}{ASCIIEscapes.RESET}" for line in lines]
        return "\n".join(wrapped_lines)

    @staticmethod
    def color(text: str, color: str = 'yellow') -> str:
        color_code = getattr(ASCIIEscapes, color.upper(), ASCIIEscapes.YELLOW)
        return ASCIIEscapes.wrap(text, color_code)

    @staticmethod
    def background(text: str, color: str = 'yellow') -> str:
        color_code = getattr(ASCIIEscapes, f"BG_{color.upper()}", ASCIIEscapes.BG_YELLOW)
        return ASCIIEscapes.wrap(text, color_code)

    @staticmethod
    def bold(text: str) -> str:
        return ASCIIEscapes.wrap(text, ASCIIEscapes.BOLD)

    @staticmethod
    def italic(text: str) -> str:
        return ASCIIEscapes.wrap(text, ASCIIEscapes.ITALIC)

    @staticmethod
    def style(
        text: str,
        color: Optional[str] = None,
        background: Optional[str] = None,
        bold: bool = False,
        italic: bool = False
    ) -> str:
        code = ""
        if color:
            code += getattr(ASCIIEscapes, color.upper(), ASCIIEscapes.YELLOW)
        if background:
            code += getattr(ASCIIEscapes, f"BG_{background.upper()}", ASCIIEscapes.BG_YELLOW)
        if bold:
            code += ASCIIEscapes.BOLD
        if italic:
            code += ASCIIEscapes.ITALIC
        return ASCIIEscapes.wrap(text, code)

class FormatUtils:
    @staticmethod
    def error(*args):
        msg = " ".join(args)
        return f"{ASCIIEscapes.color(' ERROR ', 'red')}{msg}"

    @staticmethod
    def info(*args):
        msg = " ".join(args)
        return f"{ASCIIEscapes.color(' INFO ', 'cyan')}{msg}"

    @staticmethod
    def success(*args):
        msg = " ".join(args)
        return f"{ASCIIEscapes.color(' SUCCESS ', 'green')}{msg}"

    @staticmethod
    def warning(*args):
        msg = " ".join(args)
        return f"{ASCIIEscapes.color(' WARNING ', 'yellow')}{msg}"

    @staticmethod
    def highlight(text: str, color: str = 'yellow') -> str:
        return ASCIIEscapes.color(text, color)

    @staticmethod
    def background(text: str, color: str = 'yellow') -> str:
        return ASCIIEscapes.background(text, color)

    @staticmethod
    def bold(text: str) -> str:
        return ASCIIEscapes.bold(text)

    @staticmethod
    def italic(text: str) -> str:
        return ASCIIEscapes.italic(text)

class PrintUtils:
    def __init__(self):
        pass

    @staticmethod
    def error(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.error(msg), **kwargs)

    @staticmethod
    def info(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.info(msg), **kwargs)

    @staticmethod
    def success(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.success(msg), **kwargs)

    @staticmethod
    def warning(*args, **kwargs):
        msg = " ".join(args)
        print(FormatUtils.warning(msg), **kwargs)


class ProgressBarOptions(BaseModel):
    length: int = 20
    fill_char: str = PTOOLS_DEFAULT_FILL_CHAR
    empty_char: str = PTOOLS_DEFAULT_EMPTY_CHAR
    bracket_char: str = PTOOLS_DEFAULT_BRACKET_CHAR
    show_percentage: bool = False

    @classmethod
    def model_validate(cls, values):
        fill_char = values.get('fill_char')
        empty_char = values.get('empty_char')
        if len(fill_char) != 1 or len(empty_char) != 1:
            raise ValueError("fill_char and empty_char must be single characters")

        bracket_char = values.get('bracket_char')
        if len(bracket_char) != 2:
            raise ValueError("bracket_char must be 2 characters")

        return values

class FormattedText:
    @staticmethod
    def progress(i: int, total: int):
        return f"[{i}/{total}]"

    @staticmethod
    def percent(i: int, total: int):
        return f"[{(i/total)*100:.2f}%]"

    @staticmethod
    def progress_bar(
        i: int,
        total: int,
        opts: ProgressBarOptions = ProgressBarOptions()
    ) -> str:
        length, fill_char, empty_char, bracket_char = \
            opts.length, opts.fill_char, opts.empty_char, opts.bracket_char

        filled_length = int(length * i // total)
        bar = fill_char * filled_length + empty_char * (length - filled_length)
        total_str = f" {i}/{total}" if not opts.show_percentage else f" {(i/total)*100:.2f}%"
        return f"{bracket_char[0]}{bar}{bracket_char[1]} {total_str}"

class Pipes:
        BRANCH = '├──'
        VERTICAL = '│'
        END = '└──'
        SPACE = '    '

class TreeText:
    class TreeNode:
        def __init__(self, name: str, children: Optional[list['TreeText.TreeNode']] = None):
            self.name = name
            self.children = children or []

        def add_child(self, child: 'TreeText.TreeNode'):
            self.children.append(child)


    class FileTreeNode(TreeNode):
        _name = ""
        size = 0

        def __init__(
            self,
            name: str,
            is_directory: bool,
            is_symlink: bool,
            is_expanded: bool = True,
            size: int = 0
        ):
            self._name = name
            self.children = []
            self.is_directory = is_directory
            self.is_symlink = is_symlink
            self.is_expanded = is_expanded
            self.size = size

        def add_child(
            self,
            child: 'TreeText.FileTreeNode',
        ):
            self.children.append(child)

        @property
        def name(self):
            extension = os.path.splitext(self._name)[1] if not self.is_directory else None
            icon = KnownExtensions.get_icon(
                extension,
                is_dir=self.is_directory,
                is_symlink=self.is_symlink,
                has_children=len(self.children) > 0
            )

            res = f"{icon} {self._name}"
            if self.size > 1024:
                res += f" ({ASCIIEscapes.style(humanize.naturalsize(self.size), color='green')})"
            return res

    class PipeBuilder:
        @staticmethod
        def tree_to_pipes(
            node: 'TreeText.TreeNode',
            prefix: str = '',
            is_first: bool = True,
            is_last: bool = True,
            pipes = Pipes
        ) -> list[str]:
            lines = []
            if not is_first:
                connector = pipes.END if is_last else pipes.BRANCH
                lines.append(f"{prefix}{connector} {node.name}")
                new_prefix = prefix + (pipes.SPACE if is_last else pipes.VERTICAL + '   ')
            else:
                lines.append(node.name)
                new_prefix = ''
            for i, child in enumerate(node.children):
                is_child_last = (i == len(node.children) - 1)
                lines.extend(TreeText.PipeBuilder.tree_to_pipes(child, new_prefix, is_first=False, is_last=is_child_last))
            return lines

    @staticmethod
    def render_tree(root: 'TreeText.TreeNode', pipes = Pipes) -> str:
        lines = TreeText.PipeBuilder.tree_to_pipes(root, prefix='', is_first=True, is_last=False, pipes=pipes)
        return "\n".join(lines)

def fdebug(title, **kwargs):
    msg = "\n   ".join([
        FormatUtils.background("[DEBUG]", "yellow") + FormatUtils.bold(f" {title}"),
        *[f"- {FormatUtils.highlight(str(k), 'yellow')}={FormatUtils.highlight(repr(v), 'green')}" for k, v in kwargs.items()]
    ])
    return msg

if __name__ == "__main__":
    # Test logs
    print(FormatUtils.error("This is an error message"))
    print(FormatUtils.info("This is an info message"))
    print(FormatUtils.success("This is a success message"))
    print(FormatUtils.warning("This is a warning message"))

    # Test colors
    print(ASCIIEscapes.color("This is red text", "red"))
    print(ASCIIEscapes.color("This is yellow text", "yellow"))
    print(ASCIIEscapes.color("This is green text", "green"))
    print(ASCIIEscapes.color("This is blue text", "blue"))
    print(ASCIIEscapes.color("This is magenta text", "magenta"))
    print(ASCIIEscapes.color("This is cyan text", "cyan"))

    # Test background colors
    print(ASCIIEscapes.background("This has a red background", "red"))
    print(ASCIIEscapes.background("This has a green background", "green"))
    print(ASCIIEscapes.background("This has a yellow background", "yellow"))
    print(ASCIIEscapes.background("This has a blue background", "blue"))
    print(ASCIIEscapes.background("This has a magenta background", "magenta"))
    print(ASCIIEscapes.background("This has a cyan background", "cyan"))

    # Test bold and italic
    print(ASCIIEscapes.bold("This is bold text"))
    print(ASCIIEscapes.italic("This is italic text"))

    # Test combined styles
    print(ASCIIEscapes.style("This is bold red text on yellow background", color="red", background="yellow", bold=True))
    print(ASCIIEscapes.style("This is italic cyan text", color="cyan", italic=True))
    print(ASCIIEscapes.style("This is bold magenta text", color="magenta", bold=True))

    # Test multiple lines
    multi_line_text = "This is line 1 of 3 green bold text\nThis is line 2\nThis is line 3"
    print(ASCIIEscapes.style(multi_line_text, color="green", bold=True, background="red", italic=True))

    # Test formatted text
    print(FormattedText.progress(3, 10))
    print(FormattedText.percent(3, 10))
    print(FormattedText.progress_bar(3, 10))

    # Test tree rendering
    root = TreeText.TreeNode("root", [
        TreeText.TreeNode("child1"),
        TreeText.TreeNode("child2", [
            TreeText.TreeNode("grandchild1"),
            TreeText.TreeNode("grandchild2"),
        ]),
        TreeText.TreeNode("child3")
    ])
    print(TreeText.render_tree(root))

    # Test simple tree
    simple_root = TreeText.TreeNode("root", [
        TreeText.TreeNode("child1"),
        TreeText.TreeNode("child2"),
        TreeText.TreeNode("child3")
    ])
    print(TreeText.render_tree(simple_root))

    # Custom tree node with lambda name
    class CustomNode(TreeText.TreeNode):
        icons = {
            'file': '📄',
            'directory_closed': '📁',
            'directory': '📂',
        }
        def __init__(
            self,
            data: List[str],
            children: Optional[list['TreeText.TreeNode']] = None
        ):
            name, kind = data
            match (kind, len(children) if children else 0):
                case ('file', _):
                    icon = self.icons['file']
                case ('directory', 0):
                    icon = self.icons['directory_closed']
                case ('directory', _):
                    icon = self.icons['directory']
                case _:
                    icon = '?'

            super().__init__(f"{icon} {name}", children)

    custom_root = CustomNode(['root', 'directory'], [
        CustomNode(['child.txt', 'file']),
        CustomNode(['child_dir', 'directory'], [
            CustomNode(['grandchild.txt', 'file']),
            CustomNode(['grandchild_dir', 'directory'])
        ])
    ])
    print(TreeText.render_tree(custom_root))

    # Test progress bar with \r
    import time
    total = 10
    for i in range(total + 1):
        print(f"\r{FormattedText.progress_bar(i, total, ProgressBarOptions(show_percentage=True))}", end="")
        time.sleep(0.1)
    print()