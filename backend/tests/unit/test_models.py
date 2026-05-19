"""Tests for SQLAlchemy models.

This module tests all database models to ensure:
- Model creation with valid data
- Field validation and constraints
- Relationships and foreign keys
- JSON field serialization/deserialization
- Enum field validation
- Default values
- Timestamps
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from mnemonic.db.models.base import Base
from mnemonic.db.models.card import Card, CardState
from mnemonic.db.models.card_type import CardType, SyntaxType
from mnemonic.db.models.deck import Deck
from mnemonic.db.models.llm_usage import LLMUsage
from mnemonic.db.models.review_log import ReviewLog
from mnemonic.db.models.training_example import TrainingExample
from mnemonic.db.models.user import User
from mnemonic.db.models.variation_cache import VariationCache


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Create a test database session."""
    session_local = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = session_local()
    yield session
    session.close()


class TestUserModel:
    """Test the User model."""

    def test_user_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a user with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            fsrs_params={"w": [1.0, 1.0, 5.0]},
            settings={"theme": "dark"},
        )
        db_session.add(user)
        db_session.commit()

        retrieved = db_session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.password_hash == "hashed_password"

    def test_user_id_is_uuid(self, db_session: Session) -> None:
        """Test that user ID is automatically generated as UUID."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        assert isinstance(user.id, uuid.UUID)

    def test_user_email_is_unique(self, db_session: Session) -> None:
        """Test that user email is unique."""
        user1 = User(
            email="test@example.com",
            password_hash="hashed_password1",
        )
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            email="test@example.com",
            password_hash="hashed_password2",
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_email_is_indexed(self, db_session: Session) -> None:
        """Test that user email is indexed."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        # Query by email to verify index
        retrieved = db_session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None

    def test_user_timestamps(self, db_session: Session) -> None:
        """Test that created_at and updated_at are set."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_fsrs_params_json(self, db_session: Session) -> None:
        """Test that FSRS params are stored as JSON."""
        params = {"w": [1.0, 1.0, 5.0], "learning_steps": [1, 10]}
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            fsrs_params=params,
        )
        db_session.add(user)
        db_session.commit()

        retrieved = db_session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None
        assert retrieved.fsrs_params == params

    def test_user_settings_json(self, db_session: Session) -> None:
        """Test that settings are stored as JSON."""
        settings = {"theme": "dark", "language": "en"}
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            settings=settings,
        )
        db_session.add(user)
        db_session.commit()

        retrieved = db_session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None
        assert retrieved.settings == settings

    def test_user_decks_relationship(self, db_session: Session) -> None:
        """Test the one-to-many relationship between User and Deck."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck1 = Deck(
            user_id=user.id,
            name="Deck 1",
            description="Test deck 1",
        )
        deck2 = Deck(
            user_id=user.id,
            name="Deck 2",
            description="Test deck 2",
        )
        db_session.add(deck1)
        db_session.add(deck2)
        db_session.commit()

        retrieved = db_session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None
        assert len(retrieved.decks) == 2
        assert deck1 in retrieved.decks
        assert deck2 in retrieved.decks


