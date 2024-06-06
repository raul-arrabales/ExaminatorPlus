
# Partially based on https://github.com/mmz-001/knowledge_gpt/tree/main
# Partually based on https://medium.com/@hugoalmeidamoreira/a-streamlit-quizz-template-505ae87c387f 


import os

import hmac

import streamlit as st

from components.sidebar import sidebar

from ui import (
    wrap_doc_in_html,
    is_query_valid,
    is_file_valid,
    is_open_ai_key_valid,
    display_file_read_error,
)

from fileinput.caching import bootstrap_caching
from fileinput.parsing import read_file
from rag.chunking import chunk_file
from rag.vectorizing import embed_files
from rag.qa import query_folder
from rag.examgen import generate_questions_withTopic, GeneratedQuestion
from rag.utils import get_llm

# MARK: Session State 
# Session state
default_values = {
    'question_list': None,
    'question_idx': 0, 
    'current_question': 0, 
    'score': 0, 
    'selected_option': None, 
    'selected_option_id': None, 
    'correct_option': None,
    'answer_submitted': False,
    'taking_quiz': False
    }
for key, value in default_values.items():
    st.session_state.setdefault(key, value)

# Session state reset
def restart_session():
    st.session_state.question_list = None
    st.session_state.question_idx = 0
    st.session_state.score = 0
    st.session_state.selected_option = None
    st.session_state.selected_option_id = None
    st.session_state.correct_option = None
    st.session_state.answer_submitted = False    
    st.session_state.taking_quiz = False 


def submit_answer():
    if st.session_state.selected_option is not None:
        st.session_state.answer_submitted = True
        if st.session_state.selected_option_id == st.session_state.correct_option:
            st.session_state.score += 1
    else:    
        st.warning("Please select an option before submitting.")  

def next_question():
    st.session_state.question_idx += 1
    st.session_state.selected_option = None
    st.session_state.selected_option_id = None
    st.session_state.answer_submitted = False

def start_quiz():
    st.session_state.taking_quiz = True


# MARK: GenAI Config
EMBEDDING = "openai"
VECTOR_STORE = "faiss"
MODEL_LIST = ["gpt-3.5-turbo-0125", "gpt-4-0125-preview"]
TEMP_LEVELS = [0,0.5,1,1.5,2]
CHUNK_SIZES = [200,300,400,500]
CHUNK_OVERLAPS = [0,20,30,40,50]


# Uncomment to enable debug mode
# MODEL_LIST.insert(0, "debug")

st.set_page_config(page_title="Examinator Plus", page_icon="📖", layout="wide")

# MARK: Page PW
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


# Remove pw checking after secrets have been removed. 
# if not check_password():
#    st.stop()  # Do not continue if check_password is not True.


st.header("📖 Examinator Plus", divider='rainbow')

# Enable caching for expensive functions
bootstrap_caching()

sidebar()

# MARK: AI Settings
##################################################
st.subheader('1. Configure AI setting (optional)')
##################################################

with st.expander("Generative AI Advanced Options"):

    # My OpenAI key might be obtained:
    # - Stored as a streamlit secret
    # - As an os env vble (e.g. if usign a container)        
    # - Input by user in this text input of type password:
    api_key_input = st.text_input(        
        "OpenAI API Key",
        type="password",
        placeholder="Paste your OpenAI API key here (sk-...)",
        help="You can get your API key from https://platform.openai.com/account/api-keys.", 
        # My OpenAI key stored as a secret or a os env vble (if usign a container)
        value = os.environ.get("OPENAI_API_KEY", None) or st.secrets["OPENAI_API_KEY"] 
        # value=os.environ.get("OPENAI_API_KEY", None) or st.session_state.get("OPENAI_API_KEY", ""),
        )
    st.session_state["OPENAI_API_KEY"] = api_key_input

    model: str = st.selectbox("***Model (LLM)***", options=MODEL_LIST) 
    if model:
        st.write('You selected: ***' + model + '*** as the Large Language Model to use.')
    model_temp: float = st.selectbox("***Temperature***", options=TEMP_LEVELS) 
    if model:
        st.write('You selected a ***temp of ' + str(model_temp) + '***.')       

    chunk_size: int = st.selectbox("File Segmentation: ***Chunk Size***", options=CHUNK_SIZES)
    if chunk_size: 
        st.write('You selected a chunk size of: ***' + str(chunk_size) + ' tokens***.')

    chunk_overlap: int = st.selectbox("File Segmentation: ***Chunk Overlap***", options=CHUNK_OVERLAPS)
    if chunk_overlap or (chunk_overlap == 0): 
        st.write('You selected a chunk overlap of: ***' + str(chunk_overlap) + ' tokens***.')


