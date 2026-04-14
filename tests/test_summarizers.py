"""Tests for LLM summarizer modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.summarizers.base import (
    OpenAISummarizer,
    AnthropicSummarizer,
    create_summarizer,
)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("src.summarizers.base.OpenAI") as mock:
        yield mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch("src.summarizers.base.Anthropic") as mock:
        yield mock


class TestOpenAISummarizer:
    """Test OpenAI summarizer."""

    def test_init_without_api_key(self):
        """Test initialization raises error without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key"):
                OpenAISummarizer(api_key=None)

    @patch("src.summarizers.base.os.getenv")
    def test_init_with_env_key(self, mock_getenv):
        """Test initialization with environment variable."""
        mock_getenv.return_value = "test-key"
        with patch("src.summarizers.base.OpenAI"):
            summarizer = OpenAISummarizer()
            assert summarizer.api_key == "test-key"

    @patch("src.summarizers.base.OpenAI")
    def test_summarize(self, mock_client, mock_openai_response):
        """Test summarizing a single paper."""
        mock_instance = Mock()
        mock_instance.chat.completions.create.return_value = mock_openai_response
        mock_client.return_value = mock_instance

        summarizer = OpenAISummarizer(api_key="test-key")

        paper_info = """
        论文 1:
        标题：Test Paper
        摘要：This is a test abstract.
        """

        result = summarizer.summarize(paper_info)

        assert isinstance(result, str)
        mock_instance.chat.completions.create.assert_called_once()

    @patch("src.summarizers.base.OpenAI")
    def test_generate_report(self, mock_client, mock_openai_response):
        """Test generating a daily report."""
        mock_instance = Mock()
        mock_instance.chat.completions.create.return_value = mock_openai_response
        mock_client.return_value = mock_instance

        summarizer = OpenAISummarizer(api_key="test-key")

        papers_text = "论文内容..."

        result = summarizer.generate_report(papers_text)

        assert isinstance(result, str)
        assert "Test Paper" in result

    @patch("src.summarizers.base.OpenAI")
    def test_api_error_handling(self, mock_client):
        """Test API error handling."""
        mock_instance = Mock()
        mock_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_client.return_value = mock_instance

        summarizer = OpenAISummarizer(api_key="test-key")

        with pytest.raises(RuntimeError, match="OpenAI API call failed"):
            summarizer.generate_report("test")


class TestAnthropicSummarizer:
    """Test Anthropic summarizer."""

    def test_init_without_api_key(self):
        """Test initialization raises error without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key"):
                AnthropicSummarizer(api_key=None)

    @patch("src.summarizers.base.os.getenv")
    def test_init_with_env_key(self, mock_getenv):
        """Test initialization with environment variable."""
        mock_getenv.return_value = "test-key"
        with patch("src.summarizers.base.Anthropic"):
            summarizer = AnthropicSummarizer()
            assert summarizer.api_key == "test-key"

    @patch("src.summarizers.base.Anthropic")
    def test_summarize(self, mock_client):
        """Test summarizing a single paper."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Summary content")]
        mock_instance = Mock()
        mock_instance.messages.create.return_value = mock_response
        mock_client.return_value = mock_instance

        summarizer = AnthropicSummarizer(api_key="test-key")

        paper_info = """
        论文 1:
        标题：Test Paper
        摘要：This is a test abstract.
        """

        result = summarizer.summarize(paper_info)

        assert result == "Summary content"

    @patch("src.summarizers.base.Anthropic")
    def test_generate_report(self, mock_client):
        """Test generating a daily report."""
        mock_response = Mock()
        mock_response.content = [Mock(text="# Report\n\nContent")]
        mock_instance = Mock()
        mock_instance.messages.create.return_value = mock_response
        mock_client.return_value = mock_instance

        summarizer = AnthropicSummarizer(api_key="test-key")

        result = summarizer.generate_report("papers text")

        assert "# Report" in result

    @patch("src.summarizers.base.Anthropic")
    def test_api_error_handling(self, mock_client):
        """Test API error handling."""
        mock_instance = Mock()
        mock_instance.messages.create.side_effect = Exception("API Error")
        mock_client.return_value = mock_instance

        summarizer = AnthropicSummarizer(api_key="test-key")

        with pytest.raises(RuntimeError, match="Anthropic API call failed"):
            summarizer.generate_report("test")


class TestCreateSummarizer:
    """Test summarizer factory function."""

    @patch("src.summarizers.base.OpenAI")
    def test_create_openai_summarizer(self, mock_openai):
        """Test creating OpenAI summarizer."""
        summarizer = create_summarizer(provider="openai", api_key="test-key")
        assert isinstance(summarizer, OpenAISummarizer)

    @patch("src.summarizers.base.Anthropic")
    def test_create_anthropic_summarizer(self, mock_anthropic):
        """Test creating Anthropic summarizer."""
        summarizer = create_summarizer(provider="anthropic", api_key="test-key")
        assert isinstance(summarizer, AnthropicSummarizer)

    def test_create_invalid_provider(self):
        """Test creating summarizer with invalid provider."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            create_summarizer(provider="invalid", api_key="test-key")

    @patch("src.summarizers.base.OpenAI")
    def test_custom_parameters(self, mock_openai):
        """Test creating summarizer with custom parameters."""
        summarizer = create_summarizer(
            provider="openai",
            model="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            api_key="test-key",
        )

        assert summarizer.model == "gpt-4"
        assert summarizer.temperature == 0.5
        assert summarizer.max_tokens == 1000
