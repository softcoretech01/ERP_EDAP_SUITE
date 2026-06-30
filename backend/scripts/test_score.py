def test_score():
    words = "how many purchase orders were created this month".split()
    extended_words = set(words)
    for w in words:
        if w.endswith('s') and len(w) > 3:
            extended_words.add(w[:-1])
    
    tables = [
        "tbl_purchaseorder_detail",
        "tbl_purchaseorder_header",
        "tbl_purchasememo_header",
        "tbl_purchaserequisition_header"
    ]
    
    for t in tables:
        score = 0
        for w in extended_words:
            if w in t:
                score += 1
        print(f"{t}: {score}")

test_score()
