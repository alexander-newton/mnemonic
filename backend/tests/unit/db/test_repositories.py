"""Tests for repository pattern implementation.

This module tests all repository classes to ensure:
- CRUD operations work correctly
- NotFoundError raised when appropriate (NOT silent None returns)
- Pagination works (skip, limit)
- Domain-specific queries return correct results
- Edge cases (empty results, invalid IDs, etc.)
- Database constraints are respected (unique email, foreign keys)
- Proper exception handling (no silent failures)
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mnemonic.db.models.base import Base
from mnemonic.db.models.card import Card, CardState
from mnemonic.db.models.card_type import CardType, SyntaxType
from mnemonic.db.models.deck import Deck
from mnemonic.db.models.review_log import ReviewLog
from mnemonic.db.models.user import User
from mnemonic.db.repositories.base import BaseRepository
from mnemonic.db.repositories.card import CardRepository
from mnemonic.db.repositories.deck import DeckRepository
from mnemonic.db.repositories.review_log import ReviewLogRepository
from mnemonic.db.repositories.user import UserRepository
from mnemonic.exceptions import CardNotFoundError, DeckNotFoundError, NotFoundError


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


@pytest.fixture
def base_card_type(db_session: Session) -> CardType:
    """Create a basic card type for testing."""
    card_type = CardType(
        name="Front/Back",
        syntax_type=SyntaxType.FRONTBACK,
        is_builtin=True,
    )
    db_session.add(card_type)
    db_session.commit()
    return card_type


class TestBaseRepository:
    """Test the BaseRepository base class."""

    def test_get_raises_not_found_for_invalid_id(self, db_session: Session) -> None:
        """Test that get() raises NotFoundError for invalid ID."""
        repo = BaseRepository(User)
        with pytest.raises(NotFoundError) as exc:
            repo.get(db_session, uuid.uuid4())
        assert "not found" in str(exc.value).lower()

    def test_get_returns_entity_for_valid_id(self, db_session: Session) -> None:
        """Test that get() returns entity for valid ID."""
        user = User(
            email="test@example.com",
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        repo = BaseRepository(User)
        result = repo.get(db_session, user.id)
        assert result.id == user.id
        assert result.email == "test@example.com"

    def test_get_all_returns_all_entities(self, db_session: Session) -> None:
        """Test that get_all() returns all entities."""
        users = [
            User(email="test1@example.com", password_hash="hashed"),
            User(email="test2@example.com", password_hash="hashed"),
            User(email="test3@example.com", password_hash="hashed"),
        ]
        db_session.add_all(users)
        db_session.commit()

        repo = BaseRepository(User)
        results = repo.get_all(db_session)
        assert len(results) == 3

    def test_get_all_with_pagination(self, db_session: Session) -> None:
        """Test that get_all() respects skip and limit parameters."""
        users = [
            User(email=f"test{i}@example.com", password_hash="hashed")
            for i in range(10)
        ]
        db_session.add_all(users)
        db_session.commit()

        repo = BaseRepository(User)
        results = repo.get_all(db_session, skip=2, limit=3)
        assert len(results) == 3

    def test_get_all_empty_result(self, db_session: Session) -> None:
        """Test that get_all() returns empty list when no entities."""
        repo = BaseRepository(User)
        results = repo.get_all(db_session)
        assert results == []

    def test_create_creates_new_entity(self, db_session: Session) -> None:
        """Test that create() creates a new entity."""
        repo = BaseRepository(User)
        result = repo.create(
            db_session,
            email="test@example.com",
            password_hash="hashed",
        )
        assert result.email == "test@example.com"

        retrieved = repo.get(db_session, result.id)
        assert retrieved.email == "test@example.com"

    def test_update_updates_existing_entity(self, db_session: Session) -> None:
        """Test that update() modifies existing entity."""
        user = User(
            email="test@example.com",
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        repo = BaseRepository(User)
        repo.update(
            db_session,
            user.id,
            email="updated@example.com",
        )

        retrieved = repo.get(db_session, user.id)
        assert retrieved.email == "updated@example.com"

    def test_update_raises_not_found_for_invalid_id(
        self, db_session: Session
    ) -> None:
        """Test that update() raises NotFoundError for invalid ID."""
        repo = BaseRepository(User)
        with pytest.raises(NotFoundError) as exc:
            repo.update(db_session, uuid.uuid4(), email="updated@example.com")
        assert "not found" in str(exc.value).lower()

    def test_delete_removes_entity(self, db_session: Session) -> None:
        """Test that delete() removes entity."""
        user = User(
            email="test@example.com",
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.id

        repo = BaseRepository(User)
        repo.delete(db_session, user_id)

        with pytest.raises(NotFoundError):
            repo.get(db_session, user_id)

    def test_delete_raises_not_found_for_invalid_id(
        self, db_session: Session
    ) -> None:
        """Test that delete() raises NotFoundError for invalid ID."""
        repo = BaseRepository(User)
        with pytest.raises(NotFoundError) as exc:
            repo.delete(db_session, uuid.uuid4())
        assert "not found" in str(exc.value).lower()


class TestUserRepository:
    """Test the UserRepository."""

    def test_get_by_email_returns_user(self, db_session: Session) -> None:
        """Test that get_by_email() returns the correct user."""
        user = User(
            email="test@example.com",
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        repo = UserRepository()
        result = repo.get_by_email(db_session, "test@example.com")
        assert result.id == user.id
        assert result.email == "test@example.com"

    def test_get_by_email_raises_not_found(self, db_session: Session) -> None:
        """Test that get_by_email() raises NotFoundError when email not found."""
        repo = UserRepository()
        with pytest.raises(NotFoundError) as exc:
            repo.get_by_email(db_session, "nonexistent@example.com")
        assert "not found" in str(exc.value).lower()
        assert "nonexistent@example.com" in str(exc.value)

    def test_exists_by_email_returns_true(self, db_session: Session) -> None:
        """Test that exists_by_email() returns True when email exists."""
        user = User(
            email="test@example.com",
            password_hash="hashed",
        )
        db_session.add(user)
        db_session.commit()

        repo = UserRepository()
        assert repo.exists_by_email(db_session, "test@example.com") is True

    def test_exists_by_email_returns_false(self, db_session: Session) -> None:
        """Test that exists_by_email() returns False when email doesn't exist."""
        repo = UserRepository()
        assert repo.exists_by_email(db_session, "nonexistent@example.com") is False

    def test_create_user_creates_user(self, db_session: Session) -> None:
        """Test that create_user() creates a user with email and password."""
        repo = UserRepository()
        user = repo.create_user(
            db_session,
            email="test@example.com",
            password_hash="hashed",
        )
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed"

    def test_create_user_with_fsrs_params(self, db_session: Session) -> None:
        """Test that create_user() handles fsrs_params."""
        repo = UserRepository()
        fsrs_params = {"w": [1.0, 1.0, 5.0]}
        user = repo.create_user(
            db_session,
            email="test@example.com",
            password_hash="hashed",
            fsrs_params=fsrs_params,
        )
        assert user.fsrs_params == fsrs_params

    def test_create_user_with_settings(self, db_session: Session) -> None:
        """Test that create_user() handles settings."""
        repo = UserRepository()
        settings = {"theme": "dark"}
        user = repo.create_user(
            db_session,
            email="test@example.com",
            password_hash="hashed",
            settings=settings,
        )
        assert user.settings == settings


