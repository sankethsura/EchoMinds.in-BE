import logging
import asyncio
import traceback

from dotenv import load_dotenv
from livekit.agents import Agent, AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli
from livekit.agents.voice import AgentSession
from livekit.plugins import deepgram, openai, silero

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("echominds.agent")

INSTRUCTIONS = """You are Aria, a friendly and intelligent voice assistant created by EchoMinds.
You are having a real-time voice conversation with the user.

Guidelines:
- Be warm, concise, and helpful. Keep responses conversational and natural for voice.
- Avoid bullet points, markdown, or lists — speak in flowing sentences.
- If asked something you don't know, say so honestly and offer to help with something else.
- You only communicate in English.
- Keep responses under 3 sentences unless the user explicitly asks for more detail.
"""


def prewarm(proc: JobProcess) -> None:
    logger.info("Prewarming — loading Silero VAD model")
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("VAD model loaded successfully")
    except Exception:
        logger.error("VAD prewarm failed:\n%s", traceback.format_exc())
        raise


async def entrypoint(ctx: JobContext) -> None:
    logger.info("=== Agent job started === room=%s", ctx.room.name)

    try:
        logger.info("Connecting to room with AUDIO_ONLY subscribe")
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info("Connected to room. Participants: %s", list(ctx.room.remote_participants.keys()))
    except Exception:
        logger.error("Failed to connect to room:\n%s", traceback.format_exc())
        raise

    try:
        vad = ctx.proc.userdata.get("vad")
        if vad is None:
            logger.error("VAD not found in userdata — prewarm may have failed")
            raise RuntimeError("VAD model missing from userdata")

        logger.info("Building AgentSession with Deepgram STT + GPT-4o-mini + OpenAI TTS")
        session = AgentSession(
            vad=vad,
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=deepgram.TTS(model="aura-2-andromeda-en"),
            allow_interruptions=True,
        )

        @session.on("agent_state_changed")
        def on_state_changed(ev) -> None:
            logger.info("Agent state → %s", ev)

    except Exception:
        logger.error("Failed to build AgentSession:\n%s", traceback.format_exc())
        raise

    try:
        agent = Agent(instructions=INSTRUCTIONS)
        logger.info("Starting AgentSession (awaiting session.start)")
        await session.start(agent, room=ctx.room)
        logger.info("AgentSession started — session is running")
    except Exception:
        logger.error("session.start() failed:\n%s", traceback.format_exc())
        raise

    try:
        logger.info("Sending greeting")
        await session.say(
            "Hi, I'm Aria, your voice assistant. How can I help you today?",
            allow_interruptions=True,
        )
        logger.info("Greeting sent successfully")
    except Exception:
        logger.error("session.say() failed:\n%s", traceback.format_exc())
        raise

    logger.info("Aria ready — waiting for session to end")
    try:
        await session.wait_for_inactive()
        logger.info("Session ended (wait_for_inactive returned)")
    except Exception:
        logger.error("wait_for_inactive() error:\n%s", traceback.format_exc())


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
