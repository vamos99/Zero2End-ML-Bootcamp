from sqlalchemy import create_engine
import streamlit as st
from src.config import DATABASE_URL

@st.cache_resource
def get_db_connection():
    engine = create_engine(DATABASE_URL)
    return engine
