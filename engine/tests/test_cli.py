import pytest

from cartograph import main


def test_version_flag(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out.startswith("cartograph 0.1.0")
