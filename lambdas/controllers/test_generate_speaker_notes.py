"""
Unit tests for Generate Speaker Notes Lambda Function
"""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set environment variables before importing the handler
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-4-0"
os.environ["SESSIONS_TABLE"] = "test-sessions-table"
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["MAX_CONCURRENT_SLIDES"] = "3"
os.environ["DEFAULT_SECONDS_PER_SLIDE"] = "60"

from generate_speaker_notes import (
    SlideInfo,
    SpeakerNote,
    SpeakerNotesRequest,
    calculate_time_allocation,
    create_notes_prompt,
    generate_notes_for_slide,
    generate_notes_parallel,
    generate_overall_guidance,
    lambda_handler,
    save_metadata_to_dynamodb,
    save_notes_to_s3,
    translate_notes,
)


@pytest.fixture
def valid_event():
    """Valid API Gateway event"""
    return {
        "body": json.dumps(
            {
                "presentation_id": "test-presentation-123",
                "session_id": "test-session-456",
                "slides": [
                    {
                        "slide_number": 1,
                        "title": "Introduction",
                        "content": "Welcome to the presentation",
                        "visual_description": "Company logo",
                        "estimated_duration": 90,
                    },
                    {
                        "slide_number": 2,
                        "title": "Main Topic",
                        "content": "Key points about the topic",
                        "visual_description": "Data chart",
                        "estimated_duration": 120,
                    },
                    {
                        "slide_number": 3,
                        "title": "Conclusion",
                        "content": "Summary and next steps",
                        "visual_description": "Call to action",
                        "estimated_duration": 90,
                    },
                ],
                "presentation_context": {
                    "total_duration": 20,
                    "audience": "executives",
                    "style": "professional",
                    "purpose": "quarterly review",
                },
                "audience_type": "executives",
                "presentation_duration": 5,
                "note_style": "detailed",
                "language": "en",
                "include_transitions": True,
                "include_timing": True,
                "include_audience_interaction": True,
                "expertise_level": "intermediate",
            }
        ),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"requestId": "test-request-id"},
    }


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock response for speaker notes"""
    return {
        "opening": "Good morning everyone, thank you for joining today",
        "main_points": [
            "First, we will review last quarter performance",
            "Next, we discuss current initiatives",
            "Finally, we outline next steps",
        ],
        "detailed_notes": "Start with a warm greeting and establish rapport. Review the agenda briefly.",
        "transitions": {
            "from_previous": "Building on our introduction...",
            "to_next": "Now let us dive into the details...",
        },
        "timing_guidance": {
            "opening": "0:00-0:15",
            "main_content": "0:15-1:15",
            "closing": "1:15-1:30",
        },
        "audience_cues": ["Ask if anyone has questions", "Gauge engagement level"],
        "key_examples": ["Example of successful project", "Case study from Q3"],
        "potential_questions": [
            "Q: What about budget constraints?",
            "A: We have allocated resources accordingly",
        ],
        "confidence_tips": [
            "Make eye contact with key stakeholders",
            "Pause for emphasis on important points",
        ],
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = "test-request-id"
    context.function_name = "generate-speaker-notes"
    context.memory_limit_in_mb = "256"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-west-2:123456789:function:generate-speaker-notes"
    )
    return context


class TestSpeakerNotesRequest:
    """Test request validation"""

    def test_valid_request(self):
        """Test valid request creation"""
        slides = [SlideInfo(slide_number=1, title="Test", content="Content")]
        request = SpeakerNotesRequest(presentation_id="test-123", slides=slides)
        assert request.presentation_id == "test-123"
        assert len(request.slides) == 1
        assert request.note_style == "detailed"  # default

    def test_invalid_style(self):
        """Test style validation"""
        slides = [SlideInfo(slide_number=1, title="Test", content="Content")]
        with pytest.raises(ValueError):
            SpeakerNotesRequest(
                presentation_id="test-123", slides=slides, note_style="invalid_style"
            )

    def test_invalid_expertise_level(self):
        """Test expertise level validation"""
        slides = [SlideInfo(slide_number=1, title="Test", content="Content")]
        with pytest.raises(ValueError):
            SpeakerNotesRequest(
                presentation_id="test-123",
                slides=slides,
                expertise_level="super_expert",
            )

    def test_invalid_language(self):
        """Test language validation"""
        slides = [SlideInfo(slide_number=1, title="Test", content="Content")]
        with pytest.raises(ValueError):
            SpeakerNotesRequest(
                presentation_id="test-123", slides=slides, language="unsupported"
            )

    def test_presentation_duration_limits(self):
        """Test presentation duration limits"""
        slides = [SlideInfo(slide_number=1, title="Test", content="Content")]
        # Too long
        with pytest.raises(ValueError):
            SpeakerNotesRequest(
                presentation_id="test-123", slides=slides, presentation_duration=200
            )


class TestTimeAllocation:
    """Test time allocation calculation"""

    def test_even_distribution_no_estimates(self):
        """Test even time distribution without estimates"""
        slides = [
            SlideInfo(slide_number=1, title="Intro", content="Content"),
            SlideInfo(slide_number=2, title="Main", content="Content"),
            SlideInfo(slide_number=3, title="End", content="Content"),
        ]

        allocation = calculate_time_allocation(slides, 10)  # 10 minutes

        # Should give more time to first and last slides
        assert allocation[1] == 90  # 15% of 600 seconds
        assert allocation[3] == 90  # 15% of 600 seconds
        assert allocation[2] == 420  # Remaining time

    def test_with_estimated_durations(self):
        """Test time allocation with provided estimates"""
        slides = [
            SlideInfo(
                slide_number=1, title="Intro", content="Content", estimated_duration=60
            ),
            SlideInfo(
                slide_number=2, title="Main", content="Content", estimated_duration=120
            ),
            SlideInfo(
                slide_number=3, title="End", content="Content", estimated_duration=60
            ),
        ]

        allocation = calculate_time_allocation(slides, 10)  # 10 minutes = 600 seconds

        # Should scale proportionally: 240 seconds total -> 600 seconds
        # Ratio = 600/240 = 2.5
        assert allocation[1] == 150  # 60 * 2.5
        assert allocation[2] == 300  # 120 * 2.5
        assert allocation[3] == 150  # 60 * 2.5

    def test_single_slide(self):
        """Test time allocation for single slide"""
        slides = [SlideInfo(slide_number=1, title="Only", content="Content")]

        allocation = calculate_time_allocation(slides, 5)  # 5 minutes

        assert allocation[1] == 300  # All 5 minutes


class TestPromptCreation:
    """Test prompt creation for speaker notes"""

    def test_detailed_style_prompt(self):
        """Test prompt for detailed style"""
        slide = SlideInfo(
            slide_number=1,
            title="Introduction",
            content="Welcome content",
            visual_description="Logo slide",
        )

        prompt = create_notes_prompt(
            slide=slide,
            context={"audience": "executives"},
            style="detailed",
            language="en",
            time_seconds=90,
            include_transitions=True,
            include_audience=True,
            expertise_level="intermediate",
            prev_slide=None,
            next_slide=SlideInfo(slide_number=2, title="Next", content="Next content"),
        )

        assert "Introduction" in prompt
        assert "executives" in prompt
        assert "90 seconds" in prompt
        assert "comprehensive notes" in prompt.lower()

    def test_technical_style_prompt(self):
        """Test prompt for technical style"""
        slide = SlideInfo(
            slide_number=2, title="Technical Details", content="Complex information"
        )

        prompt = create_notes_prompt(
            slide=slide,
            context={},
            style="technical",
            language="en",
            time_seconds=120,
            include_transitions=False,
            include_audience=False,
            expertise_level="expert",
        )

        assert "technical details" in prompt.lower()
        assert "data points" in prompt.lower()

    def test_multilingual_prompt(self):
        """Test prompt for non-English language"""
        slide = SlideInfo(slide_number=1, title="Introduction", content="Content")

        prompt = create_notes_prompt(
            slide=slide,
            context={},
            style="concise",
            language="ja",
            time_seconds=60,
            include_transitions=False,
            include_audience=False,
            expertise_level="beginner",
        )

        assert "Generate notes in ja" in prompt


class TestNotesGeneration:
    """Test speaker notes generation"""

    @patch("generate_speaker_notes.bedrock_runtime")
    def test_successful_notes_generation(self, mock_bedrock, mock_bedrock_response):
        """Test successful notes generation for a slide"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {"content": [{"text": json.dumps(mock_bedrock_response)}]}
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        slide = SlideInfo(slide_number=1, title="Test Slide", content="Test content")

        notes = generate_notes_for_slide(
            slide=slide,
            context={"audience": "general"},
            style="detailed",
            language="en",
            time_seconds=90,
            include_transitions=True,
            include_audience=True,
            expertise_level="intermediate",
        )

        assert notes["opening"] == mock_bedrock_response["opening"]
        assert notes["main_points"] == mock_bedrock_response["main_points"]
        assert "transitions" in notes
        mock_bedrock.invoke_model.assert_called_once()

    @patch("generate_speaker_notes.bedrock_runtime")
    def test_notes_generation_with_fallback(self, mock_bedrock):
        """Test notes generation with fallback on error"""
        mock_bedrock.invoke_model.side_effect = Exception("API error")

        slide = SlideInfo(slide_number=1, title="Test Slide", content="Test content")

        notes = generate_notes_for_slide(
            slide=slide,
            context={},
            style="detailed",
            language="en",
            time_seconds=90,
            include_transitions=False,
            include_audience=False,
            expertise_level="intermediate",
        )

        # Should return fallback notes
        assert "opening" in notes
        assert "main_points" in notes
        assert "detailed_notes" in notes
        assert "Test Slide" in notes["detailed_notes"]


