"""
RAG search service using LangChain for query processing and response generation.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from langchain.schema import Document as LangChainDocument
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.document_processor import DocumentService
from app.config.settings import settings


class RAGSearchService:
    """RAG search service using LangChain for query processing."""
    
    def __init__(self, db: Session):
        """
        Initialize the RAG search service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.document_service = DocumentService(db)
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
        
        # Create RAG prompt template
        self.rag_prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant that answers questions based on the provided context from documentation.

Context:
{context}

Question: {question}

Instructions:
1. Answer the question based ONLY on the provided context
2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in the provided context to answer that question."
3. Be concise but comprehensive
4. Include relevant code examples or specifics from the context when applicable
5. If you reference specific information, mention which document it came from

Answer:""")

    def search(
        self,
        query: str,
        k: int = 5,
        document_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Perform RAG search to answer a query.
        
        Args:
            query: User query/question
            k: Number of chunks to retrieve
            document_ids: Optional filter by specific document IDs
            file_types: Optional filter by file types
            min_similarity: Minimum similarity threshold
            
        Returns:
            Dict[str, Any]: Search results with answer and sources
        """
        try:
            # Step 1: Generate query embedding
            query_embedding = self.embedding_service.generate_query_embedding(query)
            
            # Step 2: Build metadata filter
            where_filter = self._build_metadata_filter(document_ids, file_types)
            
            # Step 3: Retrieve relevant chunks
            search_results = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                k=k,
                where=where_filter,
                min_similarity=min_similarity
            )
            
            if not search_results:
                return {
                    "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                    "sources": [],
                    "query": query,
                    "total_chunks": 0,
                    "search_results": []
                }
            
            # Step 4: Prepare context and generate answer
            context = self._prepare_context(search_results)
            answer = self._generate_answer(query, context)
            
            # Step 5: Prepare response with source information
            sources = self._prepare_sources(search_results)
            
            return {
                "answer": answer,
                "sources": sources,
                "query": query,
                "total_chunks": len(search_results),
                "search_results": [
                    {
                        "content": result["document"],
                        "similarity_score": result["similarity_score"],
                        "metadata": result["metadata"],
                        "document_id": result["metadata"].get("document_id"),
                        "chunk_index": result["metadata"].get("chunk_index"),
                        "file_name": result["metadata"].get("file_name")
                    }
                    for result in search_results
                ]
            }
            
        except Exception as e:
            raise Exception(f"RAG search failed: {str(e)}")
    
    def similarity_search_only(
        self,
        query: str,
        k: int = 10,
        document_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Perform similarity search without LLM generation (for browsing/exploration).
        
        Args:
            query: Search query
            k: Number of chunks to retrieve
            document_ids: Optional filter by specific document IDs
            file_types: Optional filter by file types
            min_similarity: Minimum similarity threshold
            
        Returns:
            Dict[str, Any]: Search results without generated answer
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_query_embedding(query)
            
            # Build metadata filter
            where_filter = self._build_metadata_filter(document_ids, file_types)
            
            # Retrieve relevant chunks
            search_results = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                k=k,
                where=where_filter,
                min_similarity=min_similarity
            )
            
            # Prepare response
            sources = self._prepare_sources(search_results)
            
            return {
                "sources": sources,
                "query": query,
                "total_chunks": len(search_results),
                "search_results": [
                    {
                        "content": result["document"],
                        "similarity_score": result["similarity_score"],
                        "metadata": result["metadata"],
                        "document_id": result["metadata"].get("document_id"),
                        "chunk_index": result["metadata"].get("chunk_index"),
                        "file_name": result["metadata"].get("file_name")
                    }
                    for result in search_results
                ]
            }
            
        except Exception as e:
            raise Exception(f"Similarity search failed: {str(e)}")
    
    def _build_metadata_filter(
        self,
        document_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build metadata filter for ChromaDB query.
        
        Args:
            document_ids: Optional document ID filter
            file_types: Optional file type filter
            
        Returns:
            Optional[Dict[str, Any]]: ChromaDB where filter
        """
        where_conditions = {}
        
        if document_ids:
            if len(document_ids) == 1:
                where_conditions["document_id"] = str(document_ids[0])
            else:
                where_conditions["document_id"] = {"$in": [str(doc_id) for doc_id in document_ids]}
        
        if file_types:
            if len(file_types) == 1:
                where_conditions["file_type"] = file_types[0]
            else:
                where_conditions["file_type"] = {"$in": file_types}
        
        return where_conditions if where_conditions else None
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare context string from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            str: Formatted context string
        """
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            metadata = result["metadata"]
            file_name = metadata.get("file_name", "Unknown")
            chunk_index = metadata.get("chunk_index", "Unknown")
            
            context_part = f"""
--- Source {i} (from {file_name}, chunk {chunk_index}) ---
{result["document"].strip()}
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using LLM with retrieved context.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            str: Generated answer
        """
        try:
            # Create the RAG chain
            rag_chain = (
                {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                | self.rag_prompt
                | self.llm
                | StrOutputParser()
            )
            
            # Generate answer
            answer = rag_chain.invoke({"context": context, "question": query})
            
            return answer.strip()
            
        except Exception as e:
            return f"I encountered an error while generating an answer: {str(e)}"
    
    def _prepare_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare source information from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            List[Dict[str, Any]]: Formatted source information
        """
        sources = []
        
        # Extract unique document IDs
        document_ids = set()
        for result in search_results:
            doc_id = result["metadata"].get("document_id")
            if doc_id:
                try:
                    document_ids.add(int(doc_id))
                except (ValueError, TypeError):
                    pass
        
        # Fetch all documents in a single query if any document IDs exist
        documents_dict = {}
        if document_ids:
            try:
                documents = self.document_service.get_documents_by_ids(list(document_ids))
                documents_dict = {doc.id: doc for doc in documents}
            except Exception as e:
                print(f"Warning: Failed to fetch documents: {e}")
        
        # Prepare sources with document information
        for result in search_results:
            metadata = result["metadata"]
            document_id = metadata.get("document_id")
            
            source = {
                "document_id": document_id,
                "file_name": metadata.get("file_name", "Unknown"),
                "chunk_index": metadata.get("chunk_index"),
                "similarity_score": result["similarity_score"],
                "content_preview": result["document"][:200] + "..." if len(result["document"]) > 200 else result["document"],
                "character_count": metadata.get("character_count"),
                "word_count": metadata.get("word_count")
            }
            
            # Add document-level information if available
            if document_id and int(document_id) in documents_dict:
                document = documents_dict[int(document_id)]
                source.update({
                    "document_title": document.title or document.original_filename,
                    "document_status": document.status,
                    "file_type": document.file_type,
                    "uploaded_at": document.created_at  # Use created_at instead of uploaded_at
                })
            
            sources.append(source)
        
        return sources
    
    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on partial query (future enhancement).
        
        Args:
            partial_query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            List[str]: Search suggestions
        """
        # For now, return empty list - this can be enhanced later
        # with query history, popular searches, or document analysis
        return []
    
    def get_related_questions(self, query: str, context: str) -> List[str]:
        """
        Generate related questions based on the query and context.
        
        Args:
            query: Original query
            context: Retrieved context
            
        Returns:
            List[str]: Related questions
        """
        try:
            related_prompt = ChatPromptTemplate.from_template("""
Based on the original question and the provided context, suggest 3 related questions that a user might want to ask.

Original Question: {question}

Context: {context}

Generate 3 specific, actionable questions that are related to the original question and can be answered using the provided context. Format as a simple list, one question per line, without numbering.

Related Questions:""")
            
            chain = related_prompt | self.llm | StrOutputParser()
            response = chain.invoke({"question": query, "context": context})
            
            # Parse the response into a list
            questions = [q.strip() for q in response.split('\n') if q.strip() and not q.strip().startswith('-')]
            return questions[:3]  # Return max 3 questions
            
        except Exception as e:
            print(f"Failed to generate related questions: {str(e)}")
            return [] 