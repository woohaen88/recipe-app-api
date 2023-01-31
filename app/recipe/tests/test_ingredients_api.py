from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.test import TestCase
from django.contrib.auth import get_user_model

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer


INGREDIENT_URL = reverse("recipe:ingredient-list")
RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(ingredient_id):
    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def recipe_url(recipe_id):
    """Create and return a recipe detail URL"""
    return reverse("recipe:recipe-detail", args=[recipe_id])


def create_user(**params):
    defaults = {
        "email": "user@example.com",
        "password": "password123",
    }

    defaults.update(params)

    return get_user_model().objects.create_user(**defaults)


def create_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        "title": "Sample recipe title",
        "time_minute": 22,
        "price": Decimal(5.25),
        "description": "Sample Description",
        "link": "http://example.com/recipe.pdf",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicIngredientsApiTests(TestCase):
    """Test Unauthenticated API request"""

    def setUp(self) -> None:

        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API request"""

    def setUp(self) -> None:
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """ingredients 모든 인스턴스 호출"""

        # 1. Kale, Vanila Ingredients 객체 생성
        Ingredient.objects.create(user=self.user, name="Kale")
        Ingredient.objects.create(user=self.user, name="Vanila")

        # 1.1 INGREDIENT_URL로 요청
        res = self.client.get(INGREDIENT_URL)

        # 2.object -> serializer
        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)

        # 3. response는 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 3.1 response.data와 serializer.data가 같아야함
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of limited to user"""

        # 1. 새로운 user로 Ingredient 객체를 만듬
        Ingredient.objects.create(
            user=create_user(email="user2@example.com"), name="Salt"
        )

        # 2. authenticate user로 Ingredient 객체를 만듬
        ingredient = Ingredient.objects.create(user=self.user, name="Pepper")

        # INGREDIT_URL로 요청
        res = self.client.get(INGREDIENT_URL)

        # 상태코드는 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 인증된 객체의 갯수는 1개
        self.assertEqual(len(res.data), 1)

        # 인증된 객체의 유효성 검사
        self.assertEqual(res.data[0].get("name"), ingredient.name)
        self.assertEqual(res.data[0].get("id"), ingredient.id)

    def test_update_ingredient(self):
        """Test updating an ingredient."""

        # 1. ingredient 객체를 만들고
        ingredient = Ingredient.objects.create(user=self.user, name="Cilantro")

        payload = {
            "name": "Salt",
        }

        # 2. 새로운 객체로 patch 함
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)
        ingredient.refresh_from_db()

        # 3. 그리고 이 객체가 payload와 같은지 검사
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload.get("name"))

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name="Salt")

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exists = Ingredient.objects.filter(user=self.user).exists()
        self.assertFalse(exists)
