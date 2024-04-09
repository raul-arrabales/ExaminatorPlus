
import ast 

from typing import List

from langchain.docstore.document import Document

from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage,SystemMessage

from rag.vectorizing import FolderIndex

from rag.prompts_qgen import build_QGen_System_Prompt,build_QGen_User_Prompt


class GeneratedQuestion:
    id: str
    gen_text: str
    question: str
    error: bool
    qtype: str
    topic: str
    options: List[str]
    options_ids: List[str]
    correct_option: str
    explanation: str
    source: str
    excerpt: str    

    def __init__(self, id, gen_text, question_text, err, qtype, topic, options, options_ids, correct_option, explanation, source, excerpt):
        self.id = id
        self.gen_text = gen_text
        self.question_text = question_text
        self.error = err
        self.qtype = qtype
        self.topic = topic
        self.options = options
        self.options_ids = options_ids
        self.correct_option = correct_option
        self.explanation = explanation
        self.source = source
        self.excerpt = excerpt
    



def generate_questions_withTopic(
    num_questions: int,
    questions_type: str,
    questions_topic: str,
    difficulty: str,
    folder_index: FolderIndex,
    llm: ChatOpenAI,
    num_chunks: int = 5
) -> GeneratedQuestion:
    
    relevant_docs = folder_index.index.similarity_search(questions_topic, k=num_chunks)
    system_prompt = build_QGen_System_Prompt(question_type=questions_type,num_options=4,difficulty=difficulty)
    user_prompt = build_QGen_User_Prompt(num_questions=num_questions,course_content=relevant_docs)
    messages = [SystemMessage(content=system_prompt),HumanMessage(content=user_prompt)]
    response = llm.invoke(messages)

    try: 
        questions_list = ast.literal_eval(response.content.replace("```python","").replace("```",""))
        malformed = None
    except Exception as e:
        malformed = response 

    if not malformed: 
        questions = [
            GeneratedQuestion(
                id=question.get("question_id"),
                gen_text=response,
                question_text=question.get("question_text"),
                err=False,
                qtype=questions_type, 
                topic=question.get("topic"),
                options=question.get("question_options"),
                options_ids=question.get("question_options_ids"),
                correct_option=question.get("correct_option"),
                explanation=question.get("explanation"),
                source=question.get("source"),
                excerpt=question.get("excerpt")
                )
            for question in questions_list
        ]
    else: 
        questions = [GeneratedQuestion(
                id=None,
                gen_text=response,
                question_text=None,
                err=True, # Just to signal the error and get the malformed generated text
                qtype=questions_type, 
                topic=None,
                options=None,
                options_ids=None,
                correct_option=None,
                explanation=None,
                source=None,
                excerpt=None
                )]

    return questions

