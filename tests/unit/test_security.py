import pytest

from app.security import hash_password, verify_password


def test_round_trip():
    h = hash_password("Gr4vity-Well")
    assert verify_password("Gr4vity-Well", h)


def test_wrong_password_fails():
    h = hash_password("Gr4vity-Well")
    assert not verify_password("gr4vity-well", h)


def test_salting_produces_distinct_hashes():
    assert hash_password("Same-Input-9") != hash_password("Same-Input-9")


def test_hash_format_is_bcrypt():
    assert hash_password("Format-Check-1").startswith("$2b$")


def test_hash_never_contains_plaintext():
    assert "Plain-Text-7" not in hash_password("Plain-Text-7")


def test_input_over_72_bytes_is_rejected():
    with pytest.raises(ValueError):
        hash_password("x" * 73)


def test_input_at_exactly_72_bytes_is_accepted():
    h = hash_password("x" * 72)
    assert verify_password("x" * 72, h)


def test_multibyte_input_is_measured_in_bytes():
    # 25 four-byte emoji = 100 bytes despite len() == 25
    with pytest.raises(ValueError):
        hash_password("\U0001f512" * 25)


def test_verify_against_garbage_hash_returns_false():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_empty_string_round_trips():
    # bcrypt permits empty input; rejecting empty passwords is the
    # schema layer's policy job (Branch 3), not the hash layer's.
    h = hash_password("")
    assert verify_password("", h)