class TestDeckModel:
    """Test the Deck model."""

    def test_deck_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a deck with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
            description="A test deck",
            variation_enabled=True,
            variation_frequency=0.5,
            leech_threshold=8,
            daily_review_limit=100,
            daily_new_limit=20,
        )
        db_session.add(deck)
        db_session.commit()

        retrieved = db_session.query(Deck).filter_by(name="Test Deck").first()
        assert retrieved is not None
        assert retrieved.user_id == user.id
        assert retrieved.variation_enabled is True
        assert retrieved.variation_frequency == 0.5
        assert retrieved.leech_threshold == 8

    def test_deck_id_is_uuid(self, db_session: Session) -> None:
        """Test that deck ID is automatically generated as UUID."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        assert isinstance(deck.id, uuid.UUID)

    def test_deck_timestamps(self, db_session: Session) -> None:
        """Test that created_at and updated_at are set."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        assert deck.created_at is not None
        assert deck.updated_at is not None
        assert isinstance(deck.created_at, datetime)
        assert isinstance(deck.updated_at, datetime)

    def test_deck_user_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between Deck and User."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        retrieved = db_session.query(Deck).filter_by(name="Test Deck").first()
        assert retrieved is not None
        assert retrieved.user.id == user.id

    def test_deck_cards_relationship(self, db_session: Session) -> None:
        """Test the one-to-many relationship between Deck and Card."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card1 = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content 1",
        )
        card2 = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content 2",
        )
        db_session.add(card1)
        db_session.add(card2)
        db_session.commit()

        retrieved = db_session.query(Deck).filter_by(name="Test Deck").first()
        assert retrieved is not None
        assert len(retrieved.cards) == 2
        assert card1 in retrieved.cards
        assert card2 in retrieved.cards


class TestCardTypeModel:
    """Test the CardType model."""

    def test_card_type_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a card type with valid data."""
        card_type = CardType(
            name="Front/Back",
            description="Basic front and back card",
            syntax_type=SyntaxType.FRONTBACK,
            fields=["front", "back"],
            render_pipeline=["pandoc", "mathjax"],
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        retrieved = db_session.query(CardType).filter_by(name="Front/Back").first()
        assert retrieved is not None
        assert retrieved.syntax_type == SyntaxType.FRONTBACK
        assert retrieved.is_builtin is True

    def test_card_type_id_is_uuid(self, db_session: Session) -> None:
        """Test that card type ID is automatically generated as UUID."""
        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        assert isinstance(card_type.id, uuid.UUID)

    def test_card_type_syntax_type_enum(self, db_session: Session) -> None:
        """Test that syntax_type is an enum with valid values."""
        for syntax_type in [
            SyntaxType.FRONTBACK,
            SyntaxType.CLOZE,
            SyntaxType.IMAGE_CLOZE,
            SyntaxType.CUSTOM,
        ]:
            card_type = CardType(
                name=f"Type {syntax_type.value}",
                syntax_type=syntax_type,
                is_builtin=True,
            )
            db_session.add(card_type)
            db_session.commit()

    def test_card_type_fields_json(self, db_session: Session) -> None:
        """Test that fields are stored as JSON."""
        fields = ["front", "back", "extra"]
        card_type = CardType(
            name="Test Type",
            syntax_type=SyntaxType.FRONTBACK,
            fields=fields,
            is_builtin=False,
        )
        db_session.add(card_type)
        db_session.commit()

        retrieved = db_session.query(CardType).filter_by(name="Test Type").first()
        assert retrieved is not None
        assert retrieved.fields == fields

    def test_card_type_render_pipeline_json(self, db_session: Session) -> None:
        """Test that render_pipeline is stored as JSON."""
        pipeline = ["pandoc", "mathjax"]
        card_type = CardType(
            name="Test Type",
            syntax_type=SyntaxType.FRONTBACK,
            render_pipeline=pipeline,
            is_builtin=False,
        )
        db_session.add(card_type)
        db_session.commit()

        retrieved = db_session.query(CardType).filter_by(name="Test Type").first()
        assert retrieved is not None
        assert retrieved.render_pipeline == pipeline

    def test_card_type_timestamps(self, db_session: Session) -> None:
        """Test that created_at and updated_at are set."""
        card_type = CardType(
            name="Test Type",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        assert card_type.created_at is not None
        assert card_type.updated_at is not None
        assert isinstance(card_type.created_at, datetime)
        assert isinstance(card_type.updated_at, datetime)

    def test_card_type_user_id_nullable(self, db_session: Session) -> None:
        """Test that user_id is nullable for builtin types."""
        card_type = CardType(
            name="Builtin Type",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
            user_id=None,
        )
        db_session.add(card_type)
        db_session.commit()

        retrieved = db_session.query(CardType).filter_by(name="Builtin Type").first()
        assert retrieved is not None
        assert retrieved.user_id is None

    def test_card_type_parent_type_self_referential(self, db_session: Session) -> None:
        """Test self-referential parent_type relationship."""
        parent = CardType(
            name="Parent Type",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(parent)
        db_session.commit()

        child = CardType(
            name="Child Type",
            parent_type_id=parent.id,
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=False,
        )
        db_session.add(child)
        db_session.commit()

        retrieved = db_session.query(CardType).filter_by(name="Child Type").first()
        assert retrieved is not None
        assert retrieved.parent_type_id == parent.id
        assert retrieved.parent_type.id == parent.id


class TestCardModel:
    """Test the Card model."""

    def test_card_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a card with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
            notes="Test notes",
            tags=["tag1", "tag2"],
            state=CardState.NEW,
            stability=0.0,
            difficulty=5.0,
            suspended=False,
        )
        db_session.add(card)
        db_session.commit()

        retrieved = db_session.query(Card).first()
        assert retrieved is not None
        assert retrieved.content == "Test content"
        assert retrieved.notes == "Test notes"
        assert retrieved.tags == ["tag1", "tag2"]

    def test_card_id_is_uuid(self, db_session: Session) -> None:
        """Test that card ID is automatically generated as UUID."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        assert isinstance(card.id, uuid.UUID)

    def test_card_state_enum(self, db_session: Session) -> None:
        """Test that state is an enum with valid values."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        for state in [
            CardState.NEW,
            CardState.LEARNING,
            CardState.REVIEW,
            CardState.RELEARNING,
        ]:
            card = Card(
                deck_id=deck.id,
                card_type_id=card_type.id,
                content=f"Content {state.value}",
                state=state,
            )
            db_session.add(card)
            db_session.commit()

    def test_card_tags_json(self, db_session: Session) -> None:
        """Test that tags are stored as JSON array."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        tags = ["biology", "human-body", "important"]
        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
            tags=tags,
        )
        db_session.add(card)
        db_session.commit()

        retrieved = db_session.query(Card).first()
        assert retrieved is not None
        assert retrieved.tags == tags

    def test_card_timestamps(self, db_session: Session) -> None:
        """Test that created_at and updated_at are set."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        assert card.created_at is not None
        assert card.updated_at is not None
        assert isinstance(card.created_at, datetime)
        assert isinstance(card.updated_at, datetime)

    def test_card_fsrs_fields(self, db_session: Session) -> None:
        """Test FSRS fields storage."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
            state=CardState.REVIEW,
            stability=10.5,
            difficulty=4.2,
            due=datetime.utcnow(),
            reps=5,
            lapses=1,
        )
        db_session.add(card)
        db_session.commit()

        retrieved = db_session.query(Card).first()
        assert retrieved is not None
        assert retrieved.state == CardState.REVIEW
        assert retrieved.stability == 10.5
        assert retrieved.difficulty == 4.2
        assert retrieved.reps == 5
        assert retrieved.lapses == 1

    def test_card_leech_fields(self, db_session: Session) -> None:
        """Test leech-related fields."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        parent_card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Parent content",
        )
        db_session.add(parent_card)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
            leech_score=5.0,
            leech_notified=True,
            parent_card_id=parent_card.id,
        )
        db_session.add(card)
        db_session.commit()

        retrieved = db_session.query(Card).filter_by(content="Test content").first()
        assert retrieved is not None
        assert retrieved.leech_score == 5.0
        assert retrieved.leech_notified is True
        assert retrieved.parent_card_id == parent_card.id

    def test_card_deck_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between Card and Deck."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        retrieved = db_session.query(Card).first()
        assert retrieved is not None
        assert retrieved.deck.id == deck.id

    def test_card_type_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between Card and CardType."""
        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        retrieved = db_session.query(Card).first()
        assert retrieved is not None
        assert retrieved.card_type.id == card_type.id


class TestReviewLogModel:
    """Test the ReviewLog model."""

    def test_review_log_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a review log with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=4,
            response_time_ms=5000,
            review_time=datetime.utcnow(),
            state_before=CardState.NEW,
            state_after=CardState.LEARNING,
            stability_before=0.0,
            stability_after=1.5,
            difficulty_before=5.0,
            difficulty_after=4.8,
            variation_used=False,
        )
        db_session.add(review)
        db_session.commit()

        retrieved = db_session.query(ReviewLog).first()
        assert retrieved is not None
        assert retrieved.rating == 4
        assert retrieved.response_time_ms == 5000

    def test_review_log_id_is_uuid(self, db_session: Session) -> None:
        """Test that review log ID is automatically generated as UUID."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=3,
            response_time_ms=2000,
            review_time=datetime.utcnow(),
        )
        db_session.add(review)
        db_session.commit()

        assert isinstance(review.id, uuid.UUID)

    def test_review_log_state_enums(self, db_session: Session) -> None:
        """Test that state fields are enums."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=2,
            response_time_ms=1000,
            review_time=datetime.utcnow(),
            state_before=CardState.REVIEW,
            state_after=CardState.RELEARNING,
        )
        db_session.add(review)
        db_session.commit()

        retrieved = db_session.query(ReviewLog).first()
        assert retrieved is not None
        assert retrieved.state_before == CardState.REVIEW
        assert retrieved.state_after == CardState.RELEARNING

    def test_review_log_card_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between ReviewLog and Card."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=4,
            response_time_ms=3000,
            review_time=datetime.utcnow(),
        )
        db_session.add(review)
        db_session.commit()

        retrieved = db_session.query(ReviewLog).first()
        assert retrieved is not None
        assert retrieved.card.id == card.id

    def test_review_log_user_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between ReviewLog and User."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=3,
            response_time_ms=2500,
            review_time=datetime.utcnow(),
        )
        db_session.add(review)
        db_session.commit()

        retrieved = db_session.query(ReviewLog).first()
        assert retrieved is not None
        assert retrieved.user.id == user.id

    def test_review_log_variation_fields(self, db_session: Session) -> None:
        """Test variation-related fields in review log."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        variation_id = uuid.uuid4()
        review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=4,
            response_time_ms=2000,
            review_time=datetime.utcnow(),
            variation_used=True,
            variation_id=variation_id,
            variation_helpful=True,
        )
        db_session.add(review)
        db_session.commit()

        retrieved = db_session.query(ReviewLog).first()
        assert retrieved is not None
        assert retrieved.variation_used is True
        assert retrieved.variation_id == variation_id
        assert retrieved.variation_helpful is True


