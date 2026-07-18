"""Unit tests for ethomorphic.ecwf.core.ECWFCore."""

from __future__ import annotations

import json

import numpy as np
import pytest

from ethomorphic.ecwf.core import ECWFCore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ecwf5() -> ECWFCore:
    """ECWFCore with 5 cognitive and 5 ethical dims (seeded)."""
    return ECWFCore(num_cognitive_dims=5, num_ethical_dims=5, random_state=42)


@pytest.fixture
def ecwf16() -> ECWFCore:
    """ECWFCore with 16 cognitive and 16 ethical dims."""
    return ECWFCore(num_cognitive_dims=16, num_ethical_dims=16, random_state=123)


@pytest.fixture
def ecwf32() -> ECWFCore:
    """ECWFCore with 32 cognitive and 32 ethical dims."""
    return ECWFCore(num_cognitive_dims=32, num_ethical_dims=32, random_state=999)


# ---------------------------------------------------------------------------
# compute_ecwf
# ---------------------------------------------------------------------------

class TestComputeECWF:
    """Tests for the core compute_ecwf method."""

    def test_output_is_complex(self, ecwf5: ECWFCore) -> None:
        x = np.zeros((1, 5))
        e = np.zeros((1, 5))
        result = ecwf5.compute_ecwf(x, e, t=0.0)
        assert np.iscomplexobj(result)

    def test_output_shape_single(self, ecwf5: ECWFCore) -> None:
        x = np.zeros((1, 5))
        e = np.zeros((1, 5))
        result = ecwf5.compute_ecwf(x, e, t=0.0)
        assert result.shape == (1,)

    def test_output_shape_batch(self, ecwf5: ECWFCore) -> None:
        x = np.zeros((3, 5))
        e = np.zeros((3, 5))
        result = ecwf5.compute_ecwf(x, e, t=0.0)
        assert result.shape == (3,)

    @pytest.mark.parametrize("dims", [5, 16, 32])
    def test_configurable_dimensions(self, dims: int) -> None:
        ecwf = ECWFCore(num_cognitive_dims=dims, num_ethical_dims=dims, random_state=0)
        x = np.ones((1, dims)) * 0.5
        e = np.ones((1, dims)) * 0.5
        result = ecwf.compute_ecwf(x, e, t=1.0)
        assert np.iscomplexobj(result)
        assert result.shape == (1,)

    def test_nonzero_output(self, ecwf5: ECWFCore) -> None:
        x = np.ones((1, 5)) * 0.5
        e = np.ones((1, 5)) * 0.5
        result = ecwf5.compute_ecwf(x, e, t=0.0)
        assert np.any(np.abs(result) > 0)


# ---------------------------------------------------------------------------
# calculate_entropy
# ---------------------------------------------------------------------------

class TestEntropy:
    """Tests for the entropy calculation."""

    def test_zero_state_entropy(self, ecwf5: ECWFCore) -> None:
        psi = np.zeros(5, dtype=complex)
        assert ecwf5.calculate_entropy(psi) == 0.0

    def test_uniform_state_entropy(self, ecwf5: ECWFCore) -> None:
        # Uniform distribution should have maximum entropy
        psi = np.ones(4, dtype=complex)
        ent = ecwf5.calculate_entropy(psi)
        assert ent > 0

    def test_single_peak_low_entropy(self, ecwf5: ECWFCore) -> None:
        psi = np.zeros(10, dtype=complex)
        psi[0] = 1.0 + 0j
        ent = ecwf5.calculate_entropy(psi)
        # Single non-zero element ⟹ near-zero entropy
        assert ent < 0.1

    def test_entropy_nonnegative(self, ecwf5: ECWFCore) -> None:
        psi = np.random.RandomState(7).randn(20) + 1j * np.random.RandomState(8).randn(20)
        assert ecwf5.calculate_entropy(psi) >= 0


