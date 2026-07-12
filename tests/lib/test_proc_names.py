"""Tests for process display-name resolution."""

from ptools.lib.proc.names import resolve

no_labels = lambda path: None


def test_plain_process_keeps_its_name():
    result = resolve("kernel_task", "", [], label_resolver=no_labels)
    assert result["name"] == "kernel_task"
    assert result["bundle"] == ""
    assert result["kind"] == ""


def test_app_bundle_name_wins_over_truncated_comm():
    result = resolve(
        "Google Chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        [],
        label_resolver=no_labels,
    )
    assert result["name"] == "Google Chrome"
    assert result["bundle"] == "Google Chrome"
    assert result["kind"] == "app"


def test_nested_helper_uses_innermost_bundle_and_helper_kind():
    exe = (
        "/Applications/Google Chrome.app/Contents/Frameworks/"
        "Google Chrome Framework.framework/Versions/1/Helpers/"
        "Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)"
    )
    result = resolve("Google Chrome He", exe, [], label_resolver=no_labels)
    assert result["bundle"] == "Google Chrome Helper (Renderer)"
    assert result["kind"] == "helper"


def test_interpreter_shows_script_name():
    result = resolve(
        "python3", "/usr/local/bin/python3.12",
        ["python3", "manage.py", "runserver"],
        label_resolver=no_labels,
    )
    assert result["name"] == "python3.12 (manage.py)"


def test_interpreter_skips_flags_and_handles_dash_m():
    result = resolve(
        "python", "/usr/bin/python3",
        ["python3", "-u", "-m", "http.server"],
        label_resolver=no_labels,
    )
    assert result["name"] == "python3 (http.server)"


def test_java_jar():
    result = resolve(
        "java", "/usr/bin/java",
        ["java", "-Xmx2g", "-jar", "/opt/apps/server.jar"],
        label_resolver=no_labels,
    )
    assert result["name"] == "java (server.jar)"


def test_node_script():
    result = resolve(
        "node", "/opt/homebrew/bin/node",
        ["node", "/Users/me/project/node_modules/.bin/vite", "dev"],
        label_resolver=no_labels,
    )
    assert result["name"] == "node (vite)"


def test_interpreter_without_script_keeps_comm():
    result = resolve("node", "/opt/homebrew/bin/node", ["node"], label_resolver=no_labels)
    assert result["name"] == "node"


def test_inline_code_is_not_a_script():
    result = resolve("zsh", "/bin/zsh", ["/bin/zsh", "-c", "echo /some/path"], label_resolver=no_labels)
    assert result["name"] == "zsh"
    result = resolve("node", "/usr/bin/node", ["node", "-e", "console.log(1)"], label_resolver=no_labels)
    assert result["name"] == "node"


def test_user_label_beats_everything():
    result = resolve(
        "node", "/opt/homebrew/bin/node",
        ["node", "server.js"],
        label_resolver=lambda path: "My Dev Server",
    )
    assert result["name"] == "My Dev Server"
    assert result["label"] == "My Dev Server"


def test_label_resolver_errors_are_swallowed():
    def broken(path):
        raise RuntimeError("config unreadable")
    result = resolve("node", "/opt/homebrew/bin/node", ["node", "x.js"], label_resolver=broken)
    assert result["name"] == "node (x.js)"
