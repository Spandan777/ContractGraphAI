import os,json
def analyze_with_gemini(clauses):
    if not os.getenv("GEMINI_API_KEY"):
        return {"status":"not_configured","findings":[],"error":"GEMINI_API_KEY is not set."}
    try:
        from google import genai
        client=genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
        payload=[{"id":c["id"],"title":c["title"],"text":c["text"]} for c in clauses]
        prompt=("Find possible cross-clause inconsistencies, treating scope differences cautiously. "
          "Return JSON only: {\"findings\":[{\"risk_type\":\"...\",\"severity\":\"low|medium|high\","
          "\"clauses\":[\"C1\",\"C2\"],\"claim\":\"...\",\"rationale\":\"...\"}]}. "
          "Use only supplied IDs. Not legal advice.\\n"+json.dumps(payload))
        raw=client.models.generate_content(model=model,contents=prompt).text or ""
        i,j=raw.find("{"),raw.rfind("}")
        data=json.loads(raw[i:j+1]) if i>=0 and j>i else {}
        by={c["id"]:c for c in clauses}; accepted=[]
        for f in data.get("findings",[]):
            ids=f.get("clauses",[])
            if isinstance(ids,list) and len(ids)>=2 and len(ids)==len(set(ids)) and all(x in by for x in ids) and f.get("claim"):
                accepted.append({**f,"evidence":[by[x]["text"] for x in ids],"origin":"gemini_hypothesis"})
        return {"status":"success","model":model,"findings":accepted,"error":None}
    except Exception as e:
        return {"status":"error","findings":[],"error":f"{type(e).__name__}: {e}"}