openai_api_key = st.session_state.get("OPENAI_API_KEY")
if not openai_api_key:
    st.warning(
        "An OpenAI API key is required in AI Settings. You can get a key at"
        " https://platform.openai.com/account/api-keys."
    )

# MARK: Select Files
##################################################
st.subheader('2. Select your course contents')
##################################################

uploaded_file = st.file_uploader(
    "Upload a pdf, docx, or txt file",
    type=["pdf", "docx", "txt"],
    help="Scanned documents are not supported yet!",
)

# Loading and segmenting file
if uploaded_file:        
    try:
        file = read_file(uploaded_file)
    except Exception as e:
        display_file_read_error(e, file_name=uploaded_file.name)

    chunked_file = chunk_file(file, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if not is_file_valid(file):
        st.stop()

    if not is_open_ai_key_valid(openai_api_key, model):
        st.stop()

    with st.spinner("Indexing document... This may take a while ⏳"):
        folder_index = embed_files(
            files=[chunked_file],
            embedding=EMBEDDING if model != "debug" else "debug",
            vector_store=VECTOR_STORE if model != "debug" else "debug",
            openai_api_key=openai_api_key
            )


##################################################
st.subheader('3. Start asking and answering questions')
##################################################

tabQuestions, tabQA = st.tabs(["📖 Exam Questions", "❔ Question Answering"])

# MARK: Exam Questions Tab
##########################
# Exam Question TAB
##########################
with tabQuestions:

    st.write('Generating exam questions from selected document/s.')

    with st.expander("Advanced Options for Exam Questions"):
        questions_type = st.radio("What type of questions do you want to generate?",
                                  ["Multiple Choice", "True/False"],
                                  captions = ["To select the right answer from a set os possible answers.", "To assess the truth of a statement."])

        if questions_type == 'Multiple Choice':
            st.write('You selected ***Multiple Choice***.')
        else:
            st.write("You selected ***True/False***.")

        questions_difficulty = st.radio("Degree of difficulty of questions",
                                  ["Low", "Medium","high"])

        if questions_difficulty == 'Low':
            st.write('You selected ***Low degree of difficulty***.')
        elif questions_difficulty == 'Medium':
            st.write('You selected ***Medium degree of difficulty***.')
        else: 
            st.write('You selected ***High degree of difficulty***.')

        questions_topic = st.radio("Should questions be about a specified topic?",
                                  ["No", "Yes"])

        if questions_topic == 'No':
            st.write('You selected ***No Specific Topic***.')
        else: 
            selected_topic = st.text_input("Please, specify a topic", 'AI')
            if selected_topic: 
                st.write('You selected the topic: ' + selected_topic)

    if not uploaded_file:
        st.stop() 

    with st.form(key="examq_form"):
        num_questions = st.number_input('Number of questions:', min_value=1, max_value=10, value=5, step=1)
        gen_questions = st.form_submit_button("Generate!")               

    if gen_questions:

        # Generate questions
        if not st.session_state.taking_quiz: # It not already taking the quiz

            start_quiz()

            llm = get_llm(model=model, openai_api_key=openai_api_key, temperature=model_temp)

            if questions_topic == 'Yes':
                list_of_questions = generate_questions_withTopic(
                    num_questions=num_questions,
                    questions_type=questions_type,
                    questions_topic=selected_topic,
                    difficulty=questions_difficulty,
                    folder_index=folder_index,
                    llm=llm, 
                    num_chunks=5)
            
                # Check for errors
                if len(list_of_questions) == 1: 
                    if list_of_questions[0].error: 
                        st.warning("Error in generation: " + list_of_questions[0].gen_text)
                        #st.stop()
                
                st.session_state.question_list = list_of_questions
            else:        
                st.write("you must select a topic")

    # Display questions
    if st.session_state.question_list:
        # Progress Bar and Score Display
        cur_progress = (st.session_state.question_idx + 1) / len(st.session_state.question_list)
        st.metric(label="Score", value=f"{st.session_state.score} / {len(st.session_state.question_list)}")
        st.progress(cur_progress)

        # Displaying the Question and Answer Options
        question_item = st.session_state.question_list[st.session_state.question_idx]
        st.subheader(f"Question {st.session_state.question_idx + 1}")
        st.title(f"{question_item.question_text}") 

        # Update state with correct option for this question
        st.session_state.correct_option = question_item.correct_option

        #Answer Selection and Feedback
        if st.session_state.answer_submitted:
            for i, option in enumerate(question_item.options):
                label = option
                option_id = question_item.options_ids[i]
                if option_id == question_item.correct_option:
                    st.success(f"{label} (Correct answer)")
                elif option_id == st.session_state.selected_option:
                    st.error(f"{label} (Incorrect answer)")
                else:
                    st.write(label)
            # Print explanation, source and excerpt
            st.markdown('---')
            st.markdown('#### Explanation')
            st.write(question_item.explanation)
            st.markdown('#### Source')
            st.write(question_item.source)
            st.markdown('#### Excerpt')
            st.write(question_item.excerpt)
        else:
            for i, option in enumerate(question_item.options):
                if st.button(option, key=i, use_container_width=True):
                    st.session_state.selected_option = option 
                    st.session_state.selected_option_id = question_item.options_ids[i]
            
        #Submission Button and Navigation
        if st.session_state.answer_submitted:
            if st.session_state.question_idx < len(st.session_state.question_list) - 1:
                st.button('Next', on_click=next_question)
            else:
                st.write(f"Quiz completed! Your score is: {st.session_state.score} / {len(st.session_state.question_list)}")
                if st.button('Restart', on_click=restart_session):
                    pass
        else:
            if st.session_state.question_idx < len(st.session_state.question_list):
                st.button('Submit', on_click=submit_answer)

            # for question in list_of_questions:
            #     st.markdown("---")
            #     st.markdown("### " + question.question_text)
            #     for opt in question.options:
            #         st.markdown("#### " + opt)
                # choices = ["Please select an answer"]
                # choices = choices + [ans for ans in question.options_ids]  
                # user_guess = st.selectbox('Answer:', choices, key=question.id)
                # if user_guess != "Please select an answer":
                #     if user_guess == question.correct_option:
                #         st.markdown("### Contratulations! 🎉🥳 Your answer is correct.")
                #         st.markdown("The explanation is: " + question.explanation)
                #     else:
                #         st.markdown("### Ops! 😭 Your answer is wrong.")
                #         st.markdown("The correct answer is: " + question.correct_option)
                #         st.markdown("The explanation is: " + question.explanation)
                # with st.expander("Solution"):
                #     st.markdown("##### The correct answer is: " + question.correct_option)
                #     st.markdown("##### The explanation is: " + question.explanation)
                #     st.markdown("##### The source is: " + question.source)
                #     st.markdown("##### Original text is: " + question.excerpt)


# MARK: Q&A Tab
##########################
# Question & Answering TAB
##########################
with tabQA:

    st.write('Asking questions about the content of the selected document/s.')

    with st.expander("Advanced Options for Question Answering"):
        return_all_chunks = st.checkbox("Show all chunks retrieved from vector search")
        show_full_doc = st.checkbox("Show parsed contents of the document")

    if not uploaded_file:
        st.stop()



    with st.form(key="qa_form"):
        query = st.text_area("Ask a question about the document")
        submit = st.form_submit_button("Submit")


    if show_full_doc:
        with st.expander("Document"):
            # Hack to get around st.markdown rendering LaTeX
            st.markdown(f"<p>{wrap_doc_in_html(file.docs)}</p>", unsafe_allow_html=True)


    if submit:
        if not is_query_valid(query):
            st.stop()

        # Output Columns
        answer_col, sources_col = st.columns(2)

        llm = get_llm(model=model, openai_api_key=openai_api_key, temperature=model_temp)
        result = query_folder(
            folder_index=folder_index,
            query=query,
            return_all=return_all_chunks,
            llm=llm,
        )

        with answer_col:
            st.markdown("#### Answer")
            st.markdown(result.answer)

        with sources_col:
            st.markdown("#### Sources")
            for source in result.sources:
                st.markdown(source.page_content)
                st.markdown(source.metadata["source"])
                st.markdown("---")

