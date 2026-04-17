"""
Tests for the display module (config_tree, flat_table_rows, make_table,
as_table).
"""

from cfx import Config, Float, Int, String
from cfx.display import (
    as_table,
    config_tree,
    flat_table_rows,
    make_table,
)


# ---------------------------------------------------------------------------
# Test configs
#############################################################################

class FlatDisplay(Config):
    """A flat config for display tests."""
    confid = "flat"
    x = Float(1.0, "x value")
    y = Int(2, "y value")


class InnerDisplay(Config):
    """Inner node."""
    confid = "inner"
    val = Float(3.0, "inner value")


class OuterDisplay(Config, components=[InnerDisplay]):
    """Outer node."""
    confid = "outer"
    name = String("test", "outer name")


class MultilineDoc(Config):
    """First line.

    Second paragraph.
    Third line.
    """
    confid = "multiline"
    z = Float(0.0, "z value")


#############################################################################
# config_tree
#############################################################################

class TestConfigTree:
    def test_flat_shows_class_name(self):
        tree = config_tree(FlatDisplay())
        assert "FlatDisplay" in tree

    def test_flat_shows_docstring(self):
        tree = config_tree(FlatDisplay())
        assert "flat config for display tests" in tree

    def test_nested_uses_box_drawing(self):
        tree = config_tree(OuterDisplay())
        assert "└─" in tree

    def test_nested_shows_both_classes(self):
        tree = config_tree(OuterDisplay())
        assert "OuterDisplay" in tree
        assert "InnerDisplay" in tree

    def test_multiline_docstring_preserved(self):
        tree = config_tree(MultilineDoc())
        assert "Second paragraph" in tree
        assert "Third line" in tree

    def test_no_class_returns_just_name(self):
        class NoDoc(Config):
            confid = "nodoc"
            f = Float(1.0, "f")
        tree = config_tree(NoDoc())
        assert "NoDoc" in tree
        assert ":" not in tree  # no colon when there's no docstring


#############################################################################
# flat_table_rows
#############################################################################

class TestFlatTableRows:
    def test_flat_row_count(self):
        rows = flat_table_rows(FlatDisplay())
        assert len(rows) == 2  # x and y

    def test_flat_row_structure(self):
        rows = flat_table_rows(FlatDisplay())
        assert all(len(r) == 4 for r in rows)  # (class, key, value, doc)

    def test_flat_row_class_name(self):
        rows = flat_table_rows(FlatDisplay())
        assert all(r[0] == "FlatDisplay" for r in rows)

    def test_flat_row_keys(self):
        rows = flat_table_rows(FlatDisplay())
        keys = {r[1] for r in rows}
        assert keys == {"x", "y"}

    def test_nested_includes_own_and_sub_fields(self):
        rows = flat_table_rows(OuterDisplay())
        keys = {r[1] for r in rows}
        assert "name" in keys
        assert "val" in keys

    def test_nested_row_class_names(self):
        rows = flat_table_rows(OuterDisplay())
        class_names = {r[0] for r in rows}
        assert "OuterDisplay" in class_names
        assert "InnerDisplay" in class_names


#############################################################################
# make_table — text mode
#############################################################################

class TestMakeTableText:
    def test_returns_string(self):
        rows = flat_table_rows(FlatDisplay())
        assert isinstance(make_table(rows, format="text"), str)

    def test_header_present(self):
        rows = flat_table_rows(FlatDisplay())
        text = make_table(rows, format="text")
        assert "Config" in text
        assert "Key" in text
        assert "Value" in text
        assert "Description" in text

    def test_separator_line_present(self):
        rows = flat_table_rows(FlatDisplay())
        text = make_table(rows, format="text")
        assert "-+-" in text

    def test_field_key_in_output(self):
        rows = flat_table_rows(FlatDisplay())
        text = make_table(rows, format="text")
        assert "x" in text
        assert "y" in text


#############################################################################
# make_table — html mode
#############################################################################

class TestMakeTableHtml:
    def test_returns_string(self):
        rows = flat_table_rows(FlatDisplay())
        assert isinstance(make_table(rows, format="html"), str)

    def test_has_table_tag(self):
        rows = flat_table_rows(FlatDisplay())
        html = make_table(rows, format="html")
        assert "<table>" in html
        assert "</table>" in html

    def test_has_header_cells(self):
        rows = flat_table_rows(FlatDisplay())
        html = make_table(rows, format="html")
        assert "<th>" in html

    def test_has_data_cells(self):
        rows = flat_table_rows(FlatDisplay())
        html = make_table(rows, format="html")
        assert "<td>" in html

    def test_table_attrs_applied(self):
        rows = flat_table_rows(FlatDisplay())
        html = make_table(rows, format="html",
                          table_attrs={"class": "cfg", "id": "tbl"})
        assert 'class="cfg"' in html
        assert 'id="tbl"' in html
        assert "<table" in html

    def test_table_attrs_none_gives_plain_table_tag(self):
        rows = flat_table_rows(FlatDisplay())
        html = make_table(rows, format="html")
        assert "<table>" in html


#############################################################################
# as_table
#############################################################################

class TestAsTable:
    def test_text_contains_tree_and_table(self):
        text = as_table(FlatDisplay())
        assert "FlatDisplay" in text
        assert "Config" in text

    def test_html_starts_with_pre(self):
        html = as_table(FlatDisplay(), format="html")
        assert html.startswith("<pre>")

    def test_html_contains_table(self):
        html = as_table(FlatDisplay(), format="html")
        assert "<table>" in html

    def test_html_table_attrs_propagated(self):
        html = as_table(FlatDisplay(), format="html",
                        table_attrs={"class": "my-cfg"})
        assert 'class="my-cfg"' in html
