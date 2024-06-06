
import os 

import streamlit as st

from components.faq import faq
from components.about import about


def sidebar():
    with st.sidebar:
        st.markdown(
            "## How to use\n"
            "0. Provide your [OpenAI API key](https://platform.openai.com/account/api-keys) 🔑\n"
            "   (see advanced options)\n"
            "1. Upload course content files 📄\n"
            "2. Enter the topic you want to practice 💬\n"
            "3. Configure the type of questions ⚙️\n"
            "4. Generate the questions ❔\n"
        )




        st.markdown("---")
        about()
        st.markdown("---")
        faq()