import os

from langchain.chains import ConversationChain
from langchain import LLMChain, GoogleSearchAPIWrapper
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory, FileChatMessageHistory


from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from .db import VectorDB

HISTORY_DIR = "./chat_history"

def load_conversation_history(conversation_id: str):
    file_path = os.path.join(HISTORY_DIR, f"{conversation_id}.json")
    return FileChatMessageHistory(file_path)


def log_user_message(history: FileChatMessageHistory, user_message: str):
    history.add_user_message(user_message)


def log_bot_message(history: FileChatMessageHistory, bot_message: str):
    history.add_ai_message(bot_message)


def get_chat_history(conversation_id: str):
    history = load_conversation_history(conversation_id)
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        input_key="user_message",
        chat_memory=history,
    )

    return memory.buffer

def read_prompt_template(file_path: str) -> str:
    with open(file_path, "r") as f:
        prompt_template = f.read()

    return prompt_template

def create_chain(llm, template_path, output_key):
    return LLMChain(
        llm=llm,
        prompt=ChatPromptTemplate.from_template(
            template=read_prompt_template(template_path)
        ),
        output_key=output_key,
        verbose=True,
    )




# def query_web_search(user_message: str) -> str:
#     context = {"user_message": user_message}
#     context["related_web_search_results"] = search_tool.run(user_message)
#
#     has_value = search_value_check_chain.run(context)
#
#     print(has_value)
#     if has_value == "Y":
#         return search_compression_chain.run(context)
#     else:
#         return ""


class KakaoLangChain:
    history_dir: str
    _db: str
    _llm: ChatOpenAI
    _search: Tool

    _langchain: dict[str, LLMChain]
    
    def __init__(self, history_dir: str, db: VectorDB):
        self.history_dir = history_dir
        self._db = db
        self._llm = ChatOpenAI(temperature=0.1, max_tokens=200, model="gpt-3.5-turbo")

        self.set_search()
        self.set_langchains()

    def set_search(self):
        _api_key = os.environ["GOOGLE_API_KEY"]
        _cse_id = os.environ["GOOGLE_CSE_ID"]

        search = GoogleSearchAPIWrapper(
            google_api_key=_api_key,
            google_cse_id=_cse_id
        )
        self._search = Tool(
            name="google_search",
            description="Google Search API Wrapper",
            func=search.run,
        )

    def set_langchains(self):
        prefix_dir = "./assets/templates"
        self._langchain = dict()
        self._langchain['search_value_check'] = create_chain(
            llm=self._llm,
            template_path=prefix_dir + "/search_value_check.txt" ,
            output_key="output"
        )
        self._langchain['search_compression'] = create_chain(
            llm=self._llm,
            template_path=prefix_dir + "/search_compress.txt",
            output_key="output"
        )
        self._langchain['information_response'] = create_chain(
            llm=self._llm,
            template_path=prefix_dir + "/information_response.txt",
            output_key="output"
        )
        self._langchain['parse_intent'] = create_chain(
            llm=self._llm,
            template_path=prefix_dir + "/parse_intent.txt",
            output_key="intent"
        )
        self._langchain['default_chain'] = create_chain(
            llm=self._llm,
            template_path=prefix_dir + "/default_response.txt",
            output_key="output"
        )

    def gernerate_answer(self, user_message, conversation_id: str = 'fa1010') -> dict[str, str]:
        history_file = load_conversation_history(conversation_id)

        context = dict(user_message=user_message)
        context["input"] = context["user_message"]
        context["intent_list"] = read_prompt_template("./assets/templates/intent_list.txt")
        context["chat_history"] = get_chat_history(conversation_id)

        intent = self._langchain['parse_intent'].run(context)
        print("intent: "+intent)

        answer = ""
        if intent == "kakao_social":
            context["related_documents"] = self._db.query(context["user_message"])
            answer = self._langchain['information_response'].run(context)

        elif intent == "kakao_sync":
            context["related_documents"] = self._db.query(context["user_message"])
            answer = self._langchain['information_response'].run(context)

        elif intent == "kakao_talk_channel":
            context["related_documents"] = self._db.query(context["user_message"])
            answer = self._langchain['information_response'].run(context)
        else:   # enhancement
            context["related_documents"] = self._db.query(context["user_message"])
            answer = self._langchain['information_response'].run(context)

            context["related_documents"] = self._db.query(context["user_message"])
            context["compressed_web_search_results"] = self._search.run(
                context["user_message"]
            )
            answer = self._langchain['default_chain'].run(context)

        log_user_message(history_file, user_message)
        log_bot_message(history_file, answer)
        return {"answer": answer}





