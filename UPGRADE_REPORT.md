# Upgrade Report: pydantic v1 → v2

**Target library:** pydantic  
**From version:** 1.x  
**To version:** 2.x  
**Final status:** ✅ GREEN — 77 passed, 0 failed

---

## Files Modified

| File | BC IDs Applied |
|------|----------------|
| `src/uplift_demo/settings.py` | BC-001 |
| `src/uplift_demo/models.py` | BC-002, BC-003, BC-004 |
| `src/uplift_demo/service.py` | BC-005 |
| `requirements.txt` | BC-001 |
| `tests/test_models.py` | BC-006 (auto-applied, see below) |

---

## Breaking Changes Applied

### BC-001 — `BaseSettings` moved to `pydantic-settings`
- **File:** `src/uplift_demo/settings.py`
- **Change:** `from pydantic import BaseSettings` → `from pydantic_settings import BaseSettings, SettingsConfigDict`
- **Change:** `class Config: env_prefix = "UPLIFT_"` → `model_config = SettingsConfigDict(env_prefix="UPLIFT_")`
- **File:** `requirements.txt`
- **Change:** Added `pydantic-settings>=2`; upgraded pydantic pin to `pydantic>=2`
- **Status:** ✅ Applied

### BC-002 — `@validator` / `@root_validator` replaced
- **File:** `src/uplift_demo/models.py`
- **Changes:**
  - Removed `validator`, `root_validator` from imports; added `field_validator`, `model_validator`, `ConfigDict`
  - `@validator("name")` → `@field_validator("name") @classmethod` on `Customer.strip_name`
  - `@validator("order_id")` → `@field_validator("order_id") @classmethod` on `Order.order_id_prefix`
  - `@root_validator` → `@model_validator(mode="after")`; body updated from `values` dict to `self` instance; returns `self`
- **Status:** ✅ Applied

### BC-003 — `class Config` attribute changes
- **File:** `src/uplift_demo/models.py`
- **Change:** `class Config: allow_mutation = False` → `model_config = ConfigDict(frozen=True)` on `OrderItem`
- **File:** `src/uplift_demo/settings.py`
- **Change:** `class Config:` replaced with `model_config = SettingsConfigDict(...)` (see BC-001)
- **Status:** ✅ Applied

### BC-004 — `regex=` / `min_items=` Field kwargs renamed
- **File:** `src/uplift_demo/models.py`
- **Changes:**
  - `Field(..., regex=r"...")` → `Field(..., pattern=r"...")` on `Customer.email`
  - `Field(..., min_items=1)` → `Field(..., min_length=1)` on `Order.items`
- **Status:** ✅ Applied

### BC-005 — `.dict()` / `.json()` / `.copy()` / `.schema()` / `.parse_obj()` renamed
- **File:** `src/uplift_demo/service.py`
- **Changes:**
  - `.parse_obj(payload)` → `Order.model_validate(payload)`
  - `.parse_raw(raw)` → `Order.model_validate_json(raw)`
  - `.dict()` → `.model_dump()`
  - `.json()` → `.model_dump_json()`
  - `.copy(update=...)` → `.model_copy(update=...)`
  - `.schema()` → `Order.model_json_schema()`
- **Status:** ✅ Applied

### BC-006 — `frozen=True` raises `ValidationError` instead of `TypeError` (behavioral)
- **File:** `tests/test_models.py`, line 58
- **Change:** `pytest.raises(TypeError)` → `pytest.raises(ValidationError)` in `test_order_items_are_immutable`
- **Status:** ✅ Auto-applied by verifier (see `needs_human_review` section)

---

## Test Run History

| Attempt | Result | Failures |
|---------|--------|----------|
| 1 | ❌ FAILED | 1 |
| 2 | ✅ PASSED | 0 |

**Attempt 1 failure:**  
`tests/test_models.py::test_order_items_are_immutable` — `pydantic_core.ValidationError` raised but test expected `TypeError` (BC-006).

---

## Needs Human Review

| BC ID | File | Line | Reason | Status |
|-------|------|------|--------|--------|
| BC-006 | `tests/test_models.py` | 58 | Behavioral change: pydantic v2 `frozen=True` raises `pydantic.ValidationError` on mutation instead of `TypeError` (v1 `allow_mutation=False`). Test assertion updated from `pytest.raises(TypeError)` to `pytest.raises(ValidationError)`. | **auto-applied** |

---

## Summary

All six breaking-change IDs were resolved:

- **BC-001** through **BC-005**: patched in `src/` by the code-migrator agents.
- **BC-006**: test-side assertion updated by the verifier (pre-approved fix).

The test suite reached **77 passed / 0 failed** on attempt 2.
