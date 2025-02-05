from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.vectorstores import FAISS
from langchain_chroma import Chroma
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain_core.prompts import PromptTemplate

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI


prompt_template = """请根据以下上下文回答最后的问题。如果你不知道答案，请直接说不知道，切勿编造答案。回答应简洁明了，最多使用三句话，确保直接针对问题，并鼓励提问者提出更多问题。

{context}

问题：{question}

有帮助的答案："""

class Rag:
    _instance = None

    def __new__(cls, config: dict=None):
        if cls._instance is None:
            cls._instance = super(Rag, cls).__new__(cls)
            cls._instance.init(config)  # 初始化实例属性
        return cls._instance

    def init(self, config: dict):
        self.doc_path = config.get("doc_path")
        self.emb_model = config.get("emb_model")
        self.template = prompt_template
        self.custom_rag_prompt = PromptTemplate.from_template(self.template)
        self.llm = ChatOpenAI(model=config.get("model_name")
                              , base_url=config.get("base_url"), api_key=config.get("api_key"))
        # 定义加载器，支持不同文档类型
        loader = DirectoryLoader(
            self.doc_path,
            glob="**/*.md",
            loader_cls= TextLoader
        )
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)

        model_kwargs = {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': True}
        embedding_model = HuggingFaceBgeEmbeddings(model_name=self.emb_model
                                                   , model_kwargs=model_kwargs
                                                   , encode_kwargs=encode_kwargs)

        #embeddings = embedding_model.embed_documents([doc.content for doc in documents])
        #vector_store = FAISS.from_embeddings(documents=splits, embedding=embeddings)
        vector_store = Chroma.from_documents(documents=splits, embedding=embedding_model)
        retriever = vector_store.as_retriever()

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        self.rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | self.custom_rag_prompt
                | self.llm
                | StrOutputParser()
        )

    def query(self, query):
        result = self.rag_chain.invoke(query)
        return f"帮你找到: {query} 相关的信息，" + str(result)


if __name__ == "__main__":
    config = {""}
