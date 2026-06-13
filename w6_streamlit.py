"""
Workshop6 App1 - Streamlit UI for Apex Auto Insurance AgentCore Agent
"""

import streamlit as st
import boto3
import json
import uuid
import traceback

st.set_page_config(page_title="🚗 Apex Auto Insurance", page_icon="🚗", layout="centered")

"""
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-2:744079559870:runtime/w5app1projectname1_w5app1Agent1alKczI4xDy"
REGION      = "us-east-2"
Sample Format is shown above.
Make sure get the Runtime ID of your AgentCore Agent and paste it in place <Paste_Your_RuntimeID-of-your-AgentCoreAgent_Here> below. 
And fill in your Region and Account also
"""

RUNTIME_ARN = "arn:aws:bedrock-agentcore:<Paste_Your_Region>:<Paste_Your_AWS_Account>:runtime/<Paste_Your_RuntimeID-of-your-AgentCoreAgent_Here>"
REGION      = "<Paste_Your_Region>"

@st.cache_resource
def get_client():
    return boto3.client("bedrock-agentcore", region_name=REGION)


def parse_chunk(raw):
    text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    result = []
    for line in text.split("\n\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("data: "):
            line = line[6:].strip()
        try:
            line = json.loads(line)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        result.append(str(line))
    return "".join(result)


def call_agent(prompt: str, session_id: str) -> str:
    try:
        client = get_client()
        response = client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=json.dumps({"inputText": prompt}).encode("utf-8")
        )

        event_stream = response.get("response", response.get("outputStream"))
        if event_stream is None:
            return f"❌ No stream found. Response keys: {list(response.keys())}"

        collected = []
        for event in event_stream:
            if isinstance(event, (bytes, str)):
                collected.append(parse_chunk(event))
            elif isinstance(event, dict):
                for key in ("chunk", "ContentChunk"):
                    if key in event:
                        val = event[key].get("bytes", "")
                        if val:
                            collected.append(parse_chunk(val))
                if "internalServerException" in event:
                    return f"❌ AgentCore error: {event['internalServerException']}"
                elif "validationException" in event:
                    return f"❌ Validation error: {event['validationException']}"

        if not collected:
            return "⚠️ Agent returned an empty response."

        return "".join(collected).strip()

    except Exception as e:
        return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🚗 Apex Auto Insurance")
st.caption("Powered by AWS AgentCore · Ask me about quotes, claims, and coverage")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Hello! I'm Apex, your auto insurance assistant. I can help you with:\n\n"
            "- 💰 **Insurance quotes** for your vehicle\n"
            "- 📋 **Policy coverage** (liability, collision, comprehensive)\n"
            "- 🔧 **Filing and tracking claims**\n"
            "- 📄 **Policy renewals and cancellations**\n"
            "- 💡 **Understanding deductibles and premiums**\n\n"
            "What can I help you with today?"
        )
    })

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

with st.sidebar:
    st.header("💡 Try asking...")
    suggestions = [
        "Get me a quote for a 2022 Honda Civic",
        "What does comprehensive coverage include?",
        "What is collision coverage?",
        "How do I file a claim?",
        "How can I lower my premium?",
        "What is an insurance deductible?",
        "How do I renew my policy?",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state["suggestion"] = s
            st.rerun()

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.caption(f"Region: {REGION}")
    st.caption(f"Session: {st.session_state.session_id[:8]}...")

if "suggestion" in st.session_state:
    prompt = st.session_state.pop("suggestion")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Apex is thinking..."):
            response = call_agent(prompt, st.session_state.session_id)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

if prompt := st.chat_input("Ask about quotes, coverage, claims..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Apex is thinking..."):
            response = call_agent(prompt, st.session_state.session_id)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})