class TestTranslation:
    """Test notes translation"""

    @patch("generate_speaker_notes.translate")
    def test_successful_translation(self, mock_translate):
        """Test successful translation of notes"""
        mock_translate.translate_text.return_value = {
            "TranslatedText": "Texto traducido"
        }

        notes_data = {
            "opening": "Opening text",
            "main_points": ["Point 1", "Point 2"],
            "detailed_notes": "Detailed text",
            "audience_cues": ["Cue 1"],
        }

        translated = translate_notes(notes_data, "es")

        assert translated["opening"] == "Texto traducido"
        assert all(p == "Texto traducido" for p in translated["main_points"])
        assert translated["detailed_notes"] == "Texto traducido"

    @patch("generate_speaker_notes.translate")
    def test_translation_failure_fallback(self, mock_translate):
        """Test fallback when translation fails"""
        mock_translate.translate_text.side_effect = Exception("Translation error")

        notes_data = {"opening": "Opening text", "main_points": ["Point 1"]}

        translated = translate_notes(notes_data, "es")

        # Should return original text
        assert translated["opening"] == "Opening text"
        assert translated["main_points"] == ["Point 1"]


class TestParallelGeneration:
    """Test parallel notes generation"""

    @patch("generate_speaker_notes.generate_notes_for_slide")
    def test_parallel_generation_success(self, mock_generate, mock_bedrock_response):
        """Test successful parallel generation"""
        mock_generate.return_value = mock_bedrock_response

        slides = [
            SlideInfo(slide_number=1, title="Slide 1", content="Content 1"),
            SlideInfo(slide_number=2, title="Slide 2", content="Content 2"),
            SlideInfo(slide_number=3, title="Slide 3", content="Content 3"),
        ]

        time_allocation = {1: 90, 2: 120, 3: 90}

        notes = generate_notes_parallel(
            slides=slides,
            context={},
            style="detailed",
            language="en",
            time_allocation=time_allocation,
            include_transitions=True,
            include_audience=False,
            expertise_level="intermediate",
        )

        assert len(notes) == 3
        assert all(isinstance(note, SpeakerNote) for note in notes)
        assert notes[0].slide_number == 1
        assert notes[1].slide_number == 2
        assert notes[2].slide_number == 3
        assert mock_generate.call_count == 3

    @patch("generate_speaker_notes.generate_notes_for_slide")
    def test_parallel_generation_with_failure(self, mock_generate):
        """Test parallel generation with some failures"""

        def side_effect(*args, **kwargs):
            slide = args[0]
            if slide.slide_number == 2:
                raise Exception("Generation failed")
            return {
                "opening": "Test opening",
                "main_points": ["Point 1"],
                "detailed_notes": "Test notes",
            }

        mock_generate.side_effect = side_effect

        slides = [
            SlideInfo(slide_number=1, title="Slide 1", content="Content 1"),
            SlideInfo(slide_number=2, title="Slide 2", content="Content 2"),
            SlideInfo(slide_number=3, title="Slide 3", content="Content 3"),
        ]

        time_allocation = {1: 90, 2: 120, 3: 90}

        notes = generate_notes_parallel(
            slides=slides,
            context={},
            style="detailed",
            language="en",
            time_allocation=time_allocation,
            include_transitions=False,
            include_audience=False,
            expertise_level="intermediate",
        )

        assert len(notes) == 3
        # Slide 2 should have fallback notes
        slide2_note = next(n for n in notes if n.slide_number == 2)
        assert slide2_note.confidence_level == 0.5


