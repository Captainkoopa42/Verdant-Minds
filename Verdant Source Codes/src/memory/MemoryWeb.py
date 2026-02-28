import json
import math
import random
import networkx as nx
import numpy as np
import time
from typing import Dict, List, Tuple, Any, Optional

class MemoryWeb:
    """
    Associative memory system using a graph-based representation.
    Enables dynamic, associative linkage of concepts with stability
    and spread activation mechanisms.
    """
    
    def __init__(self):
        """Initialize the Memory Web."""
        self.graph = nx.Graph()
        self.memory_store = {}
        self.thought_clusters = {}
        self.activation_history = {}
        self.edge_policy = "default"
        
        # Memory performance metrics
        self.metrics = {
            "total_concepts": 0,
            "total_connections": 0,
            "avg_stability": 0.0,
            "created_timestamp": time.time(),
            "last_access_timestamp": time.time()
        }
    
    def add_concept(self, label: str, stability: float = 0.5, metadata: Dict[str, Any] = None):
        """Backward-compatible alias for ``add_thought``."""
        return self.add_thought(label=label, stability=stability, metadata=metadata)

    def get_concept(self, label: str) -> Optional[Dict[str, Any]]:
        """Backward-compatible alias returning concept details."""
        return self.get_concept_details(label)

    def add_thought(self, label: str, stability: float = 0.5, metadata: Dict[str, Any] = None):
        """
        Add a concept to memory with specified stability.
        
        Args:
            label: Concept label/name
            stability: Initial concept stability (0-1)
            metadata: Additional concept metadata
        """
        if label not in self.memory_store:
            # Create new concept entry
            self.memory_store[label] = {
                "stability": stability,
                "connections": [],
                "first_seen": time.time(),
                "last_accessed": time.time(),
                "access_count": 1
            }
            
            # Add metadata if provided
            if metadata:
                self.memory_store[label]["metadata"] = metadata
            
            # Add to graph
            self.graph.add_node(label, stability=stability)
            
            # Connect to most stable existing thoughts for initial integration
            if len(self.memory_store) > 1:
                sorted_thoughts = sorted(
                    self.memory_store.keys(),
                    key=lambda x: self.memory_store[x]["stability"],
                    reverse=True
                )[:3]  # Connect to top 3 stable thoughts
                
                for conn in sorted_thoughts:
                    self.connect_thoughts(label, conn, edge_policy=self.edge_policy)
            
            # Update metrics
            self.metrics["total_concepts"] += 1
            
        else:
            # Update existing thought
            self.memory_store[label]["last_accessed"] = time.time()
            self.memory_store[label]["access_count"] += 1
            
            # Slightly reinforce existing memory
            old_stability = self.memory_store[label]["stability"]
            new_stability = min(1.0, old_stability + 0.02)
            self.memory_store[label]["stability"] = new_stability
            
            # Update metadata if provided
            if metadata and "metadata" in self.memory_store[label]:
                self.memory_store[label]["metadata"].update(metadata)
            elif metadata:
                self.memory_store[label]["metadata"] = metadata
        
        # Update last access time
        self.metrics["last_access_timestamp"] = time.time()
    
    def _get_ethical_charge(self, concept_name: str) -> float:
        """Map concept names to ethical charge in [-1, 1] using principle lookup."""
        principles = {
            "non_maleficence": 0.9,
            "beneficence": 0.8,
            "autonomy": 0.8,
            "justice": 0.8,
            "transparency": 0.7,
        }

        name = str(concept_name or "").lower()
        for principle, weight in principles.items():
            principle_tokens = {principle, principle.replace("_", " ")}
            if any(token in name for token in principle_tokens):
                return max(-1.0, min(1.0, (float(weight) - 0.5) * 2.0))

        return 0.0

    def connect_thoughts(self, label1: str, label2: str, initial_weight: float = 0.5, edge_policy: str = "default") -> bool:
        """
        Links two thoughts together with a dynamic connection weight.
        
        Args:
            label1: First concept label
            label2: Second concept label
            initial_weight: Initial connection weight
        
        Returns:
            True if a new connection was created, False if updated
        """
        if label1 not in self.memory_store or label2 not in self.memory_store:
            return False
        
        # Calculate weight based on stability of both concepts
        weight = min(1.0, initial_weight * 
                     (self.memory_store[label1]["stability"] + 
                      self.memory_store[label2]["stability"]) / 2)
        
        delta_e = None
        if edge_policy == "pconnect":
            e_a = self._get_ethical_charge(label1)
            e_b = self._get_ethical_charge(label2)
            delta_e = abs(e_a - e_b)
            delta_E = 1.0 - weight
            p_eth = 0.6
            beta_E = 1.0
            prob = (1.0 - p_eth * delta_e) * math.exp(-beta_E * delta_E)
            prob = max(0.0, min(1.0, prob))
            if random.random() > prob:
                return False

        # Check if connection already exists
        new_connection = True
        
        # Update connections in memory store
        if label2 not in [conn[0] for conn in self.memory_store[label1]["connections"]]:
            self.memory_store[label1]["connections"].append((label2, weight))
        else:
            new_connection = False
            # Update existing connection
            for i, (conn, existing_weight) in enumerate(self.memory_store[label1]["connections"]):
                if conn == label2:
                    # Blend weights
                    new_weight = existing_weight * 0.7 + weight * 0.3
                    self.memory_store[label1]["connections"][i] = (conn, new_weight)
                    break
                    
        if label1 not in [conn[0] for conn in self.memory_store[label2]["connections"]]:
            self.memory_store[label2]["connections"].append((label1, weight))
        else:
            # Update existing connection
            for i, (conn, existing_weight) in enumerate(self.memory_store[label2]["connections"]):
                if conn == label1:
                    # Blend weights
                    new_weight = existing_weight * 0.7 + weight * 0.3
                    self.memory_store[label2]["connections"][i] = (conn, new_weight)
                    break
        
        # Add or update edge in graph
        if self.graph.has_edge(label1, label2):
            current_weight = self.graph.get_edge_data(label1, label2)["weight"]
            new_weight = current_weight * 0.7 + weight * 0.3
            self.graph[label1][label2]["weight"] = new_weight
            if delta_e is not None:
                self.graph[label1][label2]["delta_e"] = float(delta_e)
        else:
            edge_attrs = {"weight": weight}
            if delta_e is not None:
                edge_attrs["delta_e"] = float(delta_e)
            self.graph.add_edge(label1, label2, **edge_attrs)
            self.metrics["total_connections"] += 1
            
        # Update metrics
        self.metrics["last_access_timestamp"] = time.time()
        self._update_average_stability()
            
        return new_connection
    
    def retrieve_related_thoughts(self, label: str, depth: int = 2, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Gets related thoughts based on graph connectivity.
        
        Args:
            label: Concept label to start from
            depth: Search depth (hops in graph)
            limit: Maximum number of results
            
        Returns:
            List of (concept, relevance) tuples
        """
        if label not in self.memory_store:
            return []
        
        related_thoughts = []
        
        if label in self.graph:
            # Get subgraph of neighbors up to specified depth
            subgraph = nx.ego_graph(self.graph, label, radius=depth)
            
            # Convert to list of (thought, relevance) tuples
            for node in subgraph.nodes():
                if node != label:
                    # Calculate relevance based on path length and node stability
                    path_length = nx.shortest_path_length(subgraph, source=label, target=node)
                    stability = self.memory_store.get(node, {}).get("stability", 0.5)
                    
                    # Higher stability, shorter path = more relevant
                    relevance = stability / (path_length + 1)
                    related_thoughts.append((node, relevance))
        
        # Sort by relevance and limit results
        related_thoughts.sort(key=lambda x: x[1], reverse=True)
        
        # Update access time for retrieved concepts
        current_time = time.time()
        for concept, _ in related_thoughts[:limit]:
            if concept in self.memory_store:
                self.memory_store[concept]["last_accessed"] = current_time
                self.memory_store[concept]["access_count"] += 1
        
        self.metrics["last_access_timestamp"] = current_time
        
        return related_thoughts[:limit]
    
    def activate_concepts(self, seed_concepts: List[str], activation_strength: float = 0.7, 
                         spread_factor: float = 0.5) -> Dict[str, float]:
        """
        Perform spreading activation from seed concepts.
        
        Args:
            seed_concepts: Initial concepts to activate
            activation_strength: Initial activation strength
            spread_factor: How much activation spreads (0-1)
            
        Returns:
            Dictionary mapping concepts to activation levels
        """
        activations = {}
        visited = set()
        
        # Queue with (concept, activation_level, depth)
        queue = [(concept, activation_strength, 0) for concept in seed_concepts]
        
        # Arbitrary limits to prevent excessive spread
        max_depth = 3
        activation_threshold = 0.1
        
        while queue:
            concept, activation, depth = queue.pop(0)
            
            # Skip if already processed or below threshold
            if concept in visited or activation < activation_threshold:
                continue
                
            # Skip if depth too high
            if depth > max_depth:
                continue
                
            # Add to visited
            visited.add(concept)
            
            # Update activation (keep maximum if already activated)
            if concept in activations:
                activations[concept] = max(activations[concept], activation)
            else:
                activations[concept] = activation
                
            # Skip spread if concept not in memory
            if concept not in self.memory_store:
                continue
                
            # Get connections
            connections = self.memory_store[concept]["connections"]
            
            # Spread activation to neighbors
            for neighbor, weight in connections:
                # New activation = current * connection_weight * spread_factor
                new_activation = activation * weight * spread_factor
                
                # Add to queue
                queue.append((neighbor, new_activation, depth + 1))
        
        # Track activation history
        timestamp = time.time()
        for concept, activation in activations.items():
            if concept not in self.activation_history:
                self.activation_history[concept] = []
            
            self.activation_history[concept].append((timestamp, activation))
            
            # Keep history at reasonable size
            if len(self.activation_history[concept]) > 100:
                self.activation_history[concept] = self.activation_history[concept][-100:]
        
        return activations
    
    def cluster_thoughts(self, algorithm: str = 'louvain', min_stability: float = 0.3) -> Dict[str, List[str]]:
        """
        Cluster concepts in the memory web.
        
        Args:
            algorithm: Clustering algorithm ('louvain' or 'label_propagation')
            min_stability: Minimum concept stability to include
            
        Returns:
            Dictionary mapping cluster IDs to concept lists
        """
        # Filter nodes by stability
        stable_nodes = [
            node for node in self.graph.nodes() 
            if self.memory_store.get(node, {}).get("stability", 0) >= min_stability
        ]
        
        subgraph = self.graph.subgraph(stable_nodes)
        
        # Cannot cluster empty graph
        if not subgraph.nodes():
            return {}
        
        # Apply clustering algorithm
        if algorithm == 'louvain':
            try:
                from community import best_partition
                partition = best_partition(subgraph)
            except ImportError:
                # Fallback to networkx communities
                partition = self._fallback_clustering(subgraph)
        elif algorithm == 'label_propagation':
            partition = {}
            # Convert node labels to integers for algorithm
            node_map = {node: i for i, node in enumerate(subgraph.nodes())}
            reverse_map = {i: node for node, i in node_map.items()}
            
            # Create integer graph
            int_graph = nx.Graph()
            for u, v, data in subgraph.edges(data=True):
                int_graph.add_edge(node_map[u], node_map[v], weight=data.get('weight', 1.0))
                
            # Apply label propagation
            try:
                from networkx.algorithms.community import label_propagation_communities
                communities = label_propagation_communities(int_graph)
                
                # Convert back to original node labels
                for i, community in enumerate(communities):
                    for node_int in community:
                        partition[reverse_map[node_int]] = i
            except (ImportError, AttributeError):
                # Fallback to simpler algorithm
                partition = self._fallback_clustering(subgraph)
        else:
            # Default to fallback
            partition = self._fallback_clustering(subgraph)
        
        # Convert partition to clusters
        clusters = {}
        for node, cluster_id in partition.items():
            cluster_key = str(cluster_id)
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(node)
        
        # Update stored clusters
        self.thought_clusters = clusters
        
        return clusters
    
    def _fallback_clustering(self, graph):
        """Simple fallback clustering when community detection algorithms are unavailable."""
        # Use a basic connected components approach
        components = list(nx.connected_components(graph))
        partition = {}
        
        for i, component in enumerate(components):
            for node in component:
                partition[node] = i
                
        return partition
    
    def reinforce_memory(self, label: str, amount: float = 0.1) -> float:
        """
        Reinforce a specific memory concept.
        
        Args:
            label: Concept to reinforce
            amount: Reinforcement amount (0-1)
            
        Returns:
            New stability value
        """
        if label not in self.memory_store:
            return 0.0
            
        # Get current stability
        current_stability = self.memory_store[label]["stability"]
        
        # Apply reinforcement
        new_stability = min(1.0, current_stability + amount)
        self.memory_store[label]["stability"] = new_stability
        
        # Update node properties in graph
        if label in self.graph:
            self.graph.nodes[label]["stability"] = new_stability
            
        # Update metrics
        self.metrics["last_access_timestamp"] = time.time()
        self._update_average_stability()
        
        return new_stability
    
    def decay_memories(self, decay_factor: float = 0.01, time_threshold: float = 86400) -> int:
        """
        Apply decay to memories not accessed recently.
        
        Args:
            decay_factor: Amount to decay stability
            time_threshold: Time in seconds (default: 1 day)
            
        Returns:
            Number of concepts affected
        """
        current_time = time.time()
        affected_count = 0
        
        for concept, data in self.memory_store.items():
            last_accessed = data.get("last_accessed", 0)
            
            # Apply decay to concepts not accessed recently
            if current_time - last_accessed > time_threshold:
                old_stability = data["stability"]
                new_stability = max(0.1, old_stability - decay_factor)
                
                # Update stability
                data["stability"] = new_stability
                
                # Update node properties in graph
                if concept in self.graph:
                    self.graph.nodes[concept]["stability"] = new_stability
                    
                affected_count += 1
        
        # Update metrics
        if affected_count > 0:
            self._update_average_stability()
            
        return affected_count
    
    def get_concept_details(self, label: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a concept.
        
        Args:
            label: Concept label
            
        Returns:
            Dictionary with concept details or None if not found
        """
        if label not in self.memory_store:
            return None
            
        # Create copy of memory data
        concept_data = dict(self.memory_store[label])
        
        # Add graph-specific metrics
        if label in self.graph:
            # Add degree (number of connections)
            concept_data["degree"] = self.graph.degree[label]
            
            # Add centrality score
            try:
                centralities = nx.closeness_centrality(self.graph)
                concept_data["centrality"] = centralities.get(label, 0)
            except:
                concept_data["centrality"] = 0
            
        # Add cluster membership
        for cluster_id, members in self.thought_clusters.items():
            if label in members:
                concept_data["cluster"] = cluster_id
                break
                
        return concept_data
    
    def to_state_dict(self) -> Dict[str, Any]:
        """Serialize MemoryWeb state to a JSON-compatible dictionary."""
        serial_memory_store = {}
        for label, data in self.memory_store.items():
            entry = dict(data)
            connections = entry.get("connections", [])
            entry["connections"] = [
                [str(conn_label), float(weight)] for conn_label, weight in connections
            ]
            serial_memory_store[str(label)] = entry

        edge_list = []
        for source, target, attrs in self.graph.edges(data=True):
            edge_list.append({
                "source": str(source),
                "target": str(target),
                "weight": float(attrs.get("weight", 0.0)),
                "delta_e": attrs.get("delta_e"),
            })

        node_stability = {
            str(node): float(attrs.get("stability", 0.0))
            for node, attrs in self.graph.nodes(data=True)
        }

        return {
            "memory_store": serial_memory_store,
            "metrics": dict(self.metrics),
            "thought_clusters": dict(self.thought_clusters),
            "activation_history": dict(self.activation_history),
            "graph": {
                "nodes": node_stability,
                "edges": edge_list,
            },
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Load MemoryWeb state from a dictionary produced by ``to_state_dict``."""
        state = state or {}
        self.graph = nx.Graph()

        loaded_store = state.get("memory_store", {}) or {}
        self.memory_store = {}
        for label, data in loaded_store.items():
            entry = dict(data)
            connections = entry.get("connections", [])
            entry["connections"] = [
                (str(conn_label), float(weight)) for conn_label, weight in connections
            ]
            self.memory_store[str(label)] = entry

        graph_state = state.get("graph", {}) or {}
        nodes = graph_state.get("nodes", {}) or {}
        for label, data in self.memory_store.items():
            stability = float(data.get("stability", nodes.get(label, 0.0)))
            self.graph.add_node(label, stability=stability)

        for edge in graph_state.get("edges", []) or []:
            source = str(edge.get("source"))
            target = str(edge.get("target"))
            if source in self.memory_store and target in self.memory_store and source != target:
                edge_attrs = {"weight": float(edge.get("weight", 0.0))}
                if edge.get("delta_e") is not None:
                    edge_attrs["delta_e"] = float(edge.get("delta_e"))
                self.graph.add_edge(source, target, **edge_attrs)

        self.thought_clusters = dict(state.get("thought_clusters", {}) or {})
        self.activation_history = dict(state.get("activation_history", {}) or {})
        self.metrics = dict(state.get("metrics", {}) or {})

        # Keep derived metrics coherent after load
        self.metrics.setdefault("created_timestamp", time.time())
        self.metrics["last_access_timestamp"] = self.metrics.get("last_access_timestamp", time.time())
        self.metrics["total_concepts"] = len(self.memory_store)
        self.metrics["total_connections"] = self.graph.number_of_edges()
        self._update_average_stability()

    def save_state(self, path: str) -> None:
        """Persist MemoryWeb state to disk as JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_state_dict(), f, indent=2)

    def load_state(self, path: str) -> None:
        """Load MemoryWeb state from disk."""
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.from_state_dict(state)

    def _update_average_stability(self):
        """Update average stability metric."""
        if not self.memory_store:
            self.metrics["avg_stability"] = 0.0
            return
            
        total_stability = sum(data["stability"] for data in self.memory_store.values())
        self.metrics["avg_stability"] = total_stability / len(self.memory_store)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get memory web performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        # Update metrics
        self.metrics["total_concepts"] = len(self.memory_store)
        self.metrics["total_connections"] = self.graph.number_of_edges()
        self._update_average_stability()
        
        # Add additional metrics for more comprehensive reporting
        active_concepts = sum(1 for data in self.memory_store.values() 
                             if time.time() - data.get("last_accessed", 0) < 86400)  # Active in last day
        
        # Calculate network metrics if graph is non-empty
        network_metrics = {}
        if self.graph.number_of_nodes() > 0:
            try:
                # Average degree
                degrees = [d for _, d in self.graph.degree()]
                avg_degree = sum(degrees) / max(1, len(degrees))
                network_metrics["avg_degree"] = avg_degree
                
                # Graph density
                network_metrics["graph_density"] = nx.density(self.graph)
                
                # Number of clusters
                network_metrics["cluster_count"] = len(self.thought_clusters)
                
                # Calculate largest cluster size
                if self.thought_clusters:
                    largest_cluster = max(self.thought_clusters.values(), key=len)
                    network_metrics["largest_cluster_size"] = len(largest_cluster)
            except Exception as e:
                # Fallback if network analysis fails
                network_metrics["error"] = str(e)
        
        # Add activation metrics
        activation_metrics = {
            "total_activations": sum(len(history) for history in self.activation_history.values()),
            "active_concepts_count": active_concepts,
            "active_concepts_ratio": active_concepts / max(1, len(self.memory_store))
        }
        
        # Time-based metrics
        time_metrics = {
            "age_seconds": time.time() - self.metrics["created_timestamp"],
            "time_since_last_access": time.time() - self.metrics["last_access_timestamp"]
        }
        
        # Combine all metrics
        return {
            **self.metrics,
            **network_metrics,
            **activation_metrics,
            **time_metrics
        }