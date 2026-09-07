"""The default metadata alias remains portable in wheel-only installations."""
from gjb438c_suite import cli, render
from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.registry import default_front_matter_template


def test_legacy_builtin_alias_in_wheel(tmp_path, monkeypatch):
    monkeypatch.setattr(render, '__file__', str(tmp_path / 'installed/gjb438c_suite/render.py'))
    source = tmp_path / 'OCD.md'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    assert render.resolve_front_template(parse_markdown(source)) == default_front_matter_template().absolute()


def test_project_template_overrides_legacy_alias(tmp_path, monkeypatch):
    monkeypatch.setattr(render, '__file__', str(tmp_path / 'installed/gjb438c_suite/render.py'))
    custom = tmp_path / 'templates/front-matter/standard-front-matter.docx'
    custom.parent.mkdir(parents=True)
    custom.write_bytes(default_front_matter_template().read_bytes())
    source = tmp_path / 'OCD.md'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    assert render.resolve_front_template(parse_markdown(source)) == custom.absolute()