class TestOverallGuidance:
    """Test overall presentation guidance generation"""

    def test_generate_overall_guidance(self):
        """Test overall guidance generation"""
        slides = [
            SlideInfo(slide_number=1, title="Intro", content="Content"),
            SlideInfo(slide_number=2, title="Main", content="Content"),
            SlideInfo(slide_number=3, title="End", content="Content"),
        ]

        guidance = generate_overall_guidance(
            slides=slides,
            context={"style": "professional"},
            total_minutes=15,
            audience_type="executives",
        )

        assert "opening_strategy" in guidance
        assert "pacing_advice" in guidance
        assert "executives" in guidance["audience_engagement"]
        assert "backup_plans" in guidance
        assert "confidence_builders" in guidance
        assert isinstance(guidance["confidence_builders"], list)


class TestS3Operations:
    """Test S3 save operations"""

    @patch("generate_speaker_notes.s3")
    def test_save_notes_to_s3(self, mock_s3):
        """Test saving notes to S3"""
        speaker_notes = [
            SpeakerNote(
                slide_number=1,
                main_points=["Point 1"],
                detailed_notes="Details",
                confidence_level=0.9,
            )
        ]

        overall_guidance = {"opening_strategy": "Strong start"}

        location = save_notes_to_s3(
            presentation_id="test-123",
            speaker_notes=speaker_notes,
            overall_guidance=overall_guidance,
        )

        assert location == "s3://test-bucket/speaker-notes/test-123/notes.json"
        mock_s3.put_object.assert_called_once()

        # Check S3 put_object was called with correct parameters
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert "speaker-notes/test-123/notes.json" in call_args[1]["Key"]


