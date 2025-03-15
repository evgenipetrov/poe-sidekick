from poe_sidekick.foo import foo


def test_foo() -> None:
    assert foo("foo") == "foo"
