import uuid
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from livekit.api import AccessToken, VideoGrants

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EchoMinds API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/token")
async def get_token(
    room: str = Query(default=None, description="Room name to join"),
    participant: str = Query(default=None, description="Participant identity"),
) -> dict[str, str]:
    room_name = room or f"echominds-{uuid.uuid4().hex[:8]}"
    participant_identity = participant or f"user-{uuid.uuid4().hex[:6]}"

    try:
        token = (
            AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(participant_identity)
            .with_name(participant_identity)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )
    except Exception as exc:
        logger.error("Token generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate token") from exc

    logger.info("Token issued for room=%s participant=%s", room_name, participant_identity)
    return {
        "token": token,
        "room": room_name,
        "url": settings.livekit_url,
        "identity": participant_identity,
    }