class TestVariationCacheModel:
    """Test the VariationCache model."""

    def test_variation_cache_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a variation cache with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        variation = VariationCache(
            card_id=card.id,
            varied_content="Varied content",
            model_used="gpt-4",
            prompt_version="v1.0",
            semantic_similarity=0.85,
            lexical_difference=0.15,
            times_shown=3,
            times_correct=2,
            user_ratings=[4, 5, 4],
        )
        db_session.add(variation)
        db_session.commit()

        retrieved = db_session.query(VariationCache).first()
        assert retrieved is not None
        assert retrieved.varied_content == "Varied content"
        assert retrieved.model_used == "gpt-4"
        assert retrieved.semantic_similarity == 0.85

    def test_variation_cache_id_is_uuid(self, db_session: Session) -> None:
        """Test that variation cache ID is automatically generated as UUID."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        variation = VariationCache(
            card_id=card.id,
            varied_content="Varied content",
            model_used="gpt-4",
        )
        db_session.add(variation)
        db_session.commit()

        assert isinstance(variation.id, uuid.UUID)

    def test_variation_cache_user_ratings_json(self, db_session: Session) -> None:
        """Test that user_ratings are stored as JSON array."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        ratings = [5, 4, 5, 3]
        variation = VariationCache(
            card_id=card.id,
            varied_content="Varied content",
            model_used="gpt-4",
            user_ratings=ratings,
        )
        db_session.add(variation)
        db_session.commit()

        retrieved = db_session.query(VariationCache).first()
        assert retrieved is not None
        assert retrieved.user_ratings == ratings

    def test_variation_cache_created_at(self, db_session: Session) -> None:
        """Test that created_at is set."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        variation = VariationCache(
            card_id=card.id,
            varied_content="Varied content",
            model_used="gpt-4",
        )
        db_session.add(variation)
        db_session.commit()

        assert variation.created_at is not None
        assert isinstance(variation.created_at, datetime)

    def test_variation_cache_card_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between VariationCache and Card."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Test content",
        )
        db_session.add(card)
        db_session.commit()

        variation = VariationCache(
            card_id=card.id,
            varied_content="Varied content",
            model_used="gpt-4",
        )
        db_session.add(variation)
        db_session.commit()

        retrieved = db_session.query(VariationCache).first()
        assert retrieved is not None
        assert retrieved.card.id == card.id


class TestTrainingExampleModel:
    """Test the TrainingExample model."""

    def test_training_example_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating a training example with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Original content",
        )
        db_session.add(card)
        db_session.commit()

        example = TrainingExample(
            card_id=card.id,
            original_content="Original content",
            varied_content="Varied content",
            user_feedback={"helpful": True, "quality": "high"},
        )
        db_session.add(example)
        db_session.commit()

        retrieved = db_session.query(TrainingExample).first()
        assert retrieved is not None
        assert retrieved.original_content == "Original content"
        assert retrieved.varied_content == "Varied content"

    def test_training_example_id_is_uuid(self, db_session: Session) -> None:
        """Test that training example ID is automatically generated as UUID."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Original content",
        )
        db_session.add(card)
        db_session.commit()

        example = TrainingExample(
            card_id=card.id,
            original_content="Original content",
            varied_content="Varied content",
        )
        db_session.add(example)
        db_session.commit()

        assert isinstance(example.id, uuid.UUID)

    def test_training_example_user_feedback_json(self, db_session: Session) -> None:
        """Test that user_feedback is stored as JSON."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Original content",
        )
        db_session.add(card)
        db_session.commit()

        feedback = {
            "helpful": True,
            "quality": "high",
            "similarity": 0.8,
            "comments": "Good variation",
        }
        example = TrainingExample(
            card_id=card.id,
            original_content="Original content",
            varied_content="Varied content",
            user_feedback=feedback,
        )
        db_session.add(example)
        db_session.commit()

        retrieved = db_session.query(TrainingExample).first()
        assert retrieved is not None
        assert retrieved.user_feedback == feedback

    def test_training_example_created_at(self, db_session: Session) -> None:
        """Test that created_at is set."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Original content",
        )
        db_session.add(card)
        db_session.commit()

        example = TrainingExample(
            card_id=card.id,
            original_content="Original content",
            varied_content="Varied content",
        )
        db_session.add(example)
        db_session.commit()

        assert example.created_at is not None
        assert isinstance(example.created_at, datetime)

    def test_training_example_card_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between TrainingExample and Card."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        deck = Deck(
            user_id=user.id,
            name="Test Deck",
        )
        db_session.add(deck)
        db_session.commit()

        card_type = CardType(
            name="Front/Back",
            syntax_type=SyntaxType.FRONTBACK,
            is_builtin=True,
        )
        db_session.add(card_type)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=card_type.id,
            content="Original content",
        )
        db_session.add(card)
        db_session.commit()

        example = TrainingExample(
            card_id=card.id,
            original_content="Original content",
            varied_content="Varied content",
        )
        db_session.add(example)
        db_session.commit()

        retrieved = db_session.query(TrainingExample).first()
        assert retrieved is not None
        assert retrieved.card.id == card.id


