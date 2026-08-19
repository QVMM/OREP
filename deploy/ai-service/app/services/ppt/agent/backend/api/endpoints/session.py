"""Session cleanup endpoint."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.api.auth import ensure_session_owner
from backend.session.manager import session_manager

router = APIRouter()


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, request: Request) -> Response:
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    ensure_session_owner(session, request)

    session_manager.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
