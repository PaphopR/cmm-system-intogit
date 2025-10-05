from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=True)
import os

import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from tools1 import objectdetection, datacollection

memory = InMemorySaver()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro",temperature=0)
#llm = ChatOpenAI(model="gpt-4.1", temperature=0)
#llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp",temperature=0)

steel_detect_count_agent = create_react_agent(
    model=llm,
    tools=[objectdetection],
    name="steel_detect_count_agent",
    prompt="""

        You are an expert in object detection, specialized in detecting and counting steel hollow sections from the image that the user provides.

        Your primary responsibility is to detect the cross-section (end-face) of Square Hollow Sections (SHS) and Rectangular Hollow Sections (RHS) 
        in the given image, count how many distinct sections appear, and return that count accurately.

        Once the number of sections is detected, this result should be passed into the 'quantity' field in the 'datacollection()' function 
        for material tracking and documentation purposes.

        **Important Guidelines:**
            1. If the user provides only an image without any information related to tracking and recording material flows across the three main construction processes ('Hauling', 'Stock', 'Usage'), you have to request the information from the user provides it **after object detection is complete**.
            2. Always operate in a **step-by-step** manner
            3. You must support user input in both **Thai and English languages**, and normalize them to standard values for internal processing.
            4. You have to **never perform tasks beyond your defined responsibility**. 
               If a user query involves tasks outside your work, you must **delegate or pass control to the appropriate agent responsible for that task**.
            5. Your task is not to assume or generate information beyond the scope unless clearly provided by the user.
    
    """
)

data_collection_agent = create_react_agent(
    model=llm,
    tools=[datacollection],
    name="data_collection_agent",
    prompt="""
    
        You are a specialized expert in tracking and recording material flows across the three main construction processes: Hauling, Stock, and Usage.

        Your primary responsibility is to receive dynamic user inputs (queries), analyze them, and accurately allocate the relevant information into the appropriate database fields 
        and then return the results to the user by using this agent tools function.
    
        **Important Guidelines:**
            1. You must operate in a **step-by-step** manner, ensuring clear reasoning and structured handling of the data.
            2. User input may be in either **Thai or English**, so your system must support both languages effectively.
            3. Handle various datetime formats, units, and mixed-language phrasing commonly found in construction log inputs.
            4. Your focus is on **data extraction and classification**, not general conversation. Maintain clarity and accuracy in transforming input into structured records.
            5. You have to **never perform tasks beyond your defined responsibility**. 
               If a user query involves tasks outside your work, you must **delegate or pass control to the appropriate agent responsible for that task**.
            6. Your task is not to assume or generate information beyond the scope unless clearly provided by the user.

    """
)

workflow = create_supervisor(
    [data_collection_agent,steel_detect_count_agent],
    model = llm,
    prompt = """
    
        You are the best supervisor who manage the 'steel_detect_count_agent' and 'data_collection_agent'.
        
        For detecting and counting steel hollow sections from the image that the user provides problems, 
    Use 'steel_detect_count_agent'
            - If the input involves an 'image file' or 'image path', it should be sent to this agent. 
            You have to **never perform tasks beyond your defined responsibility**.
        
        For record or collect data problems AND show the output that recorded, Use 'data_collection_agent'.
            - If the input is 'user query or input describing 3 processes records', it should be sent to this agent.
            - WHATEVER SITUATION, If the data is successfully recorded, you always HAVE TO display the recorded result in the following friendly and structured format:
                
                "
                ### Data Recorded Successfully\n
                Datetime: {{datetime}}\n
                Process Type: {{process}}\n
                Material Flow: {{flow}}\n  
                Steel Family: {{family}}\n 
                Dimension: {{dimension}}\n
                Length: {{length}}\n
                Quantity: {{quantity}} ea\n
                Roof Element: {{element}}\n
                Description: {{description}}\n
                "

                Keep the emojis and layout to improve readability. You may explain or interact with the user in a friendly way in Thai or English, 
            but do not omit this exact format when displaying recorded results.
            You have to **never perform tasks beyond your defined responsibility**.
    
        **Important Guidelines:**
            1. You must operate in a **step-by-step** manner, ensuring clear reasoning and structured handling of the data.
            2. User input may be in either **Thai or English**, so your system must support both languages effectively.
        
    """,
    output_mode="full_history",
).compile(
    checkpointer=memory,
)

config = {"configurable": {"thread_id": "1"}}

# UI setup
st.set_page_config(
    page_title="CMM System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select a page",
        options=["Chat", "Data Visualization"],
        index=0,
        horizontal=True,
    )

if page == "Chat":
    st.markdown(
        "<h1 style='text-align: center;'>🧠 Construction Material Management System</h1>",
        unsafe_allow_html=True
        )
    with st.container(border=True):
        st.markdown(
        "<h4 style='text-align: center;'>LLM Supervisor Agent Assistant for Construction Materials Tracking and Data Collection</h4>",
        unsafe_allow_html=True
        )
        st.markdown(
        "<h6 style='text-align: center;'>In part of Steel Hollow Section (SHS) and Rectangular Hollow Section (RHS)</h6>",
        unsafe_allow_html=True
        )


    # Helper function to get response
    def get_response(messages):
        with st.spinner("Thinking...", show_time=True, _cache=True):
            response = workflow.invoke({"messages": messages},config=config)
            return response

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Render existing messages
    for msg in st.session_state.messages:
        if isinstance(msg, AIMessage):
            st.chat_message("assistant",avatar="🧠").info(msg.content)
        elif isinstance(msg, HumanMessage):
            st.chat_message("user",avatar="👷").write(msg.content)

    # Handle user input
    if user_input := st.chat_input("What you will do today?",accept_file=True,file_type=['jpg','png','jpeg']):
        
        #user_message = user_input.text if hasattr(user_input, "text") else str(user_input)
        
        with st.chat_message("user",avatar="👷"):
            if user_input.text:
                st.write(user_input.text)
                st.session_state.messages.append(HumanMessage(content=user_input.text))

            import tempfile
            from PIL import Image

            if (bool(user_input.text) and bool(user_input.files)) or bool(user_input.files):
                uploaded_file = user_input.files[0]
                image = Image.open(uploaded_file).convert("RGB")

                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    image.save(tmp, format="JPEG")
                    image_path = tmp.name
                
                col1, col2 = st.columns(2)
                imagedetect, result = objectdetection(image_path)
                col1.image(image, caption="📷 Uploaded Image", use_container_width=True)
                col2.image(imagedetect, caption="🧠 AI Detection Result", use_container_width=True)

                # ส่ง path ไปให้ agent
                query_input = f"{user_input.text} | Detect image from path: {image_path}"
                st.session_state.messages.append(HumanMessage(content=query_input))

        #===== ai zone =====#

        response = get_response(st.session_state.messages)
        ai_content = response["messages"][-1].content if "messages" in response else "(No response)"

        with st.chat_message("assistant",avatar="🧠"):
            st.info(ai_content)
            
            with st.expander("Details response"):
                st.write(response["messages"])
        
        st.session_state.messages.append(AIMessage(content=ai_content))

        #try:
        #    os.remove(image_path)
        #    st.warning(f"completed: Temporary file {image_path} deleted successfully.")
        #except Exception as e:
        #    st.empty()

elif page == "Data Visualization":
    from st_visiualization import load_data, show_charts
    st.header("📊 Data Visualization")
    # โหลดข้อมูลจาก Supabase
    df = load_data()

    # แสดงผลกราฟต่าง ๆ
    show_charts(df)