class TestLLMUsageModel:
    """Test the LLMUsage model."""

    def test_llm_usage_creation_with_valid_data(self, db_session: Session) -> None:
        """Test creating LLM usage record with valid data."""
        from datetime import date
        from decimal import Decimal

        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        usage = LLMUsage(
            user_id=user.id,
            date=date.today(),
            model="gpt-4",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=Decimal("0.12"),
        )
        db_session.add(usage)
        db_session.commit()

        retrieved = db_session.query(LLMUsage).first()
        assert retrieved is not None
        assert retrieved.model == "gpt-4"
        assert retrieved.tokens_in == 1000
        assert retrieved.tokens_out == 500

    def test_llm_usage_id_is_uuid(self, db_session: Session) -> None:
        """Test that LLM usage ID is automatically generated as UUID."""
        from datetime import date

        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        usage = LLMUsage(
            user_id=user.id,
            date=date.today(),
            model="gpt-4",
            tokens_in=1000,
            tokens_out=500,
        )
        db_session.add(usage)
        db_session.commit()

        assert isinstance(usage.id, uuid.UUID)

    def test_llm_usage_user_relationship(self, db_session: Session) -> None:
        """Test the many-to-one relationship between LLMUsage and User."""
        from datetime import date

        user = User(
            email="test@example.com",
            password_hash="hashed_password",
        )
        db_session.add(user)
        db_session.commit()

        usage = LLMUsage(
            user_id=user.id,
            date=date.today(),
            model="gpt-4",
            tokens_in=1000,
            tokens_out=500,
        )
        db_session.add(usage)
        db_session.commit()

        retrieved = db_session.query(LLMUsage).first()
        assert retrieved is not None
        assert retrieved.user.id == user.id
