import isodate
from urllib.parse import urlparse, parse_qs
from google import genai
from google.adk.models import Gemini
from google.genai import types
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from .. import config

gemini_client = genai.Client(api_key=config.GEMINI_API_KEY, vertexai=False)
yt_client = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


def get_video_id(url: str) -> str:
    """Extracts video ID from various YouTube URL formats."""
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            p = parse_qs(parsed.query)
            return p["v"][0]
        if parsed.path[:7] == "/embed/":
            return parsed.path.split("/")[2]
        if parsed.path[:3] == "/v/":
            return parsed.path.split("/")[2]
    return ""


async def youtube_summary(url: str, query: str):
    """
    Answer questions about a specific YouTube video, focusing on specific query
    Args:
    url (str): a YouTube URL
    query (str): a query or questions to answer about the video
    """

    model = (
        config.GOOGLE_FLASH_MODEL.model
        if isinstance(config.GOOGLE_FLASH_MODEL, Gemini)
        else config.GOOGLE_FLASH_MODEL
    )

    video_id = get_video_id(url)
    if not video_id:
        return {"status": "failed", "message": "Invalid YouTube URL"}

    try:
        request = yt_client.videos().list(part="contentDetails", id=video_id)
        response = request.execute()

        if not response["items"]:
            return {"status": "failed", "message": "Video not found via API"}

        iso_duration = response["items"][0]["contentDetails"]["duration"]
        duration_seconds = isodate.parse_duration(iso_duration).total_seconds()

        contents = []

        if duration_seconds > 1800:
            try:
                YT_transcriber = YouTubeTranscriptApi()
                transcript_list = YT_transcriber.list(video_id=video_id)
                transcriptions = transcript_list.find_transcript(
                    language_codes=["en", "en-US", "ru", "ru-RU"]
                ).fetch()
                formatter = TextFormatter()
                transcript_text = formatter.format_transcript(transcriptions)

                prompt = f"Video Transcript:\n{transcript_text}\n\nUser Query: {query}"
                contents = [types.Part(text=prompt)]

            except Exception as e:
                return {
                    "status": "failed",
                    "message": f"Transcript retrieval failed: {str(e)}",
                }
        else:
            contents = [
                types.Part(
                    file_data=types.FileData(file_uri=url, mime_type="video/mp4")
                ),
                types.Part(text=query),
            ]

        response = gemini_client.models.generate_content(
            model=model,
            contents=contents,
        )

        if response and response.text:
            return {"status": "success", "message": response.text}
        else:
            return {"status": "failed", "message": "No response text generated."}

    except Exception as e:
        return {"status": "error", "message": str(e)}
