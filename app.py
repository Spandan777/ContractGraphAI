import json
import pandas as pd
import streamlit as st
from src.contractgraph.pipeline import analyze_contract
from src.contractgraph.sample_data import SAMPLE_CONTRACT
from src.contractgraph.ablation import empty_results
st.set_page_config(page_title="ContractGraph AI",layout="wide")
st.title("ContractGraph AI")
st.caption("Retrieval-augmented cross-clause risk detection with dependency graphs and evidence traceability.")
st.warning("Research prototype only. Not legal advice. It does not determine enforceability.")
with st.sidebar:
    use_gemini=st.checkbox("Enable optional Gemini analysis",False)
    st.caption("Requires GEMINI_API_KEY. LLM output is treated as a hypothesis.")
uploaded=st.file_uploader("Upload a contract",type=["pdf","txt","md"])
if st.button("Load synthetic demo"): st.session_state["demo"]=SAMPLE_CONTRACT
source=uploaded or st.session_state.get("demo")
if source and st.button("Analyze contract",type="primary"):
    with st.spinner("Analyzing..."): st.session_state["result"]=analyze_contract(source,use_gemini)
r=st.session_state.get("result")
if r:
    if r["status"]!="success": st.error(r["validation"]); st.stop()
    a,b,c,d=st.columns(4)
    a.metric("Clauses",len(r["clauses"])); b.metric("Graph edges",len(r["graph_edges"]))
    c.metric("Rule candidates",len(r["verified_findings"]))
    d.metric("Traceable",sum(x["evidence_verified"] for x in r["verified_findings"]))
    tabs=st.tabs(["Overview","Clauses","Graph","Findings","Retrieval","Gemini","Evaluation"])
    with tabs[0]:
        st.write(r["validation"])
        st.info("Different values may be valid when scope, trigger or precedence differs.")
    with tabs[1]:
        st.dataframe(pd.DataFrame([{"ID":x["id"],"Title":x["title"],"Aspects":", ".join(x["aspects"]),"Text":x["text"]} for x in r["clauses"]]),use_container_width=True)
    with tabs[2]:
        st.dataframe(pd.DataFrame(r["graph_edges"]),use_container_width=True)
        st.caption("Potential-conflict edges identify pairs to compare. They do not establish legal conflict.")
    with tabs[3]:
        for f in r["verified_findings"]:
            with st.expander(f'{f["severity"].upper()} · {f["risk_type"]} · {", ".join(f["clauses"])}'):
                st.write(f["claim"]); st.write(f["rationale"])
                st.write("Source traceability:",f["evidence_verified"])
                st.write("Semantic support assessed:",f["semantic_support_assessed"])
                for cid,ev in zip(f["clauses"],f["evidence"]): st.markdown(f"**{cid}**"); st.code(ev)
    with tabs[4]:
        for k,hits in r["baseline_retrieval"].items():
            st.markdown("**"+k.title()+"**")
            st.dataframe(pd.DataFrame([{"ID":x["id"],"Score":round(x["score"],4),"Text":x["text"]} for x in hits]),use_container_width=True)
    with tabs[5]:
        g=r.get("gemini",{}); st.write("Status:",g.get("status"))
        if g.get("error"): st.warning(g["error"])
        for f in g.get("verified_findings",[]): st.write(f)
    with tabs[6]:
        st.dataframe(pd.DataFrame(empty_results()),use_container_width=True)
        st.warning("Metrics are intentionally blank until human-adjudicated gold annotations and experiments exist.")
    st.download_button("Download analysis JSON",json.dumps(r,indent=2),file_name="contractgraph_analysis.json")
else:
    st.info("Upload a PDF, TXT or Markdown file, or load the synthetic demonstration.")
