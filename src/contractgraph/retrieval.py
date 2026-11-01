from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
def retrieve(query, clauses, k=5):
    if not clauses: return []
    try:
        m=TfidfVectorizer(stop_words="english",ngram_range=(1,2)).fit_transform(
            [query]+[c["text"] for c in clauses])
        scores=cosine_similarity(m[0:1],m[1:]).ravel()
    except ValueError: return []
    ranked=sorted(zip(clauses,scores),key=lambda x:float(x[1]),reverse=True)[:k]
    return [{**c,"score":float(s)} for c,s in ranked]
