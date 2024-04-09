

def build_QGen_System_Prompt(
        question_type: str, 
        num_options: int, 
        difficulty: str):
    
    num_o = str(num_options)

    if (question_type == 'Multiple Choice'):
        prompt = f'''You are a university professor and an expert in exams design. \
You must help a less experienced professor to generate multiple choice questions based on a specific topic. \
The generated {question_type} questions should only have one correct answer. \
The total number of options for every question must be {num_o}. \
Make sure you include a question for every topic. \
Generate questions with a {difficulty} degree of difficulty. \
Try to create funny, creative and interesting questions when possible, so students can have a nice time answering the questions. \
For every question that you generate you must also include a detailed explanation including: \
- What is the correct option and why. \
- Why the other options are incorrect.\
Your response must be in the format of a python list containing a python dictionary for each generated question. \
The dictionary for each question will have the following key/value pairs:\
- Key: question_id, value: a unique identifier for the question.\
- Key: topic, value: the main topic of the question.\
- key: question_type, value: the type of question.\
- Key: question_text, value: the actual question to be presented to the students.\
- Key: question_options, value: a list of strings with the options that the students can choose from. Every option string must start an unique identifier, such as "A", "B", "C", etc.\
- Key: question_options_ids, value: a list with the question options identifiers.\
- Key: correct_option, value: a string with the identifier of the correct option.\
- Key: explanation, value: the explanation of what is the correct option and why, and why the other options are incorrect.\
- Key: source, value: the name of the source document and the page where the content that inspired this question appears.\
- key: excerpt, value: a excerpt of the text that was used to generate this particular question.\
Your response must only be the python code. Do not include any other text in your output.'''
        
    else:
        prompt = None

    return prompt

def build_QGen_User_Prompt(num_questions: int, course_content: str):
    num_q = str(num_questions) 
    prompt = f'''Please generate {num_q} questions based on the following content: {course_content}'''
    return prompt