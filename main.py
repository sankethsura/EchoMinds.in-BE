import uuid
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from livekit.api import AccessToken, VideoGrants, LiveKitAPI
from livekit.protocol.sip import CreateSIPParticipantRequest

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EchoMinds API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _issue_token(room_name: str, identity: str, can_publish: bool = True) -> str:
    return (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/token")
async def get_token(
    room: str = Query(default=None),
    participant: str = Query(default=None),
) -> dict[str, str]:
    room_name = room or f"echominds-{uuid.uuid4().hex[:8]}"
    identity = participant or f"user-{uuid.uuid4().hex[:6]}"

    try:
        token = _issue_token(room_name, identity, can_publish=True)
    except Exception as exc:
        logger.error("Token generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate token") from exc

    logger.info("Token issued room=%s identity=%s", room_name, identity)
    return {"token": token, "room": room_name, "url": settings.livekit_url, "identity": identity}


# ── Phone call feature ─────────────────────────────────────────────────────────

class CallRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit() or c == "+")
        if not digits.startswith("+"):
            digits = "+" + digits
        if len(digits) < 8:
            raise ValueError("Phone number too short")
        return digits


@app.post("/call")
async def start_call(body: CallRequest) -> dict[str, str]:
    if not settings.sip_enabled:
        raise HTTPException(
            status_code=503,
            detail="SIP calling is not configured. Set LIVEKIT_SIP_TRUNK_ID in the backend environment.",
        )

    room_name = f"echominds-call-{uuid.uuid4().hex[:8]}"
    observer_identity = f"observer-{uuid.uuid4().hex[:6]}"

    try:
        # Token for the frontend to observe the call room (listen-only)
        token = _issue_token(room_name, observer_identity, can_publish=False)
    except Exception as exc:
        logger.error("Token generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate token") from exc

    try:
        async with LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ) as lk:
            sip_info = await lk.sip.create_sip_participant(
                CreateSIPParticipantRequest(
                    sip_trunk_id=settings.livekit_sip_trunk_id,
                    sip_call_to=body.phone_number,
                    room_name=room_name,
                    participant_identity="phone-user",
                    participant_name=body.phone_number,
                    play_dialtone=True,
                    hide_phone_number=False,
                )
            )
            logger.info("SIP call placed sip_participant=%s room=%s to=%s",
                        sip_info.participant_identity, room_name, body.phone_number)
    except Exception as exc:
        logger.error("SIP call failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to place call: {exc}") from exc

    return {
        "token": token,
        "room": room_name,
        "url": settings.livekit_url,
        "identity": observer_identity,
        "phone_number": body.phone_number,
    }


@app.get("/sip-status")
async def sip_status() -> dict[str, bool]:
    return {"enabled": settings.sip_enabled}
