from cartograph.evaluate import score_one, summarize
from cartograph.search import BM25, Doc, tokenize

FILE_OF = {1: "a.js", 2: "a.js", 3: "b.js", 4: "c.js"}


def test_score_one():
    s = score_one([2, 3, 1], {3, 4}, FILE_OF)
    assert (s["acc@1"], s["acc@5"], s["mrr"], s["recall@10"]) == (0.0, 1.0, 0.5, 0.5)
    assert s["file_acc@5"] == 1.0
    miss = score_one([1, 2], {4}, FILE_OF)
    assert (miss["acc@10"], miss["mrr"], miss["file_acc@5"]) == (0.0, 0.0, 0.0)


def test_summarize_latency_percentiles():
    rows = [{"acc@1": float(i % 2), "ms": float(i)} for i in range(1, 21)]
    s = summarize(rows)
    assert (s["n"], s["acc@1"], s["p50_ms"], s["p95_ms"]) == (20, 0.5, 11.0, 20.0)


def test_tokenize_splits_code_names():
    assert tokenize("getUserById parseHTTPHeader user_name the") == [
        "get", "user", "id", "parse", "http", "header", "user", "name"]


def test_bm25_ranks_matching_function_first():
    docs = [Doc(1, "a.js", "sendFile", "res.sendFile stream file to client"),
            Doc(2, "b.js", "cookie", "res.cookie set cookie header"),
            Doc(3, "c.js", "json", "res.json send json body")]
    assert BM25(docs)("how do I set a cookie?")[0] == 2
