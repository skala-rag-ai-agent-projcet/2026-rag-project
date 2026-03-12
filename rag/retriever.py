import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import EMBEDDING_MODEL, FAISS_INDEX_PATH, DATA_DIR


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vectorstore(force_rebuild: bool = False) -> FAISS | None:
    """Build or load FAISS vectorstore from PDF/MD files in data/ directory."""
    embeddings = get_embeddings()

    if os.path.exists(FAISS_INDEX_PATH) and not force_rebuild:
        return FAISS.load_local(
            FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True
        )

    pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]
    md_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".md")]

    if not pdf_files and not md_files:
        print("[RAG] data/ 디렉토리에 PDF/MD 파일이 없습니다. RAG를 사용할 수 없습니다.")
        return None

    documents = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        documents.extend(docs)
        print(f"[RAG] 로드 완료: {pdf_file} ({len(docs)} pages)")

    for md_file in md_files:
        md_path = os.path.join(DATA_DIR, md_file)
        loader = TextLoader(md_path, encoding="utf-8")
        docs = loader.load()
        documents.extend(docs)
        print(f"[RAG] 로드 완료: {md_file}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    print(f"[RAG] {len(pdf_files)}개 PDF + {len(md_files)}개 MD → {len(chunks)}개 청크 생성")

    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(FAISS_INDEX_PATH)
    print(f"[RAG] FAISS 인덱스 저장: {FAISS_INDEX_PATH}")

    return vectorstore


def get_retriever(vectorstore: FAISS | None, k: int = 5):
    """Get a retriever from the vectorstore."""
    if vectorstore is None:
        return None
    return vectorstore.as_retriever(search_kwargs={"k": k})


def retrieve_context(retriever, query: str) -> str:
    """Retrieve relevant context for a query."""
    if retriever is None:
        return "(RAG 문서 없음)"

    docs = retriever.invoke(query)
    if not docs:
        return "(관련 문서를 찾지 못했습니다)"

    context_parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        context_parts.append(
            f"[Document {i}] (Source: {os.path.basename(source)})\n{doc.page_content}"
        )

    return "\n\n".join(context_parts)
