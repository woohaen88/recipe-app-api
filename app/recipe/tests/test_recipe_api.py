"""
Tests for recipe APIs.
"""
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerialzier,
)


RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return a recipe detail URL"""
    return reverse("recipe:recipe-detail", args=[recipe_id])


def image_upload_url(recipe_id):
    """create and return an image upload url"""
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


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


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unautenticated API requests."""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated API Request.s"""

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_user(email="user@example.com", password="test123!@#")

        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):

        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""
        other_user = create_user(
            email="other@example.com",
            password="password123",
        )
        # create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerialzier(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self) -> None:
        """Test creating a recipe"""
        payload = {
            "title": "Sample recipe title",
            "time_minute": 22,
            "price": Decimal(5.25),
            "description": "Sample Description",
            "link": "http://example.com/recipe.pdf",
        }
        res = self.client.post(RECIPES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of a recipe."""
        original_link = "https:example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title="sample recipe title",
            link=original_link,
        )

        payload = {"title": "New recipe title"}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test Full update of a recipe"""
        original_payload = {
            "title": "Sample recipe title",
            "time_minute": 22,
            "price": Decimal("5.25"),
            "description": "Sample Description",
            "link": "http://example.com/recipe.pdf",
        }
        recipe = create_recipe(
            user=self.user,
            **original_payload,
        )

        update_payload = {
            "title": "New Sample recipe title",
            "time_minute": 30,
            "price": Decimal("5.30"),
            "description": "New Sample Description",
            "link": "http://new_example.com/recipe.pdf",
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, update_payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in update_payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(email="user2@example.com", password="test123!@#")
        recipe = create_recipe(user=self.user)

        payload = {"user": new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = create_user(
            email="user2@example.com",
            password="test123!@#",
        )
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            "title": "Thai Prawn Curry",
            "time_minute": 30,
            "price": Decimal("2.50"),
            "tags": [
                {"name": "Thai"},
                {"name": "Dinner"},
            ],
        }

        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload.get("tags"):
            exists = recipe.tags.filter(
                name=tag.get("name"),
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_indian = Tag.objects.create(user=self.user, name="Indian")
        payload = {
            "title": "Thai Prawn Curry",
            "time_minute": 30,
            "price": Decimal("2.50"),
            "tags": [
                {"name": "Thai"},
                {"name": "Indian"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload.get("tags"):
            exists = recipe.tags.filter(
                name=tag.get("name"),
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating a recipe"""

        # 1. create recipe object
        recipe = create_recipe(user=self.user)

        # 1-1. request patch Tag object to detail_url
        payload = {
            "tags": [
                {
                    "name": "Lunch",
                }
            ]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        # 1-2 .response status code == 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 2. get 'Lunch' tag from recipe object
        new_tag = Tag.objects.get(user=self.user, name="Lunch")

        # 2.1 New Tag should be in Tag object
        self.assertIn(new_tag, Tag.objects.all())

    def test_update_recipe_assign_tag(self):
        """Test assign an existing tag when updating a recipe."""

        # 1. create sample Tag object.
        tag_breakfast = Tag.objects.create(user=self.user, name="breakfast")

        # 1.1. create sample Recipe object.
        recipe = create_recipe(user=self.user)

        # 1.2. assign tag object to Recipe object.
        recipe.tags.add(tag_breakfast)

        # 2. create another sample Tag object.
        tag_lunch = Tag.objects.create(user=self.user, name="Lunch")

        # 2.1 request detail url
        url = detail_url(recipe.id)
        payload = {"tags": [{"name": "Lunch"}]}
        res = self.client.patch(url, payload, format="json")

        # 3. should be response status code == 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 4. should be in '#2 instance' in Receipe objects
        self.assertIn(tag_lunch, recipe.tags.all())

        # 5. '#1 instance' should not be in Receipe object
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """Tet clearing a recipes tags."""

        # 1. create Tag object
        tag = Tag.objects.create(user=self.user, name="Dessert")

        # 1.1 create Recipe object
        recipe = create_recipe(user=self.user)

        # 1.2 assign Tag object to Recipe object
        recipe.tags.add(tag)

        # 2. tags를 빈 리스트로 update하여
        payload = {"tags": []}

        # 2.1 detail url로 요청
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        # 3. 응답코드는 200이어야 함
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 3.1 태그 갯수는 0이어야함(비웠으니)
        # 비우거나 지우면 갯수 체크!
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Tet creating a recipe with new ingredients."""
        payload = {
            "title": "Sample recipe title",
            "time_minute": 22,
            "price": Decimal(5.25),
            "description": "Sample Description",
            "link": "http://example.com/recipe.pdf",
            "ingredients": [{"name": "Cauliflower"}, {"name": "Salt"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload.get("ingredients"):
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient.get("name"),
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a new recipe with existing ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name="Fish")
        payload = {
            "title": "Sample recipe title",
            "time_minute": 22,
            "price": Decimal(5.25),
            "description": "Sample Description",
            "link": "http://example.com/recipe.pdf",
            "ingredients": [
                {"name": "Cauliflower"},
                {"name": "Fish"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload.get("ingredients"):
            exists = recipe.ingredients.filter(
                name=ingredient.get("name"),
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {"ingredients": [{"name": "Limes"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        new_ingredient = Ingredient.objects.get(user=self.user, name="Limes")
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe."""
        ingredient1 = Ingredient.objects.create(user=self.user, name="Pepper")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name="Chili")
        payload = {"ingredients": [{"name": "Chili"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipes ingredients."""
        ingredients = Ingredient.objects.create(user=self.user, name="Garlic")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredients)

        payload = {"ingredients": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)


class ImageUploadTests(TestCase):
    """Tests for the image upload API"""

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_user(
            email="example@example.com",
            password="passwordtest",
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self) -> None:
        self.recipe.image.delete()

    def test_upload_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {"image": "notanimage"}
        res = self.client.post(url, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
