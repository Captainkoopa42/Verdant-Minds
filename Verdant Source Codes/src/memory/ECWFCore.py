import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

class ECWFCore:
    """
    Ethical Cognitive Wave Function (ECWF) implementation.
    
    Represents cognitive and ethical states as quantum-inspired wave functions,
    enabling probabilistic reasoning, uncertainty representation, and
    dynamic evolution of mental states.
    """
    
    def __init__(self, num_cognitive_dims: int = 5, num_ethical_dims: int = 5,
                 num_facets: int = 7, feedback_factor: float = 0.05,
                 adaptive_rate: float = 0.1, random_state: Optional[int] = None):
        """
        Initialize the ECWF core.
        
        Args:
            num_cognitive_dims: Number of cognitive dimensions
            num_ethical_dims: Number of ethical dimensions
            num_facets: Number of wave facets (similar to basis states)
            feedback_factor: Feedback influence strength
            adaptive_rate: Rate of parameter adaptation
            random_state: Random seed for reproducibility
        """
        self.num_cognitive_dims = num_cognitive_dims
        self.num_ethical_dims = num_ethical_dims
        self.num_facets = num_facets
        self.feedback_factor = feedback_factor
        self.adaptive_rate = adaptive_rate
        
        # Set random state for reproducibility
        self.random_state = random_state
        self.rng = np.random.RandomState(random_state)
        
        # Initialize wave parameters
        self._initialize_parameters()
        
        # Track wave state history
        self.past_states = []
        
        # Name cognitive and ethical dimensions
        self.cognitive_dim_names = [f"C{i+1}" for i in range(num_cognitive_dims)]
        self.ethical_dim_names = [f"E{i+1}" for i in range(num_ethical_dims)]
        
        # Dimension meanings (can be set later)
        self.dimension_meanings = {}
    
    def create_wave_function(self, x_input: Optional[np.ndarray] = None,
                             e_input: Optional[np.ndarray] = None,
                             t: float = 0.0) -> np.ndarray:
        """Backward-compatible wrapper that returns an ECWF state tensor."""
        if x_input is None:
            x_input = np.zeros((1, self.num_cognitive_dims), dtype=float)
        if e_input is None:
            e_input = np.zeros((1, self.num_ethical_dims), dtype=float)
        return self.compute_ecwf(x_input, e_input, t)

    def _initialize_parameters(self):
        """Initialize wave function parameters."""
        # Cognitive wave numbers (k_i)
        self.k = self.rng.uniform(-1, 1, size=(self.num_facets, self.num_cognitive_dims))
        
        # Ethical wave numbers (m_i)
        self.m = self.rng.uniform(-1, 1, size=(self.num_facets, self.num_ethical_dims))
        
        # Angular frequencies (omega_i)
        self.omega = self.rng.uniform(0, 2 * np.pi, size=self.num_facets)
        
        # Phase shifts (phi_i)
        self.phi = self.rng.uniform(0, 2 * np.pi, size=self.num_facets)
        
        # Amplitude modulation factors
        self.amplitude_factors = self.rng.uniform(0.8, 1.2, size=self.num_facets)
    
    def compute_ecwf(self, x_input: np.ndarray, e_input: np.ndarray, t: float) -> np.ndarray:
        """
        Compute the Ethical Cognitive Wave Function.
        
        Args:
            x_input: Cognitive input tensor of shape (..., num_cognitive_dims)
            e_input: Ethical input tensor of shape (..., num_ethical_dims)
            t: Time parameter
            
        Returns:
            Complex wave function output of shape (...)
        """
        # Initialize result with zeros (complex)
        result = np.zeros(x_input.shape[:-1], dtype=complex)
        
        # Compute contribution from each facet
        for i in range(self.num_facets):
            # Calculate amplitude
            amplitude = self._calculate_amplitude(x_input, e_input, t, i)
            
            # Calculate phase
            # Cognitive contribution to phase
            cognitive_phase = np.tensordot(x_input, self.k[i], axes=([-1], [-1]))
            
            # Ethical contribution to phase
            ethical_phase = np.tensordot(e_input, self.m[i], axes=([-1], [-1]))
            
            # Complete phase calculation
            phase = (2 * np.pi * (cognitive_phase + ethical_phase) - 
                    self.omega[i] * t + self.phi[i])
            
            # Add contribution to result using Euler's formula
            result += amplitude * np.exp(1j * phase)
        
        # Apply memory effect from past states
        if self.past_states:
            # Use weighted average of past states with exponential decay
            weights = np.exp(-0.1 * np.arange(len(self.past_states)))
            weights = weights / weights.sum()  # Normalize weights
            
            memory_effect = np.average(self.past_states, axis=0, weights=weights)
            result += 0.1 * memory_effect  # 10% memory influence
        
        # Store current state for future memory effects
        self.past_states.append(result)
        if len(self.past_states) > 20:  # Limit history length
            self.past_states.pop(0)
        
        return result
    
    def _calculate_amplitude(self, x: np.ndarray, e: np.ndarray, t: float, i: int) -> np.ndarray:
        """
        Calculate amplitude for facet i.
        
        Args:
            x: Cognitive input
            e: Ethical input
            t: Time parameter
            i: Facet index
            
        Returns:
            Amplitude for this facet
        """
        # Calculate base terms
        cognitive_term = np.sum(x**2, axis=-1) / self.num_cognitive_dims
        ethical_term = np.sum(e**2, axis=-1) / self.num_ethical_dims
        
        # Calculate interaction term (dot product between cognitive and ethical inputs)
        min_dims = min(self.num_cognitive_dims, self.num_ethical_dims)
        
        # Use the minimum dimensions for interaction calculation
        x_min = x[..., :min_dims]
        e_min = e[..., :min_dims]
        
        # Compute dot product along last dimension
        interaction_term = np.sum(x_min * e_min, axis=-1)
        
        # Apply feedback and adaptation effects
        feedback_term = self.feedback_factor * np.sin(interaction_term + t)
        adaptive_term = self.adaptive_rate * np.tanh(cognitive_term - ethical_term)
        
        # Compute final amplitude with Gaussian-like envelope
        amplitude = (
            self.amplitude_factors[i] * 
            np.exp(-(cognitive_term + 2 * ethical_term) / (2 * (i + 1))) * 
            (1 + 0.5 * np.sin(3 * t) + feedback_term + adaptive_term)
        )
        
        # Ensure amplitude is positive and non-zero
        return np.maximum(amplitude, 1e-10)
    
    def calculate_entropy(self, psi: np.ndarray) -> float:
        """
        Calculate the entropy of the wave function.
        
        Args:
            psi: Wave function state
            
        Returns:
            Entropy value (higher means more uncertainty)
        """
        # Calculate probabilities from wave function
        p = np.abs(psi)**2
        p_sum = np.sum(p)
        
        # Avoid division by zero
        if p_sum == 0:
            return 0
        
        # Normalize
        p = p / p_sum
        
        # Calculate entropy (-sum(p*log(p)))
        # Add small constant to avoid log(0)
        entropy = -np.sum(p * np.log2(p + 1e-10))
        
        return entropy
    
    def compute_sensitivities(self, x_input: np.ndarray, e_input: np.ndarray, 
                             t: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute sensitivity of the wave function to input dimensions.
        
        Args:
            x_input: Cognitive input
            e_input: Ethical input
            t: Time parameter
            
        Returns:
            Tuple of (cognitive_sensitivities, ethical_sensitivities)
        """
        # Compute baseline output
        baseline = self.compute_ecwf(x_input, e_input, t)
        
        # Initialize sensitivity arrays
        cognitive_sens = np.zeros_like(x_input)
        ethical_sens = np.zeros_like(e_input)
        
        # Small perturbation amount
        delta = 1e-5
        
        # Compute sensitivities for cognitive dimensions
        for i in range(self.num_cognitive_dims):
            # Create perturbed input
            x_perturbed = x_input.copy()
            x_perturbed[..., i] += delta
            
            # Compute output with perturbation
            perturbed = self.compute_ecwf(x_perturbed, e_input, t)
            
            # Calculate sensitivity as magnitude of difference
            cognitive_sens[..., i] = np.abs((perturbed - baseline) / delta)
        
        # Compute sensitivities for ethical dimensions
        for i in range(self.num_ethical_dims):
            # Create perturbed input
            e_perturbed = e_input.copy()
            e_perturbed[..., i] += delta
            
            # Compute output with perturbation
            perturbed = self.compute_ecwf(x_input, e_perturbed, t)
            
            # Calculate sensitivity as magnitude of difference
            ethical_sens[..., i] = np.abs((perturbed - baseline) / delta)
        
        # Normalize sensitivities to [0, 1] range
        cognitive_max = np.max(cognitive_sens)
        ethical_max = np.max(ethical_sens)
        
        if cognitive_max > 0:
            cognitive_sens /= cognitive_max
        
        if ethical_max > 0:
            ethical_sens /= ethical_max
        
        return cognitive_sens, ethical_sens
    
    def update_parameters(self, cognitive_influence: np.ndarray, 
                         ethical_influence: np.ndarray, factor: float = 0.1):
        """
        Update wave function parameters based on external influence.
        
        Args:
            cognitive_influence: Influence vector for cognitive dimensions
            ethical_influence: Influence vector for ethical dimensions
            factor: Scaling factor for parameter updates
        """
        # Normalize influence vectors
        if np.max(np.abs(cognitive_influence)) > 0:
            cognitive_influence = cognitive_influence / np.max(np.abs(cognitive_influence))
        
        if np.max(np.abs(ethical_influence)) > 0:
            ethical_influence = ethical_influence / np.max(np.abs(ethical_influence))
        
        # Apply small updates to parameters
        for i in range(self.num_facets):
            # Update cognitive wave numbers
            self.k[i] += factor * cognitive_influence * self.rng.normal(0, 0.1, size=self.k[i].shape)
            
            # Update ethical wave numbers
            self.m[i] += factor * ethical_influence * self.rng.normal(0, 0.1, size=self.m[i].shape)
            
            # Update frequency and phase
            avg_influence = (np.sum(cognitive_influence) + np.sum(ethical_influence)) / 2
            self.omega[i] += factor * avg_influence * self.rng.normal(0, 0.1)
            self.phi[i] += factor * avg_influence * self.rng.normal(0, 0.1)
    
    def set_dimension_meanings(self, cognitive_meanings: Dict[int, str] = None,
                              ethical_meanings: Dict[int, str] = None):
        """
        Set semantic meanings for dimensions.
        
        Args:
            cognitive_meanings: Dictionary mapping cognitive dimension indices to meanings
            ethical_meanings: Dictionary mapping ethical dimension indices to meanings
        """
        # Initialize dimension meanings
        self.dimension_meanings = {}
        
        # Set cognitive dimension meanings
        if cognitive_meanings:
            for idx, meaning in cognitive_meanings.items():
                if 0 <= idx < self.num_cognitive_dims:
                    dim_name = f"C{idx+1}"
                    self.dimension_meanings[dim_name] = meaning
        
        # Set ethical dimension meanings
        if ethical_meanings:
            for idx, meaning in ethical_meanings.items():
                if 0 <= idx < self.num_ethical_dims:
                    dim_name = f"E{idx+1}"
                    self.dimension_meanings[dim_name] = meaning
        
        return self.dimension_meanings
    
    def to_state_dict(self, include_past_states: bool = False) -> Dict[str, Any]:
        """Serialize ECWFCore parameters into a JSON-compatible dictionary."""
        state = {
            "num_cognitive_dims": self.num_cognitive_dims,
            "num_ethical_dims": self.num_ethical_dims,
            "num_facets": self.num_facets,
            "feedback_factor": self.feedback_factor,
            "adaptive_rate": self.adaptive_rate,
            "random_state": self.random_state,
            "k": self.k.tolist(),
            "m": self.m.tolist(),
            "omega": self.omega.tolist(),
            "phi": self.phi.tolist(),
            "amplitude_factors": self.amplitude_factors.tolist(),
            "dimension_meanings": dict(self.dimension_meanings),
        }

        if include_past_states:
            serialized_states = []
            for state_arr in self.past_states:
                arr = np.asarray(state_arr)
                serialized_states.append({
                    "real": np.real(arr).tolist(),
                    "imag": np.imag(arr).tolist(),
                })
            state["past_states"] = serialized_states

        return state

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Load ECWFCore parameters from a dictionary produced by ``to_state_dict``."""
        state = state or {}
        self.num_cognitive_dims = int(state.get("num_cognitive_dims", self.num_cognitive_dims))
        self.num_ethical_dims = int(state.get("num_ethical_dims", self.num_ethical_dims))
        self.num_facets = int(state.get("num_facets", self.num_facets))
        self.feedback_factor = float(state.get("feedback_factor", self.feedback_factor))
        self.adaptive_rate = float(state.get("adaptive_rate", self.adaptive_rate))
        self.random_state = state.get("random_state", self.random_state)
        self.rng = np.random.RandomState(self.random_state)

        self.k = np.array(state.get("k", self.k), dtype=float)
        self.m = np.array(state.get("m", self.m), dtype=float)
        self.omega = np.array(state.get("omega", self.omega), dtype=float)
        self.phi = np.array(state.get("phi", self.phi), dtype=float)
        self.amplitude_factors = np.array(state.get("amplitude_factors", self.amplitude_factors), dtype=float)

        self.cognitive_dim_names = [f"C{i+1}" for i in range(self.num_cognitive_dims)]
        self.ethical_dim_names = [f"E{i+1}" for i in range(self.num_ethical_dims)]
        self.dimension_meanings = dict(state.get("dimension_meanings", self.dimension_meanings) or {})

        loaded_states = []
        for past in state.get("past_states", []) or []:
            real = np.array(past.get("real", []), dtype=float)
            imag = np.array(past.get("imag", []), dtype=float)
            loaded_states.append(real + 1j * imag)
        self.past_states = loaded_states

    def save_state(self, path: str, include_past_states: bool = False) -> None:
        """Persist ECWFCore state to disk."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_state_dict(include_past_states=include_past_states), f, indent=2)

    def load_state(self, path: str) -> None:
        """Load ECWFCore state from disk."""
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.from_state_dict(state)

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current ECWF state.
        
        Returns:
            Dictionary of state information
        """
        return {
            "num_cognitive_dims": self.num_cognitive_dims,
            "num_ethical_dims": self.num_ethical_dims,
            "num_facets": self.num_facets,
            "adaptive_rate": self.adaptive_rate,
            "feedback_factor": self.feedback_factor,
            "dimension_meanings": self.dimension_meanings,
            "past_states_count": len(self.past_states)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the ECWF.
        
        Returns:
            Dictionary of metrics
        """
        # Calculate average entropy from recent states
        recent_entropies = [self.calculate_entropy(state) for state in self.past_states[-5:]] if self.past_states else [0]
        avg_entropy = sum(recent_entropies) / len(recent_entropies)
        
        return {
            "average_entropy": avg_entropy,
            "parameter_complexity": {
                "k_complexity": np.mean(np.std(self.k, axis=0)),
                "m_complexity": np.mean(np.std(self.m, axis=0)),
                "phase_diversity": np.std(self.phi)
            },
            "dimension_count": self.num_cognitive_dims + self.num_ethical_dims,
            "memory_depth": len(self.past_states)
        }