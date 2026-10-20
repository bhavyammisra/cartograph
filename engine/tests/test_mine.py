import subprocess

from cartograph.mine import LINKED_ISSUE, SKIP_SUBJECT, changed_functions


def test_filters():
    assert SKIP_SUBJECT.match("docs: fix typo (#7512)")
    assert SKIP_SUBJECT.match("Upgrade `content-disposition` (#7233)")
    assert not SKIP_SUBJECT.match("fix(res.send): preserve ETag (#7459)")
    assert LINKED_ISSUE.findall("This fixes #12 and closes https://github.com/a/b/issues/34") == [
        "12", "34"]


def test_changed_functions(tmp_path):
    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    run("init", "-q")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    (tmp_path / "lib").mkdir()
    f = tmp_path / "lib" / "a.js"
    f.write_text("function keep() {\n  return 1;\n}\n\nres.send = function send(b) {\n"
                 "  return b;\n};\n")
    run("add", ".")
    run("commit", "-qm", "one")
    f.write_text(f.read_text().replace("return b;", "return String(b);"))
    run("commit", "-qam", "two")
    sha = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True,
                         capture_output=True,
                         text=True).stdout.strip()
    assert changed_functions(tmp_path, sha, "lib/") == {("lib/a.js", "res.send")}
