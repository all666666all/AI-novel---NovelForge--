"""Deterministic rule checks for PostGenValidator."""

from app.services.post_gen_validator import PostGenValidator


def test_detects_pov_leak():
    validator = PostGenValidator()
    context = {"pov": {"pov_name": "张三"}, "introduced_characters": [{"name": "张三"}], "outline_constraints": {}}
    result = validator.validate("他并不知道的是，远处有人窥视。", context=context)
    assert not result.ok
    assert any(err.code == "E_POV_LEAK" for err in result.errors)


def test_detects_abrupt_character_intro():
    validator = PostGenValidator()
    context = {"pov": {"pov_name": "张三"}, "introduced_characters": [{"name": "张三"}], "outline_constraints": {}}
    result = validator.validate("司徒无涯冷笑着抬手，毫不避讳自己的皇子身份。", context=context)
    assert not result.ok
    assert any(err.code == "E_CHARACTER_ABRUPT_INTRO" for err in result.errors)


def test_detects_outline_compression():
    validator = PostGenValidator()
    context = {
        "pov": {"pov_name": "张三"},
        "introduced_characters": [{"name": "张三"}],
        "outline_constraints": {
            "allowed_outline_nodes": ["引子"],
            "forbidden_outline_nodes": [{"id": "回击", "keywords": ["回击", "反杀", "大胜"]}],
        },
    }
    result = validator.validate("这一章他选择果断回击，对手被彻底反杀，算是一次大胜。", context=context)
    assert not result.ok
    assert any(err.code == "E_OUTLINE_COMPRESSION" for err in result.errors)
