"""Welcome to Pynecone! This file outlines the steps to create a basic app."""

# Import pynecone.
import openai
from datetime import datetime

import pynecone as pc
from pynecone.base import Base

# from app_name.sssecret import secret_gpt_key

from langchain import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.schema import SystemMessage

from .bot_util.db import VectorDB
from .bot_util.langchain import KakaoLangChain
import os

# openai.api_key = "<YOUR_OPENAI_API_KEY>"
openai.api_key = os.environ["OPENAI_API_KEY"]


def load_data(path: str) -> str:
    """Load data from the file."""
    with open(path, "r") as f:
        return f.read()

# print(load_data("./datas/project_data.txt"))

project_data = load_data("./datas/project_data.txt")

class ChatBot:
    chain = None
    def __init__(self, llm):
        self.llm = llm
        self.document = project_data

    # 이런 식으로 하나의 chain만 구성해서 질의응답을 하는 것이 요구사항에 부합한지 잘 모르겠습니다.
    # 좀 더 정교한 추론 혹은 가이드를 위해서는 여러 개의 chaining을 해주지 않아도 원하는 퀄리티의 대답을 얻을 수 있을까요?
    # 또 이런 다큐먼트 기반의 챗봇을 구성하는 경우 퀄리티를 높히는 방법은 무엇이 있는지 궁금합니다.
    def get_chain(self) -> str:

        system_message = f"assistant는 다음 가이드를 토대로 user의 질문에 적절히 질의응답한다. \n {self.document}"
        system_message_prompt = SystemMessage(content=system_message)

        human_template = "질문: {question}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        chain = LLMChain(llm=self.llm, prompt=chat_prompt)

        self.chain = chain

        return chain


cb = ChatBot(ChatOpenAI(temperature=0.0, max_tokens=1024, model="gpt-3.5-turbo-16k"))

class Message(Base):
    original_text: str
    text: str
    created_at: str
    # to_lang: str


class State(pc.State):
    """The app state."""

    text: str = ""
    messages: list[Message] = []
    src_lang: str = "한국어"
    trg_lang: str = "영어"

    last_answer =""
    _db = None

    _lc: KakaoLangChain = None

    def post(self):
        self.messages = [
            Message(
                original_text=self.text,
                #text=self.output,
                # text=cb.get_chain().run(self.text),
                text=self._lc.gernerate_answer(self.text)['answer'],
                created_at=datetime.now().strftime("%B %d, %Y %I:%M %p"),
                # to_lang=self.trg_lang,
            )
        ] + self.messages

        # print(self._db.query(query=self.text))
        # print(self._lc.gernerate_answer(self.text)['answer'])

    def load(self):

        data_src = "./datas"
        persist_dir = "./chroma-persist"
        collection_name = "ka-bot"
        self._db = VectorDB(data_dir=data_src, persist_dir=persist_dir, collection_name=collection_name)

        self._db.load_data()

        self._lc = KakaoLangChain(history_dir="./history", db=self._db)






# Define views.


def header():
    """Basic instructions to get started."""
    return pc.box(
        pc.text("DBaaS DOBI 🗺", font_size="2rem"),
        pc.text(
            "Ask whatever you need to know. DOBI will serve you!!",
            margin_top="0.5rem",
            color="#666",
        ),
    )


def down_arrow():
    return pc.vstack(
        pc.icon(
            tag="arrow_down",
            color="#666",
        )
    )


def text_box(text):
    return pc.text(
        text,
        background_color="#fff",
        padding="1rem",
        border_radius="8px",
    )


def message(message):
    return pc.box(
        pc.vstack(
            text_box(message.original_text),
            down_arrow(),
            text_box(message.text),
            pc.box(
                # pc.text(message.to_lang),
                pc.text(" · ", margin_x="0.3rem"),
                pc.text(message.created_at),
                display="flex",
                font_size="0.8rem",
                color="#662",
            ),
            spacing="0.3rem",
            align_items="left",
        ),
        background_color="#f5f5f5",
        padding="1rem",
        border_radius="8px",
    )


def smallcaps(text, **kwargs):
    return pc.text(
        text,
        font_size="0.7rem",
        font_weight="bold",
        text_transform="uppercase",
        letter_spacing="0.05rem",
        **kwargs,
    )


def output():
    return pc.box(
        pc.box(
            smallcaps(
                "Output",
                color="#aeaeaf",
                background_color="white",
                padding_x="0.1rem",
            ),
            position="absolute",
            top="-0.5rem",
        ),
        pc.text(State.last_answer),
        padding="1rem",
        border="1px solid #eaeaef",
        margin_top="1rem",
        border_radius="8px",
        position="relative",
    )


def index():
    """The main view."""
    return pc.container(
        header(),

        pc.button("load data", on_click=State.load, margin_top="1rem"),
        pc.hstack(
            pc.input(
                placeholder="Text to translate",
                on_blur=State.set_text,
                margin_top="1rem",
                border_color="#eaeaef"
            ),
            pc.button("Send", on_click=State.post, margin_top="1rem"),
        ),
        pc.vstack(
            pc.foreach(State.messages, message),
            margin_top="2rem",
            spacing="1rem",
            align_items="left"
        ),
        padding="2rem",
        max_width="600px"
    )


# Add state and page to the app.
app = pc.App(state=State)
app.add_page(index, title="Translator")
app.compile()