class TestDynamoDBOperations:
    """Test DynamoDB operations"""

    @patch("generate_speaker_notes.dynamodb")
    def test_save_metadata_to_dynamodb(self, mock_dynamodb):
        """Test saving metadata to DynamoDB"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table

        save_metadata_to_dynamodb(
            presentation_id="test-123",
            session_id="session-456",
            notes_count=5,
            style="detailed",
            language="en",
        )

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args[1]["Item"]

        assert item["presentation_id"] == "test-123"
        assert item["session_id"] == "session-456"
        assert item["notes_count"] == 5
        assert item["style"] == "detailed"
        assert item["language"] == "en"


class TestLambdaHandler:
    """Test main Lambda handler"""

    @patch("generate_speaker_notes.save_metadata_to_dynamodb")
    @patch("generate_speaker_notes.save_notes_to_s3")
    @patch("generate_speaker_notes.generate_notes_parallel")
    def test_successful_generation(
        self, mock_generate, mock_s3, mock_dynamodb, valid_event, lambda_context
    ):
        """Test successful speaker notes generation"""
        mock_generate.return_value = [
            SpeakerNote(
                slide_number=1,
                main_points=["Point 1"],
                detailed_notes="Notes for slide 1",
                confidence_level=0.9,
            ),
            SpeakerNote(
                slide_number=2,
                main_points=["Point 2"],
                detailed_notes="Notes for slide 2",
                confidence_level=0.9,
            ),
        ]

        mock_s3.return_value = "s3://test-bucket/speaker-notes/test-123/notes.json"

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert len(body["speaker_notes"]) == 2
        assert body["presentation_id"] == "test-presentation-123"
        assert "overall_guidance" in body
        assert "presentation_flow" in body
        assert "time_management" in body

        mock_generate.assert_called_once()
        mock_s3.assert_called_once()
        mock_dynamodb.assert_called_once()

    def test_invalid_request(self, lambda_context):
        """Test invalid request handling"""
        event = {
            "body": json.dumps(
                {"presentation_id": "test-123", "slides": []}
            )  # Invalid: no slides
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    @patch("generate_speaker_notes.generate_notes_parallel")
    def test_generation_error_handling(
        self, mock_generate, valid_event, lambda_context
    ):
        """Test error handling during generation"""
        mock_generate.side_effect = Exception("Generation failed")

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_cors_headers(self, valid_event, lambda_context):
        """Test CORS headers in response"""
        response = lambda_handler(valid_event, lambda_context)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
