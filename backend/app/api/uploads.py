from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from ..auth.permissions import RequiresPermission, get_current_user_token
from ..core.tenant_manager import tenant_manager
from ..services.rag_service import rag_service
import io
import docx
import fitz
import pandas as pd

router = APIRouter()

@router.post("/document")
async def upload_document(
    file: UploadFile = File(...), 
    user_id: int = Depends(RequiresPermission("upload_access")),
    token_payload: dict = Depends(get_current_user_token)
):
    valid_extensions = ('.pdf', '.txt', '.csv', '.doc', '.docx', '.xls', '.xlsx')
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(status_code=400, detail="Unsupported file format")
        
    content = await file.read()
    text = ""
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.pdf'):
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            for page in pdf_doc:
                text += page.get_text() + "\n"
        elif filename.endswith('.docx') or filename.endswith('.doc'):
            try:
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join([p.text for p in doc.paragraphs])
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid or unsupported Word document format")
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))
            text = df.to_string(index=False)
        elif filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
            text = df.to_string(index=False)
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse document: {str(e)}")
        
    if not text.strip():
        raise HTTPException(status_code=400, detail="Document contains no extractable text")
        
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    await rag_service.index_documents(tenant_id, [text], metadata_list=[{"filename": file.filename}])
    
    return {"message": f"Successfully indexed {file.filename}"}

@router.get("/documents")
async def list_documents(
    user_id: int = Depends(RequiresPermission("upload_access")),
    token_payload: dict = Depends(get_current_user_token)
):
    tenant_id = tenant_manager.get_tenant_id_from_token(token_payload)
    from ..services.qdrant_service import qdrant_service
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    try:
        qdrant_service.init_collections()
        # LlamaIndex usually stores tenant_id directly in the payload or under metadata.
        # We will scroll points to find unique filenames for this tenant.
        response = qdrant_service.client.scroll(
            collection_name="document_collection",
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    )
                ]
            ),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        points = response[0]
        filenames = set()
        
        for point in points:
            payload = point.payload or {}
            # Check LlamaIndex specific payload structure
            if "filename" in payload:
                filenames.add(payload["filename"])
            elif "metadata" in payload and "filename" in payload["metadata"]:
                filenames.add(payload["metadata"]["filename"])
            elif "_node_content" in payload:
                try:
                    import json
                    node_content = json.loads(payload["_node_content"])
                    if "metadata" in node_content and "filename" in node_content["metadata"]:
                        filenames.add(node_content["metadata"]["filename"])
                except:
                    pass
                    
        return {"documents": sorted(list(filenames))}
    except Exception as e:
        # If collection doesn't exist yet, just return empty list
        return {"documents": []}
