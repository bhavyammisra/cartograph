from cartograph.evaluate import evaluate, score_one, summarize
from cartograph.search import BM25, Doc, rrf, tokenize


def test_rrf_rewards_agreement():
    # 7 is 2nd in both lists, so it beats 1 and 9, which each top only one list.
    assert rrf([[1, 7, 3], [9, 7, 4]])[0] == 7
    # 1st + 3rd (1/61 + 1/63) still edges out 2nd + 2nd (2/62)
    assert rrf([[1, 7, 3], [9, 7, 1]])[0] == 1
    assert rrf([[5]]) == [5]

FILE_OF = {1: "a.js", 2: "a.js", 3: "b.js", 4: "c.js"}


def test_score_one():
    s = score_one([2, 3, 1], {3, 4}, FILE_OF)
    assert (s["acc@1"], s["acc@5"], s["mrr"], s["recall@10"]) == (0.0, 1.0, 0.5, 0.5)
    assert s["file_acc@5"] == 1.0
    miss = score_one([1, 2], {4}, FILE_OF)
    assert (miss["acc@10"], miss["mrr"], miss["file_acc@5"]) == (0.0, 0.0, 0.0)


def test_checkpoint_resumes_without_rerunning(tmp_path):
    docs = [Doc(1, "a.js", "f", ""), Doc(2, "b.js", "g", "")]
    qs = [{"id": i, "source": "hand", "type": "meaning", "question": "q",
           "gold": [{"path": "a.js", "qualname": "f"}]} for i in ("q1", "q2")]
    calls = []
    retriever = lambda q: calls.append(q) or [1]
    ckpt = tmp_path / "run.partial.jsonl"
    evaluate(qs[:1], docs, retriever, ckpt)  # "crash" after the first question
    rows = evaluate(qs, docs, retriever, ckpt)
    assert len(calls) == 2 and [r["id"] for r in rows] == ["q1", "q2"]
    assert all(r["acc@1"] == 1.0 for r in rows)


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