class TestDeckRepository:
    """Test the DeckRepository."""

    def test_get_by_user_returns_user_decks(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_user() returns only the user's decks."""
        user1 = User(email="user1@example.com", password_hash="hashed")
        user2 = User(email="user2@example.com", password_hash="hashed")
        db_session.add_all([user1, user2])
        db_session.commit()

        user1_deck1 = Deck(user_id=user1.id, name="Deck 1")
        user1_deck2 = Deck(user_id=user1.id, name="Deck 2")
        user2_deck = Deck(user_id=user2.id, name="User 2 Deck")
        db_session.add_all([user1_deck1, user1_deck2, user2_deck])
        db_session.commit()

        repo = DeckRepository()
        results = repo.get_by_user(db_session, user1.id)
        assert len(results) == 2
        assert user1_deck1 in results
        assert user1_deck2 in results
        assert user2_deck not in results

    def test_get_by_user_with_pagination(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_user() respects skip and limit."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        decks = [Deck(user_id=user.id, name=f"Deck {i}") for i in range(10)]
        db_session.add_all(decks)
        db_session.commit()

        repo = DeckRepository()
        results = repo.get_by_user(db_session, user.id, skip=2, limit=3)
        assert len(results) == 3

    def test_get_by_user_empty_result(self, db_session: Session) -> None:
        """Test that get_by_user() returns empty list when user has no decks."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        repo = DeckRepository()
        results = repo.get_by_user(db_session, user.id)
        assert results == []

    def test_get_with_card_counts(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_with_card_counts() includes card statistics."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        cards = [
            Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content 1", state=CardState.NEW),
            Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content 2", state=CardState.LEARNING),
            Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content 3", state=CardState.REVIEW),
        ]
        db_session.add_all(cards)
        db_session.commit()

        repo = DeckRepository()
        result = repo.get_with_card_counts(db_session, deck.id)
        assert result is not None
        assert result.id == deck.id
        assert len(result.cards) == 3

    def test_get_with_card_counts_raises_not_found(self, db_session: Session) -> None:
        """Test that get_with_card_counts() raises NotFoundError for invalid ID."""
        repo = DeckRepository()
        with pytest.raises(DeckNotFoundError) as exc:
            repo.get_with_card_counts(db_session, uuid.uuid4())
        assert "not found" in str(exc.value).lower()

    def test_update_settings(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that update_settings() updates deck configuration."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck", variation_enabled=True)
        db_session.add(deck)
        db_session.commit()

        repo = DeckRepository()
        repo.update_settings(
            db_session,
            deck.id,
            variation_enabled=False,
            variation_frequency=0.3,
            leech_threshold=10,
        )

        retrieved = repo.get(db_session, deck.id)
        assert retrieved.variation_enabled is False
        assert retrieved.variation_frequency == 0.3
        assert retrieved.leech_threshold == 10

    def test_update_settings_raises_not_found(self, db_session: Session) -> None:
        """Test that update_settings() raises NotFoundError for invalid ID."""
        repo = DeckRepository()
        with pytest.raises(DeckNotFoundError) as exc:
            repo.update_settings(db_session, uuid.uuid4(), variation_enabled=False)
        assert "not found" in str(exc.value).lower()


class TestCardRepository:
    """Test the CardRepository."""

    def test_get_by_deck_returns_deck_cards(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_deck() returns only the deck's cards."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck1 = Deck(user_id=user.id, name="Deck 1")
        deck2 = Deck(user_id=user.id, name="Deck 2")
        db_session.add_all([deck1, deck2])
        db_session.commit()

        deck1_card1 = Card(deck_id=deck1.id, card_type_id=base_card_type.id, content="Content 1")
        deck1_card2 = Card(deck_id=deck1.id, card_type_id=base_card_type.id, content="Content 2")
        deck2_card = Card(deck_id=deck2.id, card_type_id=base_card_type.id, content="Content 3")
        db_session.add_all([deck1_card1, deck1_card2, deck2_card])
        db_session.commit()

        repo = CardRepository()
        results = repo.get_by_deck(db_session, deck1.id)
        assert len(results) == 2
        assert deck1_card1 in results
        assert deck1_card2 in results
        assert deck2_card not in results

    def test_get_by_deck_with_pagination(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_deck() respects skip and limit."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        cards = [
            Card(deck_id=deck.id, card_type_id=base_card_type.id, content=f"Content {i}")
            for i in range(10)
        ]
        db_session.add_all(cards)
        db_session.commit()

        repo = CardRepository()
        results = repo.get_by_deck(db_session, deck.id, skip=2, limit=3)
        assert len(results) == 3

    def test_get_by_deck_empty_result(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_deck() returns empty list when deck has no cards."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Empty Deck")
        db_session.add(deck)
        db_session.commit()

        repo = CardRepository()
        results = repo.get_by_deck(db_session, deck.id)
        assert results == []

    def test_get_due_for_review(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_due_for_review() returns due cards."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        now = datetime.utcnow()
        due_card = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Due",
            state=CardState.REVIEW,
            due=now - timedelta(days=1),
        )
        not_due_card = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Not Due",
            state=CardState.REVIEW,
            due=now + timedelta(days=1),
        )
        db_session.add_all([due_card, not_due_card])
        db_session.commit()

        repo = CardRepository()
        results = repo.get_due_for_review(db_session, user.id)
        assert len(results) == 1
        assert due_card in results
        assert not_due_card not in results

    def test_get_by_state_returns_cards_with_state(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_state() filters by card state."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        new_card = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="New",
            state=CardState.NEW,
        )
        learning_card = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Learning",
            state=CardState.LEARNING,
        )
        db_session.add_all([new_card, learning_card])
        db_session.commit()

        repo = CardRepository()
        results = repo.get_by_state(db_session, deck.id, CardState.NEW)
        assert len(results) == 1
        assert new_card in results
        assert learning_card not in results

    def test_get_leeches_returns_high_score_cards(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_leeches() returns cards with high leech scores."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        leech = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Leech",
            leech_score=10.0,
        )
        not_leech = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Not Leech",
            leech_score=5.0,
        )
        db_session.add_all([leech, not_leech])
        db_session.commit()

        repo = CardRepository()
        results = repo.get_leeches(db_session, deck.id, threshold=8)
        assert len(results) == 1
        assert leech in results
        assert not_leech not in results

    def test_get_leeches_default_threshold(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_leeches() uses default threshold."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck", leech_threshold=8)
        db_session.add(deck)
        db_session.commit()

        leech = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Leech",
            leech_score=9.0,
        )
        db_session.add(leech)
        db_session.commit()

        repo = CardRepository()
        results = repo.get_leeches(db_session, deck.id)
        assert len(results) == 1

    def test_suspend_marks_card_suspended(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that suspend() marks a card as suspended."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Content",
            suspended=False,
        )
        db_session.add(card)
        db_session.commit()

        repo = CardRepository()
        repo.suspend(db_session, card.id)

        retrieved = repo.get(db_session, card.id)
        assert retrieved.suspended is True

    def test_suspend_raises_not_found(self, db_session: Session) -> None:
        """Test that suspend() raises CardNotFoundError for invalid ID."""
        repo = CardRepository()
        with pytest.raises(CardNotFoundError) as exc:
            repo.suspend(db_session, uuid.uuid4())
        assert "not found" in str(exc.value).lower()

    def test_unsuspend_marks_card_not_suspended(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that unsuspend() removes suspension."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(
            deck_id=deck.id,
            card_type_id=base_card_type.id,
            content="Content",
            suspended=True,
        )
        db_session.add(card)
        db_session.commit()

        repo = CardRepository()
        repo.unsuspend(db_session, card.id)

        retrieved = repo.get(db_session, card.id)
        assert retrieved.suspended is False

    def test_unsuspend_raises_not_found(self, db_session: Session) -> None:
        """Test that unsuspend() raises CardNotFoundError for invalid ID."""
        repo = CardRepository()
        with pytest.raises(CardNotFoundError) as exc:
            repo.unsuspend(db_session, uuid.uuid4())
        assert "not found" in str(exc.value).lower()


class TestReviewLogRepository:
    """Test the ReviewLogRepository."""

    def test_get_by_card_returns_card_reviews(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_card() returns review logs for a card."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card1 = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content 1")
        card2 = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content 2")
        db_session.add_all([card1, card2])
        db_session.commit()

        review1 = ReviewLog(
            card_id=card1.id,
            user_id=user.id,
            rating=4,
            response_time_ms=5000,
            review_time=datetime.utcnow(),
        )
        review2 = ReviewLog(
            card_id=card1.id,
            user_id=user.id,
            rating=3,
            response_time_ms=4000,
            review_time=datetime.utcnow(),
        )
        review3 = ReviewLog(
            card_id=card2.id,
            user_id=user.id,
            rating=2,
            response_time_ms=3000,
            review_time=datetime.utcnow(),
        )
        db_session.add_all([review1, review2, review3])
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_by_card(db_session, card1.id)
        assert len(results) == 2
        assert review1 in results
        assert review2 in results
        assert review3 not in results

    def test_get_by_card_with_limit(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_card() respects limit parameter."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content")
        db_session.add(card)
        db_session.commit()

        reviews = [
            ReviewLog(
                card_id=card.id,
                user_id=user.id,
                rating=i % 4 + 1,
                response_time_ms=1000,
                review_time=datetime.utcnow(),
            )
            for i in range(10)
        ]
        db_session.add_all(reviews)
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_by_card(db_session, card.id, limit=3)
        assert len(results) == 3

    def test_get_by_card_empty_result(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_card() returns empty list when card has no reviews."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content")
        db_session.add(card)
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_by_card(db_session, card.id)
        assert results == []

    def test_get_by_user_returns_user_reviews(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_user() returns review logs for a user."""
        user1 = User(email="user1@example.com", password_hash="hashed")
        user2 = User(email="user2@example.com", password_hash="hashed")
        db_session.add_all([user1, user2])
        db_session.commit()

        deck = Deck(user_id=user1.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content")
        db_session.add(card)
        db_session.commit()

        user1_review = ReviewLog(
            card_id=card.id,
            user_id=user1.id,
            rating=4,
            response_time_ms=5000,
            review_time=datetime.utcnow(),
        )
        user2_review = ReviewLog(
            card_id=card.id,
            user_id=user2.id,
            rating=3,
            response_time_ms=4000,
            review_time=datetime.utcnow(),
        )
        db_session.add_all([user1_review, user2_review])
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_by_user(db_session, user1.id)
        assert len(results) == 1
        assert user1_review in results
        assert user2_review not in results

    def test_get_by_user_with_pagination(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_by_user() respects skip and limit."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content")
        db_session.add(card)
        db_session.commit()

        reviews = [
            ReviewLog(
                card_id=card.id,
                user_id=user.id,
                rating=i % 4 + 1,
                response_time_ms=1000,
                review_time=datetime.utcnow(),
            )
            for i in range(10)
        ]
        db_session.add_all(reviews)
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_by_user(db_session, user.id, skip=2, limit=3)
        assert len(results) == 3

    def test_get_recent_returns_recent_reviews(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_recent() returns reviews from last N days."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        deck = Deck(user_id=user.id, name="Test Deck")
        db_session.add(deck)
        db_session.commit()

        card = Card(deck_id=deck.id, card_type_id=base_card_type.id, content="Content")
        db_session.add(card)
        db_session.commit()

        now = datetime.utcnow()
        recent_review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=4,
            response_time_ms=5000,
            review_time=now - timedelta(days=3),
        )
        old_review = ReviewLog(
            card_id=card.id,
            user_id=user.id,
            rating=3,
            response_time_ms=4000,
            review_time=now - timedelta(days=10),
        )
        db_session.add_all([recent_review, old_review])
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_recent(db_session, user.id, days=7)
        assert len(results) == 1
        assert recent_review in results
        assert old_review not in results

    def test_get_recent_empty_result(
        self, db_session: Session, base_card_type: CardType
    ) -> None:
        """Test that get_recent() returns empty list when no recent reviews."""
        user = User(email="test@example.com", password_hash="hashed")
        db_session.add(user)
        db_session.commit()

        repo = ReviewLogRepository()
        results = repo.get_recent(db_session, user.id, days=7)
        assert results == []
