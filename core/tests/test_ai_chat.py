from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from core.models import User, Educator, Category, Publication, PublicationType
from core.storage import save_publication_html

from django.contrib.auth.hashers import make_password
from django.test import override_settings

@override_settings(GEMINI_API_KEY="test-key")
class AIChatAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="profesor_test@comunidadia.edu",
            name="Profesor Test",
            password=make_password("Password123!"),
            is_verified=True
        )
        self.educator = Educator.objects.create(
            user=self.user,
            nick_name="profesor_test"
        )
        self.category = Category.objects.create(
            name="Inteligencia Artificial",
            slug="inteligencia-artificial",
            description="Categoría de prueba"
        )
        content_url = save_publication_html("<p>La inteligencia artificial generativa transforma el aula de clases.</p>")
        self.publication = Publication.objects.create(
            title="Guía de IA para Profesores",
            publication_type=PublicationType.ARTICLE,
            content_url=content_url,
            educator=self.educator,
            category=self.category
        )
        self.chat_url = "/api/ai/chat/"

    @patch("core.gemini_service.genai.Client")
    def test_ai_chat_general_query_success(self, mock_genai_client):
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "La IA en educación permite personalizar el aprendizaje."
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        payload = {
            "message": "¿Qué es la IA en educación?",
            "publication_id": None,
            "history": []
        }
        
        response = self.client.post(self.chat_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("response", response.data)
        self.assertEqual(response.data["context_used"], False)
        self.assertEqual(response.data["response"], "La IA en educación permite personalizar el aprendizaje.")

    @patch("core.gemini_service.genai.Client")
    def test_ai_chat_with_publication_context(self, mock_genai_client):
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Esta publicación sobre Guía de IA explica cómo transformar el aula."
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        payload = {
            "message": "Resume este artículo",
            "publication_id": self.publication.id,
            "history": []
        }

        response = self.client.post(self.chat_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["context_used"], True)
        self.assertIn("Guía de IA", response.data["response"])

    @patch("core.gemini_service.genai.Client")
    def test_ai_chat_invalid_publication_id_fallback(self, mock_genai_client):
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Respuesta sin contexto."
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        payload = {
            "message": "Hola AI",
            "publication_id": 99999,
            "history": []
        }

        response = self.client.post(self.chat_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["context_used"], False)

    def test_ai_chat_validation_error(self):
        payload = {}
        response = self.client.post(self.chat_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