# ---------------------------------------------------------------------------
# compute_sensitivities
# ---------------------------------------------------------------------------

class TestSensitivities:
    """Tests for sensitivity computation."""

    def test_sensitivities_shape(self, ecwf5: ECWFCore) -> None:
        x = np.ones((1, 1, 5)) * 0.5
        e = np.ones((1, 1, 5)) * 0.5
        csens, esens = ecwf5.compute_sensitivities(x, e, t=0.0)
        assert csens.shape == x.shape
        assert esens.shape == e.shape

    def test_sensitivities_normalised(self, ecwf5: ECWFCore) -> None:
        x = np.ones((1, 1, 5)) * 0.5
        e = np.ones((1, 1, 5)) * 0.5
        csens, esens = ecwf5.compute_sensitivities(x, e, t=0.0)
        # Max should be <= 1 (normalised)
        assert np.max(csens) <= 1.0 + 1e-7
        assert np.max(esens) <= 1.0 + 1e-7

    def test_sensitivities_nonnegative(self, ecwf5: ECWFCore) -> None:
        x = np.ones((1, 1, 5)) * 0.3
        e = np.ones((1, 1, 5)) * 0.7
        csens, esens = ecwf5.compute_sensitivities(x, e, t=0.5)
        assert np.all(csens >= 0)
        assert np.all(esens >= 0)


# ---------------------------------------------------------------------------
# to_state_dict / from_state_dict
# ---------------------------------------------------------------------------

class TestSerialization:
    """Tests for state serialisation roundtrip."""

    def test_roundtrip_basic(self, ecwf5: ECWFCore) -> None:
        sd = ecwf5.to_state_dict()
        restored = ECWFCore.from_state_dict(sd)

        assert restored.num_cognitive_dims == ecwf5.num_cognitive_dims
        assert restored.num_ethical_dims == ecwf5.num_ethical_dims
        assert restored.num_facets == ecwf5.num_facets
        np.testing.assert_array_almost_equal(restored.k, ecwf5.k)
        np.testing.assert_array_almost_equal(restored.m, ecwf5.m)
        np.testing.assert_array_almost_equal(restored.omega, ecwf5.omega)
        np.testing.assert_array_almost_equal(restored.phi, ecwf5.phi)
        np.testing.assert_array_almost_equal(
            restored.amplitude_factors, ecwf5.amplitude_factors
        )

    def test_roundtrip_json_serialisable(self, ecwf5: ECWFCore) -> None:
        sd = ecwf5.to_state_dict()
        # Must be JSON-serialisable
        json_str = json.dumps(sd)
        assert isinstance(json_str, str)

    def test_roundtrip_with_history(self, ecwf5: ECWFCore) -> None:
        # Generate some history
        x = np.ones((1, 5)) * 0.5
        e = np.ones((1, 5)) * 0.5
        for t in range(5):
            ecwf5.compute_ecwf(x, e, float(t))

        sd = ecwf5.to_state_dict(include_past_states=True)
        restored = ECWFCore.from_state_dict(sd)
        assert len(restored.past_states) == len(ecwf5.past_states)

    def test_roundtrip_produces_same_output(self) -> None:
        original = ECWFCore(num_cognitive_dims=8, num_ethical_dims=4, random_state=77)
        sd = original.to_state_dict()
        restored = ECWFCore.from_state_dict(sd)

        x = np.ones((1, 8)) * 0.3
        e = np.ones((1, 4)) * 0.6

        out_orig = original.compute_ecwf(x, e, t=1.5)
        out_rest = restored.compute_ecwf(x, e, t=1.5)
        np.testing.assert_array_almost_equal(out_orig, out_rest)

    def test_chunked_structure(self, ecwf5: ECWFCore) -> None:
        sd = ecwf5.to_state_dict()
        assert "metadata" in sd
        assert "parameters" in sd
        assert "num_cognitive_dims" in sd["metadata"]
        assert "k" in sd["parameters"]
