"""Tests for Hermes per-skill licence + verification + importer metadata."""

from pathlib import Path

from openjarvis.skills.importer import SkillImporter
from openjarvis.skills.parser import SkillParser
from openjarvis.skills.sources.base import ResolvedSkill
from openjarvis.skills.sources.hermes import HermesResolver
from openjarvis.skills.tool_translator import ToolTranslator
from openjarvis.skills.verify import verify_skill

SKILL_MD = """---
name: demo-skill
description: A demo skill
allowed-tools: Read, Bash
---

Do the thing. See scripts/run.py for the helper.
"""


def _write_skill(root: Path, *, license_text=None, frontmatter_license=None) -> Path:
    skill_dir = root / "skills" / "demo" / "demo-skill"
    skill_dir.mkdir(parents=True)
    fm = "---\nname: demo-skill\ndescription: A demo skill\nallowed-tools: Read, Bash\n"
    if frontmatter_license:
        fm += f"license: {frontmatter_license}\n"
    fm += "---\n\nDo the thing. See scripts/run.py for the helper.\n"
    (skill_dir / "SKILL.md").write_text(fm)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "run.py").write_text("print('hi')\n")
    if license_text is not None:
        (skill_dir / "LICENSE").write_text(license_text)
    return skill_dir


def test_resolver_records_skill_dir_license(tmp_path):
    _write_skill(tmp_path, license_text="MIT License\n\nPermission...")
    resolver = HermesResolver(cache_root=tmp_path)
    skills = resolver.list_skills()
    assert len(skills) == 1
    assert skills[0].sidecar_data["license"] == "MIT"
    assert skills[0].sidecar_data["license_status"] == "verified"
    assert skills[0].sidecar_data["license_source"] == "skill-dir"


def test_resolver_falls_back_to_repo_license(tmp_path):
    _write_skill(tmp_path)
    (tmp_path / "LICENSE").write_text("MIT License\n\nPermission...")
    resolver = HermesResolver(cache_root=tmp_path)
    skills = resolver.list_skills()
    assert skills[0].sidecar_data["license"] == "MIT"
    assert skills[0].sidecar_data["license_source"] == "repo-root"


def test_resolver_records_missing_license(tmp_path):
    _write_skill(tmp_path)
    resolver = HermesResolver(cache_root=tmp_path)
    skills = resolver.list_skills()
    assert skills[0].sidecar_data["license_status"] == "missing"


def test_resolver_frontmatter_license_is_declared(tmp_path):
    _write_skill(tmp_path, frontmatter_license="Custom-Proprietary")
    resolver = HermesResolver(cache_root=tmp_path)
    skills = resolver.list_skills()
    assert skills[0].sidecar_data["license"] == "Custom-Proprietary"
    assert skills[0].sidecar_data["license_status"] == "declared"


def test_verify_passes_clean_skill(tmp_path):
    skill_dir = _write_skill(tmp_path, license_text="MIT License")
    result = verify_skill(skill_dir)
    assert result.passed, result.issues
    assert result.license == "MIT"
    assert result.license_status == "verified"


def test_verify_flags_missing_description_and_unknown_tool(tmp_path):
    skill_dir = tmp_path / "bad"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: bad\nallowed-tools: Teleport\n---\n\nBody.\n"
    )
    result = verify_skill(skill_dir)
    assert not result.passed
    assert any("description" in i for i in result.issues)
    assert result.unknown_tools == ["Teleport"]
    assert result.license_status == "missing"


def test_verify_flags_missing_reference_and_symlink(tmp_path):
    skill_dir = tmp_path / "ref"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: ref\ndescription: d\nlicense: MIT\n---\n\nSee scripts/gone.py.\n"
    )
    (tmp_path / "target.txt").write_text("x")
    (skill_dir / "link.txt").symlink_to(tmp_path / "target.txt")
    result = verify_skill(skill_dir)
    assert not result.passed
    assert result.missing_references == ["scripts/gone.py"]
    assert any("symlink" in i for i in result.issues)


def test_importer_writes_license_metadata(tmp_path):
    skill_dir = _write_skill(tmp_path, license_text="MIT License")
    resolved = ResolvedSkill(
        name="demo-skill",
        source="hermes",
        path=skill_dir,
        category="demo",
        description="A demo skill",
        commit="abc",
        sidecar_data={
            "license": "MIT",
            "license_status": "verified",
            "license_source": "skill-dir",
        },
    )
    importer = SkillImporter(
        SkillParser(), ToolTranslator(), target_root=tmp_path / "out"
    )
    result = importer.import_skill(resolved)
    assert result.success
    metadata = (tmp_path / "out" / "hermes" / "demo-skill" / ".source").read_text()
    assert 'license = "MIT"' in metadata
    assert 'license_status = "verified"' in metadata
    assert 'license_source = "skill-dir"' in metadata


def test_importer_missing_license_recorded_verbatim(tmp_path):
    skill_dir = _write_skill(tmp_path)
    resolved = ResolvedSkill(
        name="demo-skill",
        source="hermes",
        path=skill_dir,
        category="demo",
        description="A demo skill",
        commit="abc",
        sidecar_data={
            "license": "",
            "license_status": "missing",
            "license_source": "none",
        },
    )
    importer = SkillImporter(
        SkillParser(), ToolTranslator(), target_root=tmp_path / "out"
    )
    assert importer.import_skill(resolved).success
    metadata = (tmp_path / "out" / "hermes" / "demo-skill" / ".source").read_text()
    assert 'license_status = "missing"' in metadata
